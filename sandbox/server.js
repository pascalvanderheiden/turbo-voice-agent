const express = require("express");
const { spawn } = require("child_process");
const crypto = require("crypto");

const app = express();
app.use(express.json());

const tasks = new Map();

app.get("/health", (_req, res) => {
  res.json({ status: "ready" });
});

app.post("/tasks", (req, res) => {
  const { command, args = [], workDir = "/workspace" } = req.body;

  if (!command) {
    return res.status(400).json({ error: "command is required" });
  }

  const id = crypto.randomUUID();
  const output = [];
  let exitCode = null;

  const proc = spawn(command, args, {
    cwd: workDir,
    shell: true,
    env: { ...process.env, FORCE_COLOR: "0" },
  });

  proc.stdout.on("data", (chunk) => {
    output.push({ type: "stdout", data: chunk.toString() });
  });

  proc.stderr.on("data", (chunk) => {
    output.push({ type: "stderr", data: chunk.toString() });
  });

  proc.on("close", (code) => {
    exitCode = code;
    output.push({ type: "exit", code });
  });

  tasks.set(id, { proc, output, exitCode: () => exitCode });

  res.status(201).json({ id });
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

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Sandbox server listening on port ${port}`);
});
