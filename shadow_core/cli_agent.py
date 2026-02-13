"""
CLI Agent — Real Gemini conversation in a PTY subprocess.

Each agent runs an interactive Python script inside a pseudo-terminal,
calling the CLIProxyAPI (127.0.0.1:8317) with streaming output visible
in the browser via xterm.js.
"""

import json
import os
import pty
import select
import signal
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class CLIAgent:
    """
    One agent = One PTY terminal = One Gemini conversation.

    The agent runs a Python script that:
      1. Prints a banner with the task
      2. Calls Gemini via CLIProxyAPI
      3. Streams the response character-by-character
      4. Writes artifacts to workspace
      5. Prints DONE: marker when finished
    """

    IDLE_TIMEOUT = 300  # 5 minutes
    MAX_OUTPUT = 256 * 1024  # 256KB output buffer

    def __init__(self, slot_id: int, workspace_root: Path):
        self.slot_id = slot_id
        self.workspace_root = workspace_root
        self.workspace: Optional[Path] = None
        self.task: Optional[dict] = None
        self.todo_id: Optional[int] = None

        # PTY state
        self.master_fd: Optional[int] = None
        self.child_pid: Optional[int] = None
        self._running = False
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None

        # Output buffer — reader thread appends, WebSocket reads
        self._output_buf = bytearray()
        self._output_lock = threading.Lock()
        self._read_pos = 0  # per-client read position

        # Result
        self.result: str = ""
        self.status: str = "idle"  # idle | running | done | failed

        # Reader thread
        self._reader_thread: Optional[threading.Thread] = None

    @property
    def is_busy(self) -> bool:
        return self.status in ("running",)

    @property
    def is_idle(self) -> bool:
        return self.status in ("idle", "done", "failed")

    def assign(self, todo_id: int, task: dict) -> bool:
        """Assign a task and start the Gemini CLI session."""
        if self.is_busy:
            return False

        self.todo_id = todo_id
        self.task = task
        self.workspace = self.workspace_root / f"cli_{self.slot_id}_todo_{todo_id}"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.status = "running"
        self.result = ""
        self._output_buf = bytearray()
        self._read_pos = 0
        self._started_at = time.time()
        self._finished_at = None

        return self._spawn_pty()

    def _build_script(self) -> str:
        """Generate the Python script that runs the Gemini session."""
        task_json = json.dumps(self.task)
        workspace_str = str(self.workspace)

        return f'''#!/usr/bin/env python3
"""Shadow CLI Agent — Slot {self.slot_id} — Todo #{self.todo_id}"""
import json, sys, time, urllib.request

TASK = json.loads("""{task_json}""")
WORKSPACE = "{workspace_str}"
GEMINI_URL = "http://127.0.0.1:8317/v1/chat/completions"
MODEL = "gemini-2.5-flash"

task_text = TASK.get("task", "unknown")
category = TASK.get("category", "other")
priority = TASK.get("priority", 5)

# ── Banner ──
print("\\033[1;36m" + "═" * 60 + "\\033[0m")
print(f"\\033[1;37m  Shadow Agent — Slot {self.slot_id}\\033[0m")
print(f"\\033[0;33m  Task:\\033[0m {{task_text}}")
print(f"\\033[0;33m  Category:\\033[0m {{category}} | \\033[0;33mPriority:\\033[0m {{priority}}/10")
print("\\033[1;36m" + "═" * 60 + "\\033[0m")
print()

# ── System prompts by category ──
SYSTEM_PROMPTS = {{
    "email": "You are a professional email writer. Draft a complete, polished email.",
    "code": "You are an expert programmer. Write complete, working code with comments and explanations.",
    "research": "You are a thorough researcher. Provide comprehensive analysis with findings and sources.",
    "schedule": "You are a scheduling assistant. Create detailed plans with time estimates.",
    "call": "You are a communication expert. Prepare talking points and anticipated questions.",
    "purchase": "You are a smart shopping assistant. Compare options and give clear recommendations.",
}}
system_msg = SYSTEM_PROMPTS.get(category, "You are Shadow Agent, an autonomous AI assistant. Provide a complete, actionable answer.")

user_msg = f"Task: {{task_text}}\\nPriority: {{priority}}/10\\nCategory: {{category}}\\n\\nProvide a complete, detailed solution."

print("\\033[0;90m⏳ Calling Gemini...\\033[0m")
print()
sys.stdout.flush()

try:
    payload = json.dumps({{
        "model": MODEL,
        "messages": [
            {{"role": "system", "content": system_msg}},
            {{"role": "user", "content": user_msg}},
        ],
        "max_tokens": 4096,
        "temperature": 0.4,
        "stream": False,
    }}).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={{"Content-Type": "application/json"}},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        result = data["choices"][0]["message"]["content"]

    # Stream output character by character for terminal effect
    for i, ch in enumerate(result):
        sys.stdout.write(ch)
        if i % 3 == 0:
            sys.stdout.flush()
            time.sleep(0.005)
    sys.stdout.flush()
    print()
    print()

    # Write solution file
    from pathlib import Path
    ws = Path(WORKSPACE)
    (ws / "solution.md").write_text(f"# {{task_text}}\\n\\n{{result}}\\n")
    print(f"\\033[0;32m📄 Saved: solution.md\\033[0m")

    # Write result marker
    print()
    print("\\033[1;36m" + "─" * 60 + "\\033[0m")
    print(f"\\033[1;32m✅ DONE: {{task_text[:60]}}\\033[0m")
    print("\\033[1;36m" + "─" * 60 + "\\033[0m")

    # Write status for result extraction
    status_data = {{
        "status": "done",
        "result": result,
        "todo_id": {self.todo_id},
        "slot_id": {self.slot_id},
    }}
    (ws / "status.json").write_text(json.dumps(status_data))

except Exception as e:
    print(f"\\033[1;31m❌ ERROR: {{e}}\\033[0m")
    from pathlib import Path
    ws = Path(WORKSPACE)
    status_data = {{
        "status": "failed",
        "result": f"Error: {{e}}",
        "todo_id": {self.todo_id},
        "slot_id": {self.slot_id},
    }}
    (ws / "status.json").write_text(json.dumps(status_data))

sys.stdout.flush()
'''

    def _spawn_pty(self) -> bool:
        """Fork a PTY subprocess running the Gemini session."""
        import sys as _sys

        script = self._build_script()
        script_path = self.workspace / "agent_cli.py"
        script_path.write_text(script)

        try:
            pid, fd = pty.fork()

            if pid == 0:
                # Child process — exec Python with the script
                os.execvp(_sys.executable, [_sys.executable, str(script_path)])
                # Never reached
            else:
                # Parent — store PTY master fd
                self.child_pid = pid
                self.master_fd = fd
                self._running = True

                # Start reader thread
                self._reader_thread = threading.Thread(
                    target=self._read_pty_output, daemon=True
                )
                self._reader_thread.start()

                # Start watchdog
                threading.Thread(target=self._watchdog, daemon=True).start()

                return True

        except Exception as e:
            self.status = "failed"
            self.result = f"PTY spawn failed: {e}"
            return False

    def _read_pty_output(self):
        """Read PTY output in a loop, append to buffer."""
        try:
            while self._running:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if r:
                    try:
                        data = os.read(self.master_fd, 4096)
                        if not data:
                            break
                        with self._output_lock:
                            self._output_buf.extend(data)
                            # Trim if too large
                            if len(self._output_buf) > self.MAX_OUTPUT:
                                self._output_buf = self._output_buf[-self.MAX_OUTPUT:]
                    except OSError:
                        break
        finally:
            self._running = False
            self._finish()

    def _watchdog(self):
        """Monitor child process and enforce timeout."""
        while self._running:
            time.sleep(1)
            # Check if child exited
            try:
                pid, exit_status = os.waitpid(self.child_pid, os.WNOHANG)
                if pid != 0:
                    self._running = False
                    self._finish()
                    return
            except ChildProcessError:
                self._running = False
                self._finish()
                return

            # Check idle timeout
            elapsed = time.time() - self._started_at
            if elapsed > self.IDLE_TIMEOUT:
                self.kill()
                self.status = "failed"
                self.result = f"Timed out after {self.IDLE_TIMEOUT}s"
                return

    def _finish(self):
        """Read final result from status.json."""
        self._finished_at = time.time()
        if self.workspace:
            status_path = self.workspace / "status.json"
            if status_path.exists():
                try:
                    data = json.loads(status_path.read_text())
                    self.result = data.get("result", "")
                    self.status = "done" if data.get("status") == "done" else "failed"
                except Exception:
                    self.status = "done"
            else:
                self.status = "done"

        # Close PTY fd
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

    def get_output_since(self, pos: int = 0) -> tuple[bytes, int]:
        """Return output bytes from position. Returns (data, new_position)."""
        with self._output_lock:
            data = bytes(self._output_buf[pos:])
            return data, len(self._output_buf)

    def get_full_output(self) -> bytes:
        """Return all buffered output."""
        with self._output_lock:
            return bytes(self._output_buf)

    def send_input(self, text: str):
        """Send input to the PTY (for interactive sessions)."""
        if self.master_fd is not None and self._running:
            os.write(self.master_fd, text.encode())

    def kill(self):
        """Force-kill the agent process."""
        self._running = False
        if self.child_pid:
            try:
                os.kill(self.child_pid, signal.SIGTERM)
                time.sleep(0.5)
                os.kill(self.child_pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                os.waitpid(self.child_pid, os.WNOHANG)
            except ChildProcessError:
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

    def reset(self):
        """Kill and reset to idle state."""
        self.kill()
        self.status = "idle"
        self.task = None
        self.todo_id = None
        self.result = ""
        self._output_buf = bytearray()
        self._read_pos = 0

    def to_dict(self) -> dict:
        """Serialize slot status for API."""
        return {
            "slot_id": self.slot_id,
            "status": self.status,
            "todo_id": self.todo_id,
            "task": self.task.get("task", "") if self.task else "",
            "category": self.task.get("category", "other") if self.task else "",
            "elapsed": round(time.time() - self._started_at, 1) if self._started_at else 0,
            "result_preview": self.result[:200] if self.result else "",
        }

    def __repr__(self):
        return f"<CLIAgent slot={self.slot_id} status={self.status}>"
