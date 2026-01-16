"""arXiv API search service."""

import asyncio
from typing import List, Optional

import arxiv

from ..models.search_result import SearchResult
from ..models import SearchSource, UUID


class ArxivSearchService:
    """
    Service for searching arXiv papers.
    
    No authentication required - arXiv API is public.
    
    Rate Limits:
    - Recommended: 1 request per second
    - No daily quota
    
    Best Practices:
    - Use specific search queries
    - Filter by date for recent papers
    - Search by title, author, or category
    """
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize arXiv search service.
        
        Args:
            rate_limit_delay: Delay in seconds between requests (default: 1.0)
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time: Optional[float] = None
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting to respect arXiv API guidelines."""
        if self.last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def search(
        self,
        query: str,
        query_id: UUID,
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance
    ) -> List[SearchResult]:
        """
        Search arXiv papers.
        
        Args:
            query: Search query (supports field-specific searches: ti:title, au:author, cat:category)
            query_id: ID of the research query
            max_results: Maximum number of results to return
            sort_by: Sort criterion (Relevance, LastUpdatedDate, SubmittedDate)
            
        Returns:
            List of SearchResult objects
            
        Example queries:
            - "quantum computing" (all fields)
            - "ti:quantum computing" (title only)
            - "au:Alice Smith" (author)
            - "cat:quant-ph" (category)
        """
        await self._rate_limit()
        
        # Create search
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )
        
        def _run_sync() -> List[SearchResult]:
            search_results: List[SearchResult] = []
            for result in search.results():
                authors = [author.name for author in result.authors]
                search_results.append(
                    SearchResult(
                        query_id=query_id,
                        source=SearchSource.ARXIV,
                        title=result.title,
                        url=result.entry_id,
                        snippet=result.summary[:500] if result.summary else "",
                        authors=authors,
                        published_date=result.published,
                    )
                )
            return search_results

        return await asyncio.to_thread(_run_sync)
    
    async def search_with_keywords(
        self,
        keywords: List[str],
        query_id: UUID,
        max_results: int = 10,
        recent_only: bool = True
    ) -> List[SearchResult]:
        """
        Search arXiv papers using multiple keywords.
        
        Args:
            keywords: List of search keywords
            query_id: ID of the research query
            max_results: Maximum number of results
            recent_only: If True, sort by last updated date to get recent papers
            
        Returns:
            List of SearchResult objects
        """
        # Combine keywords with AND logic
        query = " AND ".join(keywords)
        
        # Sort by date if recent_only is True
        sort_by = arxiv.SortCriterion.LastUpdatedDate if recent_only else arxiv.SortCriterion.Relevance
        
        return await self.search(query, query_id, max_results, sort_by)
    
    async def search_by_category(
        self,
        category: str,
        query_id: UUID,
        keywords: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search arXiv papers by category.
        
        Args:
            category: arXiv category (e.g., "cs.AI", "quant-ph", "math.CO")
            query_id: ID of the research query
            keywords: Optional keywords to refine search
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
            
        Common categories:
            - cs.AI: Artificial Intelligence
            - cs.LG: Machine Learning
            - quant-ph: Quantum Physics
            - math.CO: Combinatorics
        """
        if keywords:
            keyword_query = " AND ".join(keywords)
            query = f"cat:{category} AND ({keyword_query})"
        else:
            query = f"cat:{category}"
        
        return await self.search(query, query_id, max_results)
