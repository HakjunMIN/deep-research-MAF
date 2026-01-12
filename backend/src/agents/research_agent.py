"""
Research Agent - Executes searches and collects information.

This agent:
1. Executes the research plan from Planning Agent
2. Performs Google and arXiv searches
3. Optionally performs DuckDuckGo and Bing searches (controlled via env vars)
4. Collects and stores search results
5. Analyzes relevance of results

Environment Variables:
- ENABLE_GOOGLE_SEARCH: Enable Google Custom Search (default: true)
- ENABLE_ARXIV_SEARCH: Enable arXiv search (default: true)
- ENABLE_DUCKDUCKGO_SEARCH: Enable DuckDuckGo search (default: false)
- ENABLE_BING_SEARCH: Enable Bing Grounding search (default: false)
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agent_framework import AgentRunContext

from .base import BaseCustomAgent
from ..models import AgentId, SearchSource
from ..models.research_plan import ResearchPlan
from ..models.search_result import SearchResult
from ..services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


class ResearchAgent(BaseCustomAgent):
    """
    Research Agent executes searches and gathers information.
    
    Responsibilities:
    - Execute research plan steps
    - Perform Google Custom Search (if enabled)
    - Perform arXiv searches (if enabled)
    - Perform DuckDuckGo searches (if enabled)
    - Perform Bing Grounding searches (if enabled)
    - Analyze result relevance
    - Store search results
    
    Environment Variables:
    - ENABLE_GOOGLE_SEARCH: Enable Google Custom Search (default: "true")
    - ENABLE_ARXIV_SEARCH: Enable arXiv search (default: "true")
    - ENABLE_DUCKDUCKGO_SEARCH: Enable DuckDuckGo search (default: "false")
    - ENABLE_BING_SEARCH: Enable Bing Grounding search (default: "false")
    """
    
    def __init__(self):
        """Initialize Research Agent with configured search services."""
        super().__init__(
            agent_id=AgentId.RESEARCH,
            agent_name="Research Agent",
            agent_description="Executes searches and collects relevant information"
        )
        
        # Check which search services to enable via environment variables
        self.google_enabled = os.getenv("ENABLE_GOOGLE_SEARCH", "true").lower() == "true"
        self.arxiv_enabled = os.getenv("ENABLE_ARXIV_SEARCH", "true").lower() == "true"
        self.duckduckgo_enabled = os.getenv("ENABLE_DUCKDUCKGO_SEARCH", "false").lower() == "true"
        self.bing_enabled = os.getenv("ENABLE_BING_SEARCH", "false").lower() == "true"
        
        # Initialize enabled services
        self.google_service: Optional[Any] = None
        self.arxiv_service: Optional[Any] = None
        self.duckduckgo_service: Optional[Any] = None
        self.bing_service: Optional[Any] = None
        
        if self.google_enabled:
            try:
                from ..services.google_search import GoogleSearchService
                self.google_service = GoogleSearchService()
                logger.info("Google Search service enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Search service: {e}")
                self.google_enabled = False
        
        if self.arxiv_enabled:
            try:
                from ..services.arxiv_search import ArxivSearchService
                self.arxiv_service = ArxivSearchService()
                logger.info("arXiv Search service enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize arXiv Search service: {e}")
                self.arxiv_enabled = False
        
        if self.duckduckgo_enabled:
            try:
                from ..services.duckduckgo_search import DuckDuckGoSearchService
                self.duckduckgo_service = DuckDuckGoSearchService()
                logger.info("DuckDuckGo Search service enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize DuckDuckGo Search service: {e}")
                self.duckduckgo_enabled = False
        
        if self.bing_enabled:
            try:
                from ..services.bing_grounding_search import BingGroundingSearchService
                self.bing_service = BingGroundingSearchService()
                logger.info("Bing Grounding Search service enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Bing Grounding Search service: {e}")
                self.bing_enabled = False
        
        self.openai_service = AzureOpenAIService()

        # Concurrency controls (protects external APIs + speeds up overall runtime)
        # Note: search services may have their own rate limits; keep these modest.
        self.search_concurrency = max(1, int(os.getenv("SEARCH_CONCURRENCY", "4")))
        self.scoring_concurrency = max(1, int(os.getenv("RELEVANCE_SCORING_CONCURRENCY", "6")))
        
        # Store search events for streaming to frontend
        self.search_events: List[Dict[str, Any]] = []
        
        # Log enabled services
        enabled_services = []
        if self.google_enabled:
            enabled_services.append("Google")
        if self.arxiv_enabled:
            enabled_services.append("arXiv")
        if self.duckduckgo_enabled:
            enabled_services.append("DuckDuckGo")
        if self.bing_enabled:
            enabled_services.append("Bing")
        logger.info(f"Research Agent initialized with services: {', '.join(enabled_services) or 'None'}")
    
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Execute research plan and collect search results.
        
        Args:
            context: Agent execution context
            
        Returns:
            Dict with search_results and statistics
        """
        try:
            logger.info("ResearchAgent.execute started")
            # Clear search events for new execution
            self.search_events = []
            
            # Get research plan from context
            research_plan: ResearchPlan = self.get_shared_state(context, "research_plan")
            query = self.get_shared_state(context, "query")
            logger.info(f"Research plan: {research_plan}")
            logger.info(f"Query: {query}")
            query_id = str(query.id)
            
            if not research_plan:
                logger.error("Research plan not found in context")
                raise ValueError("Research plan not found in context")
            
            all_results: List[SearchResult] = []
            step_count = len(research_plan.search_steps)
            
            self.log_step(f"🔍 Starting research with {step_count} search steps...")
            
            # Execute each search step
            for idx, step in enumerate(research_plan.search_steps):
                self.log_step(f"🔎 Executing step {idx + 1}/{step_count}: {step.description}")
                
                # Execute searches for this step
                step_results = await self._execute_search_step(
                    query_id=query_id,
                    query_content=query.content,
                    step=step
                )
                
                self.log_step(f"✓ Found {len(step_results)} results for step {idx + 1}")
                all_results.extend(step_results)
            
            # Analyze and score all results
            self.log_step(f"📊 Analyzing relevance of {len(all_results)} total results...")
            scored_results = await self._score_results(query.content, all_results)
            self.log_step("✓ Relevance analysis complete")
            
            # Sort by relevance score (descending)
            scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Store in shared state
            self.set_shared_state(context, "search_results", scored_results)
            
            # Calculate statistics
            stats = self._calculate_statistics(scored_results)
            
            result = {
                "search_results": scored_results,
                "total_results": len(scored_results),
                "statistics": stats,
                "search_events": self.search_events  # Include search events for frontend
            }
            logger.info(f"ResearchAgent.execute completed. Total results: {len(scored_results)}")
            return result
            
        except Exception as e:
            logger.error(f"ResearchAgent.execute failed: {e}", exc_info=True)
            raise
    
    async def _execute_search_step(
        self,
        query_id: str,
        query_content: str,
        step: Any  # SearchStep from research_plan
    ) -> List[SearchResult]:
        """
        Execute a single search step across specified sources.
        
        Args:
            query_id: Query identifier
            query_content: Original query text
            step: SearchStep instance
            
        Returns:
            List of SearchResult instances
        """
        results: List[SearchResult] = []
        
        # Combine keywords for search
        search_query = " ".join(step.keywords)

        search_semaphore = asyncio.Semaphore(self.search_concurrency)

        async def run_source(source: SearchSource) -> List[SearchResult]:
            async with search_semaphore:
                if source == SearchSource.GOOGLE and self.google_enabled and self.google_service:
                    tool_name = "Google"
                    self.log_step(f"🔍 Google 검색: {search_query}")
                elif source == SearchSource.ARXIV and self.arxiv_enabled and self.arxiv_service:
                    tool_name = "arXiv"
                    self.log_step(f"📚 arXiv 검색: {search_query}")
                elif source == SearchSource.DUCKDUCKGO and self.duckduckgo_enabled and self.duckduckgo_service:
                    tool_name = "DuckDuckGo"
                    self.log_step(f"🦆 DuckDuckGo 검색: {search_query}")
                elif source == SearchSource.BING and self.bing_enabled and self.bing_service:
                    tool_name = "Bing"
                    self.log_step(f"🔎 Bing 검색: {search_query}")
                else:
                    return []

                event_id = str(uuid4())
                event: Dict[str, Any] = {
                    "id": event_id,
                    "tool": tool_name,
                    "query": search_query,
                    "keywords": step.keywords,
                    "status": "searching",
                }
                self.search_events.append(event)
                await self.emit_event({"type": "search_event", **event})

                try:
                    if tool_name == "Google":
                        source_results = await self.google_service.search(
                            query=search_query,
                            query_id=query_id,
                        )
                    elif tool_name == "arXiv":
                        source_results = await self.arxiv_service.search_with_keywords(
                            query_id=query_id,
                            keywords=step.keywords,
                            max_results=5,
                        )
                    elif tool_name == "DuckDuckGo":
                        source_results = await self.duckduckgo_service.search_with_keywords(
                            query_id=query_id,
                            keywords=step.keywords,
                            max_results=10,
                        )
                    else:  # Bing
                        source_results = await self.bing_service.search_with_keywords(
                            query_id=query_id,
                            keywords=step.keywords,
                            max_results=10,
                        )
                    event["status"] = "completed"
                    event["results_count"] = len(source_results)
                    event["results"] = [
                        {"title": str(r.title), "url": str(r.url), "snippet": str(r.snippet)}
                        for r in source_results[:3]
                    ]
                    await self.emit_event({"type": "search_event", **event})
                    return source_results
                except Exception as e:
                    event["status"] = "failed"
                    event["error"] = str(e)
                    await self.emit_event({"type": "search_event", **event})
                    logger.error(
                        f"{self.agent_id.value}: {tool_name} search failed for query {query_id}: {str(e)}",
                        exc_info=True,
                    )
                    return []

        # Execute enabled sources concurrently (bounded)
        tasks = [run_source(source) for source in step.sources]
        if tasks:
            per_source_results = await asyncio.gather(*tasks)
            for chunk in per_source_results:
                results.extend(chunk)
        
        return results
    
    async def _score_results(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Analyze and score search results for relevance.
        
        Args:
            query: Original query text
            results: List of search results
            
        Returns:
            Results with updated relevance_score
        """
        scoring_semaphore = asyncio.Semaphore(self.scoring_concurrency)

        async def score_one(result: SearchResult) -> None:
            async with scoring_semaphore:
                try:
                    score = await self.openai_service.analyze_relevance(
                        query=query,
                        title=result.title,
                        snippet=result.snippet,
                    )
                    result.relevance_score = score
                except Exception as e:
                    result.relevance_score = self._basic_relevance_score(
                        query,
                        result.title,
                        result.snippet,
                    )
                    logger.error(
                        f"{self.agent_id.value}: Relevance scoring failed for query {result.query_id}, using fallback: {str(e)}",
                        exc_info=True,
                    )

        await asyncio.gather(*(score_one(r) for r in results))
        
        return results
    
    def _basic_relevance_score(
        self,
        query: str,
        title: str,
        snippet: str
    ) -> float:
        """
        Calculate basic relevance score using keyword matching.
        
        Args:
            query: Original query
            title: Result title
            snippet: Result snippet
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        query_terms = set(query.lower().split())
        text = f"{title} {snippet}".lower()
        
        # Count matching terms
        matches = sum(1 for term in query_terms if term in text)
        
        # Normalize to 0-1 range
        if not query_terms:
            return 0.5
        
        score = matches / len(query_terms)
        
        # Boost if title contains query terms
        title_lower = title.lower()
        title_matches = sum(1 for term in query_terms if term in title_lower)
        if title_matches > 0:
            score = min(1.0, score + (title_matches / len(query_terms)) * 0.2)
        
        return score
    
    def _calculate_statistics(
        self,
        results: List[SearchResult]
    ) -> Dict[str, Any]:
        """
        Calculate statistics about search results.
        
        Args:
            results: List of search results
            
        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                "total": 0,
                "google": 0,
                "arxiv": 0,
                "duckduckgo": 0,
                "bing": 0,
                "avg_relevance": 0.0,
                "high_relevance_count": 0
            }
        
        google_count = sum(1 for r in results if r.source == SearchSource.GOOGLE)
        arxiv_count = sum(1 for r in results if r.source == SearchSource.ARXIV)
        duckduckgo_count = sum(1 for r in results if r.source == SearchSource.DUCKDUCKGO)
        bing_count = sum(1 for r in results if r.source == SearchSource.BING)
        
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        high_relevance = sum(1 for r in results if r.relevance_score >= 0.7)
        
        return {
            "total": len(results),
            "google": google_count,
            "arxiv": arxiv_count,
            "duckduckgo": duckduckgo_count,
            "bing": bing_count,
            "avg_relevance": round(avg_relevance, 2),
            "high_relevance_count": high_relevance
        }


# Export
__all__ = ["ResearchAgent"]
