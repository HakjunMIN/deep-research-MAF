"""DuckDuckGo Search API service."""

import asyncio
from typing import List

from ddgs import DDGS

from ..models.search_result import SearchResult
from ..models import SearchSource, UUID


class DuckDuckGoSearchService:
    """
    Service for performing DuckDuckGo search queries.
    
    No authentication required - DuckDuckGo API is public.
    
    Rate Limits:
    - Generally lenient, but excessive requests may be blocked
    - Recommended: 1-2 requests per second
    
    Returns up to 10 results per query by default.
    """
    
    def __init__(self):
        """
        Initialize DuckDuckGo search service.
        """
        self.ddgs = DDGS()
    
    async def search(
        self,
        query: str,
        query_id: UUID,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform a DuckDuckGo search query.
        
        Args:
            query: Search query string
            query_id: ID of the research query
            num_results: Number of results to return (max 10)
            
        Returns:
            List of SearchResult objects
            
        Raises:
            Exception: If search fails
        """
        def _run_sync() -> List[SearchResult]:
            try:
                results = self.ddgs.text(
                    query,
                    max_results=min(num_results, 10),
                )

                search_results: List[SearchResult] = []
                for item in list(results):
                    search_results.append(
                        SearchResult(
                            query_id=query_id,
                            source=SearchSource.DUCKDUCKGO,
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                        )
                    )

                return search_results
            except Exception as e:
                raise Exception(f"DuckDuckGo Search error: {str(e)}") from e

        return await asyncio.to_thread(_run_sync)
    
    async def search_with_keywords(
        self,
        query_id: UUID,
        keywords: List[str],
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform search with multiple keywords.
        
        Args:
            query_id: ID of the research query
            keywords: List of keywords to search
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        # Combine keywords into search query
        search_query = " ".join(keywords)
        return await self.search(
            query=search_query,
            query_id=query_id,
            num_results=max_results
        )
