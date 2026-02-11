"""Azure OpenAI Service client for LLM interactions."""

import asyncio
import os
from typing import Any, Dict, List, Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
try:
    from openai import AsyncAzureOpenAI
except Exception:  # pragma: no cover
    AsyncAzureOpenAI = None  # type: ignore
from openai.types.chat import ChatCompletion


class AzureOpenAIService:
    """
    Service for interacting with Azure OpenAI API.
    
    Configured via environment variables:
    - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
    - AZURE_OPENAI_DEPLOYMENT_NAME: Deployment name (e.g., gpt-4)
    - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)
    
    Uses DefaultAzureCredential for authentication.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None,
        credential: Optional[DefaultAzureCredential] = None
    ):
        """
        Initialize Azure OpenAI client.
        
        Args:
            endpoint: Azure OpenAI endpoint (defaults to AZURE_OPENAI_ENDPOINT env var)
            deployment_name: Deployment name (defaults to AZURE_OPENAI_DEPLOYMENT_NAME env var)
            api_version: API version (defaults to AZURE_OPENAI_API_VERSION or 2024-02-15-preview)
            credential: Azure credential (defaults to DefaultAzureCredential)
        """
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.credential = credential or DefaultAzureCredential()
        
        if not self.endpoint:
            raise ValueError("Azure OpenAI endpoint is required")
        if not self.deployment_name:
            raise ValueError("Azure OpenAI deployment name is required")

        # Create token provider for Azure AD authentication
        self.token_provider = get_bearer_token_provider(
            self.credential,
            "https://cognitiveservices.azure.com/.default"
        )

        self._async_client = None
        self._sync_client = None

        if AsyncAzureOpenAI is not None:
            self._async_client = AsyncAzureOpenAI(
                azure_ad_token_provider=self.token_provider,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
        else:
            self._sync_client = AzureOpenAI(
                azure_ad_token_provider=self.token_provider,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> ChatCompletion:
        """
        Create a chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments for the API
            
        Returns:
            ChatCompletion response
        """
        if self._async_client is not None:
            response = await self._async_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response

        # Fallback: sync client executed in a thread to avoid blocking the event loop
        if self._sync_client is None:
            self._sync_client = AzureOpenAI(
                azure_ad_token_provider=self.token_provider,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )

        def _call_sync() -> ChatCompletion:
            return self._sync_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        return await asyncio.to_thread(_call_sync)
    
    async def extract_text(self, response: ChatCompletion) -> str:
        """
        Extract text content from a chat completion response.
        
        Args:
            response: ChatCompletion response
            
        Returns:
            Extracted text content
        """
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""
    
    async def generate_keywords(self, query: str) -> List[str]:
        """
        Generate search keywords from a query using LLM.
        
        Args:
            query: Research question
            
        Returns:
            List of extracted keywords
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts relevant keywords for research queries. Return keywords as a comma-separated list."
            },
            {
                "role": "user",
                "content": f"Extract 5-10 relevant keywords for this research question: {query}"
            }
        ]
        
        response = await self.chat_completion(messages, temperature=0.3)
        text = await self.extract_text(response)
        
        # Parse comma-separated keywords
        keywords = [kw.strip() for kw in text.split(",") if kw.strip()]
        return keywords
    
    async def analyze_relevance(self, query: str, snippet: str, title: Optional[str] = None) -> float:
        """
        Analyze the relevance of a search result snippet to a query.
        
        Args:
            query: Research question
            snippet: Search result snippet
            title: Optional title of the search result
            
        Returns:
            Relevance score (0.0 - 1.0)
        """
        content_parts = [f"Query: {query}"]
        if title:
            content_parts.append(f"Title: {title}")
        content_parts.append(f"Snippet: {snippet}")
        content_parts.append("How relevant is this result to the query? (0.0 - 1.0)")
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that evaluates the relevance of search results. Return only a number between 0.0 and 1.0."
            },
            {
                "role": "user",
                "content": "\n\n".join(content_parts)
            }
        ]
        
        response = await self.chat_completion(messages, temperature=0.0, max_tokens=10)
        text = await self.extract_text(response)
        
        try:
            score = float(text.strip())
            return max(0.0, min(1.0, score))  # Clamp to [0.0, 1.0]
        except ValueError:
            return 0.5  # Default to neutral if parsing fails
