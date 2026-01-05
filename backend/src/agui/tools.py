"""
AG-UI backend tools for Deep Research Agent.

These tools are executed on the backend and their progress/results are 
streamed to the client in real-time via AG-UI protocol.
"""

import logging
import uuid
from typing import Annotated, Any

from agent_framework import ai_function
from pydantic import Field

from ..models import SearchSource
from ..models.research_plan import ResearchPlan, SearchStep
from ..models.search_result import SearchResult
from ..models.synthesized_answer import SynthesizedAnswer, SourceCitation, AnswerMetadata
from ..services.google_search import GoogleSearchService
from ..services.arxiv_search import ArxivSearchService
from ..services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)

# Initialize services (singleton pattern)
_google_service = None
_arxiv_service = None
_openai_service = None


def get_google_service() -> GoogleSearchService:
    """Get or create Google search service instance."""
    global _google_service
    if _google_service is None:
        _google_service = GoogleSearchService()
    return _google_service


def get_arxiv_service() -> ArxivSearchService:
    """Get or create arXiv search service instance."""
    global _arxiv_service
    if _arxiv_service is None:
        _arxiv_service = ArxivSearchService()
    return _arxiv_service


def get_openai_service() -> AzureOpenAIService:
    """Get or create Azure OpenAI service instance."""
    global _openai_service
    if _openai_service is None:
        _openai_service = AzureOpenAIService()
    return _openai_service


@ai_function
async def search_google(
    query: Annotated[str, Field(description="The search query to execute on Google")],
    max_results: Annotated[int, Field(description="Maximum number of results to return")] = 10,
) -> dict[str, Any]:
    """
    Search Google for relevant web pages and articles.
    
    Use this tool when you need to find general web content, news articles,
    documentation, or any publicly available information on the internet.
    """
    logger.info(f"Executing Google search: {query}")
    try:
        service = get_google_service()
        results = await service.search(
            query=query,
            query_id=str(uuid.uuid4()),
            num_results=max_results
        )
        
        # Convert SearchResult objects to dictionaries
        result_dicts = []
        for r in results:
            result_dicts.append({
                "title": r.title,
                "url": str(r.url),  # Convert HttpUrl to string for JSON serialization
                "snippet": r.snippet,
                "source": r.source.value if hasattr(r.source, 'value') else str(r.source),
                "relevance_score": r.relevance_score,
            })
        
        logger.info(f"Google search found {len(result_dicts)} results")
        return {
            "query": query,
            "source": "google",
            "results_count": len(result_dicts),
            "results": result_dicts,
        }
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        return {
            "query": query,
            "source": "google",
            "error": str(e),
            "results_count": 0,
            "results": [],
        }


@ai_function
async def search_arxiv(
    query: Annotated[str, Field(description="The search query for academic papers")],
    max_results: Annotated[int, Field(description="Maximum number of papers to return")] = 10,
) -> dict[str, Any]:
    """
    Search arXiv for academic papers and research articles.
    
    Use this tool when the user's question is about scientific research,
    academic topics, or when they need peer-reviewed sources.
    """
    logger.info(f"Executing arXiv search: {query}")
    try:
        service = get_arxiv_service()
        results = await service.search(
            query=query,
            query_id=str(uuid.uuid4()),
            max_results=max_results
        )
        
        # Convert SearchResult objects to dictionaries
        result_dicts = []
        for r in results:
            result_dicts.append({
                "title": r.title,
                "url": str(r.url),  # Convert HttpUrl to string for JSON serialization
                "snippet": r.snippet,
                "source": r.source.value if hasattr(r.source, 'value') else str(r.source),
                "relevance_score": r.relevance_score,
                "authors": getattr(r, 'authors', []),
                "published_date": str(getattr(r, 'published_date', '')),
            })
        
        logger.info(f"arXiv search found {len(result_dicts)} results")
        return {
            "query": query,
            "source": "arxiv",
            "results_count": len(result_dicts),
            "results": result_dicts,
        }
    except Exception as e:
        logger.error(f"arXiv search failed: {e}")
        return {
            "query": query,
            "source": "arxiv",
            "error": str(e),
            "results_count": 0,
            "results": [],
        }


