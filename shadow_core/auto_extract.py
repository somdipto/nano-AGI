"""
Auto-Extraction — Gemini-powered intent detection with confidence routing.

Flow:
  Sentence → Gemini analyzes intent → confidence determines action:
    HIGH  → Auto-add to To-Do (no user confirmation)
    MED   → Suggest in Chat ("Should I add this?")
    LOW   → Ignore, store for context
"""

import json
import re
import urllib.request
from typing import Optional

from .personality import get_personality_engine

GEMINI_URL = "http://127.0.0.1:8317/v1/chat/completions"
MODEL = "gemini-2.5-flash"

EXTRACTION_PROMPT = """You are an intent analyzer for a personal AI assistant.
Given the user's spoken sentence, determine:

1. Is this an actionable task? (something that needs to be DONE)
2. What is the confidence level? (high/medium/low)
3. Extract the task if actionable.
4. Categorize it (email, code, research, schedule, call, purchase, health, travel, finance, other).
5. Estimate urgency (1-10).
6. Detect any deadline mentioned.

RULES:
- ALWAYS provide a "shadow_reply". It should be Shadow's direct response to the user's speech.
- Detect REFINEMENTS: If the user is adding details (deadline, priority, notes) to a task they just mentioned in the context (e.g., "Actually make that urgent" or "Add a deadline for tomorrow"), set "is_refinement": true.
- "I need to..." = HIGH confidence task
- "Maybe I should..." = MEDIUM confidence  
- Casual conversation = "is_task": false, "confidence": "low"
- Questions about facts/opinions = Chat response, but "is_task": false.

Respond ONLY in JSON:
{
  "is_task": true/false,
  "is_refinement": true/false,
  "confidence": "high" | "medium" | "low",
  "task": "extracted task description or refined text",
  "shadow_reply": "Brief, helpful, and natural response to the user's speech",
  "category": "email|code|research|schedule|call|purchase|health|travel|finance|other",
  "urgency": 1-10,
  "deadline": "date string or null",
  "reasoning": "one sentence why"
}"""


def extract_intent(text: str, context: list[str] = None) -> dict:
    """
    Analyze spoken text and extract actionable tasks with confidence routing.
    
    Returns dict with:
      - is_task: bool
      - confidence: "high" | "medium" | "low"
      - task: The refined task description (if any)
      - shadow_reply: A brief, natural conversational response (answer the user's question or acknowledge their statement).
      - category: one of [email, code, research, schedule, other]
      - urgency: 1-10
      - is_task: true/false
      - action: "auto_add" (high confidence task), "suggest" (medium), "ignore" (chat/noise)
      - reasoning: brief logic for this action
    """
    if not text or len(text.strip()) < 5:
        return _empty_result()

    # Build context string
    context_str = ""
    if context:
        context_str = "\n\nRecent context:\n" + "\n".join(f"- {c}" for c in context[-5:])

    user_msg = f"Analyze this speech:\n\"{text}\"{context_str}"

    try:
        payload = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request(
            GEMINI_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            result = _parse_json_response(content)

    except Exception as e:
        # Fallback to keyword-based extraction
        result = _keyword_extract(text)

    # Apply personality scoring
    personality = get_personality_engine()
    if result.get("is_task"):
        personal_score = personality.score_task(
            result.get("task", text),
            result.get("urgency", 5),
            result.get("category", "other"),
        )
        result["urgency"] = personal_score

    # Determine action based on confidence
    confidence = result.get("confidence", "low")
    if confidence == "high" and result.get("is_task"):
        result["action"] = "auto_add"
    elif confidence == "medium" and result.get("is_task"):
        result["action"] = "suggest"
    else:
        result["action"] = "ignore"

    # Feed observation to personality engine
    personality.observe(
        text=text,
        intent=result.get("category", ""),
        priority=int(result.get("urgency", 0)),
        category=result.get("category", ""),
    )

    return result


def _parse_json_response(content: str) -> dict:
    """Parse JSON from Gemini response (handles markdown code blocks)."""
    # Strip markdown code fences
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return _empty_result()


def _keyword_extract(text: str) -> dict:
    """Fallback keyword-based extraction when Gemini is unavailable."""
    t = text.lower()

    # High confidence task indicators
    high_signals = ["need to", "have to", "must", "i'll", "going to", "make sure", "don't forget"]
    medium_signals = ["should", "maybe", "thinking about", "want to", "could", "might"]
    urgent_signals = ["urgent", "asap", "immediately", "deadline", "emergency", "right now"]

    is_high = any(s in t for s in high_signals)
    is_medium = any(s in t for s in medium_signals)
    is_urgent = any(s in t for s in urgent_signals)

    if not is_high and not is_medium:
        return _empty_result()

    # Detect category
    category = "other"
    if any(w in t for w in ["email", "send", "reply", "inbox"]):
        category = "email"
    elif any(w in t for w in ["code", "build", "fix", "debug", "program", "website"]):
        category = "code"
    elif any(w in t for w in ["research", "look up", "find out", "compare"]):
        category = "research"
    elif any(w in t for w in ["meeting", "schedule", "calendar", "appointment"]):
        category = "schedule"
    elif any(w in t for w in ["call", "phone", "text", "message"]):
        category = "call"
    elif any(w in t for w in ["buy", "order", "purchase", "shop"]):
        category = "purchase"
    elif any(w in t for w in ["flight", "hotel", "trip", "travel", "book"]):
        category = "travel"

    urgency = 8 if is_urgent else (7 if is_high else 5)

    return {
        "is_task": True,
        "confidence": "high" if is_high else "medium",
        "task": text.strip(),
        "category": category,
        "urgency": urgency,
        "deadline": None,
        "shadow_reply": f"Ok, I've noted that for you: {text.strip()}",
        "reasoning": "keyword extraction fallback",
    }


def _empty_result() -> dict:
    return {
        "is_task": False,
        "confidence": "low",
        "task": "",
        "category": "other",
        "urgency": 0,
        "deadline": None,
        "shadow_reply": "Got it.",
        "reasoning": "no actionable intent detected",
        "action": "ignore",
    }
