"""FastAPI application entry point for Deep Research Agent."""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.middleware import setup_all_middleware
from .api.routes import router

# Load environment variables from .env file
load_dotenv()

# Setup basic logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Deep Research Agent API")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Deep Research Agent API")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="Deep Research Agent API",
        description=(
            "Backend API for Deep Research Agent multi-agent workflow system. "
            "Supports WebSocket for real-time agent state updates and REST for query management."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Setup middleware
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    enable_request_logging = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    
    setup_all_middleware(
        app,
        allow_origins=allowed_origins,
        enable_request_logging=enable_request_logging
    )
    
    # Register routes
    app.include_router(router, prefix="", tags=["api"])
    
    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health_check():
        """Health check endpoint."""
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "deep-research-agent",
                "version": "1.0.0"
            }
        )
    
    return app


# Create application instance
app = create_app()


# Export for uvicorn
__all__ = ["app"]
