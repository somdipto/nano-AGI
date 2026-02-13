#!/usr/bin/env python3
"""
Nano-AGI — Shadow Core Web Server.
FastAPI + WebSocket with CLI Pool (5 Gemini terminal slots).
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure shadow_core is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shadow_core.database import ShadowDatabase
from shadow_core.agent import ShadowAgent, get_agent
from shadow_core.capture import RealTimeCapture
from shadow_core.cli_pool import CLIPool, get_cli_pool
from shadow_core.personality import get_personality_engine
from shadow_core.auto_extract import extract_intent
from shadow_core.predictor import get_predictor

# ── Setup ──
db = ShadowDatabase()
agent = get_agent()
capture = RealTimeCapture()
cli_pool = get_cli_pool()
personality = get_personality_engine()
predictor = get_predictor()

app = FastAPI(title="Nano-AGI", version="3.0")

# CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3777"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
NEXTJS_DIR = Path(__file__).parent.parent / "web-ui" / "out"


# ── Offline fallback ──
def _offline_analyze(text: str) -> dict:
    t = text.lower()
    urgent = ["urgent", "asap", "emergency", "deadline", "immediately"]
    tasks = ["need to", "have to", "should", "must", "todo", "remind me", "don't forget"]
    questions = ["what", "how", "why", "when", "where", "who"]

    if any(w in t for w in urgent):
        intent, priority = "urgent", 9
    elif any(w in t for w in tasks):
        intent, priority = "task", 6
    elif t.rstrip().endswith("?") or any(t.startswith(w) for w in questions):
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


# ── Background: Watch CLI pool for completed results ──
async def _watch_cli_result(websocket: WebSocket, todo_id: int, task_text: str, slot_id: int):
    """Watch for CLI agent completion and push result to WebSocket."""
    max_wait = 300  # 5 minutes
    poll_interval = 2
    elapsed = 0

    while elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        # Check completed_results for our todo
        for item in list(cli_pool.completed_results):
            if item["todo_id"] == todo_id:
                try:
                    await websocket.send_json({
                        "type": "agent_result",
                        "todo_id": todo_id,
                        "slot_id": slot_id,
                        "task": task_text,
                        "result": item.get("result", ""),
                        "status": item.get("status", "done"),
                    })
                except Exception:
                    pass
                return

    # Timeout
    try:
        await websocket.send_json({
            "type": "agent_result",
            "todo_id": todo_id,
            "slot_id": slot_id,
            "task": task_text,
            "result": f"Agent timed out after {max_wait}s",
            "status": "timeout",
        })
    except Exception:
        pass


# ══════════════════════════════════════════════
#  WebSocket: Real-time audio
# ══════════════════════════════════════════════
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    db.create_session(session_id)
    chunk_count = 0
    all_transcripts = []
    context_window = []
    start_time = datetime.now()

    # Shadow speaks first with greeting
    greeting = personality.get_greeting()
    await websocket.send_json({"type": "session_started", "session": session_id})
    await websocket.send_json({
        "type": "shadow_message",
        "text": greeting,
        "timestamp": datetime.now().isoformat(),
    })

    try:
        while True:
            data = await websocket.receive_bytes()
            if len(data) < 1000:
                continue

            text = await asyncio.to_thread(capture.transcribe_blob, data)
            if not text or len(text.strip()) < 8:
                continue

            if all_transcripts and text.strip() == all_transcripts[-1].strip():
                continue

            ts = datetime.now()
            chunk_count += 1
            all_transcripts.append(text)
            context_window.append(text)
            if len(context_window) > 10:
                context_window.pop(0)

            chunk_id = db.insert_chunk(
                timestamp=ts.timestamp(), text=text, intent=None, priority=0
            )

            await websocket.send_json({
                "type": "transcript",
                "text": text,
                "chunk": chunk_count,
                "timestamp": ts.isoformat(),
            })

            # Auto-extract intent with confidence routing
            extraction = await asyncio.to_thread(
                extract_intent, text, list(context_window)
            )

            intent = extraction.get("category", "other")
            priority = int(extraction.get("urgency", 1))
            action = extraction.get("action", "ignore")
            db.update_chunk_intent(chunk_id, intent, priority)

            await websocket.send_json({
                "type": "analysis",
                "intent": intent,
                "priority": priority,
                "confidence": extraction.get("confidence", "low"),
                "action": action,
                "summary": extraction.get("task", text[:80]),
                "reasoning": extraction.get("reasoning", ""),
            })

            # Send conversational reply if present
            if extraction.get("shadow_reply"):
                await websocket.send_json({
                    "type": "shadow_message",
                    "text": extraction["shadow_reply"],
                    "timestamp": ts.isoformat(),
                })

            # Route based on confidence
            if extraction.get("is_refinement"):
                # Update the most recent task instead of adding a new one
                conn = db._conn()
                last_todo = conn.execute("SELECT id, task FROM todos ORDER BY id DESC LIMIT 1").fetchone()
                if last_todo:
                    todo_id = last_todo["id"]
                    db.update_chunk_intent(chunk_id, intent, priority)
                    conn.execute(
                        "UPDATE todos SET task=?, priority=?, category=?, deadline=? WHERE id=?",
                        (extraction.get("task", last_todo["task"]), priority, extraction.get("category", "other"), extraction.get("deadline"), todo_id)
                    )
                    conn.commit()
                    await websocket.send_json({
                        "type": "todo_updated",
                        "id": todo_id,
                        "task": extraction.get("task", last_todo["task"]),
                        "priority": priority,
                        "category": extraction.get("category", "other"),
                    })
                conn.close()

            elif action == "auto_add" and extraction.get("is_task"):
                # HIGH confidence → auto-add to To-Do and spawn agent
                task_text = extraction.get("task", text)
                task_priority = priority
                task_category = extraction.get("category", "other")
                todo_id = db.insert_todo(
                    chunk_id=chunk_id,
                    task=task_text,
                    priority=task_priority,
                    category=task_category,
                    deadline=extraction.get("deadline"),
                )

                await websocket.send_json({
                    "type": "todo_auto",
                    "id": todo_id,
                    "task": task_text,
                    "priority": task_priority,
                    "category": task_category,
                    "action": "auto_add",
                })

                # Auto-assign to CLI pool
                todo_dict = {
                    "id": todo_id,
                    "task": task_text,
                    "priority": task_priority,
                    "category": task_category,
                }
                slot_id = await asyncio.to_thread(
                    cli_pool.assign_task, todo_id, todo_dict
                )

                await websocket.send_json({
                    "type": "agent_spawned",
                    "todo_id": todo_id,
                    "task": task_text,
                    "slot_id": slot_id,
                })

                if slot_id is not None:
                    db.update_todo_status(todo_id, "active")
                    asyncio.create_task(
                        _watch_cli_result(websocket, todo_id, task_text, slot_id)
                    )

            elif action == "suggest" and extraction.get("is_task"):
                # MEDIUM confidence → suggest in chat, let user decide
                await websocket.send_json({
                    "type": "shadow_message",
                    "text": f"Should I add this to your tasks? \"{extraction.get('task', text)}\"",
                    "suggestion": True,
                    "task_data": {
                        "task": extraction.get("task", text),
                        "priority": priority,
                        "category": extraction.get("category", "other"),
                    },
                    "timestamp": ts.isoformat(),
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")

    # End session
    duration = int((datetime.now() - start_time).total_seconds())
    summary_text = ""
    if all_transcripts and agent.available:
        try:
            summary_text = await asyncio.to_thread(
                agent.summarize_session, all_transcripts, duration
            )
        except Exception:
            summary_text = " ".join(all_transcripts)
    else:
        summary_text = " ".join(all_transcripts) if all_transcripts else "No speech detected."

    db.end_session(session_id, duration, chunk_count, summary_text)

    try:
        await websocket.send_json({
            "type": "session_ended",
            "session": session_id,
            "duration": duration,
            "chunks": chunk_count,
            "summary": summary_text,
        })
    except Exception:
        pass


# ══════════════════════════════════════════════
#  WebSocket: Terminal streaming (per slot)
# ══════════════════════════════════════════════
@app.websocket("/ws/terminal/{slot_id}")
async def terminal_ws(websocket: WebSocket, slot_id: int):
    """Stream PTY output from a CLI slot to xterm.js."""
    await websocket.accept()

    slot = cli_pool.get_slot(slot_id)
    if not slot:
        await websocket.close(code=4004, reason="Invalid slot")
        return

    read_pos = 0

    try:
        while True:
            # Read new output from PTY buffer
            data, new_pos = slot.get_output_since(read_pos)
            if data:
                await websocket.send_bytes(data)
                read_pos = new_pos

            # Also send slot status periodically
            if read_pos == new_pos:
                await websocket.send_json({
                    "type": "slot_status",
                    "slot_id": slot_id,
                    "status": slot.status,
                    "todo_id": slot.todo_id,
                    "task": slot.task.get("task", "") if slot.task else "",
                })

            await asyncio.sleep(0.1)  # 100ms poll

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ══════════════════════════════════════════════
#  WebSocket: Pool status updates
# ══════════════════════════════════════════════
@app.websocket("/ws/pool")
async def pool_ws(websocket: WebSocket):
    """Push CLI pool status to UI every 1 second."""
    await websocket.accept()
    try:
        while True:
            status = cli_pool.get_status()
            pending = db.get_pending_todos(min_priority=1)
            completed = db.get_all_todos(limit=20)
            completed_list = [t for t in completed if t.get("status") in ("completed", "approved")]

            await websocket.send_json({
                "type": "pool_update",
                "pool": status,
                "pending_count": len(pending),
                "completed_count": len(completed_list),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ══════════════════════════════════════════════
#  REST: CLI Pool
# ══════════════════════════════════════════════
@app.get("/api/cli/slots")
def get_slots():
    return cli_pool.get_status()

@app.post("/api/cli/{slot_id}/input")
async def send_input(slot_id: int, body: dict):
    """Send keyboard input to a CLI slot."""
    slot = cli_pool.get_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    text = body.get("input", "")
    if text:
        slot.send_input(text)
    return {"success": True}

@app.post("/api/cli/{slot_id}/reset")
def reset_slot(slot_id: int):
    cli_pool.reset_slot(slot_id)
    return {"success": True, "slot_id": slot_id}

@app.post("/api/cli/kill-all")
def kill_all_cli():
    cli_pool.kill_all()
    return {"success": True}


# ══════════════════════════════════════════════
#  REST: Stats, Sessions, Todos
# ══════════════════════════════════════════════
@app.get("/api/stats")
def get_stats():
    stats = db.get_stats()
    pool_status = cli_pool.get_status()
    stats["active_agents"] = pool_status["active_count"]
    stats["max_agents"] = 5
    return stats

@app.get("/api/sessions")
def get_sessions():
    return db.get_sessions()

@app.get("/api/todos")
def get_todos(status: str = None):
    if status:
        conn = db._conn()
        rows = conn.execute(
            "SELECT * FROM todos WHERE status=? ORDER BY priority DESC",
            (status,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    # Return all todos ranked by predictor
    todos = db.get_all_todos(limit=100)
    return predictor.rank_tasks(todos)

@app.post("/api/todos/{todo_id}/spawn")
def spawn_agent(todo_id: int):
    """Manually assign a todo to a CLI slot."""
    todos = db.get_all_todos(limit=200)
    todo = next((t for t in todos if t["id"] == todo_id), None)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    slot_id = cli_pool.assign_task(todo_id, todo)
    return {"success": slot_id is not None, "slot_id": slot_id, "todo_id": todo_id}


# ══════════════════════════════════════════════
#  REST: Personality & Predictions
# ══════════════════════════════════════════════
@app.get("/api/personality")
def get_personality():
    return personality.get_personality()

@app.get("/api/predictions")
def get_predictions():
    return {
        "today": personality.predict_today(),
        "schedule": predictor.get_predicted_schedule(),
    }

@app.get("/api/greeting")
def get_greeting():
    return {"greeting": personality.get_greeting()}


# ══════════════════════════════════════════════
#  Static files + SPA
# ══════════════════════════════════════════════

# Try Next.js build output first, fall back to legacy static
if NEXTJS_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(NEXTJS_DIR)), name="nextjs")

    @app.get("/{rest_of_path:path}")
    async def serve_nextjs(rest_of_path: str):
        # Try exact file first
        file_path = NEXTJS_DIR / rest_of_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Try .html
        html_path = NEXTJS_DIR / f"{rest_of_path}.html"
        if html_path.is_file():
            return FileResponse(str(html_path))
        # Fall back to index.html (SPA)
        index_path = NEXTJS_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404)
else:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))


# ── Main ──
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("   NANO-AGI — Shadow CLI Pool")
    print("=" * 55)
    print(f"   Database:  {db.db_path}")
    print(f"   Agent:     {'🟢 online' if agent.available else '🔴 offline (local mode)'}")
    print(f"   CLI Pool:  5 Gemini terminal slots")
    print(f"   Workspace: {cli_pool.workspace_root}")
    if NEXTJS_DIR.exists():
        print(f"   Frontend:  Next.js (from {NEXTJS_DIR})")
    else:
        print(f"   Frontend:  Legacy (from {STATIC_DIR})")
    print()

    # Start CLI pool background loops
    cli_pool.start()

    uvicorn.run(app, host="0.0.0.0", port=3777)
