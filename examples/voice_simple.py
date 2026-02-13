#!/usr/bin/env python3
"""
Simple voice capture demo: Whisper.cpp → memU (Gemini CLI)

A lightweight version of voice_memory_gemini.py that stores memories
without async/await complexity. Good for quick testing.

Usage:
    python examples/voice_simple.py
    python examples/voice_simple.py --interval 30   # 30s chunks
    python examples/voice_simple.py --once           # single capture
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from memu.app import MemoryService
from memu.voice_capture import WhisperCapture

SHADOW_DIR = Path("~/shadow-memory").expanduser()
TRANSCRIPT_DIR = SHADOW_DIR / "transcripts"


def get_service() -> MemoryService:
    """Create a MemoryService configured for Gemini CLI via CLIProxyAPI."""
    return MemoryService(
        llm_profiles={
            "default": {
                "provider": "openai",
                "base_url": "http://127.0.0.1:8317",
                "api_key": "sk-dummy",
                "chat_model": "gemini-2.5-flash",
                "client_backend": "httpx",
            },
            "embedding": {
                "provider": "openai",
                "base_url": "http://127.0.0.1:8317",
                "api_key": "sk-dummy",
                "embed_model": "text-embedding-004",
                "client_backend": "httpx",
            },
        },
        database_config={
            "metadata_store": {
                "provider": "sqlite",
                "dsn": f"sqlite:///{SHADOW_DIR / 'shadow_memory.db'}",
            },
            "vector_index": {"provider": "bruteforce"},
        },
        retrieve_config={"method": "rag"},
    )


def save_and_memorize(service: MemoryService, text: str, timestamp: datetime):
    """Save transcript and store in memU."""
    # Save transcript JSON
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = TRANSCRIPT_DIR / f"transcript_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    data = [{"role": "user", "content": {"text": text}, "timestamp": timestamp.isoformat()}]
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Memorize via async bridge
    try:
        result = asyncio.run(
            service.memorize(resource_url=str(filepath), modality="conversation")
        )
        items = len(result.get("items", []))
        print(f"   💾 Stored {items} memory items")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple voice → memU demo")
    parser.add_argument("--interval", type=int, default=60, help="Seconds per chunk")
    parser.add_argument("--once", action="store_true", help="Capture once and exit")
    args = parser.parse_args()

    capture = WhisperCapture()
    service = get_service()

    print("🎙️  Shadow running... Speak now!")
    print()

    if args.once:
        text, timestamp, audio_path = capture.capture_once(duration=args.interval)
        if text:
            print(f"[{timestamp.strftime('%H:%M')}] {text}")
            save_and_memorize(service, text, timestamp)
        else:
            print("No speech detected.")
        return

    def on_transcript(text: str, timestamp: datetime, audio_path: str):
        print(f"[{timestamp.strftime('%H:%M')}] {text}")
        save_and_memorize(service, text, timestamp)

    capture.capture_loop(callback=on_transcript, interval=args.interval)


if __name__ == "__main__":
    main()
