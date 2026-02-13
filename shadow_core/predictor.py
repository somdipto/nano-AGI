"""
Predictor — ranks tasks by the user's personal behavior model.

Uses personality data + time context + category patterns to produce
a personalized priority score that differs from generic urgency.
"""

from datetime import datetime
from typing import Optional

from .personality import get_personality_engine


class TaskPredictor:
    """
    Ranks tasks based on:
      - User's behavioral patterns (day/time)
      - Category affinity (what they usually do at this time)
      - Stress level (recent stress → boost urgent tasks)
      - Task age (older unfinished tasks get boosted)
      - Pattern gaps (overdue recurring tasks)
    """

    def __init__(self):
        self.personality = get_personality_engine()

    def rank_tasks(self, tasks: list[dict]) -> list[dict]:
        """
        Score and sort a list of tasks by personalized priority.
        
        Each task dict should have: task, priority, category, created_at
        Returns the same list sorted with added 'predicted_priority' field.
        """
        now = datetime.now()

        for task in tasks:
            score = self._compute_score(task, now)
            task["predicted_priority"] = round(score, 1)

        # Sort by predicted priority (highest first)
        tasks.sort(key=lambda t: t.get("predicted_priority", 0), reverse=True)
        return tasks

    def _compute_score(self, task: dict, now: datetime) -> float:
        """Compute personalized priority score for a single task."""
        base = float(task.get("priority", 5))
        category = task.get("category", "other")
        text = task.get("task", "").lower()

        # 1. Personality-based scoring
        personal = self.personality.score_task(text, int(base), category)
        score = (base + personal) / 2  # Blend base + personal

        # 2. Time-of-day relevance
        time_block = self.personality._time_block(now.hour)
        cats_key = f"{now.strftime('%A').lower()}_{time_block}"
        time_cats = self.personality.data["patterns"].get("task_categories", {}).get(cats_key, [])
        if category in time_cats:
            score += 0.8  # Boost: user typically does this category at this time

        # 3. Task age boost (older tasks bubble up)
        created = task.get("created_at") or task.get("timestamp")
        if created:
            try:
                if isinstance(created, str):
                    created_dt = datetime.fromisoformat(created)
                else:
                    created_dt = datetime.fromtimestamp(float(created))
                age_hours = (now - created_dt).total_seconds() / 3600
                if age_hours > 24:
                    score += min(2.0, age_hours / 48)  # Up to +2 for old tasks
            except (ValueError, TypeError):
                pass

        # 4. Stress context boost
        recent_stress = self._recent_stress_level()
        if recent_stress > 0.5 and base >= 7:
            score += 1.0  # Boost high-priority tasks during stress

        # 5. Deadline boost
        deadline = task.get("deadline")
        if deadline:
            try:
                dl = datetime.fromisoformat(str(deadline))
                hours_left = (dl - now).total_seconds() / 3600
                if hours_left < 0:
                    score += 3.0  # Overdue!
                elif hours_left < 4:
                    score += 2.0
                elif hours_left < 24:
                    score += 1.0
            except (ValueError, TypeError):
                pass

        return min(10.0, score)

    def _recent_stress_level(self) -> float:
        """Calculate recent stress level from personality observations."""
        spoken = self.personality.data["history"].get("tasks_spoken", [])
        recent = spoken[-10:] if spoken else []
        if not recent:
            return 0.0

        stress_count = sum(
            1 for t in recent
            if any(s in t.get("text", "").lower() for s in self.personality.STRESS_WORDS)
        )
        return stress_count / len(recent)

    def get_predicted_schedule(self) -> dict:
        """
        Generate a predicted schedule for today.
        Returns tasks grouped by time block.
        """
        predictions = self.personality.predict_today()
        now = datetime.now()

        schedule = {
            "morning": [],
            "afternoon": [],
            "evening": [],
        }

        for pred in predictions:
            # Assign to time block based on category patterns
            task_text = pred.get("task", "")
            category = ""

            # Simple heuristic for time assignment
            morning_words = {"email", "calendar", "meeting", "coffee", "schedule"}
            evening_words = {"review", "plan", "tomorrow", "dinner", "relax"}

            words = set(task_text.lower().split())
            if words & morning_words:
                schedule["morning"].append(pred)
            elif words & evening_words:
                schedule["evening"].append(pred)
            else:
                schedule["afternoon"].append(pred)

        return schedule


# ── Singleton ──

_predictor: Optional[TaskPredictor] = None


def get_predictor() -> TaskPredictor:
    global _predictor
    if _predictor is None:
        _predictor = TaskPredictor()
    return _predictor
