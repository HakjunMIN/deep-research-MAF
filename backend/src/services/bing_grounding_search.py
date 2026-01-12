"""Bing Grounding Search service using Azure AI Projects.

Note: The OpenAI Responses payload shape can vary between SDK versions
(`output` vs `output_items`). Parsing must be tolerant to avoid silently
returning 0 results.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingAgentTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
)
from azure.identity import DefaultAzureCredential

from ..models.search_result import SearchResult
from ..models import SearchSource, UUID

logger = logging.getLogger(__name__)


class BingGroundingSearchService:
    """
    Service for performing Bing Grounding Search via Azure AI Projects.
    
    Configured via environment variables:
    - AZURE_AI_PROJECT_ENDPOINT: Azure AI Project endpoint URL
    - BING_GROUNDING_CONNECTION_NAME: Bing grounding connection name in AI Foundry
    - AZURE_OPENAI_MODEL: Azure OpenAI model deployment name
    
    This service uses Azure AI Foundry's Bing Grounding tool which provides
    grounded search results with citations for AI applications.
    """
    
    def __init__(
        self,
        project_endpoint: Optional[str] = None,
        bing_connection_name: Optional[str] = None
    ):
        """
        Initialize Bing Grounding Search service.
        
        Args:
            project_endpoint: Azure AI Project endpoint URL
                (defaults to AZURE_AI_PROJECT_ENDPOINT env var)
            bing_connection_name: Bing grounding connection name
                (defaults to BING_GROUNDING_CONNECTION_NAME env var)
        """
        self.project_endpoint = (
            project_endpoint or 
            os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        )
        self.bing_connection_name = (
            bing_connection_name or 
            os.getenv("BING_GROUNDING_CONNECTION_NAME", "bingground")
        )
        
        if not self.project_endpoint:
            raise ValueError("Azure AI Project endpoint is required")
        
        # Initialize Azure AI Project client
        self.client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=DefaultAzureCredential()
        )
        
        # Get Bing grounding connection
        self.bing_connection = self.client.connections.get(
            name=self.bing_connection_name
        )

    @staticmethod
    def _to_builtin(obj: Any) -> Any:
        """Best-effort conversion to JSON-like builtins."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {str(k): BingGroundingSearchService._to_builtin(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [BingGroundingSearchService._to_builtin(v) for v in obj]

        model_dump = getattr(obj, "model_dump", None)
        if callable(model_dump):
            try:
                return BingGroundingSearchService._to_builtin(model_dump())
            except Exception:
                pass

        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            try:
                return BingGroundingSearchService._to_builtin(to_dict())
            except Exception:
                pass

        d = getattr(obj, "__dict__", None)
        if isinstance(d, dict) and d:
            return BingGroundingSearchService._to_builtin(d)

        return str(obj)

    @staticmethod
    def _walk(obj: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(obj, dict):
            yield obj
            for v in obj.values():
                yield from BingGroundingSearchService._walk(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from BingGroundingSearchService._walk(v)

    @staticmethod
    def _extract_output_text(data: Any) -> str:
        texts: List[str] = []
        for node in BingGroundingSearchService._walk(data):
            if node.get("type") == "output_text" and isinstance(node.get("text"), str):
                texts.append(node["text"])
        return "\n".join(t for t in texts if t).strip()

    @staticmethod
    def _extract_url_citations(data: Any) -> List[Dict[str, str]]:
        citations: List[Dict[str, str]] = []
        for node in BingGroundingSearchService._walk(data):
            if node.get("type") == "url_citation" and isinstance(node.get("url"), str):
                citations.append({"url": node["url"], "title": str(node.get("title") or "")})
                continue

            inner = node.get("url_citation")
            if isinstance(inner, dict) and isinstance(inner.get("url"), str):
                citations.append({"url": inner["url"], "title": str(inner.get("title") or "")})

        seen: set[str] = set()
        deduped: List[Dict[str, str]] = []
        for c in citations:
            url = c.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(c)
        return deduped
    
    async def search(
        self,
        query: str,
        query_id: UUID,
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Perform a Bing Grounding search query.
        
        Args:
            query: Search query string
            query_id: ID of the research query
            num_results: Number of results to return
            
        Returns:
            List of SearchResult objects
            
        Raises:
            Exception: If search fails
        """
        def _run_sync() -> List[SearchResult]:
            try:
                bing_tool = BingGroundingAgentTool(
                    bing_grounding=BingGroundingSearchToolParameters(
                        search_configurations=[
                            BingGroundingSearchConfiguration(
                                project_connection_id=self.bing_connection.id
                            )
                        ]
                    )
                )

                openai_client = self.client.get_openai_client()

                from azure.ai.projects.models import PromptAgentDefinition

                agent = self.client.agents.create_version(
                    agent_name="BingSearchAgent",
                    definition=PromptAgentDefinition(
                        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                        instructions="You are a search assistant. Use Bing search to find relevant information.",
                        tools=[bing_tool],
                    ),
                    description="Agent for Bing search",
                )

                try:
                    response = openai_client.responses.create(
                        input=f"Search for: {query}",
                        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
                        tool_choice="required",
                    )

                    data = self._to_builtin(response)

                    # Prefer SDK convenience field if available, otherwise extract from content blocks
                    output_text = getattr(response, "output_text", None)
                    if not isinstance(output_text, str) or not output_text.strip():
                        output_text = self._extract_output_text(data)

                    citations = self._extract_url_citations(data)
                    if not citations:
                        logger.warning(
                            "Bing grounding returned 0 citations. "
                            "If you expected results, verify ENABLE_BING_SEARCH=true, "
                            "AZURE_AI_PROJECT_ENDPOINT/BING_GROUNDING_CONNECTION_NAME, and Azure credentials. "
                            "Response top-level keys=%s",
                            list(data.keys()) if isinstance(data, dict) else type(data),
                        )

                    search_results: List[SearchResult] = []
                    for c in citations[:num_results]:
                        search_results.append(
                            SearchResult(
                                query_id=query_id,
                                source=SearchSource.BING,
                                title=c.get("title") or "",
                                url=c["url"],
                                snippet=(output_text or "")[:500],
                            )
                        )

                    return search_results
                finally:
                    try:
                        self.client.agents.delete_version(agent.name, agent.version)
                    except Exception as cleanup_exc:
                        logger.warning(
                            "Failed to delete BingSearchAgent version %s for agent %s: %s",
                            agent.version,
                            agent.name,
                            cleanup_exc,
                            exc_info=True,
                        )
            except Exception as e:
                logger.error("Bing Grounding Search error: %s", str(e), exc_info=True)
                raise Exception(f"Bing Grounding Search error: {str(e)}") from e

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_run_sync),
                timeout=30.0  
            )
        except asyncio.TimeoutError:
            logger.error("Bing Grounding Search timeout after 30 seconds for query: %s", query)
            raise Exception("Bing Grounding Search timeout after 30 seconds")
    
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
