"""
Shadow Swarm — Multi-Agent Orchestrator.
Spawns N sandbox agents for N todos, monitors health, collects results.
"""

import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from .database import ShadowDatabase
from .sandbox_agent import SandboxAgent


class ShadowSwarm:
    """
    One todo = One agent = One sandbox.

    Continuously:
      1. Polls DB for pending high-priority todos
      2. Spawns sandbox agents (up to max_parallel)
      3. Monitors agent health and collects results
      4. Updates DB with completion status + artifacts
    """

    def __init__(self, db: ShadowDatabase | None = None, max_parallel: int = 5):
        self.db = db or ShadowDatabase()
        self.workspace_root = Path.home() / "shadow-sandboxes"
        self.workspace_root.mkdir(exist_ok=True)

        self.max_parallel = max_parallel
        self.active_agents: dict[int, SandboxAgent] = {}
        self._lock = threading.Lock()
        self._running = False

        # Background threads
        self._spawn_thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None

    # ── Lifecycle ──

    def start(self):
        """Start swarm background loops (non-blocking)."""
        self._running = True

        self._spawn_thread = threading.Thread(target=self._spawn_loop, daemon=True)
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)

        self._spawn_thread.start()
        self._monitor_thread.start()

        print(f"[Swarm] Started — max {self.max_parallel} agents, dir: {self.workspace_root}")

    def stop(self):
        """Stop swarm and kill all agents."""
        self._running = False
        self.kill_all()

    def kill_all(self):
        """Emergency stop all agents."""
        with self._lock:
            for agent in self.active_agents.values():
                agent.kill()
            self.active_agents.clear()

    # ── Background loops ──

    def _spawn_loop(self):
        """Poll DB for pending todos, spawn agents."""
        while self._running:
            try:
                with self._lock:
                    available = self.max_parallel - len(self.active_agents)

                if available > 0:
                    pending = self.db.get_pending_todos(min_priority=5)
                    for todo in pending[:available]:
                        todo_id = todo["id"]

                        with self._lock:
                            if todo_id in self.active_agents:
                                continue

                        agent = SandboxAgent(
                            todo_id=todo_id,
                            task=todo,
                            workspace_root=self.workspace_root,
                        )

                        if agent.start():
                            with self._lock:
                                self.active_agents[todo_id] = agent
                            self.db.update_todo_status(todo_id, "active")
                            print(f"[Swarm] Spawned agent #{todo_id}: {todo.get('task', '')[:50]}")

            except Exception as e:
                print(f"[Swarm] Spawn error: {e}")

            time.sleep(3)  # Poll every 3 seconds

    def _monitor_loop(self):
        """Monitor agent health, harvest completed results."""
        while self._running:
            try:
                completed_ids: list[int] = []

                with self._lock:
                    for tid, agent in list(self.active_agents.items()):
                        if not agent.is_running():
                            status = agent.status()
                            final = status.get("status", "unknown")
                            artifacts = agent.artifacts()

                            # Update DB
                            db_status = "completed" if final == "completed" else "failed"
                            self.db.update_todo_status(tid, db_status)

                            # Store artifacts list in workspace_path
                            self.db.update_todo_workspace(
                                tid,
                                workspace_path=str(agent.workspace),
                                artifacts=json.dumps(artifacts),
                            )

                            print(f"[Swarm] Agent #{tid} → {db_status} ({len(artifacts)} artifacts)")
                            completed_ids.append(tid)

                    for tid in completed_ids:
                        del self.active_agents[tid]

            except Exception as e:
                print(f"[Swarm] Monitor error: {e}")

            time.sleep(2)

    # ── Manual control ──

    def spawn_for_todo(self, todo_id: int, task: dict) -> bool:
        """Manually spawn an agent for a specific todo."""
        with self._lock:
            if todo_id in self.active_agents:
                return False  # Already running

        agent = SandboxAgent(
            todo_id=todo_id,
            task=task,
            workspace_root=self.workspace_root,
        )

        if agent.start():
            with self._lock:
                self.active_agents[todo_id] = agent
            self.db.update_todo_status(todo_id, "active")
            return True
        return False

    def approve_todo(self, todo_id: int) -> bool:
        """Move sandbox artifacts to approval directory."""
        sandbox = self.workspace_root / f"todo_{todo_id}"
        approved_dir = Path.home() / "shadow-approved" / f"todo_{todo_id}"

        if sandbox.exists():
            approved_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(sandbox, approved_dir, dirs_exist_ok=True)
            self.db.update_todo_status(todo_id, "approved")
            return True
        return False

    def reject_todo(self, todo_id: int) -> bool:
        """Reject and clean up sandbox."""
        self.db.update_todo_status(todo_id, "rejected")

        # Kill if still running
        with self._lock:
            if todo_id in self.active_agents:
                self.active_agents[todo_id].kill()
                del self.active_agents[todo_id]
        return True

    # ── Queries ──

    def get_status(self) -> dict:
        """Full swarm status for UI."""
        with self._lock:
            agents = []
            for tid, agent in self.active_agents.items():
                agents.append({
                    "todo_id": tid,
                    "task": agent.task.get("task", ""),
                    "category": agent.task.get("category", "other"),
                    "priority": agent.task.get("priority", 5),
                    "running": agent.is_running(),
                    "elapsed": round(agent.elapsed(), 1),
                    "artifacts": agent.artifacts(),
                    "workspace": str(agent.workspace),
                })

        return {
            "active_count": len(agents),
            "max_parallel": self.max_parallel,
            "agents": agents,
        }

    def get_sandbox_files(self, todo_id: int) -> list[dict]:
        """List files in a sandbox."""
        ws = self.workspace_root / f"todo_{todo_id}"
        if not ws.exists():
            return []

        skip = {"agent_runner.py", "status.json", "__pycache__"}
        files = []
        for f in ws.rglob("*"):
            if f.is_file() and f.name not in skip:
                files.append({
                    "name": str(f.relative_to(ws)),
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                })
        return files

    def read_sandbox_file(self, todo_id: int, filename: str) -> str:
        """Read a file from a sandbox (with traversal protection)."""
        ws = self.workspace_root / f"todo_{todo_id}"
        path = (ws / filename).resolve()

        if not str(path).startswith(str(ws.resolve())):
            raise PermissionError("Directory traversal denied")
        if not path.exists():
            raise FileNotFoundError(filename)

        return path.read_text()


# ── Singleton ──

_swarm: ShadowSwarm | None = None


def get_swarm(db: ShadowDatabase | None = None, max_parallel: int = 5) -> ShadowSwarm:
    global _swarm
    if _swarm is None:
        _swarm = ShadowSwarm(db=db, max_parallel=max_parallel)
    return _swarm
