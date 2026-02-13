"""
Sandbox Agent — Isolated execution per todo.
Each todo spawns its own process in an isolated filesystem.

No heavy venvs — uses subprocess isolation + resource limits.
"""

import json
import os
import resource
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class SandboxAgent:
    """
    One agent = One todo = One isolated workspace.

    Creates ~/shadow-sandboxes/todo_{id}/ with:
        - agent_runner.py  (generated script)
        - status.json      (current state)
        - agent.log        (execution log)
        - <artifacts>      (emails, code, notes, etc.)
    """

    TIMEOUT = 120  # seconds max per agent (LLM calls take time)

    def __init__(self, todo_id: int, task: dict, workspace_root: Path):
        self.todo_id = todo_id
        self.task = task
        self.workspace = workspace_root / f"todo_{todo_id}"
        self.log_path = self.workspace / "agent.log"
        self.status_path = self.workspace / "status.json"
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self._started_at: Optional[float] = None

        self._init_sandbox()

    def _init_sandbox(self):
        """Create isolated filesystem workspace."""
        self.workspace.mkdir(parents=True, exist_ok=True)

        manifest = {
            "todo_id": self.todo_id,
            "task": self.task,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "artifacts": [],
        }
        self.status_path.write_text(json.dumps(manifest, indent=2))

    def get_result(self) -> str:
        """Read the solution result from status.json."""
        st = self.status()
        return st.get("result", "")

    def _build_agent_script(self) -> str:
        """Generate the Python script that runs inside the sandbox.

        The agent calls the Gemini proxy (CLIProxyAPI) to generate real
        solutions instead of static templates.
        """
        task_json = json.dumps(self.task)
        workspace_str = str(self.workspace)
        status_str = str(self.status_path)

        script = '''#!/usr/bin/env python3
"""Auto-generated sandbox agent for todo __TODO_ID__
Calls Gemini proxy for real solutions."""
import json, os, sys, time, urllib.request, urllib.error
import datetime as dt
from pathlib import Path

WORKSPACE = Path("__WORKSPACE__")
STATUS = Path("__STATUS__")
TASK = json.loads("""__TASK_JSON__""")
GEMINI_URL = "http://127.0.0.1:8317/v1/chat/completions"
MODEL = "gemini-2.5-flash"

def log(msg):
    with open(WORKSPACE / "agent.log", "a") as f:
        f.write(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}\\n")

def update_status(status, result=None, artifacts=None):
    data = {
        "todo_id": __TODO_ID__,
        "status": status,
        "artifacts": artifacts or [],
        "updated_at": time.time(),
    }
    if result:
        data["result"] = result
    STATUS.write_text(json.dumps(data, indent=2))

def call_gemini(system_prompt, user_prompt, max_tokens=2048):
    """Call Gemini proxy API and return the text response."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"Gemini call failed: {e}")
        return None

def main():
    task_text = TASK.get("task", "")
    category = TASK.get("category", "other").lower()
    priority = TASK.get("priority", 5)

    log(f"Agent started: {task_text}")
    update_status("running")

    # Build system prompt based on category
    system_prompts = {
        "email": "You are a professional email writer. Draft a complete, polished email based on the user's request. Include subject line, greeting, body, and sign-off.",
        "code": "You are an expert programmer. Write complete, working code that solves the user's request. Include comments and a brief explanation.",
        "research": "You are a thorough researcher. Provide a comprehensive analysis with key findings, supporting evidence, and actionable conclusions.",
        "schedule": "You are a scheduling assistant. Create a detailed plan with time estimates, dependencies, and preparation steps.",
        "call": "You are a communication expert. Prepare talking points, key arguments, and anticipated questions for this call/conversation.",
        "purchase": "You are a smart shopping assistant. Compare options, list pros/cons, and give a clear recommendation with reasoning.",
    }
    default_prompt = "You are Shadow Agent, an autonomous AI assistant. Solve the user's request thoroughly and provide a complete, actionable answer."
    system_msg = system_prompts.get(category, default_prompt)

    user_msg = f"Task: {task_text}\\nPriority: {priority}/10\\nCategory: {category}\\n\\nProvide a complete, detailed solution. Be thorough but concise."

    try:
        log("Calling Gemini for solution...")
        result = call_gemini(system_msg, user_msg)

        if result:
            log(f"Got response ({len(result)} chars)")

            # Write solution artifact
            solution_path = WORKSPACE / "solution.md"
            solution_path.write_text(f"# {task_text}\\n\\n{result}\\n")
            log("Wrote solution.md")

            # Collect artifacts
            artifacts = [
                str(f.relative_to(WORKSPACE)) for f in WORKSPACE.iterdir()
                if f.is_file() and f.name not in ("agent_runner.py", "status.json", "agent.log")
            ]
            update_status("completed", result=result, artifacts=artifacts)
            log(f"Agent finished. Artifacts: {artifacts}")

        else:
            # Gemini unavailable — write a fallback note
            fallback = f"Shadow Agent could not reach Gemini for task: {task_text}. Please retry or handle manually."
            solution_path = WORKSPACE / "solution.md"
            solution_path.write_text(f"# {task_text}\\n\\n{fallback}\\n")
            update_status("completed", result=fallback, artifacts=["solution.md"])
            log("Gemini unavailable, wrote fallback")

    except Exception as e:
        log(f"ERROR: {e}")
        update_status("failed", result=f"Agent error: {e}")

if __name__ == "__main__":
    main()
'''
        script = script.replace("__WORKSPACE__", workspace_str)
        script = script.replace("__STATUS__", status_str)
        script = script.replace("__TASK_JSON__", task_json)
        script = script.replace("__TODO_ID__", str(self.todo_id))
        return script

    def start(self) -> bool:
        """Start agent in an isolated subprocess."""
        script_path = self.workspace / "agent_runner.py"
        script_path.write_text(self._build_agent_script())

        env = os.environ.copy()
        env["PYTHONPATH"] = ""  # Isolate from project imports
        env["SHADOW_SANDBOX"] = "1"
        env["TODO_ID"] = str(self.todo_id)

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.workspace),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=self._set_limits,
            )
            self.pid = self.process.pid
            self._started_at = time.time()

            # Watchdog: kill if running too long
            threading.Thread(target=self._watchdog, daemon=True).start()
            return True

        except Exception as e:
            self._write_log(f"Failed to start: {e}")
            return False

    def _set_limits(self):
        """Set resource limits for the sandboxed process (macOS-safe)."""
        try:
            # 90 seconds CPU time max (Gemini calls need time)
            resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
        except (ValueError, OSError):
            pass  # Some platforms don't support this

    def _watchdog(self):
        """Kill agent if it runs beyond timeout."""
        time.sleep(self.TIMEOUT)
        if self.process and self.process.poll() is None:
            self._write_log("TIMEOUT — killing agent")
            self.process.terminate()
            time.sleep(2)
            if self.process.poll() is None:
                self.process.kill()

    def _write_log(self, msg: str):
        with open(self.log_path, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

    # ── Status & Queries ──

    def status(self) -> dict:
        """Get current agent status from status.json."""
        if self.status_path.exists():
            try:
                return json.loads(self.status_path.read_text())
            except json.JSONDecodeError:
                return {"status": "error", "todo_id": self.todo_id}
        return {"status": "unknown", "todo_id": self.todo_id}

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def elapsed(self) -> float:
        if self._started_at:
            return time.time() - self._started_at
        return 0.0

    def artifacts(self) -> list[str]:
        """List artifact files created by agent (excludes internal files)."""
        if not self.workspace.exists():
            return []
        skip = {"agent_runner.py", "status.json", "agent.log"}
        return [
            str(f.relative_to(self.workspace))
            for f in self.workspace.iterdir()
            if f.is_file() and f.name not in skip
        ]

    def read_artifact(self, filename: str) -> str:
        """Read an artifact file (with directory traversal protection)."""
        path = (self.workspace / filename).resolve()
        if not str(path).startswith(str(self.workspace.resolve())):
            raise PermissionError("Access denied")
        if not path.exists():
            raise FileNotFoundError(f"Not found: {filename}")
        return path.read_text()

    def read_log(self) -> str:
        if self.log_path.exists():
            return self.log_path.read_text()
        return ""

    # ── Lifecycle ──

    def kill(self):
        """Force-kill the agent process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            time.sleep(1)
            if self.process.poll() is None:
                self.process.kill()

    def cleanup(self):
        """Kill process and remove sandbox directory."""
        self.kill()
        if self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)

    def __repr__(self):
        st = self.status().get("status", "?")
        return f"<SandboxAgent todo={self.todo_id} status={st}>"
