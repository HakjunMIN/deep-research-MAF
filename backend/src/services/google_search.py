"""Google Custom Search API service."""

import asyncio
import os
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.search_result import SearchResult
from ..models import SearchSource, UUID


class GoogleSearchService:
    """
    Service for performing Google Custom Search API queries.
    
    Configured via environment variables:
    - GOOGLE_API_KEY: Google API key
    - GOOGLE_SEARCH_ENGINE_ID: Custom Search Engine ID
    
    Rate Limits:
    - Free tier: 100 queries/day
    - Paid tier: $5/1000 queries
    
    Returns up to 10 results per query.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None
    ):
        """
        Initialize Google Custom Search service.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            search_engine_id: Custom Search Engine ID (defaults to GOOGLE_SEARCH_ENGINE_ID env var)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not self.api_key:
            raise ValueError("Google API key is required")
        if not self.search_engine_id:
            raise ValueError("Google Search Engine ID is required")
        
        self.service = build("customsearch", "v1", developerKey=self.api_key)
    
    async def search(
        self,
        query: str,
        query_id: UUID,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform a Google Custom Search query.
        
        Args:
            query: Search query string
            query_id: ID of the research query
            num_results: Number of results to return (max 10)
            
        Returns:
            List of SearchResult objects
            
        Raises:
            HttpError: If API request fails
        """
        def _run_sync() -> List[SearchResult]:
            try:
                result = self.service.cse().list(
                    q=query,
                    cx=self.search_engine_id,
                    num=min(num_results, 10),  # API限制最大10个结果
                ).execute()

                search_results: List[SearchResult] = []
                items = result.get("items", [])

                for item in items:
                    search_results.append(
                        SearchResult(
                            query_id=query_id,
                            source=SearchSource.GOOGLE,
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                        )
                    )

                return search_results
            except HttpError as e:
                error_reason = e.reason if hasattr(e, "reason") else str(e)
                raise Exception(f"Google Search API error: {error_reason}") from e

        return await asyncio.to_thread(_run_sync)
    
    async def search_with_keywords(
        self,
        keywords: List[str],
        query_id: UUID,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform search using multiple keywords.
        
        Args:
            keywords: List of search keywords
            query_id: ID of the research query
            num_results: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        # Combine keywords into a single query
        query = " ".join(keywords)
        return await self.search(query, query_id, num_results)