@ai_function
async def create_research_plan(
    query: Annotated[str, Field(description="The research question to plan for")],
    sources: Annotated[list[str], Field(description="List of sources to use: 'google', 'arxiv'")] = None,
) -> dict[str, Any]:
    """
    Create a research plan with keywords and search steps.
    
    Use this tool to analyze a research question and create a structured
    plan before executing searches. This helps ensure comprehensive coverage
    of the topic.
    """
    logger.info(f"Creating research plan for: {query}")
    
    if sources is None:
        sources = ["google", "arxiv"]
    
    try:
        service = get_openai_service()
        
        # Generate keywords using Azure OpenAI
        keyword_prompt = f"""Analyze this research question and generate 5-8 relevant search keywords:

Question: {query}

Return only the keywords, one per line, no numbering or bullets."""
        
        messages = [{"role": "user", "content": keyword_prompt}]
        keywords_response = await service.chat_completion(messages, temperature=0.3)
        keywords_text = await service.extract_text(keywords_response)
        keywords = [k.strip() for k in keywords_text.strip().split('\n') if k.strip()]
        
        # Create search steps
        search_steps = []
        source_enums = []
        for src in sources:
            if src.lower() == "google":
                source_enums.append(SearchSource.GOOGLE)
            elif src.lower() == "arxiv":
                source_enums.append(SearchSource.ARXIV)
        
        # Main query search
        search_steps.append({
            "description": f"Search for main topic: {query}",
            "keywords": keywords[:3],
            "sources": sources,
        })
        
        # Specific aspects search
        if len(keywords) > 3:
            search_steps.append({
                "description": "Search for specific aspects and details",
                "keywords": keywords[3:],
                "sources": sources,
            })
        
        # Generate strategy summary
        strategy_prompt = f"""Create a brief research strategy summary (2-3 sentences) for this question:
Question: {query}
Keywords: {', '.join(keywords)}"""
        
        messages = [{"role": "user", "content": strategy_prompt}]
        strategy_response = await service.chat_completion(messages, temperature=0.5)
        strategy = await service.extract_text(strategy_response)
        
        plan = {
            "query": query,
            "strategy": strategy.strip(),
            "keywords": keywords,
            "search_steps": search_steps,
            "sources": sources,
        }
        
        logger.info(f"Research plan created with {len(keywords)} keywords and {len(search_steps)} steps")
        return plan
        
    except Exception as e:
        logger.error(f"Failed to create research plan: {e}")
        return {
            "query": query,
            "error": str(e),
            "keywords": [],
            "search_steps": [],
            "sources": sources,
        }


@ai_function
async def synthesize_answer(
    query: Annotated[str, Field(description="The original research question")],
    search_results: Annotated[list[dict], Field(description="List of search results to synthesize")] = None,
) -> dict[str, Any]:
    """
    Synthesize a comprehensive answer from search results.
    
    Use this tool after gathering search results to create a well-structured,
    cited answer that addresses the user's research question.
    """
    logger.info(f"Synthesizing answer for: {query}")
    
    # Handle None search_results
    if search_results is None:
        search_results = []
    
    if not search_results:
        return {
            "query": query,
            "error": "No search results provided",
            "content": "I couldn't find relevant information to answer your question.",
            "sources": [],
        }
    
    try:
        service = get_openai_service()
        
        # Prepare context from search results
        context_parts = []
        sources = []
        for i, result in enumerate(search_results[:10], 1):  # Limit to top 10
            title = result.get("title", "Unknown")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            
            context_parts.append(f"[{i}] {title}\n{snippet}")
            sources.append({
                "index": i,
                "title": title,
                "url": url,
                "snippet": snippet[:200],
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate synthesized answer
        synthesis_prompt = f"""Based on the following search results, provide a comprehensive answer to the research question.
Include citations using [n] format to reference the sources.

Research Question: {query}

Search Results:
{context}

Provide a well-structured answer with:
1. A clear introduction
2. Main findings and details
3. A brief conclusion
4. Use [n] citations to reference sources

Answer:"""
        
        messages = [{"role": "user", "content": synthesis_prompt}]
        answer_response = await service.chat_completion(messages, temperature=0.5)
        answer_content = await service.extract_text(answer_response)
        
        result = {
            "query": query,
            "content": answer_content.strip(),
            "sources": sources,
            "sources_count": len(sources),
            "confidence": 0.85,
        }
        
        logger.info(f"Answer synthesized with {len(sources)} sources")
        return result
        
    except Exception as e:
        logger.error(f"Failed to synthesize answer: {e}")
        return {
            "query": query,
            "error": str(e),
            "content": "An error occurred while synthesizing the answer.",
            "sources": [],
        }
