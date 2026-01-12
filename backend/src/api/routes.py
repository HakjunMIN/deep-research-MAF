"""FastAPI routes for Deep Research Agent API."""

import json
import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..models import SearchSource
from ..models.search_result import SearchResult
from ..models.synthesized_answer import SynthesizedAnswer
from ..workflows.group_chat import ResearchWorkflow

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Ensure INFO level is enabled

# Custom JSON encoder for UUID and datetime
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for UUID and datetime objects."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Pydantic URL types (HttpUrl/AnyUrl) may appear in models and need stringification
        module = getattr(obj.__class__, "__module__", "")
        name = getattr(obj.__class__, "__name__", "")
        if (module.startswith("pydantic_core") and name == "Url") or (
            module.startswith("pydantic") and name.endswith("Url")
        ):
            return str(obj)
        return super().default(obj)

# Router instance
router = APIRouter()


# Request/Response models
class ResearchRequest(BaseModel):
    """Request body for research query."""
    content: str = Field(..., min_length=1, max_length=2000, description="Research question text")
    search_sources: List[SearchSource] = Field(..., min_length=1, description="Search sources to use")


class ResearchResponse(BaseModel):
    """Response with complete research results from multi-agent conversation."""
    content: str = Field(..., description="Research question")
    answer: SynthesizedAnswer
    research_plan: dict | None
    search_results: List[SearchResult]


# ============================================================================
# Query Management Endpoints
# ============================================================================

@router.post("/research", status_code=status.HTTP_200_OK, response_model=ResearchResponse)
async def submit_research(request: ResearchRequest) -> ResearchResponse:
    """
    Submit a research query and get complete results synchronously.
    
    This executes the multi-agent workflow and waits for completion.
    
    Args:
        request: Research request with question and sources
        
    Returns:
        Complete research results with answer
        
    Raises:
        HTTPException: If validation or workflow execution fails
    """
    try:
        print(f"[DEBUG routes.py] Starting research for: {request.content[:50]}...")
        logger.info(f"Starting research for: {request.content[:50]}...")
        print(f"[DEBUG routes.py] Search sources: {request.search_sources}")
        logger.info(f"Search sources: {request.search_sources}")
        
        # Create workflow instance
        logger.info("Creating workflow instance...")
        workflow = ResearchWorkflow()
        logger.info("Workflow instance created successfully")
        
        # Execute workflow synchronously
        logger.info(f"Executing workflow with query: {request.content[:50]}...")
        logger.info(f"Search sources for workflow: {[str(src) for src in request.search_sources]}")
        result = await workflow.execute_query(
            query_content=request.content,
            search_sources=[str(src) for src in request.search_sources],
            ws_callback=None
        )
        logger.info(f"Workflow completed successfully. Result keys: {list(result.keys())}")
        
        # Extract content writing agent result (key is 'content' from workflow)
        content_result = result.get("content")
        logger.info(f"Content result type: {type(content_result)}, value: {content_result}")
        if not content_result:
            logger.error(f"No content result. Full result: {result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate answer"
            )
        
        # Extract the actual data from the agent result
        # content_result should be a dict with 'data' key containing the agent's return value
        content_data = content_result.get("data", {})
        logger.info(f"Content data type: {type(content_data)}, keys: {list(content_data.keys()) if isinstance(content_data, dict) else 'not a dict'}")
        
        # Extract synthesized_answer from content_data
        if isinstance(content_data, dict):
            synthesized_answer = content_data.get("synthesized_answer")
            if synthesized_answer:
                # synthesized_answer is a SynthesizedAnswer object
                answer = synthesized_answer
                logger.info("Using synthesized_answer from content_data")
            else:
                # Fallback: try to extract text content
                answer_text = content_data.get("content", "") or content_result.get("text", "")
                if not answer_text:
                    logger.error(f"No synthesized_answer or content. content_data: {content_data}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="No answer content generated"
                    )
                # Build basic synthesized answer
                answer = SynthesizedAnswer(
                    content=answer_text,
                    sources=[],
                    confidence=0.8,
                    citations=[]
                )
        else:
            logger.error(f"content_data is not a dict: {content_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid content data format"
            )
        
        logger.info(f"Answer extracted successfully. Content length: {len(answer.content) if hasattr(answer, 'content') else 0}")
        
        # Extract research_plan and search_results from other agents
        research_plan = None
        search_results = []
        
        planning_result = result.get("planning")
        if planning_result and isinstance(planning_result.get("data"), dict):
            plan_obj = planning_result["data"].get("research_plan")
            if plan_obj and hasattr(plan_obj, 'model_dump'):
                research_plan = plan_obj.model_dump()
            elif plan_obj:
                research_plan = dict(plan_obj) if isinstance(plan_obj, dict) else None
        
        research_result = result.get("research")
        if research_result and isinstance(research_result.get("data"), dict):
            search_results = research_result["data"].get("search_results", [])
        
        # Build response
        response = ResearchResponse(
            content=request.content,
            answer=answer,
            research_plan=research_plan,
            search_results=search_results
        )
        
        logger.info("Research completed successfully")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )


@router.post("/research/stream", status_code=status.HTTP_200_OK)
async def submit_research_stream(request: ResearchRequest):
    """
    Submit a research query and stream results in real-time using SSE.
    
    This executes the multi-agent workflow and streams:
    - Agent status updates (thinking, processing)
    - Character-by-character answer streaming
    - Final results
    
    Args:
        request: Research request with question and sources
        
    Returns:
        SSE stream with agent updates and results
        
    Raises:
        HTTPException: If validation or workflow execution fails
    """
    async def event_generator():
        try:
            logger.info(f"Starting streaming research for: {request.content[:50]}...")
            
            # Create workflow instance
            workflow = ResearchWorkflow()
            
            # Execute workflow with streaming
            async for event in workflow.execute_query_stream(
                query_content=request.content,
                search_sources=[str(src) for src in request.search_sources]
            ):
                # Send event as SSE
                event_data = json.dumps(event, ensure_ascii=False, cls=CustomJSONEncoder)
                yield f"data: {event_data}\n\n"
            
            logger.info("Streaming research completed")
            
        except Exception as e:
            logger.error(f"Streaming research failed: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# Export router
__all__ = ["router"]
