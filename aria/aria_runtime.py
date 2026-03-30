#!/usr/bin/env python3
"""
ARIA Runtime Service — Standalone Daemon

The runtime runs ARIA as an independent service that listens on HTTP.
Any app (Python, JavaScript, Go, etc.) can connect and request inference.

Usage:
    aria-runtime                          # Start on localhost:8000
    aria-runtime --host 0.0.0.0 --port 8000  # Bind to all interfaces
    aria-runtime --config /etc/aria/config.yaml
    aria-runtime --dev                    # Development mode
    aria-runtime --pidfile /var/run/aria.pid

Environment:
    ARIA_HOST=0.0.0.0
    ARIA_PORT=8000
    ARIA_WORKERS=4
    ARIA_MODEL=mlx-community/Qwen2.5-3B-Instruct-4bit
"""

import sys
import os
import signal
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator
import argparse
import json
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from aria.engine import ARIAEngine
from aria.config import ARIAConfig
from aria.hardening import (
    input_validator,
    rate_limiter,
    response_cache,
    error_handler,
    memory_optimizer,
    performance_monitor,
)

logger = logging.getLogger("aria.runtime")


# ─────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────


class QueryRequest(BaseModel):
    """Inference request."""

    text: str = Field(..., min_length=1, max_length=10000)
    mode: str = Field(default="adaptive", pattern="^(adaptive|baseline|cascade)$")
    timeout_ms: int = Field(default=30000, ge=1000, le=60000)


class QueryResponse(BaseModel):
    """Inference response."""

    output: str
    latency_ms: float
    tokens_generated: int
    tokens_per_second: float
    complexity: str
    mode: str
    layers_used: int
    total_layers: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    model: str
    memory_percent: float


class StatusResponse(BaseModel):
    """Status endpoint response."""

    status: str
    version: str
    model: str
    execution_mode: str
    memory_usage: dict
    uptime_seconds: float


# ─────────────────────────────────────────────
# ARIA Runtime Service
# ─────────────────────────────────────────────


