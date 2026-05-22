const express = require("express");
const { spawn } = require("child_process");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

const app = express();
app.use(express.json({ limit: '1mb' }));

const tasks = new Map();

// ── Readiness marker (written by entrypoint.sh after skill sync) ─────
const READINESS_MARKER = "/tmp/sandbox-state/skills-synced";

// ── X-GH-Token middleware state ──────────────────────────────────────
// `ghAuthenticated` flips true once we've successfully run
// `gh auth login --with-token` (either from env on startup or from the
// first request carrying an X-GH-Token header). `ghAuthInFlight` is a
// promise guard so concurrent first-requests don't race the login.
let ghAuthenticated = false;
let ghAuthInFlight = null;

// SINGLE_TASK_MODE: When set, server exits after the last task completes.
// A grace-period timer allows sequential pipeline tasks to cancel the shutdown.
const SINGLE_TASK_MODE = process.env.SINGLE_TASK_MODE === "true";
let activeTasks = 0;
let shutdownTimer = null;

// Track premium request consumption (each Copilot CLI invocation = 1 premium request)
let premiumRequests = 0;

// GitHub auth: accept GH_TOKEN or GITHUB_TOKEN (same as official Docker sandbox)
// When GH_TOKEN env var is set, gh CLI uses it directly — no need to run `gh auth login`.
// In session-pool deployments the backend sends X-GH-Token on the first request
// instead (see middleware below); env-var path is kept for local docker-compose.
const ghToken = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
if (ghToken) {
  console.log("GitHub CLI will authenticate via GH_TOKEN environment variable");
  ghAuthenticated = true; // entrypoint.sh already ran `gh auth login`
}

/**
 * Authenticate `gh` CLI with a token, idempotently.
 * Returns a promise that resolves once auth completes (success or failure).
 * Concurrent callers share the same in-flight promise.
 * The token value is never logged and is not retained after this call returns.
 */
function authenticateGh(token) {
  if (ghAuthenticated) return Promise.resolve(true);
  if (ghAuthInFlight) return ghAuthInFlight;
  ghAuthInFlight = new Promise((resolve) => {
    const proc = spawn("gh", ["auth", "login", "--with-token"], {
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env,
    });
    let stderr = "";
    proc.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    proc.on("error", (err) => {
      console.error(`[gh-auth] spawn failed: ${err.message}`);
      ghAuthInFlight = null;
      resolve(false);
    });
    proc.on("close", (code) => {
      if (code === 0) {
        ghAuthenticated = true;
        console.log("[gh-auth] gh CLI authenticated via X-GH-Token header");
        resolve(true);
      } else {
        // Surface stderr but NEVER the token. Continue serving — the
        // request itself may not need `gh`.
        console.error(`[gh-auth] gh auth login exited ${code}: ${stderr.trim()}`);
        ghAuthInFlight = null;
        resolve(false);
      }
    });
    try {
      proc.stdin.write(token);
      proc.stdin.end();
    } catch (err) {
      console.error(`[gh-auth] failed to pipe token: ${err.message}`);
      ghAuthInFlight = null;
      resolve(false);
    }
  });
  return ghAuthInFlight;
}

// Request middleware: opportunistic `gh` auth from X-GH-Token header.
// Runs before any route handler. Non-blocking on success path (auth
// happens once; subsequent requests short-circuit). On the very first
// request with a token we await the login so downstream Copilot CLI
// invocations see an authenticated gh state.
app.use(async (req, _res, next) => {
  const token = req.get("X-GH-Token");
  if (token && !ghAuthenticated) {
    try {
      await authenticateGh(token);
    } catch (err) {
      // Defensive — authenticateGh already swallows errors.
      console.error(`[gh-auth] unexpected error: ${err.message}`);
    }
  }
  // Strip the header from the in-process request object so it can't leak
  // into spawned child processes or downstream logging.
  if (token) {
    delete req.headers["x-gh-token"];
  }
  next();
});

// Default model from env (overridable per-task)
const DEFAULT_MODEL = process.env.COPILOT_MODEL || "claude-opus-4.6";

// Liveness probe: cheap, always 200 once the Node process is listening.
// The Container Apps session pool calls this on a 10s period.
app.get("/health", (_req, res) => {
  const activeTasks = [...tasks.values()].filter((t) => t.exitCode() === null).length;
  res.json({
    status: "ready",
    activeTasks,
    premiumRequests,
    model: DEFAULT_MODEL,
    ghAuth: ghAuthenticated,
  });
});

