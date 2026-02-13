"""
Shadow Core — Autonomous Agent System
Nano-AGI's hidden intelligence layer.

5-second real-time capture → analysis → autonomous execution
"""

from .database import ShadowDatabase
from .agent import ShadowAgent, get_agent
from .capture import RealTimeCapture
from .orchestrator import ShadowOrchestrator

__all__ = [
    "ShadowDatabase",
    "ShadowAgent",
    "get_agent",
    "RealTimeCapture",
    "ShadowOrchestrator",
]
