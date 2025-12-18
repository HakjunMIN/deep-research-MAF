"""FastAPI application entry point for Deep Research Agent."""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .api.middleware import setup_all_middleware
from .api.routes import router

# Load environment variables from .env file
load_dotenv()

# Configure logging to follow uvicorn's log level
# uvicorn already sets up logging, so we just configure our format
logging.basicConfig(
    format='[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get uvicorn's log level and apply it to our app loggers
uvicorn_logger = logging.getLogger("uvicorn")
app_log_level = uvicorn_logger.level if uvicorn_logger.level != logging.NOTSET else logging.INFO

# Set our application logger to follow uvicorn's level
logging.getLogger("src").setLevel(app_log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Deep Research Agent API")
    logger.info(f"Log Level: {logging.getLevelName(logger.getEffectiveLevel())}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS', 'http://localhost:5173')}")
    logger.info(f"Request Logging: {os.getenv('ENABLE_REQUEST_LOGGING', 'true')}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down Deep Research Agent API")
    logger.info("=" * 60)


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
    # For production/container apps, use "*" to allow same-origin requests
    allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    enable_request_logging = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    
    logger.info(f"Configuring middleware with origins: {allowed_origins}")
    logger.info(f"Request logging enabled: {enable_request_logging}")
    
    setup_all_middleware(
        app,
        allow_origins=allowed_origins,
        enable_request_logging=enable_request_logging
    )
    
    # Register API routes
    logger.info("Registering API routes")
    app.include_router(router, prefix="", tags=["api"])
    
    # Mount static files (frontend)
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        logger.info(f"Mounting static files from: {static_dir}")
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
    
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
    
    # Serve frontend SPA (catch-all route)
    @app.get("/{full_path:path}", tags=["frontend"])
    async def serve_frontend(full_path: str):
        """Serve the frontend SPA for all non-API routes."""
        # Skip API routes - let them be handled by their respective handlers
        if full_path.startswith(("research", "health", "docs", "redoc", "openapi.json")):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )
        
        static_dir = Path(__file__).parent.parent / "static"
        index_file = static_dir / "index.html"
        
        # If the requested path is a file that exists, serve it
        requested_file = static_dir / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)
        
        # Otherwise, serve index.html for SPA routing
        if index_file.exists():
            return FileResponse(index_file)
        
        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend not found"}
        )
    
    return app


# Create application instance
app = create_app()


# Export for uvicorn
__all__ = ["app"]