// Startup/readiness probe: returns 200 only once skills sync completed
// (marker file written by entrypoint.sh). Returns 503 otherwise so the
// session pool keeps polling instead of routing traffic. Pool config:
// period 5s, 30 attempts → ~150s max wait.
app.get("/ready", (_req, res) => {
  if (fs.existsSync(READINESS_MARKER)) {
    res.json({ ready: true });
  } else {
    res.status(503).json({ ready: false, reason: "skill sync not complete" });
  }
});

app.post("/tasks", (req, res) => {
  const {
    prompt,
    command,
    args = [],
    model = DEFAULT_MODEL,
    workDir = "/workspace",
    ghToken: perTaskToken,
    continueSession = false,
    agent,
    autopilot = false,
  } = req.body;

  // Two modes: a) raw command, b) Copilot CLI prompt
  let spawnCmd, spawnArgs;
  if (prompt) {
    // Run Copilot CLI in non-interactive mode with the given prompt
    spawnCmd = "copilot";
    spawnArgs = ["-p", prompt, "--model", model, "--autopilot", "--yolo", "--experimental"];
    // Continue from previous session to maintain context across pipeline stages
    if (continueSession) {
      spawnArgs.push("--continue");
    }
    if (agent) {
      spawnArgs.push("--agent", agent);
    }
    // Premium request multiplier depends on model tier
    // Claude Opus = 3 premium, everything else = 1
    const premiumMultiplier = /opus/i.test(model) ? 3 : 1;
    premiumRequests += premiumMultiplier;
  } else if (command) {
    spawnCmd = command;
    spawnArgs = args;
  } else {
    return res.status(400).json({ error: "prompt or command is required" });
  }

  // Use per-task token if provided, fall back to container-level env
  const effectiveToken = perTaskToken || ghToken;
  if (prompt && !effectiveToken) {
    return res.status(400).json({ error: "GitHub token required — set it in Settings → Connections" });
  }

  const id = crypto.randomUUID();
  const output = [];
  let exitCode = null;

  // Ensure workDir exists
  if (!fs.existsSync(workDir)) {
    fs.mkdirSync(workDir, { recursive: true });
  }

  // Use shell for raw commands that need PATH/pipes/&&.
  // For Copilot CLI prompts, avoid shell to preserve multi-word prompt as single arg.
  const useShell = !prompt;
  let proc;
  try {
    proc = spawn(spawnCmd, spawnArgs, {
      cwd: workDir,
      shell: useShell,
      env: {
        ...process.env,
        FORCE_COLOR: "0",
        COPILOT_MODEL: model,
        ...(effectiveToken ? { GH_TOKEN: effectiveToken } : {}),
      },
    });
  } catch (err) {
    return res.status(500).json({ error: "Failed to spawn process", details: String(err) });
  }

  proc.on("error", (err) => {
    output.push({ type: "stderr", data: `Spawn error: ${err.message}`, ts: Date.now() });
    exitCode = 1;
    output.push({ type: "exit", code: 1, ts: Date.now() });
  });

  proc.stdout.on("data", (chunk) => {
    output.push({ type: "stdout", data: chunk.toString(), ts: Date.now() });
  });

  proc.stderr.on("data", (chunk) => {
    output.push({ type: "stderr", data: chunk.toString(), ts: Date.now() });
  });

  proc.on("close", (code) => {
    exitCode = code;
    output.push({ type: "exit", code, ts: Date.now() });
    activeTasks--;
    if (SINGLE_TASK_MODE && activeTasks <= 0) {
      console.log("SINGLE_TASK_MODE: last task completed, shutting down in 30s...");
      shutdownTimer = setTimeout(() => process.exit(0), 30000);
    }
  });

  // Cancel pending shutdown — a new task arrived before the grace period expired
  if (shutdownTimer) {
    clearTimeout(shutdownTimer);
    shutdownTimer = null;
    console.log("SINGLE_TASK_MODE: shutdown cancelled — new task arrived");
  }
  activeTasks++;
  tasks.set(id, { proc, output, exitCode: () => exitCode, model, workDir });

  res.status(201).json({ id, model, workDir });
});

