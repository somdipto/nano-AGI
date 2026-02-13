"""
Shadow Agent — Hidden Gemini Intelligence.
No "Gemini CLI" exposed. All wrapped in ShadowAgent class.
Uses CLIProxyAPI (OpenAI-compatible) for truly local operation — no API keys.
"""

import json
import time
from typing import Optional

import httpx


class ShadowAgent:
    """
    Autonomous decision engine.
    Hidden Gemini intelligence — no CLI, no API keys.
    Talks to CLIProxyAPI at 127.0.0.1:8317 (local proxy → Gemini).
    """

    BASE_URL = "http://127.0.0.1:8317"
    MODEL = "gemini-2.5-flash"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self._base_url = base_url or self.BASE_URL
        self._model = model or self.MODEL
        self._last_call = 0.0
        self._min_interval = 0.8  # rate-limit: ~1 call/sec
        self._client = httpx.Client(base_url=self._base_url, timeout=30.0)
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            r = self._client.get("/v1/models")
            return r.status_code == 200
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def _think(self, prompt: str, max_tokens: int = 1024) -> str:
        """Internal reasoning — rate-limited, hidden from user."""
        # Rate limit
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        if not self._available:
            return ""

        try:
            r = self._client.post(
                "/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            self._last_call = time.time()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Shadow] Think error: {e}")
            return ""

    def analyze_chunk(self, text: str, context: list[str] | None = None) -> dict:
        """
        Real-time analysis of a 5-second voice chunk.
        Returns intent, priority, and extracted tasks.
        """
        context_str = "\n".join(context[-5:]) if context else "None"

        prompt = f"""You are Shadow Agent, an autonomous assistant. Analyze this 5-second voice chunk in real-time.

CHUNK: "{text}"
RECENT CONTEXT (last few chunks):
{context_str}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "intent": "task|casual|urgent|question|ignore",
    "priority": <1-10>,
    "confidence": <0.0-1.0>,
    "summary": "<one sentence summary of what was said>",
    "extracted_tasks": [
        {{
            "task": "<clear action description>",
            "category": "<email|code|call|research|schedule|purchase|other>",
            "deadline": "<YYYY-MM-DD or null>",
            "priority": <1-10>
        }}
    ]
}}

Priority guide:
- 9-10: Urgent (deadlines, health, money)
- 7-8: Work tasks with deadlines
- 5-6: General todos, ideas
- 1-4: Casual chat, no action needed
- If the text is noise or meaningless, use intent "ignore" and priority 1"""

        response = self._think(prompt)
        return self._parse_json(response, fallback={
            "intent": "ignore",
            "priority": 1,
            "confidence": 0.0,
            "summary": text[:100] if text else "",
            "extracted_tasks": [],
        })

    def summarize_session(self, transcripts: list[str], duration_seconds: int) -> str:
        """Generate an intelligent session summary."""
        if not transcripts:
            return "No speech detected during this session."

        full_text = " ".join(transcripts)
        word_count = len(full_text.split())
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60

        prompt = f"""Summarize this voice session concisely.

Duration: {minutes}m {seconds}s
Words: {word_count}
Transcript: {full_text[:2000]}

Provide:
1. One-paragraph summary of what was discussed
2. Key points (bullet list, max 5)
3. Any action items mentioned

Be concise. No headers, no fluff."""

        result = self._think(prompt, max_tokens=512)
        if not result:
            # Fallback: local summary
            sentences = [s.strip() for s in full_text.replace(".", ".\n").split("\n") if s.strip()]
            return f"Session: {minutes}m {seconds}s • {word_count} words\n\n" + "\n".join(f"• {s}" for s in sentences[:5])

        return result

    def _parse_json(self, text: str, fallback: dict) -> dict:
        """Safely parse JSON from LLM response."""
        if not text:
            return fallback
        try:
            # Strip markdown code fences if present
            clean = text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                # Remove first and last ```
                start = 1 if lines[0].startswith("```") else 0
                end = -1 if lines[-1].strip() == "```" else len(lines)
                clean = "\n".join(lines[start:end])
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return fallback


# ── Singleton ──

_agent: Optional[ShadowAgent] = None


def get_agent() -> ShadowAgent:
    global _agent
    if _agent is None:
        _agent = ShadowAgent()
    return _agent
