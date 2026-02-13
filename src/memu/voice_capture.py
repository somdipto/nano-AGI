#!/usr/bin/env python3
"""
Voice capture module using Whisper.cpp
Integrates with your Gemini-modified memU for 24/7 ambient transcription.
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple


class WhisperCapture:
    """24/7 audio capture with Whisper.cpp transcription."""

    def __init__(self, whisper_path: str = "~/whisper.cpp", model: str = "base.en"):
        """
        Initialize WhisperCapture.

        Args:
            whisper_path: Path to the whisper.cpp installation directory.
            model: Model name (e.g. "base.en", "small.en", "medium.en").
        """
        self.whisper_path = Path(whisper_path).expanduser()
        self.model_path = self.whisper_path / "models" / f"ggml-{model}.bin"
        self._verify_setup()

    def _verify_setup(self):
        """Check Whisper.cpp and ffmpeg are installed."""
        if not self.whisper_path.exists():
            raise RuntimeError(
                f"Whisper.cpp not found at {self.whisper_path}\n"
                "Run: bash scripts/setup_whisper.sh"
            )

        main_bin = self.whisper_path / "main"
        whisper_cli = self.whisper_path / "build" / "bin" / "whisper-cli"
        if main_bin.exists():
            self._whisper_bin = str(main_bin)
        elif whisper_cli.exists():
            self._whisper_bin = str(whisper_cli)
        else:
            raise RuntimeError(
                f"Whisper.cpp binary not found at {main_bin} or {whisper_cli}\n"
                "Run: cd ~/whisper.cpp && make"
            )

        if not self.model_path.exists():
            raise RuntimeError(
                f"Model not found at {self.model_path}\n"
                "Run: cd ~/whisper.cpp && bash ./models/download-ggml-model.sh base.en"
            )

        # Check ffmpeg — also try common install locations
        import shutil
        self._ffmpeg_bin = shutil.which("ffmpeg")
        if not self._ffmpeg_bin:
            # Fallback: check common Homebrew / system paths
            for candidate in ["/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"]:
                if Path(candidate).exists():
                    self._ffmpeg_bin = candidate
                    break
        if not self._ffmpeg_bin:
            raise RuntimeError(
                "ffmpeg not found. Install with: brew install ffmpeg"
            )

        print(f"✅ Whisper.cpp ready: {self._whisper_bin}")
        print(f"✅ Model: {self.model_path.name}")

    def record_chunk(self, duration: int = 60, output_path: Optional[str] = None) -> Optional[str]:
        """
        Record an audio chunk using ffmpeg.

        Args:
            duration: Seconds to record.
            output_path: Where to save the .wav file. Auto-generated if None.

        Returns:
            Path to the recorded audio file, or None on failure.
        """
        if output_path is None:
            output_path = f"/tmp/shadow_{int(time.time())}.wav"

        # macOS: avfoundation, input ":0" = system audio + mic
        # Grant mic permission in System Preferences → Privacy → Microphone
        cmd = [
            self._ffmpeg_bin,
            "-f", "avfoundation",
            "-i", ":0",
            "-t", str(duration),
            "-ar", "16000",   # 16 kHz required by Whisper
            "-ac", "1",       # Mono
            "-y",             # Overwrite
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            print(f"⚠️  Recording error: {stderr[:200]}")
            return None

        return output_path

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio using Whisper.cpp.

        Args:
            audio_path: Path to a 16 kHz mono .wav file.

        Returns:
            Transcribed text (may be empty if no speech detected).
        """
        cmd = [
            self._whisper_bin,
            "-m", str(self.model_path),
            "-f", audio_path,
            "--no-timestamps",
            "-np",               # No prints except result
            "--language", "en",
            "--no-gpu",          # CPU-only (Metal crashes on pre-M1 Macs)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # whisper.cpp outputs transcription lines on stdout
        lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]

        if not lines:
            return ""

        # Join the output lines into a single transcript
        return " ".join(lines)

    def capture_loop(self, callback, interval: int = 60):
        """
        Run a 24/7 capture loop: record → transcribe → callback.

        Args:
            callback: Called with (text: str, timestamp: datetime, audio_path: str)
                      for every non-empty transcription.
            interval: Duration of each recording chunk in seconds.
        """
        print(f"🎙️  Starting 24/7 capture (every {interval}s)")
        print("Press Ctrl+C to stop")
        print("-" * 50)

        try:
            while True:
                timestamp = datetime.now()

                # Record
                audio_path = self.record_chunk(duration=interval)
                if not audio_path:
                    time.sleep(1)
                    continue

                # Transcribe
                text = self.transcribe(audio_path)

                # Invoke callback for meaningful transcripts
                if text and len(text.strip()) > 3:
                    callback(text, timestamp, audio_path)

                # Cleanup temp audio
                try:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except OSError:
                    pass

        except KeyboardInterrupt:
            print("\n👋 Capture stopped")

    def capture_once(self, duration: int = 10) -> Tuple[str, datetime, Optional[str]]:
        """
        Record and transcribe a single chunk.

        Args:
            duration: Seconds to record.

        Returns:
            Tuple of (transcript, timestamp, audio_path).
            audio_path is NOT cleaned up — caller decides.
        """
        timestamp = datetime.now()
        audio_path = self.record_chunk(duration=duration)

        if not audio_path:
            return "", timestamp, None

        text = self.transcribe(audio_path)
        return text, timestamp, audio_path
