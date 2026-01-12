"""Research Query model."""

from typing import List

from pydantic import Field, field_validator

from . import BaseEntity, QueryStatus, SearchSource


class ResearchQuery(BaseEntity):
    """
    Represents a research question from the user with metadata.
    
    Validation Rules:
    - content: 1-2000 characters
    - search_sources: At least one source selected
    - status: Defaults to 'pending'
    """
    
    content: str = Field(..., min_length=1, max_length=2000, description="User's question text")
    search_sources: List[SearchSource] = Field(
        ...,
        min_length=1,
        description="Selected search sources (google, arxiv, or both)"
    )
    status: QueryStatus = Field(default=QueryStatus.PENDING, description="Processing status")
    
    @field_validator("search_sources")
    @classmethod
    def validate_search_sources(cls, v: List[SearchSource]) -> List[SearchSource]:
        """Ensure at least one search source is selected."""
        if not v:
            raise ValueError("At least one search source must be selected")
        valid_sources = set(SearchSource)
        for source in v:
            if source not in valid_sources:
                raise ValueError(f"Invalid search source: {source}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "thread_id": "660e8400-e29b-41d4-a716-446655440001",
                "content": "quantum computing의 최신 발전 동향은?",
                "search_sources": ["google", "arxiv"],
                "status": "processing",
                "created_at": "2025-11-14T10:30:00Z"
            }
        }
