const express = require("express");
const { spawn } = require("child_process");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

const app = express();
app.use(express.json());

const tasks = new Map();

// Track premium request consumption (each Copilot CLI invocation = 1 premium request)
let premiumRequests = 0;

// GitHub auth: accept GH_TOKEN or GITHUB_TOKEN (same as official Docker sandbox)
// When GH_TOKEN env var is set, gh CLI uses it directly — no need to run `gh auth login`.
const ghToken = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
if (ghToken) {
  console.log("GitHub CLI will authenticate via GH_TOKEN environment variable");
}

// Default model from env (overridable per-task)
const DEFAULT_MODEL = process.env.COPILOT_MODEL || "claude-opus-4.6";

app.get("/health", (_req, res) => {
  const activeTasks = [...tasks.values()].filter((t) => t.exitCode() === null).length;
  res.json({
    status: "ready",
    activeTasks,
    premiumRequests,
    model: DEFAULT_MODEL,
    ghAuth: !!ghToken,
  });
});

app.post("/tasks", (req, res) => {
  const {
    prompt,
    command,
    args = [],
    model = DEFAULT_MODEL,
    workDir = "/workspace",
    ghToken: perTaskToken,
  } = req.body;

  // Two modes: a) raw command, b) Copilot CLI prompt
  let spawnCmd, spawnArgs;
  if (prompt) {
    // Run Copilot CLI in non-interactive mode with the given prompt
    spawnCmd = "copilot";
    spawnArgs = ["-p", prompt, "--model", model, "--yolo"];
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
  });

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
app.listen(port, () => {
  console.log(`Copilot CLI Sandbox listening on port ${port} (model: ${DEFAULT_MODEL})`);
});
