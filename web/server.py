"""
Nano-AGI — Shadow Core Web Server
Premium voice capture + real-time analysis + autonomous task extraction.

Run:  ./.venv/bin/python3 web/server.py
Open: http://localhost:3777
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_core.database import ShadowDatabase
from shadow_core.capture import RealTimeCapture
from shadow_core.agent import ShadowAgent, get_agent

# ── App ──

app = FastAPI(title="Nano-AGI", docs_url=None, redoc_url=None)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Shared state ──

db = ShadowDatabase()
capture = RealTimeCapture()
agent = get_agent()

print()
print("=" * 55)
print("   NANO-AGI — Shadow Core")
print("=" * 55)
print(f"   Database:  {db.db_path}")
print(f"   Agent:     {'🟢 online' if agent.available else '🟡 offline (local mode)'}")
print(f"   Whisper:   {capture._whisper_bin}")
print()

# ── Routes ──

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/stats")
async def stats():
    return db.get_stats()


@app.get("/api/sessions")
async def list_sessions():
    return db.get_sessions()


@app.get("/api/todos")
async def list_todos():
    return db.get_all_todos()


@app.get("/api/chunks")
async def list_chunks():
    return db.get_recent_chunks(limit=50)


@app.post("/api/todos/{todo_id}/status")
async def update_todo(todo_id: int, body: dict):
    status = body.get("status", "done")
    db.update_todo_status(todo_id, status)
    return {"ok": True}


# ── WebSocket — Real-time audio ──

@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    """
    Browser sends audio chunks → Whisper transcribes → Agent analyzes → UI updates.

    Messages FROM server:
      session_started  → { session_id }
      transcript       → { text, timestamp, chunk_id, analysis }
      todo             → { id, task, priority, category }
      session_ended    → { summary, stats }
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    db.create_session(session_id)

    await websocket.send_json({"type": "session_started", "session_id": session_id})

    start_time = datetime.now()
    chunk_count = 0
    all_transcripts: list[str] = []
    context_window: list[str] = []

    try:
        while True:
            # Receive audio blob
            data = await websocket.receive_bytes()
            if len(data) < 500:
                continue

            chunk_count += 1

            # Run transcription in thread (blocking I/O)
            text = await asyncio.to_thread(capture.transcribe_blob, data)

            if not text or len(text.strip()) < 4:
                # Send heartbeat so UI knows we're alive
                await websocket.send_json({
                    "type": "heartbeat",
                    "chunk": chunk_count,
                })
                continue

            text = text.strip()
            ts = datetime.now()
            all_transcripts.append(text)

            # Store chunk
            chunk_id = db.insert_chunk(
                timestamp=ts.timestamp(),
                text=text,
            )

            # Update context
            context_window.append(text)
            if len(context_window) > 10:
                context_window.pop(0)

            # Send transcript immediately (before analysis)
            await websocket.send_json({
                "type": "transcript",
                "text": text,
                "timestamp": ts.isoformat(),
                "chunk": chunk_count,
                "chunk_id": chunk_id,
            })

            # Analyze with Shadow Agent (in thread)
            if agent.available:
                analysis = await asyncio.to_thread(
                    agent.analyze_chunk, text, context_window
                )
            else:
                # Offline heuristics
                analysis = _offline_analyze(text)

            intent = analysis.get("intent", "ignore")
            priority = analysis.get("priority", 1)

            # Update chunk with analysis
            db.update_chunk_intent(chunk_id, intent, priority)

            # Send analysis
            await websocket.send_json({
                "type": "analysis",
                "chunk_id": chunk_id,
                "intent": intent,
                "priority": priority,
                "confidence": analysis.get("confidence", 0),
                "summary": analysis.get("summary", text[:80]),
            })

            # Extract todos
            for task_info in analysis.get("extracted_tasks", []):
                task_text = task_info.get("task", "")
                if task_text:
                    todo_id = db.insert_todo(
                        chunk_id=chunk_id,
                        task=task_text,
                        priority=task_info.get("priority", priority),
                        category=task_info.get("category", "other"),
                        deadline=task_info.get("deadline"),
                    )
                    await websocket.send_json({
                        "type": "todo",
                        "id": todo_id,
                        "task": task_text,
                        "priority": task_info.get("priority", priority),
                        "category": task_info.get("category", "other"),
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)[:200]})
        except Exception:
            pass
    finally:
        # Session ended — generate summary
        elapsed = int((datetime.now() - start_time).total_seconds())

        if all_transcripts and agent.available:
            summary = await asyncio.to_thread(
                agent.summarize_session, all_transcripts, elapsed
            )
        elif all_transcripts:
            full = " ".join(all_transcripts)
            wc = len(full.split())
            summary = f"{elapsed // 60}m {elapsed % 60}s • {wc} words • {len(all_transcripts)} chunks"
        else:
            summary = "No speech detected."

        db.end_session(session_id, elapsed, chunk_count, summary)

        try:
            await websocket.send_json({
                "type": "session_ended",
                "session_id": session_id,
                "summary": summary,
                "duration": elapsed,
                "chunks": chunk_count,
                "transcripts": len(all_transcripts),
            })
        except Exception:
            pass


def _offline_analyze(text: str) -> dict:
    """Heuristic analysis when CLIProxyAPI is unavailable."""
    tl = text.lower()
    if any(w in tl for w in ["urgent", "asap", "deadline", "emergency"]):
        return {"intent": "urgent", "priority": 9, "confidence": 0.6, "summary": text[:80], "extracted_tasks": []}
    elif any(w in tl for w in ["need to", "have to", "should", "must", "todo", "remind"]):
        return {"intent": "task", "priority": 6, "confidence": 0.5, "summary": text[:80], "extracted_tasks": []}
    elif text.rstrip().endswith("?"):
        return {"intent": "question", "priority": 4, "confidence": 0.5, "summary": text[:80], "extracted_tasks": []}
    else:
        return {"intent": "casual", "priority": 2, "confidence": 0.4, "summary": text[:80], "extracted_tasks": []}


# ── Run ──

if __name__ == "__main__":
    import uvicorn

    print(f"🌐  Open: http://localhost:3777")
    print(f"⏹️   Press Ctrl+C to stop\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=3777,
        reload=False,
        log_level="info",
    )
