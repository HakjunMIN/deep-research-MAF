"""
Planning Agent - Analyzes user query and creates research strategy.

This agent:
1. Analyzes the user's research question
2. Generates relevant search keywords
3. Creates a structured research plan with search steps
4. Determines which sources to use (Google, arXiv)
"""

import logging
from typing import Any, Dict, List

from agent_framework import AgentRunContext

from .base import BaseCustomAgent
from ..models import AgentId, SearchSource
from ..models.research_plan import ResearchPlan, SearchStep
from ..services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


class PlanningAgent(BaseCustomAgent):
    """
    Planning Agent creates research strategy for user queries.
    
    Responsibilities:
    - Query analysis
    - Keyword generation
    - Search step planning
    - Source selection (Google vs arXiv)
    """
    
    def __init__(self):
        """Initialize Planning Agent."""
        super().__init__(
            agent_id=AgentId.PLANNING,
            agent_name="Planning Agent",
            agent_description="Analyzes research questions and creates search strategies"
        )
        self.openai_service = AzureOpenAIService()
    
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Create research plan for the query.
        
        Args:
            context: Agent execution context
            
        Returns:
            Dict with research_plan key containing ResearchPlan instance
        """
        try:
            logger.info("PlanningAgent.execute started")
            # Get query from context - if not set, create it from the task
            query = self.get_shared_state(context, "query")
            logger.info(f"Query from context: {query}")
            
            if query is None:
                # Initialize query from task if not already in state
                # The task should be the query content string
                from ..models.query import ResearchQuery
                from ..models import SearchSource
                
                task_content = getattr(context, 'task', '') or str(context)
                
                # Create a new query object with default sources
                query = ResearchQuery(
                    content=task_content,
                    search_sources=[SearchSource.GOOGLE]  # Default, will be updated if needed
                )
                
                # Store in shared state for other agents
                self.set_shared_state(context, "query", query)
            
            query_content = query.content
            query_id = str(query.id)
            
            # Step 1: Generate keywords
            self.log_step("Generating search keywords")
            keywords = await self._generate_keywords(query_content)
            
            # Step 2: Determine sources
            self.log_step("Determining search sources")
            sources = await self._determine_sources(query_content, keywords)
            
            # Step 3: Create search steps
            self.log_step("Creating search strategy")
            search_steps = await self._create_search_steps(query_content, keywords, sources)
            
            # Step 4: Create research plan
            self.log_step("Finalizing research plan")
            research_plan = ResearchPlan(
                query_id=query_id,
                strategy=await self._generate_strategy_summary(query_content, search_steps),
                keywords=keywords,
                search_steps=search_steps,
                estimated_time=self._estimate_time(search_steps)
            )
            
            # Store in shared state
            self.set_shared_state(context, "research_plan", research_plan)
            
            result = {
                "research_plan": research_plan,
                "keywords": keywords,
                "sources": sources,
                "step_count": len(search_steps)
            }
            logger.info(f"PlanningAgent.execute completed. Result keys: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"PlanningAgent.execute failed: {e}", exc_info=True)
            raise
    
    async def _generate_keywords(self, query: str) -> List[str]:
        """
        Generate relevant search keywords from query.
        
        Args:
            query: User's research question
            
        Returns:
            List of search keywords
        """
        keywords = await self.openai_service.generate_keywords(query)
        
        # Ensure we have at least the original query terms
        if not keywords:
            keywords = query.split()[:5]  # Fallback: first 5 words
        
        return keywords[:10]  # Limit to 10 keywords
    
    async def _determine_sources(
        self,
        query: str,
        keywords: List[str]
    ) -> List[SearchSource]:
        """
        Determine which sources to search based on query content.
        
        Args:
            query: User's research question
            keywords: Generated keywords
            
        Returns:
            List of SearchSource enums
        """
        # Analyze query for academic indicators
        academic_indicators = [
            "paper", "research", "study", "journal", "arxiv",
            "publication", "academic", "scientific", "theory",
            "quantum", "physics", "mathematics", "computer science"
        ]
        
        query_lower = query.lower()
        keyword_text = " ".join(keywords).lower()
        
        # Check if query suggests academic content
        is_academic = any(
            indicator in query_lower or indicator in keyword_text
            for indicator in academic_indicators
        )
        
        # Default: search both sources
        sources = [SearchSource.GOOGLE]
        
        # Add arXiv for academic queries
        if is_academic:
            sources.append(SearchSource.ARXIV)
        
        return sources
    
    async def _create_search_steps(
        self,
        query: str,
        keywords: List[str],
        sources: List[SearchSource]
    ) -> List[SearchStep]:
        """
        Create structured search steps.
        
        Args:
            query: User's research question
            keywords: Generated keywords
            sources: Determined search sources
            
        Returns:
            List of SearchStep instances
        """
        steps = []
        step_num = 1
        
        # Group keywords into themes (up to 3 groups)
        keyword_groups = self._group_keywords(keywords)
        
        for group_keywords in keyword_groups:
            # Determine sources for this step
            step_sources = sources.copy()
            
            steps.append(SearchStep(
                step_number=step_num,
                description=f"Search for: {', '.join(group_keywords)}",
                sources=step_sources,
                keywords=group_keywords
            ))
            step_num += 1
        
        return steps
    
    def _group_keywords(self, keywords: List[str]) -> List[List[str]]:
        """
        Group keywords into logical search groups.
        
        Args:
            keywords: List of all keywords
            
        Returns:
            List of keyword groups (max 3 groups)
        """
        # Simple grouping: split into chunks of 3-4 keywords
        groups = []
        chunk_size = max(3, len(keywords) // 3)
        
        for i in range(0, len(keywords), chunk_size):
            group = keywords[i:i + chunk_size]
            if group:
                groups.append(group)
            
            # Limit to 3 groups
            if len(groups) >= 3:
                break
        
        return groups if groups else [keywords]
    
    async def _generate_strategy_summary(
        self,
        query: str,
        search_steps: List[SearchStep]
    ) -> str:
        """
        Generate a human-readable strategy summary.
        
        Args:
            query: User's research question
            search_steps: Created search steps
            
        Returns:
            Strategy description
        """
        source_names = set()
        for step in search_steps:
            source_names.update(src.value for src in step.sources)
        
        sources_str = " and ".join(source_names)
        step_count = len(search_steps)
        
        return (
            f"Research strategy for '{query}': "
            f"Execute {step_count} search step(s) using {sources_str}, "
            f"focusing on key concepts and related terms."
        )
    
    def _estimate_time(self, search_steps: List[SearchStep]) -> int:
        """
        Estimate total research time in seconds.
        
        Args:
            search_steps: Created search steps
            
        Returns:
            Estimated time in seconds
        """
        # Base time: 10 seconds per search step
        # arXiv has rate limiting (1 req/sec), so add extra time
        base_time = len(search_steps) * 10
        
        # Count arXiv steps
        arxiv_steps = sum(
            1 for step in search_steps
            if SearchSource.ARXIV in step.sources
        )
        
        # Add 5 seconds per arXiv step for rate limiting
        arxiv_time = arxiv_steps * 5
        
        # Analysis and synthesis time: 20 seconds
        processing_time = 20
        
        return base_time + arxiv_time + processing_time


# Export
__all__ = ["PlanningAgent"]
