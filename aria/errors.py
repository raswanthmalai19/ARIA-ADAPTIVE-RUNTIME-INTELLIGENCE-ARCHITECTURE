"""
Enhanced API Error Handling for ARIA Runtime
Provides robust error responses with proper HTTP codes
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging
import traceback
from typing import Callable

logger = logging.getLogger("aria.error_handler")


class APIError(Exception):
    """Base class for API errors."""
    
    def __init__(self, message: str, code: int = 500, detail: str = None):
        self.message = message
        self.code = code
        self.detail = detail or message
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error (400)."""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, 400, detail)


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, 429, "Rate limit exceeded. Please wait before making another request.")


class InternalError(APIError):
    """Internal server error (500)."""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, 500, detail or "Internal server error. Please try again later.")


class ModelError(APIError):
    """Model processing error (500)."""
    def __init__(self, message: str):
        super().__init__(message, 500, "Model encountered an error. Please try again with a simpler query.")


class TimeoutError(APIError):
    """Request timeout (504)."""
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message, 504, "Request took too long. Try a shorter query.")


class ResourceError(APIError):
    """Resource exhausted (503)."""
    def __init__(self, message: str = "Resources exhausted"):
        super().__init__(message, 503, "Server is under high load. Please try again shortly.")


def setup_error_handlers(app: FastAPI):
    """
    Setup comprehensive error handling for FastAPI app.
    
    Handles:
    - Pydantic validation errors (422 → 400)
    - APIError exceptions
    - Unhandled exceptions → 500
    """
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle validation errors."""
        logger.warning(f"Validation error: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "validation_error",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        """Handle rate limit errors."""
        logger.warning(f"Rate limit exceeded from {request.client.host}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "rate_limit_exceeded",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(ModelError)
    async def model_error_handler(request: Request, exc: ModelError):
        """Handle model errors."""
        logger.error(f"Model error: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "model_error",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(TimeoutError)
    async def timeout_error_handler(request: Request, exc: TimeoutError):
        """Handle timeout errors."""
        logger.warning(f"Request timeout: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "timeout",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(ResourceError)
    async def resource_error_handler(request: Request, exc: ResourceError):
        """Handle resource exhaustion."""
        logger.error(f"Resource exhaustion: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "resource_exhausted",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle generic API errors."""
        logger.error(f"API error: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error": "api_error",
                "message": exc.message,
                "detail": exc.detail,
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        
        # Don't expose internal details in production
        detail = "An unexpected error occurred. Please try again."
        if os.getenv("ARIA_ENV") == "development":
            detail = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Internal server error",
                "detail": detail,
            }
        )


# Middleware for better error context
def add_error_context_middleware(app: FastAPI):
    """Add request logging and context to errors."""
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        """Log all requests and responses."""
        try:
            response = await call_next(request)
            
            # Log errors
            if response.status_code >= 400:
                logger.warning(
                    f"{request.method} {request.url.path} → {response.status_code} "
                    f"from {request.client.host if request.client else 'unknown'}"
                )
            
            return response
        except Exception as exc:
            logger.error(f"Request crashed: {request.method} {request.url.path}", exc_info=True)
            raise


import os
