"""
Reflect Agent - Analyzes research completeness and suggests improvements.

This agent:
1. Reviews collected search results
2. Analyzes coverage of the research question
3. Identifies gaps in information
4. Suggests additional searches if needed (future enhancement)
5. Provides quality feedback
"""

import logging
from typing import Any, Dict, List

from agent_framework import AgentRunContext

from .base import BaseCustomAgent
from ..models import AgentId
from ..models.search_result import SearchResult
from ..services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)
class ReflectAgent(BaseCustomAgent):
    """
    Reflect Agent analyzes research completeness and quality.
    
    Responsibilities:
    - Evaluate search result coverage
    - Identify information gaps
    - Assess answer readiness
    - Provide feedback for content synthesis
    """
    
    def __init__(self):
        """Initialize Reflect Agent."""
        super().__init__(
            agent_id=AgentId.REFLECT,
            agent_name="Reflect Agent",
            agent_description="Analyzes research completeness and suggests improvements"
        )
        self.openai_service = AzureOpenAIService()
    
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Analyze research completeness and provide feedback.
        
        Args:
            context: Agent execution context
            
        Returns:
            Dict with analysis, gaps, and recommendations
        """
        try:
            logger.info("ReflectAgent.execute started")
            # Get data from context
            query = self.get_shared_state(context, "query")
            research_plan = self.get_shared_state(context, "research_plan")
            search_results: List[SearchResult] = self.get_shared_state(context, "search_results")
            logger.info(f"Query: {query}")
            logger.info(f"Search results count: {len(search_results) if search_results else 0}")
            
            if not search_results:
                logger.warning("No search results available")
                return {
                    "completeness_score": 0.0,
                    "is_sufficient": False,
                    "gaps": ["No search results found"],
                    "recommendations": ["Execute search steps to gather information"],
                    "feedback": "Cannot proceed without search results"
                }
            
            # Step 1: Analyze result quality
            self.log_step("Analyzing result quality")
            quality_analysis = await self._analyze_quality(search_results)
            
            # Step 2: Check topic coverage
            self.log_step("Checking topic coverage")
            coverage_analysis = await self._analyze_coverage(
                query.content,
                research_plan.keywords,
                search_results
            )
            
            # Step 3: Generate recommendations
            self.log_step("Generating recommendations")
            recommendations = await self._generate_recommendations(
                query.content,
                quality_analysis,
                coverage_analysis
            )
            
            # Calculate overall completeness score
            completeness_score = self._calculate_completeness_score(
                quality_analysis,
                coverage_analysis
            )
            
            # Determine if sufficient for synthesis
            is_sufficient = completeness_score >= 0.6 and len(search_results) >= 3
            
            # Store feedback in shared state
            feedback_data = {
                "completeness_score": completeness_score,
                "quality_analysis": quality_analysis,
                "coverage_analysis": coverage_analysis,
                "is_sufficient": is_sufficient
            }
            self.set_shared_state(context, "reflect_feedback", feedback_data)
            
            result = {
                "completeness_score": completeness_score,
                "is_sufficient": is_sufficient,
                "gaps": coverage_analysis.get("gaps", []),
                "recommendations": recommendations,
                "feedback": self._generate_feedback_summary(
                    completeness_score,
                    is_sufficient,
                    coverage_analysis
                )
            }
            logger.info(f"ReflectAgent.execute completed. Completeness: {completeness_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"ReflectAgent.execute failed: {e}", exc_info=True)
            raise
    
    async def _analyze_quality(
        self,
        results: List[SearchResult]
    ) -> Dict[str, Any]:
        """
        Analyze the quality of search results.
        
        Args:
            results: List of search results
            
        Returns:
            Quality analysis dictionary
        """
        if not results:
            return {
                "avg_relevance": 0.0,
                "high_quality_count": 0,
                "source_diversity": 0.0
            }
        
        # Calculate average relevance
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        
        # Count high-quality results (relevance >= 0.7)
        high_quality = [r for r in results if r.relevance_score >= 0.7]
        
        # Check source diversity
        sources = set(r.source for r in results)
        source_diversity = len(sources) / 2.0  # Normalize (max 2 sources: Google, arXiv)
        
        return {
            "avg_relevance": round(avg_relevance, 2),
            "high_quality_count": len(high_quality),
            "source_diversity": round(source_diversity, 2),
            "total_results": len(results)
        }
    
    async def _analyze_coverage(
        self,
        query: str,
        keywords: List[str],
        results: List[SearchResult]
    ) -> Dict[str, Any]:
        """
        Analyze how well results cover the query topics.
        
        Args:
            query: Original research question
            keywords: Generated keywords from planning
            results: Search results
            
        Returns:
            Coverage analysis dictionary
        """
        # Combine all result text
        all_text = " ".join(
            f"{r.title} {r.snippet}" for r in results
        ).lower()
        
        # Check keyword coverage
        covered_keywords = []
        missing_keywords = []
        
        for keyword in keywords:
            if keyword.lower() in all_text:
                covered_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        coverage_ratio = (
            len(covered_keywords) / len(keywords)
            if keywords else 0.0
        )
        
        # Identify gaps (keywords not well covered)
        gaps = []
        if coverage_ratio < 0.7:
            gaps.append(f"Missing coverage for: {', '.join(missing_keywords[:3])}")
        
        if len(results) < 5:
            gaps.append("Limited number of search results")
        
        return {
            "coverage_ratio": round(coverage_ratio, 2),
            "covered_keywords": covered_keywords,
            "missing_keywords": missing_keywords,
            "gaps": gaps
        }
    
    async def _generate_recommendations(
        self,
        query: str,
        quality_analysis: Dict[str, Any],
        coverage_analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for content synthesis.
        
        Args:
            query: Original research question
            quality_analysis: Quality analysis results
            coverage_analysis: Coverage analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Quality-based recommendations
        if quality_analysis["avg_relevance"] < 0.5:
            recommendations.append(
                "Consider refining search keywords for better relevance"
            )
        
        if quality_analysis["high_quality_count"] < 3:
            recommendations.append(
                "Focus on high-quality sources with strong relevance"
            )
        
        # Coverage-based recommendations
        if coverage_analysis["coverage_ratio"] < 0.7:
            missing = coverage_analysis["missing_keywords"][:3]
            recommendations.append(
                f"Address missing topics: {', '.join(missing)}"
            )
        
        # Source diversity recommendation
        if quality_analysis["source_diversity"] < 0.5:
            recommendations.append(
                "Expand search to include more diverse sources"
            )
        
        # Default recommendation if all looks good
        if not recommendations:
            recommendations.append(
                "Results are sufficient for comprehensive answer synthesis"
            )
        
        return recommendations
    
    def _calculate_completeness_score(
        self,
        quality_analysis: Dict[str, Any],
        coverage_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate overall completeness score.
        
        Args:
            quality_analysis: Quality metrics
            coverage_analysis: Coverage metrics
            
        Returns:
            Completeness score (0.0 to 1.0)
        """
        # Weight components
        quality_weight = 0.5
        coverage_weight = 0.5
        
        # Quality component (avg relevance)
        quality_score = quality_analysis["avg_relevance"]
        
        # Coverage component
        coverage_score = coverage_analysis["coverage_ratio"]
        
        # Weighted average
        completeness = (
            quality_score * quality_weight +
            coverage_score * coverage_weight
        )
        
        return round(completeness, 2)
    
    def _generate_feedback_summary(
        self,
        completeness_score: float,
        is_sufficient: bool,
        coverage_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable feedback summary.
        
        Args:
            completeness_score: Overall completeness score
            is_sufficient: Whether results are sufficient
            coverage_analysis: Coverage details
            
        Returns:
            Feedback summary string
        """
        if is_sufficient:
            return (
                f"Research is {int(completeness_score * 100)}% complete. "
                "Results are sufficient for synthesizing a comprehensive answer."
            )
        else:
            gaps = coverage_analysis.get("gaps", [])
            gap_str = "; ".join(gaps) if gaps else "quality or coverage issues"
            return (
                f"Research is {int(completeness_score * 100)}% complete. "
                f"Identified gaps: {gap_str}. "
                "Proceeding with available information."
            )


# Export
__all__ = ["ReflectAgent"]
