"""
Shadow Orchestrator — Main controller.
5-second chunks → real-time analysis → autonomous action.
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .database import ShadowDatabase
from .agent import ShadowAgent, get_agent
from .capture import RealTimeCapture


class ShadowOrchestrator:
    """
    Master controller:
    - Connects capture → analysis → storage → workspace
    - Runs background re-prioritization
    - Exposes API for web app
    """

    def __init__(self, db: Optional[ShadowDatabase] = None):
        self.db = db or ShadowDatabase()
        self.agent = get_agent()
        self.capture = RealTimeCapture()

        self.context_window: list[str] = []
        self.max_context = 10  # ~50 seconds of context

        # Virtual workspace
        self.workspace_root = Path.home() / "shadow-workspace"
        self.workspace_root.mkdir(exist_ok=True)

        # Callbacks for real-time UI updates
        self._on_chunk_callbacks: list = []
        self._on_analysis_callbacks: list = []
        self._on_todo_callbacks: list = []

        print("[Shadow] Orchestrator initialized")
        print(f"[Shadow] Database: {self.db.db_path}")
        print(f"[Shadow] Workspace: {self.workspace_root}")
        print(f"[Shadow] Agent: {'online' if self.agent.available else 'offline (local mode)'}")

    # ── Event callbacks (for web app) ──

    def on_chunk(self, callback):
        self._on_chunk_callbacks.append(callback)

    def on_analysis(self, callback):
        self._on_analysis_callbacks.append(callback)

    def on_todo(self, callback):
        self._on_todo_callbacks.append(callback)

    def _emit_chunk(self, data):
        for cb in self._on_chunk_callbacks:
            try:
                cb(data)
            except Exception:
                pass

    def _emit_analysis(self, data):
        for cb in self._on_analysis_callbacks:
            try:
                cb(data)
            except Exception:
                pass

    def _emit_todo(self, data):
        for cb in self._on_todo_callbacks:
            try:
                cb(data)
            except Exception:
                pass

    # ── Core processing ──

    def process_chunk(self, text: str, timestamp: float) -> dict:
        """
        Process a single transcribed chunk:
        1. Store in DB
        2. Analyze with Shadow Agent
        3. Extract and store todos
        4. Emit events for UI
        """
        if not text or len(text.strip()) < 4:
            return {"intent": "ignore", "priority": 0}

        # Store raw chunk
        chunk_id = self.db.insert_chunk(
            timestamp=timestamp,
            text=text,
            intent=None,
            priority=0,
        )

        chunk_data = {
            "id": chunk_id,
            "text": text,
            "timestamp": timestamp,
            "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M:%S"),
        }
        self._emit_chunk(chunk_data)

        # Update context
        self.context_window.append(text)
        if len(self.context_window) > self.max_context:
            self.context_window.pop(0)

        # Analyze with Shadow Agent
        if self.agent.available:
            analysis = self.agent.analyze_chunk(text, self.context_window)
        else:
            # Offline fallback — basic heuristics
            analysis = self._offline_analyze(text)

        intent = analysis.get("intent", "ignore")
        priority = analysis.get("priority", 1)

        # Update chunk with analysis
        self.db.update_chunk_intent(chunk_id, intent, priority)

        analysis_data = {
            "chunk_id": chunk_id,
            "intent": intent,
            "priority": priority,
            "confidence": analysis.get("confidence", 0),
            "summary": analysis.get("summary", text[:80]),
        }
        self._emit_analysis(analysis_data)

        # Extract and store todos
        for task_info in analysis.get("extracted_tasks", []):
            task_text = task_info.get("task", "")
            if task_text:
                todo_id = self.db.insert_todo(
                    chunk_id=chunk_id,
                    task=task_text,
                    priority=task_info.get("priority", priority),
                    category=task_info.get("category", "other"),
                    deadline=task_info.get("deadline"),
                )
                todo_data = {
                    "id": todo_id,
                    "task": task_text,
                    "priority": task_info.get("priority", priority),
                    "category": task_info.get("category", "other"),
                    "status": "pending",
                }
                self._emit_todo(todo_data)
                print(f"  📋 Todo #{todo_id}: {task_text} (P{task_info.get('priority', priority)})")

        return analysis

    def process_audio_blob(self, audio_data: bytes) -> dict:
        """Process raw audio from WebSocket (browser mic)."""
        text = self.capture.transcribe_blob(audio_data)
        if not text or len(text.strip()) < 4:
            return {"intent": "ignore", "text": ""}

        ts = datetime.now().timestamp()
        analysis = self.process_chunk(text, ts)
        analysis["text"] = text
        return analysis

    def summarize_session(self, transcripts: list[str], duration: int) -> str:
        """Generate session summary via Shadow Agent."""
        if self.agent.available:
            return self.agent.summarize_session(transcripts, duration)
        else:
            # Offline fallback
            word_count = sum(len(t.split()) for t in transcripts)
            return f"Session: {duration // 60}m {duration % 60}s • {word_count} words • {len(transcripts)} chunks"

    def _offline_analyze(self, text: str) -> dict:
        """Offline heuristic analysis (when CLIProxyAPI is unavailable)."""
        text_lower = text.lower()

        # Simple keyword matching
        urgent_words = ["urgent", "asap", "emergency", "deadline", "immediately", "now"]
        task_words = ["need to", "have to", "should", "must", "todo", "remind me", "don't forget"]
        question_words = ["what", "how", "why", "when", "where", "who"]

        if any(w in text_lower for w in urgent_words):
            intent, priority = "urgent", 9
        elif any(w in text_lower for w in task_words):
            intent, priority = "task", 6
        elif text_lower.rstrip().endswith("?") or any(text_lower.startswith(w) for w in question_words):
            intent, priority = "question", 4
        else:
            intent, priority = "casual", 2

        return {
            "intent": intent,
            "priority": priority,
            "confidence": 0.5,
            "summary": text[:100],
            "extracted_tasks": [],
        }

    # ── CLI entry (standalone capture mode) ──

    def start_capture(self):
        """Start 24/7 mic capture loop (blocking)."""
        def on_chunk(text, timestamp):
            analysis = self.process_chunk(text, timestamp)
            intent = analysis.get("intent", "?")
            priority = analysis.get("priority", 0)
            ts_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            print(f"[{ts_str}] ({intent} P{priority}) {text[:60]}...")

        print("\n" + "=" * 55)
        print("   NANO-AGI — Shadow Core")
        print("   5-second real-time autonomous capture")
        print("=" * 55 + "\n")

        self.capture.start_loop(on_chunk)

    def stop_capture(self):
        self.capture.stop()


# ── CLI ──

def main():
    orch = ShadowOrchestrator()
    try:
        orch.start_capture()
    except KeyboardInterrupt:
        print("\nStopping Shadow Core...")
        orch.stop_capture()


if __name__ == "__main__":
    main()
