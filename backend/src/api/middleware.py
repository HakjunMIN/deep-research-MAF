"""FastAPI middleware for CORS and error handling."""

import logging
import traceback
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI, allow_origins: list[str] | None = None) -> None:
    """
    Configure CORS middleware for the application.
    
    Args:
        app: FastAPI application instance
        allow_origins: List of allowed origins (defaults to ["http://localhost:5173"])
    """
    if allow_origins is None:
        # Default to Vite dev server
        allow_origins = ["http://localhost:5173"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS configured with allowed origins: {allow_origins}")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global error handling.
    
    Catches all exceptions and returns consistent JSON error responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any errors.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response (either from handler or error response)
        """
        try:
            response = await call_next(request)
            return response
        
        except ValueError as e:
            # Validation errors (400 Bad Request)
            logger.warning(f"Validation error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "ValidationError",
                    "message": str(e),
                    "details": None
                }
            )
        
        except PermissionError as e:
            # Permission errors (403 Forbidden)
            logger.warning(f"Permission error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "PermissionError",
                    "message": str(e),
                    "details": None
                }
            )
        
        except FileNotFoundError as e:
            # Not found errors (404 Not Found)
            logger.warning(f"Not found error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "NotFoundError",
                    "message": str(e),
                    "details": None
                }
            )
        
        except Exception as e:
            # Unexpected errors (500 Internal Server Error)
            logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "details": str(e)
                }
            )


def setup_error_handling(app: FastAPI) -> None:
    """
    Add error handling middleware to the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(ErrorHandlingMiddleware)
    logger.info("Error handling middleware configured")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests.
    
    Logs request method, path, and response status.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from handler
        """
        # Log request
        logger.info(
            f'{{"event": "http_request", "method": "{request.method}", '
            f'"path": "{request.url.path}", "client": "{request.client.host if request.client else "unknown"}"}}'
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.info(
            f'{{"event": "http_response", "method": "{request.method}", '
            f'"path": "{request.url.path}", "status_code": {response.status_code}}}'
        )
        
        return response


def setup_request_logging(app: FastAPI) -> None:
    """
    Add request logging middleware to the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware configured")


def setup_all_middleware(
    app: FastAPI,
    allow_origins: list[str] | None = None,
    enable_request_logging: bool = True
) -> None:
    """
    Setup all middleware for the application.
    
    Args:
        app: FastAPI application instance
        allow_origins: List of allowed CORS origins
        enable_request_logging: Whether to enable request logging
    """
    setup_cors(app, allow_origins)
    setup_error_handling(app)
    
    if enable_request_logging:
        setup_request_logging(app)
    
    logger.info("All middleware configured successfully")


# Export main functions
__all__ = [
    "setup_cors",
    "setup_error_handling",
    "setup_request_logging",
    "setup_all_middleware",
    "ErrorHandlingMiddleware",
    "RequestLoggingMiddleware"
]
