"""
Personality Engine — learns user patterns and predicts behavior.

Stores patterns in ~/shadow/personality.json:
  - Behavioral patterns (morning routine, stress indicators, etc.)
  - Time-based habits (preferred work times, weekly patterns)
  - Decision speed and communication style
  - Auto-predicted tasks based on observed patterns
"""

import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


PERSONALITY_PATH = Path.home() / "shadow" / "personality.json"

DEFAULT_PERSONALITY = {
    "patterns": {
        "morning_routine": [],
        "evening_routine": [],
        "stress_indicators": [],
        "decision_speed": "unknown",
        "preferred_interruption_times": [],
        "weekly_patterns": {},
        "topic_frequency": {},
        "task_categories": {},
    },
    "predicted_today": [],
    "predicted_this_week": [],
    "history": {
        "tasks_completed": [],
        "tasks_spoken": [],
        "active_hours": {},
        "last_updated": None,
    },
    "meta": {
        "created": None,
        "observations": 0,
        "confidence": 0.0,
    },
}


class PersonalityEngine:
    """
    Learns from every interaction and builds a predictive model of the user.
    
    Key capabilities:
      - Track when user speaks (time-of-day patterns)
      - Track what topics recur (morning = email, evening = planning)
      - Detect stress signals in speech
      - Predict today's likely tasks based on day-of-week + past patterns
      - Score task urgency using personal behavior model
    """

    STRESS_WORDS = {
        "deadline", "late", "behind", "urgent", "asap", "stressed",
        "overwhelmed", "forget", "hurry", "rush", "emergency", "panic",
        "overdue", "delayed", "pressure", "worried", "anxious",
    }

    ROUTINE_SIGNALS = {
        "morning": {"coffee", "email", "calendar", "schedule", "meeting", "commute", "gym"},
        "evening": {"dinner", "relax", "plan", "review", "tomorrow", "wind down", "read"},
        "weekend": {"grocery", "clean", "laundry", "family", "trip", "shopping", "rest"},
    }

    def __init__(self, path: Optional[Path] = None):
        self.path = path or PERSONALITY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        """Load personality data from disk or create default."""
        if self.path.exists():
            try:
                with open(self.path) as f:
                    data = json.load(f)
                # Merge with defaults for any missing keys
                for key in DEFAULT_PERSONALITY:
                    if key not in data:
                        data[key] = DEFAULT_PERSONALITY[key]
                return data
            except (json.JSONDecodeError, KeyError):
                pass

        data = json.loads(json.dumps(DEFAULT_PERSONALITY))
        data["meta"]["created"] = datetime.now().isoformat()
        self._save(data)
        return data

    def _save(self, data: Optional[dict] = None):
        """Persist personality data to disk."""
        if data is None:
            data = self.data
        data["history"]["last_updated"] = datetime.now().isoformat()
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Observation: called on every spoken utterance ──

    def observe(self, text: str, intent: str = "", priority: int = 0, category: str = ""):
        """
        Feed an observation from user speech.
        Learns patterns from text, timing, intent, and category.
        """
        now = datetime.now()
        hour = now.hour
        day_name = now.strftime("%A").lower()  # monday, tuesday, ...
        time_block = self._time_block(hour)

        # Track active hours
        hour_key = str(hour)
        active_hours = self.data["history"].setdefault("active_hours", {})
        active_hours[hour_key] = active_hours.get(hour_key, 0) + 1

        # Track day-of-week patterns
        weekly = self.data["patterns"].setdefault("weekly_patterns", {})
        day_tasks = weekly.setdefault(day_name, [])

        # Extract keywords from text
        words = set(re.findall(r'\b\w{3,}\b', text.lower()))

        # Detect routine signals
        for period, signals in self.ROUTINE_SIGNALS.items():
            matches = words & signals
            if matches:
                routine_key = f"{period}_routine"
                routine = self.data["patterns"].setdefault(routine_key, [])
                for m in matches:
                    if m not in routine:
                        routine.append(m)

        # Detect stress
        stress_matches = words & self.STRESS_WORDS
        if stress_matches:
            stress_list = self.data["patterns"].setdefault("stress_indicators", [])
            for s in stress_matches:
                if s not in stress_list:
                    stress_list.append(s)

        # Track topic frequency
        topics = self.data["patterns"].setdefault("topic_frequency", {})
        for word in words:
            if len(word) > 3:  # Skip short words
                topics[word] = topics.get(word, 0) + 1

        # Track task categories
        if category:
            cats = self.data["patterns"].setdefault("task_categories", {})
            cat_key = f"{day_name}_{time_block}"
            cat_list = cats.setdefault(cat_key, [])
            if category not in cat_list:
                cat_list.append(category)

        # Track preferred interruption times (when user is most active)
        pref_times = self.data["patterns"].setdefault("preferred_interruption_times", [])
        time_str = f"{hour:02d}:00"
        if time_str not in pref_times and active_hours.get(hour_key, 0) > 3:
            pref_times.append(time_str)
            pref_times.sort()

        # Store spoken task in history
        spoken = self.data["history"].setdefault("tasks_spoken", [])
        spoken.append({
            "text": text[:200],
            "intent": intent,
            "priority": priority,
            "category": category,
            "time": now.isoformat(),
            "day": day_name,
            "hour": hour,
        })
        # Keep last 200 observations
        if len(spoken) > 200:
            self.data["history"]["tasks_spoken"] = spoken[-200:]

        # Update meta
        self.data["meta"]["observations"] = self.data["meta"].get("observations", 0) + 1
        self.data["meta"]["confidence"] = min(
            1.0, self.data["meta"]["observations"] / 100
        )

        self._save()

    def observe_task_completed(self, task: str, category: str = "", duration_seconds: int = 0):
        """Record a completed task for pattern learning."""
        now = datetime.now()
        completed = self.data["history"].setdefault("tasks_completed", [])
        completed.append({
            "task": task[:200],
            "category": category,
            "duration": duration_seconds,
            "time": now.isoformat(),
            "day": now.strftime("%A").lower(),
            "hour": now.hour,
        })
        if len(completed) > 200:
            self.data["history"]["tasks_completed"] = completed[-200:]
        self._save()

    # ── Prediction ──

    def predict_today(self) -> list[dict]:
        """
        Predict what the user is likely to do today based on:
          - Day-of-week patterns
          - Time-of-day habits
          - Recent task gaps (e.g., "hasn't called mom in 2 weeks")
          - Topic frequency
        """
        now = datetime.now()
        day_name = now.strftime("%A").lower()
        predictions = []

        # 1. Day-of-week patterns from history
        spoken = self.data["history"].get("tasks_spoken", [])
        day_tasks = [t for t in spoken if t.get("day") == day_name]

        # Find recurring themes for this day
        day_topics = Counter()
        for t in day_tasks:
            words = re.findall(r'\b\w{4,}\b', t.get("text", "").lower())
            day_topics.update(words)

        for topic, count in day_topics.most_common(5):
            if count >= 2:
                predictions.append({
                    "task": f"{topic.title()} ({day_name.title()} pattern)",
                    "source": "weekly_pattern",
                    "confidence": min(0.9, count / 10),
                    "priority": 6,
                })

        # 2. Gap detection — things user does regularly but hasn't done recently
        completed = self.data["history"].get("tasks_completed", [])
        if completed:
            # Find tasks done >2 times
            task_times = defaultdict(list)
            for t in completed:
                key = t.get("category", "") or t.get("task", "")[:30]
                try:
                    task_times[key].append(datetime.fromisoformat(t["time"]))
                except (ValueError, KeyError):
                    pass

            for key, times in task_times.items():
                if len(times) >= 2:
                    times.sort()
                    avg_gap = sum(
                        (times[i + 1] - times[i]).days for i in range(len(times) - 1)
                    ) / (len(times) - 1)

                    last = times[-1]
                    days_since = (now - last).days

                    if days_since > avg_gap * 1.5 and avg_gap > 0:
                        predictions.append({
                            "task": f"{key} ({days_since}d gap, usually every {int(avg_gap)}d)",
                            "source": "gap_detection",
                            "confidence": min(0.8, days_since / (avg_gap * 3)),
                            "priority": 7,
                        })

        # 3. Stress-based predictions
        recent_spoken = spoken[-10:] if spoken else []
        stress_count = sum(
            1 for t in recent_spoken
            if any(s in t.get("text", "").lower() for s in self.STRESS_WORDS)
        )
        if stress_count >= 2:
            predictions.append({
                "task": "Take a break (stress pattern detected)",
                "source": "stress_detection",
                "confidence": 0.7,
                "priority": 5,
            })

        # Sort by priority × confidence
        predictions.sort(key=lambda p: p["priority"] * p["confidence"], reverse=True)

        # Store predictions
        self.data["predicted_today"] = predictions[:10]
        self._save()

        return predictions[:10]

    # ── Scoring ──

    def score_task(self, task: str, priority: int = 5, category: str = "") -> float:
        """
        Score a task's urgency using personal behavior model.
        Returns a 0-10 score weighted by:
          - Base priority
          - User's pattern match (does this fit their typical behavior?)
          - Stress indicators
          - Time-of-day relevance
        """
        score = float(priority)
        text_lower = task.lower()
        words = set(re.findall(r'\b\w{3,}\b', text_lower))

        # Boost if matches a frequent topic
        topics = self.data["patterns"].get("topic_frequency", {})
        topic_matches = sum(topics.get(w, 0) for w in words)
        if topic_matches > 5:
            score += 1.0

        # Boost if stress-related
        if words & self.STRESS_WORDS:
            score += 1.5

        # Boost if matches current time block routine
        now = datetime.now()
        time_block = self._time_block(now.hour)
        routine = self.data["patterns"].get(f"{time_block}_routine", [])
        if any(r in text_lower for r in routine):
            score += 0.5

        return min(10.0, round(score, 1))

    # ── API for UI ──

    def get_personality(self) -> dict:
        """Return personality data for the UI."""
        return {
            "patterns": self.data["patterns"],
            "predicted_today": self.data.get("predicted_today", []),
            "meta": self.data["meta"],
        }

    def get_greeting(self) -> str:
        """Generate a context-aware greeting from Shadow."""
        now = datetime.now()
        hour = now.hour
        day = now.strftime("%A")
        predictions = self.predict_today()

        if hour < 12:
            greeting = f"Good morning."
        elif hour < 17:
            greeting = f"Good afternoon."
        else:
            greeting = f"Good evening."

        if predictions:
            top = predictions[0]
            greeting += f" Based on your patterns, you might want to: {top['task']}."
        else:
            greeting += f" It's {day}. What's on your mind?"

        return greeting

    # ── Helpers ──

    @staticmethod
    def _time_block(hour: int) -> str:
        if hour < 6:
            return "night"
        elif hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        else:
            return "evening"


# ── Singleton ──

_engine: Optional[PersonalityEngine] = None


def get_personality_engine() -> PersonalityEngine:
    global _engine
    if _engine is None:
        _engine = PersonalityEngine()
    return _engine
