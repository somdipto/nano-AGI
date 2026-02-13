"""
Voice Memory — Premium Web App
Record → Transcribe (Whisper.cpp) → Store (memU) → Summarize (Gemini)

Run:  ./.venv/bin/python3 web/server.py
Open: http://localhost:3777
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add project src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memu.voice_capture import WhisperCapture

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Voice Memory", docs_url=None, redoc_url=None)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Whisper capture instance (lazy init)
_whisper: Optional[WhisperCapture] = None


def get_whisper() -> WhisperCapture:
    global _whisper
    if _whisper is None:
        _whisper = WhisperCapture()
    return _whisper


# ---------------------------------------------------------------------------
# In-memory session store (lightweight — no DB needed for MVP)
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/sessions")
async def list_sessions():
    """List all past sessions."""
    result = []
    for sid, s in sorted(sessions.items(), key=lambda x: x[1]["started_at"], reverse=True):
        result.append({
            "id": sid,
            "started_at": s["started_at"],
            "ended_at": s.get("ended_at"),
            "transcript_count": len(s["transcripts"]),
            "summary": s.get("summary", ""),
            "duration": s.get("duration", 0),
        })
    return result


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full session details."""
    s = sessions.get(session_id)
    if not s:
        return {"error": "Session not found"}
    return s


# ---------------------------------------------------------------------------
# WebSocket — real-time audio streaming
# ---------------------------------------------------------------------------

@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    """
    Receive audio chunks via WebSocket, transcribe with Whisper, stream back.

    Protocol:
      Client → Server:  binary audio data (webm/wav chunks)
      Server → Client:  JSON messages:
        {"type": "transcript", "text": "...", "timestamp": "..."}
        {"type": "session_started", "session_id": "..."}
        {"type": "session_ended", "session_id": "...", "summary": "..."}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    whisper = get_whisper()

    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "id": session_id,
        "started_at": datetime.now().isoformat(),
        "transcripts": [],
        "summary": "",
        "duration": 0,
    }

    await websocket.send_json({
        "type": "session_started",
        "session_id": session_id,
    })

    chunk_count = 0
    start_time = datetime.now()

    try:
        while True:
            # Receive audio blob from browser
            data = await websocket.receive_bytes()

            if len(data) < 1000:
                # Too small — likely not valid audio
                continue

            chunk_count += 1

            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir="/tmp"
            )
            tmp.write(data)
            tmp.close()

            try:
                # Transcribe with Whisper.cpp
                text = whisper.transcribe(tmp.name)

                # Filter non-speech
                if text and len(text.strip()) > 3 and "[BLANK_AUDIO]" not in text:
                    timestamp = datetime.now().isoformat()
                    transcript_entry = {
                        "text": text.strip(),
                        "timestamp": timestamp,
                        "chunk": chunk_count,
                    }
                    sessions[session_id]["transcripts"].append(transcript_entry)

                    await websocket.send_json({
                        "type": "transcript",
                        "text": text.strip(),
                        "timestamp": timestamp,
                        "chunk": chunk_count,
                    })
            finally:
                # Cleanup temp file
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Session ended — generate summary
        elapsed = (datetime.now() - start_time).total_seconds()
        sessions[session_id]["ended_at"] = datetime.now().isoformat()
        sessions[session_id]["duration"] = round(elapsed)

        all_text = " ".join(
            t["text"] for t in sessions[session_id]["transcripts"]
        )

        if all_text.strip():
            # Build a simple summary (Gemini-free for reliability)
            word_count = len(all_text.split())
            summary = _build_summary(all_text, elapsed)
            sessions[session_id]["summary"] = summary
        else:
            sessions[session_id]["summary"] = "No speech detected during this session."

        # Try to send final summary
        try:
            await websocket.send_json({
                "type": "session_ended",
                "session_id": session_id,
                "summary": sessions[session_id]["summary"],
                "duration": sessions[session_id]["duration"],
                "transcript_count": len(sessions[session_id]["transcripts"]),
            })
        except Exception:
            pass


def _build_summary(text: str, duration: float) -> str:
    """Build a local summary from the transcript text."""
    words = text.split()
    word_count = len(words)
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    # Extract key sentences (simple approach — first and last + longest)
    sentences = [s.strip() for s in text.replace(".", ".\n").split("\n") if s.strip()]

    if len(sentences) <= 3:
        key_points = sentences
    else:
        # First, middle, and last sentences
        key_points = [
            sentences[0],
            sentences[len(sentences) // 2],
            sentences[-1],
        ]

    summary = f"📊 Session: {minutes}m {seconds}s • {word_count} words • {len(sentences)} sentences\n\n"
    summary += "📝 Key points:\n"
    for i, point in enumerate(key_points, 1):
        summary += f"  {i}. {point}\n"
    summary += f"\n💬 Full transcript: {text[:500]}{'...' if len(text) > 500 else ''}"

    return summary


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("=" * 55)
    print("🎤  Voice Memory — Premium Web App")
    print("=" * 55)
    print()
    print("🌐  Open: http://localhost:3777")
    print("🧠  Whisper.cpp: local transcription")
    print("📂  Transcripts stored in-memory")
    print()
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=3777,
        reload=False,
        log_level="info",
    )
