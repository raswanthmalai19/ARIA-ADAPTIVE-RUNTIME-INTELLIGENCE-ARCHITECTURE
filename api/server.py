"""
ARIA API Server

FastAPI application serving the ARIA engine via REST API
and the web dashboard via static files.
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from aria.engine import ARIAEngine
from aria.config import get_config
from api.routes import router, set_engine

logger = logging.getLogger("aria.server")

# Setup rotating file handler for logs
def _setup_logging():
    """Configure file-based logging."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "aria_server.log",
        maxBytes=10_000_000,
        backupCount=5
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logging.getLogger().addHandler(handler)

_setup_logging()


# Global engine and loader
engine: ARIAEngine | None = None
loader = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup."""
    global engine, loader
    from api.loader import AsyncModelLoader
    
    logger.info("Starting ARIA server...")
    
    # Initialize loader
    loader = AsyncModelLoader()
    
    # Create and initialize engine quickly
    config = get_config()
    import os
    exec_mode = os.getenv("ARIA_EXECUTION_MODE", "dynamic_layers")
    engine = ARIAEngine(config, execution_mode=exec_mode)
    set_engine(engine)
    
    # Start model loading in background via asyncio task
    # This schedules the model loading without blocking
    asyncio.create_task(loader.start_loading(engine))
    
    logger.info("ARIA server ready (model warming up in background)")

    yield

    # Cleanup
    if engine:
        engine.shutdown()
    logger.info("ARIA server stopped")


# Create FastAPI app
app = FastAPI(
    title="ARIA",
    description="Adaptive Runtime Intelligence Architecture — API Server",
    version="0.2.0",
    lifespan=lifespan,
    openapi_url=None,  # Disable OpenAPI doc generation for faster startup
    docs_url=None,  # Skip API docs
    redoc_url=None,  # Skip ReDoc
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions globally."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if getattr(app, "debug", False) else None,
        }
    )

# Include API routes
app.include_router(router)

# Serve dashboard static files
dashboard_dir = Path(__file__).parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(dashboard_dir / "static")),
        name="static",
    )

    templates = Jinja2Templates(directory=str(dashboard_dir / "templates"))

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Serve the ARIA dashboard."""
        return templates.TemplateResponse("index.html", {"request": request})
else:
    @app.get("/")
    async def root():
        return {
            "name": "ARIA",
            "version": "0.2.0",
            "status": "running",
            "docs": "/docs",
        }


def run_server():
    """Run the ARIA API server."""
    import uvicorn
    config = get_config()
    uvicorn.run(
        "api.server:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    run_server()
