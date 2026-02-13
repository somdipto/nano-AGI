"""
Real-Time Capture — 5-second overlapping audio chunks.
ffmpeg → Whisper.cpp → SQLite storage.
"""

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


class RealTimeCapture:
    """
    5-second audio capture with immediate Whisper.cpp transcription.
    Overlap-aware for continuity.
    """

    DEFAULT_WHISPER = Path.home() / "whisper.cpp" / "build" / "bin" / "whisper-cli"
    DEFAULT_MODEL = Path.home() / "whisper.cpp" / "models" / "ggml-base.en.bin"

    def __init__(
        self,
        whisper_bin: Optional[str] = None,
        model_path: Optional[str] = None,
        chunk_duration: int = 5,
    ):
        # Whisper binary
        self._whisper_bin = whisper_bin or str(self.DEFAULT_WHISPER)
        if not Path(self._whisper_bin).exists():
            raise FileNotFoundError(f"whisper-cli not found at {self._whisper_bin}")

        # Model
        self._model_path = model_path or str(self.DEFAULT_MODEL)
        if not Path(self._model_path).exists():
            raise FileNotFoundError(f"Model not found at {self._model_path}")

        # ffmpeg
        self._ffmpeg_bin = self._find_ffmpeg()
        if not self._ffmpeg_bin:
            raise FileNotFoundError("ffmpeg not found")

        self.chunk_duration = chunk_duration
        self.running = False

        print(f"✅ Whisper: {self._whisper_bin}")
        print(f"✅ Model: {Path(self._model_path).name}")
        print(f"✅ ffmpeg: {self._ffmpeg_bin}")
        print(f"✅ Chunk: {self.chunk_duration}s real-time")

    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg binary."""
        # Try PATH first
        found = shutil.which("ffmpeg")
        if found:
            return found
        # Fallback paths
        for path in ["/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"]:
            if os.path.isfile(path):
                return path
        return None

    def record_chunk(self, duration: Optional[int] = None) -> Optional[str]:
        """Record audio chunk and return path to WAV file."""
        dur = duration or self.chunk_duration
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="shadow_", delete=False, dir="/tmp"
        )
        tmp.close()

        cmd = [
            self._ffmpeg_bin,
            "-f", "avfoundation",
            "-i", ":0",
            "-t", str(dur),
            "-ar", "16000",
            "-ac", "1",
            "-y", tmp.name,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=dur + 5,
                env={**os.environ, "PATH": f"/usr/local/bin:/opt/homebrew/bin:/usr/bin:{os.environ.get('PATH', '')}"},
            )
            if os.path.getsize(tmp.name) > 1000:
                return tmp.name
            else:
                os.unlink(tmp.name)
                return None
        except (subprocess.TimeoutExpired, Exception) as e:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            return None

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio with Whisper.cpp (CPU-only for Intel Mac)."""
        cmd = [
            self._whisper_bin,
            "-m", self._model_path,
            "-f", audio_path,
            "--no-timestamps",
            "-np",
            "--language", "en",
            "--no-gpu",         # CPU-only (Metal crashes on Intel Macs)
            "--split-on-word",  # Split at word boundaries, not mid-word
            "--max-len", "0",   # No artificial length limit per segment
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            text = " ".join(lines) if lines else ""

            # Filter whisper noise / hallucinations
            if "[BLANK_AUDIO]" in text:
                return ""
            # Remove common hallucination markers
            import re
            text = re.sub(r'\[.*?\]', '', text)
            text = re.sub(r'\(.*?\)', '', text)
            # Collapse repeated phrases (whisper hallucination)
            words = text.split()
            if len(words) > 6:
                # Check if last 3 words repeat
                tail = ' '.join(words[-3:])
                count = text.count(tail)
                if count > 2:
                    # Hallucination detected, trim
                    idx = text.index(tail)
                    text = text[:idx + len(tail)]
            text = ' '.join(text.split())  # Normalize whitespace
            return text.strip()
        except (subprocess.TimeoutExpired, Exception):
            return ""

    def capture_once(self, duration: Optional[int] = None) -> tuple[str, float]:
        """Record and transcribe one chunk. Returns (text, timestamp)."""
        ts = datetime.now().timestamp()
        path = self.record_chunk(duration)
        if not path:
            return "", ts

        text = self.transcribe(path)

        # Cleanup
        try:
            os.unlink(path)
        except OSError:
            pass

        return text, ts

    def transcribe_blob(self, audio_data: bytes) -> str:
        """Transcribe raw audio bytes (from WebSocket)."""
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="shadow_ws_", delete=False, dir="/tmp"
        )
        tmp.write(audio_data)
        tmp.close()

        try:
            text = self.transcribe(tmp.name)
            return text
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def start_loop(self, callback: Callable, interval: Optional[int] = None):
        """
        Blocking capture loop — records, transcribes, calls back.

        callback(text: str, timestamp: float) — called for each non-empty chunk.
        """
        dur = interval or self.chunk_duration
        self.running = True

        print(f"\n🎙️  Real-time capture started ({dur}s chunks)")
        print("Press Ctrl+C to stop\n")

        try:
            while self.running:
                loop_start = time.time()
                text, ts = self.capture_once(dur)

                if text and len(text.strip()) > 3:
                    callback(text.strip(), ts)

                # Maintain interval timing
                elapsed = time.time() - loop_start
                sleep = max(0, dur - elapsed)
                if sleep > 0:
                    time.sleep(sleep)
        except KeyboardInterrupt:
            print("\n👋 Capture stopped")
            self.running = False

    def stop(self):
        """Stop the capture loop."""
        self.running = False
