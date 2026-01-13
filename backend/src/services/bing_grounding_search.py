"""Bing Grounding Search service using Azure AI Projects."""

import asyncio
import os
from typing import List, Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingAgentTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
)
from azure.identity import DefaultAzureCredential

from ..models.search_result import SearchResult
from ..models import SearchSource, UUID


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

                    search_results: List[SearchResult] = []

                    if hasattr(response, "output_items"):
                        for item in response.output_items:
                            if item.type == "message" and item.content:
                                for content_block in item.content:
                                    if content_block.type == "output_text" and hasattr(
                                        content_block, "annotations"
                                    ):
                                        for annotation in content_block.annotations:
                                            if annotation.type == "url_citation":
                                                search_results.append(
                                                    SearchResult(
                                                        query_id=query_id,
                                                        source=SearchSource.BING,
                                                        title=annotation.title
                                                        if hasattr(annotation, "title")
                                                        else "",
                                                        url=annotation.url,
                                                        snippet=content_block.text[:500]
                                                        if hasattr(content_block, "text")
                                                        else "",
                                                    )
                                                )

                    return search_results[:num_results]
                finally:
                    try:
                        self.client.agents.delete_version(agent.name, agent.version)
                    except Exception:
                        pass
            except Exception as e:
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
