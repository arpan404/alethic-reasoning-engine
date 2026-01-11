"""
Agents package for Google ADK-based AI agents.

This package contains all AI agents for the ATS platform, organized by function.
Each agent follows a consistent structure with agent.py, tools.py, and prompts.py.
"""

from agents.registry import registry, register_agent
from agents.base import BaseAgent

# Import all agents to register them
from agents.resume.agent import ResumeAgent
from agents.screening.agent import ScreeningAgent
from agents.evaluation.agent import EvaluationAgent

__all__ = [
    "registry",
    "register_agent",
    "BaseAgent",
    "ResumeAgent",
    "ScreeningAgent",
    "EvaluationAgent",
]