app.get("/tasks/:id/stream", (req, res) => {
  const task = tasks.get(req.params.id);
  if (!task) {
    return res.status(404).json({ error: "task not found" });
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  let cursor = 0;
  let keepAliveCounter = 0;

  const interval = setInterval(() => {
    if (cursor < task.output.length) {
      while (cursor < task.output.length) {
        const entry = task.output[cursor++];
        res.write(`data: ${JSON.stringify(entry)}\n\n`);

        if (entry.type === "exit") {
          clearInterval(interval);
          res.end();
          return;
        }
      }
      keepAliveCounter = 0;
    } else {
      // Send SSE comment as keepalive every ~15s to prevent Azure proxy idle timeouts
      keepAliveCounter++;
      if (keepAliveCounter >= 150) {
        res.write(`: keepalive\n\n`);
        keepAliveCounter = 0;
      }
    }
  }, 100);

  req.on("close", () => clearInterval(interval));
});

// Get task status (for polling)
app.get("/tasks/:id/status", (req, res) => {
  const task = tasks.get(req.params.id);
  if (!task) {
    return res.status(404).json({ error: "task not found" });
  }
  const code = task.exitCode();
  res.json({
    id: req.params.id,
    done: code !== null,
    exitCode: code,
    outputLines: task.output.length,
    // Return last 20 output lines for quick preview
    recentOutput: task.output.slice(-20),
  });
});

// Kill a running task (cleanup on timeout)
app.delete("/tasks/:id", (req, res) => {
  const task = tasks.get(req.params.id);
  if (!task) {
    return res.status(404).json({ error: "task not found" });
  }
  const code = task.exitCode();
  if (code !== null) {
    return res.json({ id: req.params.id, killed: false, alreadyDone: true, exitCode: code });
  }
  try {
    task.proc.kill("SIGTERM");
    setTimeout(() => {
      try { task.proc.kill("SIGKILL"); } catch (_) { /* already dead */ }
    }, 5000);
    console.log(`[sandbox] Killed task ${req.params.id} (SIGTERM)`);
    res.json({ id: req.params.id, killed: true });
  } catch (err) {
    res.status(500).json({ error: `Failed to kill: ${err.message}` });
  }
});

// List active/completed tasks
app.get("/tasks", (_req, res) => {
  const list = [...tasks.entries()].map(([id, t]) => ({
    id,
    exitCode: t.exitCode(),
    model: t.model,
    outputLines: t.output.length,
  }));
  res.json({ tasks: list });
});

// Send stdin input to a running task (for auto-answering CLI questions)
app.post("/tasks/:id/input", express.json(), (req, res) => {
  const task = tasks.get(req.params.id);
  if (!task) {
    return res.status(404).json({ error: "task not found" });
  }
  if (task.exitCode() !== null) {
    return res.status(409).json({ error: "task already finished" });
  }
  const input = req.body.input || "";
  try {
    task.proc.stdin.write(input + "\n");
    task.output.push({ type: "stdin", data: input, ts: Date.now() });
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: "failed to write stdin: " + err.message });
  }
});

// List and download workspace files (for screenshot retrieval)
app.get("/files", (req, res) => {
  const pattern = req.query.glob || "*.png";
  const baseDir = req.query.dir || "/workspace";
  const safeDir = path.resolve(baseDir);
  if (!safeDir.startsWith("/workspace")) {
    return res.status(403).json({ error: "Access denied" });
  }
  try {
    const result = execSync(
      `find ${safeDir} -maxdepth 5 -name '${pattern.replace(/'/g, "")}' -type f 2>/dev/null || true`,
      { encoding: "utf-8" }
    );
    const files = result.trim().split("\n").filter(Boolean);
    res.json({ files });
  } catch {
    res.json({ files: [] });
  }
});

app.get("/files/*", (req, res) => {
  const filePath = path.join("/workspace", req.params[0]);
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith("/workspace")) {
    return res.status(403).json({ error: "Access denied" });
  }
  if (!fs.existsSync(resolved)) {
    return res.status(404).json({ error: "File not found" });
  }
  const data = fs.readFileSync(resolved);
  // Return raw binary when ?raw=true
  if (req.query.raw === "true") {
    const ext = path.extname(resolved).toLowerCase();
    const mimeTypes = { ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".zip": "application/zip" };
    res.setHeader("Content-Type", mimeTypes[ext] || "application/octet-stream");
    return res.send(data);
  }
  res.json({ name: path.basename(resolved), data: data.toString("base64") });
});

