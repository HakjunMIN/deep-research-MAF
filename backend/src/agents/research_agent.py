"""
Research Agent - Executes searches and collects information.

This agent:
1. Executes the research plan from Planning Agent
2. Performs Google and arXiv searches
3. Collects and stores search results
4. Analyzes relevance of results
"""

import logging
from typing import Any, Dict, List

from agent_framework import AgentRunContext

from .base import BaseCustomAgent
from ..models import AgentId, SearchSource
from ..models.research_plan import ResearchPlan
from ..models.search_result import SearchResult
from ..services.azure_openai_service import AzureOpenAIService
from ..services.google_search import GoogleSearchService
from ..services.arxiv_search import ArxivSearchService

logger = logging.getLogger(__name__)


class ResearchAgent(BaseCustomAgent):
    """
    Research Agent executes searches and gathers information.
    
    Responsibilities:
    - Execute research plan steps
    - Perform Google Custom Search
    - Perform arXiv searches
    - Analyze result relevance
    - Store search results
    """
    
    def __init__(self):
        """Initialize Research Agent."""
        super().__init__(
            agent_id=AgentId.RESEARCH,
            agent_name="Research Agent",
            agent_description="Executes searches and collects relevant information"
        )
        self.google_service = GoogleSearchService()
        self.arxiv_service = ArxivSearchService()
        self.openai_service = AzureOpenAIService()
    
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
            
            # Execute each search step
            for idx, step in enumerate(research_plan.search_steps):
                self.log_step(f"Executing step {idx + 1}/{step_count}: {step.description}")
                
                # Execute searches for this step
                step_results = await self._execute_search_step(
                    query_id=query_id,
                    query_content=query.content,
                    step=step
                )
                
                all_results.extend(step_results)
            
            # Analyze and score all results
            self.log_step("Analyzing result relevance")
            scored_results = await self._score_results(query.content, all_results)
            
            # Sort by relevance score (descending)
            scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Store in shared state
            self.set_shared_state(context, "search_results", scored_results)
            
            # Calculate statistics
            stats = self._calculate_statistics(scored_results)
            
            result = {
                "search_results": scored_results,
                "total_results": len(scored_results),
                "statistics": stats
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
        
        # Execute searches based on sources
        for source in step.sources:
            if source == SearchSource.GOOGLE:
                try:
                    google_results = await self.google_service.search(
                        query=search_query,
                        query_id=query_id
                    )
                    # Results already have query_id set
                    results.extend(google_results)
                except Exception as e:
                    logger.error(f"{self.agent_id.value}: Google search failed for query {query_id}: {str(e)}", exc_info=True)
            
            elif source == SearchSource.ARXIV:
                try:
                    arxiv_results = await self.arxiv_service.search_with_keywords(
                        query_id=query_id,
                        keywords=step.keywords,
                        max_results=5
                    )
                    # Results already have query_id set
                    results.extend(arxiv_results)
                except Exception as e:
                    logger.error(f"{self.agent_id.value}: arXiv search failed for query {query_id}: {str(e)}", exc_info=True)
        
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
        for result in results:
            try:
                # Use OpenAI to analyze relevance
                score = await self.openai_service.analyze_relevance(
                    query=query,
                    title=result.title,
                    snippet=result.snippet
                )
                result.relevance_score = score
            except Exception as e:
                # Fallback: basic keyword matching
                result.relevance_score = self._basic_relevance_score(
                    query,
                    result.title,
                    result.snippet
                )
                logger.error(f"{self.agent_id.value}: Relevance scoring failed for query {result.query_id}, using fallback: {str(e)}", exc_info=True)
        
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
                "avg_relevance": 0.0,
                "high_relevance_count": 0
            }
        
        google_count = sum(1 for r in results if r.source == SearchSource.GOOGLE)
        arxiv_count = sum(1 for r in results if r.source == SearchSource.ARXIV)
        
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        high_relevance = sum(1 for r in results if r.relevance_score >= 0.7)
        
        return {
            "total": len(results),
            "google": google_count,
            "arxiv": arxiv_count,
            "avg_relevance": round(avg_relevance, 2),
            "high_relevance_count": high_relevance
        }


# Export
__all__ = ["ResearchAgent"]