class ARIARuntime:
    """Production ARIA runtime service."""

    VERSION = "0.2.0"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        workers: int = 1,
        config_path: Optional[str] = None,
        pidfile: Optional[str] = None,
        dev_mode: bool = False,
    ):
        self.host = host
        self.port = port
        self.workers = workers
        self.config_path = config_path
        self.pidfile = pidfile
        self.dev_mode = dev_mode
        self.engine: Optional[ARIAEngine] = None
        self.app: Optional[FastAPI] = None
        self.startup_time = None

    def setup(self):
        """Initialize runtime components."""
        logger.info("=" * 70)
        logger.info("ARIA Runtime Service v%s", self.VERSION)
        logger.info("=" * 70)
        logger.info("Initializing ARIA Engine...")

        # Load config
        if self.config_path:
            logger.info("Loading config from: %s", self.config_path)
            config = ARIAConfig.from_yaml(self.config_path)
        else:
            config = ARIAConfig()
            logger.info("Using default configuration")

        # Initialize ARIA engine
        self.engine = ARIAEngine(config=config, execution_mode="dynamic_layers")
        self.engine.initialize()

        self.startup_time = asyncio.get_event_loop().time()

        logger.info("✓ Engine initialized: %s", config.model.name)
        logger.info("✓ Execution mode: dynamic_layers")
        logger.info("✓ Ready to accept requests on %s:%s", self.host, self.port)
        logger.info("=" * 70)

    def create_app(self) -> FastAPI:
        """Create FastAPI application."""
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
        
        app = FastAPI(
            title="ARIA Runtime",
            description="Adaptive Runtime Intelligence Architecture - Inference Service",
            version=self.VERSION,
            docs_url="/docs",
            openapi_url="/openapi.json",
        )

        # CORS for local development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Serve ARIA GUI
        @app.get("/")
        async def root():
            """Serve main GUI page."""
            gui_path = Path(__file__).parent.parent / "dashboard" / "templates" / "app.html"
            if gui_path.exists():
                return FileResponse(gui_path)
            return {"message": "ARIA Runtime API"}
        
        @app.get("/gui")
        async def gui():
            """Serve main GUI page."""
            gui_path = Path(__file__).parent.parent / "dashboard" / "templates" / "app.html"
            if gui_path.exists():
                return FileResponse(gui_path)
            raise HTTPException(status_code=404, detail="GUI not found")

        # ─────────────────────────────────────────────
        # Health & Status Endpoints
        # ─────────────────────────────────────────────

        @app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint."""
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            hw_state = self.engine.memory.get_state()
            return HealthResponse(
                status="healthy",
                version=self.VERSION,
                model=self.engine.config.model.name,
                memory_percent=hw_state.memory_used_percent,
            )

        @app.get("/status", response_model=StatusResponse)
        async def status():
            """Detailed system status."""
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            uptime = (
                asyncio.get_event_loop().time() - self.startup_time
                if self.startup_time
                else 0
            )
            hw_state = self.engine.memory.get_state()
            
            # Convert HardwareState to dict for response
            memory_usage = {
                "total_mb": hw_state.memory_total_mb,
                "available_mb": hw_state.memory_available_mb,
                "used_percent": hw_state.memory_used_percent,
                "tier": hw_state.memory_tier.value,
                "process_rss_mb": hw_state.process_rss_mb,
                "swap_used_mb": hw_state.swap_used_mb,
                "cpu_percent": hw_state.cpu_percent,
            }

            return StatusResponse(
                status="ready",
                version=self.VERSION,
                model=self.engine.config.model.name,
                execution_mode="dynamic_layers",
                memory_usage=memory_usage,
                uptime_seconds=uptime,
            )

        # ─────────────────────────────────────────────
        # Inference Endpoints
        # ─────────────────────────────────────────────

        @app.post("/api/query", response_model=QueryResponse)
        async def query(request: QueryRequest):
            """
            Process query synchronously.

            Returns complete response with metrics and performance data.
            With hardening: validation, caching, rate limiting, error handling.
            """
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            # Rate limiting
            client_id = "default"  # In production, would use request.client.host
            if not rate_limiter.is_allowed(client_id):
                logger.warning("Rate limit exceeded")
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please wait before trying again.",
                )

            try:
                # Input validation
                is_valid, error_msg = input_validator.validate_query(request.text)
                if not is_valid:
                    logger.warning(f"Invalid input: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)
                
                # Sanitize input
                sanitized_text = input_validator.sanitize_query(request.text)

                logger.debug("Processing query: %s (mode=%s)", sanitized_text[:50], request.mode)
                
                # Check cache first
                cached = response_cache.get(sanitized_text, request.mode)
                if cached:
                    logger.info("Returning cached response")
                    return QueryResponse(**cached)
                
                # Check memory before processing
                if memory_optimizer.is_memory_critical():
                    logger.warning("Memory critical, running cleanup")
                    memory_optimizer.cleanup()
                
                # Process query
                result = self.engine.process(sanitized_text, mode=request.mode)

                response_dict = {
                    "output": result.response,
                    "latency_ms": result.metrics.latency_ms,
                    "tokens_generated": result.metrics.tokens_generated,
                    "tokens_per_second": result.metrics.tokens_per_second,
                    "complexity": result.query_profile.complexity_level.value,
                    "mode": request.mode,
                    "layers_used": result.metrics.layers_used,
                    "total_layers": result.metrics.total_layers or 24,
                }
                
                response = QueryResponse(**response_dict)

                # Cache successful response
                response_cache.set(sanitized_text, request.mode, response_dict)
                
                # Record performance metric
                performance_monitor.record(
                    sanitized_text,
                    result.metrics.latency_ms,
                    result.metrics.tokens_generated,
                    request.mode,
                )

                logger.info(
                    "Query processed: complexity=%s latency=%dms tokens=%d",
                    result.query_profile.complexity_level.value,
                    result.metrics.latency_ms,
                    result.metrics.tokens_generated,
                )

                return response

            except HTTPException:
                raise
            except Exception as e:
                error_handler.log_error("query_failed", e, {"query": request.text[:50]})
                raise HTTPException(
                    status_code=500,
                    detail=error_handler.get_user_message("model_error"),
                )

        @app.post("/api/query/stream")
        async def query_stream(request: QueryRequest):
            """
            Stream response tokens in real-time.

            Returns NDJSON (newline-delimited JSON) with individual tokens.
            """
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            async def generate() -> AsyncGenerator[str, None]:
                try:
                    logger.debug("Starting stream: %s", request.text[:50])

                    # For now, use synchronous streaming
                    # In production, would be fully async
                    result = self.engine.process(request.text, mode=request.mode)

                    # Stream output character by character
                    for char in result.response:
                        data = json.dumps({"token": char})
                        yield data + "\n"
                        await asyncio.sleep(0.001)  # Simulate streaming delay

                    # Final metrics
                    metrics_data = {
                        "done": True,
                        "latency_ms": result.metrics.latency_ms,
                        "tokens": result.metrics.tokens_generated,
                        "tokens_per_second": result.metrics.tokens_per_second,
                    }
                    yield json.dumps(metrics_data) + "\n"

                except Exception as e:
                    logger.error("Stream processing failed: %s", str(e))
                    yield json.dumps({"error": str(e)}) + "\n"

            return StreamingResponse(generate(), media_type="application/x-ndjson")

        # ─────────────────────────────────────────────
        # Metadata Endpoints
        # ─────────────────────────────────────────────

        @app.get("/api/models")
        async def list_models():
            """List available models."""
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            return {
                "current": self.engine.config.model.name,
                "available": [
                    "mlx-community/Qwen2.5-3B-Instruct-4bit",
                    "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
                ],
            }

        @app.get("/api/metrics")
        async def get_metrics():
            """Get aggregated metrics from current session including hardening stats."""
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            base_metrics = self.engine.reporter.get_summary()
            
            # Add hardening metrics
            base_metrics["hardening"] = {
                "cache_stats": response_cache.get_stats(),
                "performance_stats": performance_monitor.get_stats(),
                "rate_limiter_remaining": rate_limiter.get_remaining("default"),
            }
            
            return base_metrics

        @app.post("/api/reset-metrics")
        async def reset_metrics():
            """Reset metrics (useful for benchmarking)."""
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Engine not ready")

            self.engine.store.reset()
            return {"status": "metrics reset"}

        # ─────────────────────────────────────────────
        # Control Endpoints
        # ─────────────────────────────────────────────

        @app.post("/api/shutdown")
        async def shutdown():
            """Graceful shutdown endpoint."""
            logger.warning("Shutdown requested via API")
            # Note: In production, this would be behind authentication
            return {"status": "shutting down"}

        @app.get("/api/version")
        async def version():
            """Get runtime version."""
            return {"version": self.VERSION}

        return app

    def run_development(self):
        """Run in development mode (single worker, auto-reload, debug)."""
        self.setup()
        self.app = self.create_app()

        logger.info("Starting in DEVELOPMENT mode")
        logger.info("API documentation: http://%s:%s/docs", self.host, self.port)

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            workers=1,
            reload=False,
            log_level="debug",
            access_log=True,
        )

    def run_production(self):
        """Run in production mode (multiple workers, optimized)."""
        self.setup()
        self.app = self.create_app()

        logger.info("Starting in PRODUCTION mode with %d workers", self.workers)
        logger.info("API documentation: http://%s:%s/docs", self.host, self.port)

        # Write pidfile
        if self.pidfile:
            pidfile_path = Path(self.pidfile)
            pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            pidfile_path.write_text(str(os.getpid()))
            logger.info("Wrote PID to %s", self.pidfile)

        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                workers=self.workers,
                reload=False,
                log_level="info",
                access_log=True,
            )
        finally:
            # Cleanup
            if self.pidfile:
                try:
                    Path(self.pidfile).unlink()
                except FileNotFoundError:
                    pass
            if self.engine:
                self.engine.shutdown()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.warning("Received signal %d, shutting down...", signum)
        if self.pidfile:
            try:
                Path(self.pidfile).unlink()
            except FileNotFoundError:
                pass
        if self.engine:
            self.engine.shutdown()
        sys.exit(0)

    def start(self):
        """Start the runtime service."""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        if self.dev_mode:
            self.run_development()
        else:
            self.run_production()


def main():
    """CLI entry point for aria-runtime."""
    parser = argparse.ArgumentParser(
        description="ARIA Runtime Service - Adaptive Runtime Intelligence Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start on localhost:8000 (single worker)
  aria-runtime

  # Production mode (4 workers, all interfaces)
  aria-runtime --host 0.0.0.0 --port 8000 --workers 4

  # Development mode with debug logging
  aria-runtime --dev

  # With custom config
  aria-runtime --config /etc/aria/config.yaml

  # With pidfile for process management
  aria-runtime --pidfile /var/run/aria.pid

API Documentation will be available at: http://localhost:8000/docs
Health check: curl http://localhost:8000/health
Query example: curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"text": "Hello"}'
        """,
    )

    # Server configuration
    parser.add_argument(
        "--host",
        default=os.getenv("ARIA_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1, env: ARIA_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ARIA_PORT", "8000")),
        help="Port to bind to (default: 8000, env: ARIA_PORT)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("ARIA_WORKERS", "1")),
        help="Number of worker processes (default: 1, env: ARIA_WORKERS)",
    )

    # Configuration
    parser.add_argument(
        "--config",
        help="Path to config file (YAML or JSON) (env: ARIA_CONFIG)",
    )

    # Process management
    parser.add_argument(
        "--pidfile",
        help="Write process ID to file (env: ARIA_PIDFILE)",
    )

    # Mode
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Development mode (single worker, debug logging, reload disabled)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="ARIA Runtime v0.2.0",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.dev else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create and start runtime
    runtime = ARIARuntime(
        host=args.host,
        port=args.port,
        workers=args.workers,
        config_path=args.config or os.getenv("ARIA_CONFIG"),
        pidfile=args.pidfile or os.getenv("ARIA_PIDFILE"),
        dev_mode=args.dev,
    )

    runtime.start()


if __name__ == "__main__":
    main()
