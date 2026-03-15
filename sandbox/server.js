const express = require("express");
const { spawn } = require("child_process");
const crypto = require("crypto");
const path = require("path");

const app = express();
app.use(express.json());

const tasks = new Map();

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
  } = req.body;

  // Two modes: a) raw command, b) Copilot CLI prompt
  let spawnCmd, spawnArgs;
  if (prompt) {
    // Run Copilot CLI in non-interactive mode with the given prompt
    spawnCmd = "copilot";
    spawnArgs = ["-p", prompt, "--model", model, "--yolo"];
  } else if (command) {
    spawnCmd = command;
    spawnArgs = args;
  } else {
    return res.status(400).json({ error: "prompt or command is required" });
  }

  const id = crypto.randomUUID();
  const output = [];
  let exitCode = null;

  // Use shell only for raw commands (they may need PATH resolution)
  // For Copilot CLI prompts, avoid shell to preserve prompt as single argument
  const useShell = !prompt;

  const proc = spawn(spawnCmd, spawnArgs, {
    cwd: workDir,
    shell: useShell,
    env: {
      ...process.env,
      FORCE_COLOR: "0",
      COPILOT_MODEL: model,
    },
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
  res.flushHeaders();

  let cursor = 0;

  const interval = setInterval(() => {
    while (cursor < task.output.length) {
      const entry = task.output[cursor++];
      res.write(`data: ${JSON.stringify(entry)}\n\n`);

      if (entry.type === "exit") {
        clearInterval(interval);
        res.end();
        return;
      }
    }
  }, 100);

  req.on("close", () => clearInterval(interval));
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

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Copilot CLI Sandbox listening on port ${port} (model: ${DEFAULT_MODEL})`);
});
