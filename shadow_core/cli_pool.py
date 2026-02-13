"""
CLI Pool — 5-slot Gemini CLI agent manager.

Manages a pool of CLIAgent instances, auto-assigns tasks to free slots,
and queues overflow tasks for later execution.
"""

import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

from .cli_agent import CLIAgent


class CLIPool:
    """
    Pool of 5 CLI agent slots.

    - assign_task() → finds free slot, spawns agent
    - If all slots busy → queues task
    - Background thread processes queue when slots free up
    """

    MAX_SLOTS = 5

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or (Path.home() / "shadow-cli-agents")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Create 5 slots
        self.slots: list[CLIAgent] = [
            CLIAgent(slot_id=i, workspace_root=self.workspace_root)
            for i in range(self.MAX_SLOTS)
        ]

        # Task queue for overflow
        self._queue: deque = deque()
        self._lock = threading.Lock()

        # Completed results for chat delivery
        self.completed_results: deque = deque(maxlen=50)

        # Background queue processor
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the background queue processor."""
        self._running = True
        self._processor_thread = threading.Thread(
            target=self._process_queue, daemon=True
        )
        self._processor_thread.start()
        print(f"[CLIPool] Started — {self.MAX_SLOTS} slots, workspace: {self.workspace_root}")

    def stop(self):
        """Stop pool and kill all agents."""
        self._running = False
        for slot in self.slots:
            slot.kill()

    def assign_task(self, todo_id: int, task: dict) -> Optional[int]:
        """
        Assign a task to a free slot. Returns slot_id or None if queued.
        """
        with self._lock:
            # Find free slot
            for slot in self.slots:
                if slot.is_idle:
                    if slot.assign(todo_id, task):
                        print(f"[CLIPool] Assigned todo #{todo_id} → slot {slot.slot_id}: {task.get('task', '')[:50]}")
                        return slot.slot_id
                    break

            # All busy — queue it
            self._queue.append({"todo_id": todo_id, "task": task})
            print(f"[CLIPool] Queued todo #{todo_id} (all slots busy, queue: {len(self._queue)})")
            return None

    def _process_queue(self):
        """Background: assign queued tasks to freed slots, collect results."""
        while self._running:
            # Check for completed agents → collect results
            for slot in self.slots:
                if slot.status in ("done", "failed") and slot.todo_id is not None:
                    self.completed_results.append({
                        "todo_id": slot.todo_id,
                        "slot_id": slot.slot_id,
                        "task": slot.task.get("task", "") if slot.task else "",
                        "category": slot.task.get("category", "other") if slot.task else "",
                        "status": slot.status,
                        "result": slot.result,
                    })
                    print(f"[CLIPool] Slot {slot.slot_id} finished → {slot.status}")
                    # Don't reset yet — let UI read the terminal output

            # Process queue if slots available
            with self._lock:
                if self._queue:
                    for slot in self.slots:
                        if slot.is_idle and self._queue:
                            queued = self._queue.popleft()
                            slot.assign(queued["todo_id"], queued["task"])
                            print(f"[CLIPool] Dequeued todo #{queued['todo_id']} → slot {slot.slot_id}")

            time.sleep(1)

    def get_slot(self, slot_id: int) -> Optional[CLIAgent]:
        """Get a specific slot."""
        if 0 <= slot_id < self.MAX_SLOTS:
            return self.slots[slot_id]
        return None

    def get_status(self) -> dict:
        """Full pool status for API."""
        return {
            "slots": [s.to_dict() for s in self.slots],
            "queue_size": len(self._queue),
            "active_count": sum(1 for s in self.slots if s.is_busy),
            "completed_results_count": len(self.completed_results),
        }

    def reset_slot(self, slot_id: int):
        """Force-reset a slot to idle."""
        slot = self.get_slot(slot_id)
        if slot:
            slot.reset()

    def kill_all(self):
        """Emergency stop all agents."""
        for slot in self.slots:
            slot.kill()
        self._queue.clear()


# ── Singleton ──

_pool: Optional[CLIPool] = None


def get_cli_pool(workspace_root: Optional[Path] = None) -> CLIPool:
    global _pool
    if _pool is None:
        _pool = CLIPool(workspace_root=workspace_root)
    return _pool
