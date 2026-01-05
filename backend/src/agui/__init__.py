"""AG-UI integration module for Deep Research Agent."""

from .server import create_agui_app, add_agui_endpoints
from .tools import (
    search_google,
    search_arxiv,
    create_research_plan,
    synthesize_answer,
)

__all__ = [
    "create_agui_app",
    "add_agui_endpoints",
    "search_google",
    "search_arxiv",
    "create_research_plan",
    "synthesize_answer",
]
