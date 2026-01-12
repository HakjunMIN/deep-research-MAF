"""Base types and common models for the Deep Research Agent."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Enums
class QueryStatus(str, Enum):
    """Status of a research query."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchSource(str, Enum):
    """Available search sources."""
    GOOGLE = "google"
    ARXIV = "arxiv"
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"


class AgentId(str, Enum):
    """Agent identifiers."""
    PLANNING = "planning"
    RESEARCH = "research"
    REFLECT = "reflect"
    CONTENT = "content"


# Base model with common fields
class BaseEntity(BaseModel):
    """Base entity with common fields."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    class Config:
        use_enum_values = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


# Re-export for convenience
__all__ = [
    "BaseEntity",
    "QueryStatus",
    "SearchSource",
    "AgentId",
    "UUID",
    "datetime",
    "Optional",
    "Field",
]
