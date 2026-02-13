"""
Shadow Core — Autonomous voice agent with multi-agent swarm.

Modules:
    database       SQLite storage (chunks, todos, feedback, sessions, agent_logs)
    agent          Hidden Gemini intelligence via CLIProxyAPI
    capture        5-second real-time audio capture + Whisper.cpp
    orchestrator   Main controller (capture → analyze → store)
    sandbox_agent  Isolated per-todo agent execution
    swarm          Multi-agent orchestrator (N todos = N sandboxes)
"""

from .database import ShadowDatabase
from .agent import ShadowAgent, get_agent
from .capture import RealTimeCapture
from .orchestrator import ShadowOrchestrator
from .sandbox_agent import SandboxAgent
from .swarm import ShadowSwarm, get_swarm

__all__ = [
    "ShadowDatabase",
    "ShadowAgent",
    "get_agent",
    "RealTimeCapture",
    "ShadowOrchestrator",
    "SandboxAgent",
    "ShadowSwarm",
    "get_swarm",
]
