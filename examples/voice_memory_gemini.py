#!/usr/bin/env python3
"""
Shadow Agent: Whisper.cpp + Gemini-Modified memU

24/7 voice capture → local transcription → memU memory pipeline → Gemini CLI.

Prerequisites:
    1. Whisper.cpp built at ~/whisper.cpp with base.en model
    2. ffmpeg installed (brew install ffmpeg)
    3. CLIProxyAPI running (cli-proxy-api) on port 8317
    4. OAuth authenticated (cli-proxy-api --login)

Usage:
    python examples/voice_memory_gemini.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from memu.app import MemoryService
from memu.voice_capture import WhisperCapture

# Where transcripts and memory data are stored
SHADOW_DIR = Path("~/shadow-memory").expanduser()
TRANSCRIPT_DIR = SHADOW_DIR / "transcripts"


class ShadowVoiceAgent:
    """Captures ambient audio 24/7, transcribes locally, stores via memU + Gemini CLI."""

    def __init__(self):
        # Create storage dirs
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

        # Whisper.cpp for local transcription
        self.capture = WhisperCapture(
            whisper_path="~/whisper.cpp",
            model="base.en",
        )

        # memU with Gemini CLI via CLIProxyAPI (same config as example_gemini_cli_oauth.py)
        self.service = MemoryService(
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
                "vector_index": {
                    "provider": "bruteforce",
                },
            },
            retrieve_config={
                "method": "rag",
            },
        )

        print("✅ Shadow Voice Agent initialized")
        print("   • Voice: Whisper.cpp (local)")
        print("   • AI: Gemini CLI via CLIProxyAPI")
        print(f"   • Storage: {SHADOW_DIR}")
        print()

    def _save_transcript(self, text: str, timestamp: datetime) -> str:
        """Save transcript to a JSON file for memU to ingest."""
        filename = f"transcript_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = TRANSCRIPT_DIR / filename

        data = [
            {
                "role": "user",
                "content": {"text": text},
                "timestamp": timestamp.isoformat(),
            }
        ]

        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(filepath)

    async def process_transcript(self, text: str, timestamp: datetime, audio_path: str = None):
        """Process a transcript through memU → Gemini CLI pipeline."""
        time_str = timestamp.strftime("%H:%M:%S")
        print(f"[{time_str}] 📝 {text[:80]}{'...' if len(text) > 80 else ''}")

        # 1. Save transcript file
        transcript_path = self._save_transcript(text, timestamp)

        # 2. Ingest via memU (uses Gemini CLI for extraction/embedding)
        try:
            result = await self.service.memorize(
                resource_url=transcript_path,
                modality="conversation",
            )

            items_count = len(result.get("items", []))
            categories = [c.get("name", "?") for c in result.get("categories", [])]

            if items_count:
                print(f"         💾 Stored {items_count} memory items → {categories}")

        except Exception as e:
            print(f"         ⚠️  Memorize error: {e}")

        # 3. Try to extract actionable tasks
        try:
            result = await self.service.create_memory_item(
                memory_type="task",
                memory_content=f"Extract any actionable tasks from this conversation snippet: {text}",
                memory_categories=["tasks", "voice_capture"],
                user={"user_id": "shadow_agent"},
            )

            task_summary = result.get("memory_item", {}).get("summary", "")
            if task_summary and "no task" not in task_summary.lower():
                print(f"         🎯 Task: {task_summary[:60]}")
                # macOS notification
                safe_msg = task_summary[:50].replace('"', '\\"')
                os.system(
                    f'osascript -e \'display notification "{safe_msg}" with title "Shadow Task"\''
                )

        except Exception as e:
            # Task extraction is best-effort
            pass

    def run(self, interval: int = 60):
        """Start 24/7 capture loop."""

        def on_capture(text: str, timestamp: datetime, audio_path: str):
            asyncio.run(self.process_transcript(text, timestamp, audio_path))

        print(f"🎙️  Listening... (capture every {interval}s)")
        print("=" * 50)
        self.capture.capture_loop(callback=on_capture, interval=interval)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Shadow Voice Agent — 24/7 voice capture with memU")
    parser.add_argument("--interval", type=int, default=60, help="Seconds per recording chunk (default: 60)")
    parser.add_argument("--model", default="base.en", help="Whisper model (default: base.en)")
    args = parser.parse_args()

    agent = ShadowVoiceAgent()
    agent.run(interval=args.interval)


if __name__ == "__main__":
    main()
