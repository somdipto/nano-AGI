#!/usr/bin/env python3
"""
Nano-AGI — Shadow Core Web Server.
FastAPI + WebSocket with Shadow Swarm integration.
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
import uvicorn

from shadow_core.database import ShadowDatabase
from shadow_core.agent import ShadowAgent, get_agent
from shadow_core.capture import RealTimeCapture
from shadow_core.swarm import ShadowSwarm, get_swarm

# ── Setup ──
db = ShadowDatabase()
agent = get_agent()
capture = RealTimeCapture()
swarm = get_swarm(db=db, max_parallel=5)

app = FastAPI(title="Nano-AGI", version="2.0")

STATIC_DIR = Path(__file__).parent / "static"

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

# ── Background Agent Watcher ──
async def _watch_agent_result(websocket: WebSocket, todo_id: int, task_text: str):
    """Watch for agent completion and push the result to the WebSocket."""
    max_wait = 120  # seconds
    poll_interval = 2  # seconds
    elapsed = 0

    while elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        # Check completed_results deque for our todo
        result_data = None
        for item in list(swarm.completed_results):
            if item["todo_id"] == todo_id:
                result_data = item
                break

        if result_data:
            try:
                await websocket.send_json({
                    "type": "agent_result",
                    "todo_id": todo_id,
                    "task": task_text,
                    "result": result_data.get("result", ""),
                    "status": result_data.get("status", "completed"),
                    "artifacts": result_data.get("artifacts", []),
                })
            except Exception:
                pass  # WebSocket may have closed
            return

    # Timed out — send failure notice
    try:
        await websocket.send_json({
            "type": "agent_result",
            "todo_id": todo_id,
            "task": task_text,
            "result": f"Agent timed out after {max_wait}s for: {task_text}",
            "status": "timeout",
            "artifacts": [],
        })
    except Exception:
        pass

# ── WebSocket: Real-time audio ──
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    db.create_session(session_id)
    chunk_count = 0
    all_transcripts = []
    context_window = []
    start_time = datetime.now()

    await websocket.send_json({"type": "session_started", "session": session_id})

    try:
        while True:
            data = await websocket.receive_bytes()
            if len(data) < 1000:  # Skip tiny fragments
                continue

            # Transcribe
            text = await asyncio.to_thread(capture.transcribe_blob, data)
            if not text or len(text.strip()) < 8:  # Skip very short noise
                continue

            # Server-side dedup: skip if identical to last transcript
            if all_transcripts and text.strip() == all_transcripts[-1].strip():
                continue

            ts = datetime.now()
            chunk_count += 1
            all_transcripts.append(text)
            context_window.append(text)
            if len(context_window) > 10:
                context_window.pop(0)

            # Store chunk
            chunk_id = db.insert_chunk(
                timestamp=ts.timestamp(),
                text=text,
                intent=None,
                priority=0,
            )

            await websocket.send_json({
                "type": "transcript",
                "text": text,
                "chunk": chunk_count,
                "timestamp": ts.isoformat(),
            })

            # Analyze
            if agent.available:
                analysis = await asyncio.to_thread(agent.analyze_chunk, text, context_window)
            else:
                analysis = _offline_analyze(text)

            intent = analysis.get("intent", "ignore")
            priority = analysis.get("priority", 1)
            db.update_chunk_intent(chunk_id, intent, priority)

            await websocket.send_json({
                "type": "analysis",
                "intent": intent,
                "priority": priority,
                "confidence": analysis.get("confidence", 0),
                "summary": analysis.get("summary", text[:80]),
            })

            # Extract todos and IMMEDIATELY spawn agents
            for task_info in analysis.get("extracted_tasks", []):
                task_text = task_info.get("task", "")
                if task_text:
                    task_priority = task_info.get("priority", priority)
                    task_category = task_info.get("category", "other")
                    todo_id = db.insert_todo(
                        chunk_id=chunk_id,
                        task=task_text,
                        priority=task_priority,
                        category=task_category,
                        deadline=task_info.get("deadline"),
                    )
                    await websocket.send_json({
                        "type": "todo",
                        "id": todo_id,
                        "task": task_text,
                        "priority": task_priority,
                        "category": task_category,
                    })

                    # Instant-spawn agent (no waiting for poll loop)
                    todo_dict = {
                        "id": todo_id,
                        "task": task_text,
                        "priority": task_priority,
                        "category": task_category,
                        "deadline": task_info.get("deadline"),
                    }
                    spawned = await asyncio.to_thread(
                        swarm.spawn_for_todo, todo_id, todo_dict
                    )
                    if spawned:
                        await websocket.send_json({
                            "type": "agent_spawned",
                            "todo_id": todo_id,
                            "task": task_text,
                        })
                        # Background: watch for completion → push result
                        asyncio.create_task(
                            _watch_agent_result(websocket, todo_id, task_text)
                        )

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

# ── WebSocket: Swarm live updates ──
@app.websocket("/ws/swarm")
async def swarm_ws(websocket: WebSocket):
    """Push swarm status to UI every 2 seconds."""
    await websocket.accept()
    try:
        while True:
            status = swarm.get_status()
            pending = db.get_pending_todos(min_priority=1)
            completed = db.get_all_todos(limit=20)
            completed = [t for t in completed if t.get("status") in ("completed", "approved")]

            await websocket.send_json({
                "type": "swarm_update",
                "swarm": status,
                "pending_count": len(pending),
                "completed_count": len(completed),
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

# ── REST: Stats ──
@app.get("/api/stats")
def get_stats():
    stats = db.get_stats()
    swarm_status = swarm.get_status()
    stats["active_agents"] = swarm_status["active_count"]
    stats["max_agents"] = swarm_status["max_parallel"]
    return stats

# ── REST: Sessions ──
@app.get("/api/sessions")
def get_sessions():
    return db.get_sessions()

# ── REST: Todos ──
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
    return db.get_all_todos(limit=100)

@app.post("/api/todos/{todo_id}/approve")
def approve_todo(todo_id: int):
    success = swarm.approve_todo(todo_id)
    return {"success": success, "todo_id": todo_id}

@app.post("/api/todos/{todo_id}/reject")
def reject_todo(todo_id: int):
    success = swarm.reject_todo(todo_id)
    return {"success": success, "todo_id": todo_id}

@app.post("/api/todos/{todo_id}/spawn")
def spawn_agent(todo_id: int):
    """Manually trigger a sandbox agent for a specific todo."""
    todos = db.get_all_todos(limit=200)
    todo = next((t for t in todos if t["id"] == todo_id), None)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    success = swarm.spawn_for_todo(todo_id, todo)
    return {"success": success, "todo_id": todo_id}

# ── REST: Swarm ──
@app.get("/api/swarm/status")
def swarm_status():
    return swarm.get_status()

@app.get("/api/swarm/sandbox/{todo_id}/files")
def sandbox_files(todo_id: int):
    files = swarm.get_sandbox_files(todo_id)
    if not files:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    return files

@app.get("/api/swarm/sandbox/{todo_id}/file")
def sandbox_file(todo_id: int, path: str):
    try:
        content = swarm.read_sandbox_file(todo_id, path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@app.post("/api/swarm/kill-all")
def kill_all():
    swarm.kill_all()
    return {"success": True}

# ── Static files + SPA ──
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

# ── Main ──
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("   NANO-AGI — Shadow Swarm")
    print("=" * 55)
    print(f"   Database:  {db.db_path}")
    print(f"   Agent:     {'🟢 online' if agent.available else '🔴 offline (local mode)'}")
    print(f"   Swarm:     max {swarm.max_parallel} parallel agents")
    print(f"   Sandboxes: {swarm.workspace_root}")
    print()

    # Start swarm background loops
    swarm.start()

    uvicorn.run(app, host="0.0.0.0", port=3777)
