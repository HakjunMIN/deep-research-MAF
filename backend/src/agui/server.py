"""
AG-UI Server integration for Deep Research Agent.

This module provides AG-UI protocol support using Microsoft Agent Framework.
The AG-UI protocol enables:
- Server-Sent Events (SSE) for streaming responses
- Tool call events and results streaming
- Thread management for conversation context
"""

import os
import logging
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from azure.identity import DefaultAzureCredential, AzureCliCredential
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .tools import (
    search_google,
    search_arxiv,
    create_research_plan,
    synthesize_answer,
)

logger = logging.getLogger(__name__)


def get_chat_client() -> AzureOpenAIChatClient:
    """
    Create Azure OpenAI chat client with proper authentication.
    
    Returns:
        Configured AzureOpenAIChatClient instance
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    
    # Use API key if provided, otherwise use DefaultAzureCredential
    if api_key:
        logger.info("Using API key authentication for Azure OpenAI")
        return AzureOpenAIChatClient(
            api_key=api_key,
            endpoint=endpoint,
            deployment_name=deployment_name,
        )
    else:
        logger.info("Using DefaultAzureCredential for Azure OpenAI")
        try:
            credential = DefaultAzureCredential()
        except Exception:
            logger.warning("DefaultAzureCredential failed, falling back to AzureCliCredential")
            credential = AzureCliCredential()
        
        return AzureOpenAIChatClient(
            credential=credential,
            endpoint=endpoint,
            deployment_name=deployment_name,
        )


def create_research_agent() -> ChatAgent:
    """
    Create the Deep Research Agent with all tools.
    
    Returns:
        Configured ChatAgent instance with research tools
    """
    chat_client = get_chat_client()
    
    instructions = """You are a Deep Research Agent that helps users find comprehensive, 
well-sourced answers to their research questions.

Your workflow:
1. When a user asks a research question, use search_google and/or search_arxiv to gather information
2. After receiving search results, READ the results carefully
3. Write a comprehensive answer based on the search results you received

How to use search results:
- The search tools return results with title, url, snippet, and other metadata
- Read through these results and synthesize the information
- Create a well-structured answer with citations
- Use [1], [2], etc. to reference specific sources
- Include the source URLs at the end

Response format:
- Start with a clear introduction
- Present main findings in organized sections
- Include specific details and examples from the sources
- End with a conclusion
- Add a "Sources" section with numbered citations

Example:
User: "latest developments in quantum computing"
1. You call search_google and search_arxiv
2. You receive results about quantum computing breakthroughs
3. You write: "# Latest Developments in Quantum Computing\n\nRecent breakthroughs in quantum computing have... [1]\n\n## Key Developments\n...\n\n## Sources\n[1] Title - URL"

IMPORTANT:
- Always provide a final text response after using tools
- Never end without giving the user an answer
- Use Markdown formatting for better readability
- Include citations to sources"""

    agent = ChatAgent(
        name="DeepResearchAgent",
        instructions=instructions,
        chat_client=chat_client,
        tools=[
            search_google,
            search_arxiv,
            create_research_plan,
        ],
    )
    
    logger.info("Deep Research Agent created with AG-UI tools")
    return agent


def add_agui_endpoints(app: FastAPI, path: str = "/agui") -> None:
    """
    Add AG-UI endpoints to an existing FastAPI app.
    
    Args:
        app: FastAPI application instance
        path: URL path for the AG-UI endpoint
    """
    agent = create_research_agent()
    add_agent_framework_fastapi_endpoint(app, agent, path)
    logger.info(f"AG-UI endpoint registered at {path}")


def create_agui_app(
    title: str = "Deep Research AG-UI Server",
    allow_origins: Optional[list[str]] = None,
) -> FastAPI:
    """
    Create a standalone AG-UI FastAPI application.
    
    Args:
        title: Application title
        allow_origins: CORS allowed origins (defaults to ["*"])
        
    Returns:
        Configured FastAPI application with AG-UI endpoint
    """
    if allow_origins is None:
        allow_origins = ["*"]
    
    app = FastAPI(
        title=title,
        description="AG-UI protocol server for Deep Research Agent",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add AG-UI endpoint at root
    add_agui_endpoints(app, "/")
    
    # Add health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "deep-research-agui"}
    
    logger.info("AG-UI application created")
    return app


# Create default app instance for direct running
app = create_agui_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)