// Download workspace as tar.gz archive
app.get("/workspace/archive", (req, res) => {
  const baseDir = req.query.dir || "/workspace";
  const safeDir = path.resolve(baseDir);
  if (!safeDir.startsWith("/workspace")) {
    return res.status(403).json({ error: "Access denied" });
  }
  try {
    const archivePath = "/tmp/workspace-archive.tar.gz";
    execSync(
      `cd ${safeDir} && tar czf ${archivePath} --exclude='node_modules' --exclude='.git' --exclude='.cache' .`,
      { timeout: 30000 }
    );
    res.setHeader("Content-Type", "application/gzip");
    res.setHeader("Content-Disposition", "attachment; filename=workspace.tar.gz");
    const stream = fs.createReadStream(archivePath);
    stream.pipe(res);
    stream.on("end", () => {
      try { fs.unlinkSync(archivePath); } catch {}
    });
  } catch (err) {
    res.status(500).json({ error: "Failed to create archive", details: String(err) });
  }
});

const port = process.env.PORT || 3000;

// ── Skills hot-reload endpoints ──────────────────────────────────────
// Called by the backend when skills are activated/deactivated so the
// sandbox picks them up without a container restart.

app.post("/skills/sync", (_req, res) => {
  const { execSync: execSyncSkills } = require("child_process");
  try {
    const output = execSyncSkills("/app/sync-skills.sh", {
      encoding: "utf-8",
      timeout: 60000,
      env: process.env,
    });
    // Last line of sync-skills.sh is the count
    const lines = output.trim().split("\n");
    const synced = parseInt(lines[lines.length - 1], 10) || 0;
    console.log(`[skills] Synced ${synced} skill(s) from blob storage`);

    // List available skill directories
    let skills = [];
    const skillsDir = "/home/agent/.copilot/skills";
    if (fs.existsSync(skillsDir)) {
      skills = fs.readdirSync(skillsDir).filter((f) => {
        const fullPath = path.join(skillsDir, f);
        return fs.statSync(fullPath).isDirectory() && !f.startsWith(".");
      });
    }

    res.json({ synced, skills });
  } catch (err) {
    console.error(`[skills] Sync failed: ${err.message}`);
    res.status(500).json({ error: "Skill sync failed", details: err.message });
  }
});

app.delete("/skills/:name", (req, res) => {
  const skillName = req.params.name;
  const skillDir = path.join("/home/agent/.copilot/skills", skillName);
  const resolved = path.resolve(skillDir);
  // Safety: must be inside skills directory
  if (!resolved.startsWith("/home/agent/.copilot/skills/")) {
    return res.status(403).json({ error: "Access denied" });
  }
  try {
    if (fs.existsSync(resolved)) {
      fs.rmSync(resolved, { recursive: true, force: true });
      console.log(`[skills] Deleted skill '${skillName}'`);
    }
    res.json({ deleted: skillName });
  } catch (err) {
    console.error(`[skills] Delete failed for '${skillName}': ${err.message}`);
    res.status(500).json({ error: "Delete failed", details: err.message });
  }
});

// ── Reverse proxy for dev server preview ─────────────────────────────
// Forwards /proxy/:port/* to http://localhost:{port}/* so the backend
// can proxy slides preview traffic through the sandbox.
const http = require("http");

app.all("/proxy/:targetPort/*", (req, res) => {
  const targetPort = parseInt(req.params.targetPort, 10);
  if (isNaN(targetPort) || targetPort < 1024 || targetPort > 65535) {
    return res.status(400).json({ error: "Invalid port" });
  }
  const targetPath = "/" + (req.params[0] || "");
  const search = req._parsedUrl.search || "";

  const options = {
    hostname: "127.0.0.1",
    port: targetPort,
    path: targetPath + search,
    method: req.method,
    headers: { ...req.headers, host: `127.0.0.1:${targetPort}` },
  };
  // Remove express-specific headers that confuse upstream
  delete options.headers["accept-encoding"];

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on("error", (err) => {
    console.log(`[proxy] Error forwarding to port ${targetPort}: ${err.message}`);
    if (!res.headersSent) {
      res.status(502).json({ error: `Dev server not reachable on port ${targetPort}` });
    }
  });

  req.pipe(proxyReq, { end: true });
});

app.listen(port, () => {
  console.log(`Copilot CLI Sandbox listening on port ${port} (model: ${DEFAULT_MODEL})`);
});
