"""
ARIA API Routes

FastAPI routes for the ARIA REST API with production hardening.
- Input validation & sanitization
- Rate limiting per client
- Response caching
- Performance monitoring
- Memory optimization
- Comprehensive error handling
"""

from __future__ import annotations

import logging
import time
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from aria.hardening import (
    InputValidator,
    RateLimiter,
    ResponseCache,
    ErrorHandler,
)
from aria.monitor.reporter import PerformanceMonitor
from aria.memory.monitor import MemoryOptimizer
from aria.types import QueryProfile, ComplexityLevel

logger = logging.getLogger("aria.api")

router = APIRouter(prefix="/api/v1", tags=["ARIA"])

# Singleton instances (thread-safe for FastAPI)
input_validator = InputValidator()
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
response_cache = ResponseCache(max_cache_size=1000, ttl_seconds=3600)
performance_monitor = PerformanceMonitor()
memory_optimizer = MemoryOptimizer()

# Engine reference (set by server.py on startup)
_engine = None


def _get_engine():
    """Get the initialized engine."""
    return _engine


def set_engine(engine) -> None:
    """Set the engine reference for route handlers."""
    global _engine
    _engine = engine


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@router.get("/status")
async def health_check():
    """Health check endpoint."""
    engine = _get_engine()
    memory_status = memory_optimizer.get_memory_status()
    
    return {
        "status": "healthy" if engine else "initializing",
        "engine_ready": engine is not None,
        "memory": memory_status,
        "cached_responses": response_cache.get_stats(),
    }


@router.get("/stats")
async def get_stats():
    """Get performance statistics."""
    return {
        "performance": performance_monitor.get_stats(),
        "cache": response_cache.get_stats(),
        "memory": memory_optimizer.get_memory_status(),
    }


# ============================================================================
# Query Processing Endpoint
# ============================================================================

@router.post("/query")
async def process_query(payload: Dict[str, Any], req: Request):
    """
    Process a query through the full ARIA pipeline.
    
    Features:
    - Input validation & sanitization
    - Rate limiting (per client IP)
    - Response caching
    - Performance monitoring
    - Memory optimization
    - Comprehensive error handling
    
    Request body:
    {
        "query": "Your question",
        "mode": "adaptive" | "baseline" | "cascade",
        "metadata": { optional metadata }
    }
    """
    engine = _get_engine()
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "message": "ARIA engine is initializing. Please try again in a moment.",
            }
        )

    # Extract client IP for rate limiting
    client_id = req.client.host if req.client else "unknown"
    request_start = time.time()
    
    try:
        # 1. VALIDATE & SANITIZE INPUT
        query = payload.get("query", "").strip()
        mode = payload.get("mode", "adaptive").lower()
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={"error": "validation_error", "message": "Query cannot be empty"}
            )
        
        if mode not in ["adaptive", "baseline", "cascade"]:
            mode = "adaptive"
        
        # Validate and sanitize query
        is_valid, error_msg = input_validator.validate_query(query)
        if not is_valid:
            logger.warning(f"Invalid query from {client_id}: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"error": "validation_error", "message": error_msg}
            )
        
        # Sanitize the query
        query = input_validator.sanitize_query(query)
        
        # 2. CHECK RATE LIMIT
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            remaining = rate_limiter.get_remaining(client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Remaining: {remaining} requests.",
                    "remaining_requests": remaining,
                }
            )
        
        # 3. CHECK MEMORY
        memory_status = memory_optimizer.get_memory_status()
        if memory_status.get("used_percent", 0) > 85:
            logger.error(f"Memory critical ({memory_status['used_percent']}%), rejecting request")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "server_overload",
                    "message": "Server is under high resource load. Please try again later.",
                    "memory_usage_percent": memory_status["used_percent"],
                }
            )
        
        # 4. CHECK CACHE
        cached = response_cache.get(query, mode)
        if cached:
            logger.debug(f"Cache hit for: {query[:50]}...")
            cached["cached"] = True
            return JSONResponse(status_code=200, content=cached)
        
        # 5. PROCESS QUERY WITH ENGINE
        logger.info(f"Processing query [mode={mode}]: {query[:50]}...")
        
        # Simulate engine processing (will use real engine when available)
        request_latency_ms = (time.time() - request_start) * 1000
        
        response_data = {
            "query": query,
            "response": f"ARIA processed: {query}",  # Placeholder
            "complexity": "medium",
            "task_type": "general",
            "complexity_score": 0.65,
            "confidence": 0.88,
            "strategy": {"mode": mode, "layers_used": "100%"},
            "metrics": {
                "latency_ms": request_latency_ms,
                "tokens": 100,
                "tokens_per_second": 25.0,
            },
            "memory_tier": "normal",
            "fallback_triggered": False,
            "fallback_reason": None,
            "cached": False,
        }
        
        # 6. CACHE RESPONSE
        valid, error_msg = input_validator.validate_query(request.query)
        if not valid:
            logger.warning(f"Invalid query from {client_id}: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2. CHECK RATE LIMIT
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # 3. CHECK MEMORY
        if memory_optimizer.is_memory_critical():
            logger.error(f"Memory critical, rejecting request from {client_id}")
            raise HTTPException(status_code=503, detail="Server under high resource load")
        
        # 4. CHECK CACHE
        cache_key = f"{request.query}::{request.mode}"
        if cached_response := response_cache.get(request.query, request.mode):
            logger.debug(f"Cache hit for query: {request.query[:50]}...")
            # Update cached response with cache info
            cached_response['cached'] = True
            return QueryResponse(**cached_response)
        
        # 5. PROCESS QUERY
        result = engine.process(request.query, mode=request.mode)

        query_response = QueryResponse(
            query=result.query,
            response=result.response,
            complexity=result.query_profile.complexity_level.value,
            task_type=result.query_profile.task_type.value,
            complexity_score=result.query_profile.complexity_score,
            confidence=result.query_profile.confidence,
            strategy=result.strategy.to_dict(),
            metrics=result.metrics.to_dict(),
            memory_tier=result.hardware_state.memory_tier.value,
            fallback_triggered=result.fallback_triggered,
            fallback_reason=result.fallback_reason,
            cached=False,
        )
        
        # 6. RECORD METRICS
        latency_ms = (time.time() - start_time) * 1000
        tokens = result.metrics.output_tokens if hasattr(result.metrics, 'output_tokens') else 0
        
        performance_monitor.record(
            request.query,
            latency_ms,
            tokens,
            request.mode
        )
        
        # 7. CACHE RESPONSE
        response_cache.set(request.query, request.mode, query_response.dict())
        
        logger.info(f"Query '{request.query[:50]}...' processed in {latency_ms:.0f}ms by {client_id}")
        return query_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(request: AnalyzeRequest, req: Request):
    """
    Analyze a query without running inference.
    
    Includes input validation and rate limiting.
    """
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")

    client_id = req.client.host if req.client else "unknown"
    
    try:
        # VALIDATE INPUT
        valid, error_msg = input_validator.validate_query(request.query)
        if not valid:
            logger.warning(f"Invalid query from {client_id}: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # CHECK RATE LIMIT
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(status_code=429, detail="Too many requests")
        
        profile = engine.analyzer.classify(request.query)

        logger.debug(f"Analyzed query from {client_id}: {request.query[:50]}...")
        
        return AnalyzeResponse(
            query=request.query,
            complexity_level=profile.complexity_level.value,
            complexity_score=profile.complexity_score,
            task_type=profile.task_type.value,
            confidence=profile.confidence,
            estimated_output_tokens=profile.estimated_output_tokens,
            features=profile.features,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get ARIA system status."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")

    status = engine.get_status()
    return StatusResponse(**status)


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get execution statistics and benchmark comparisons."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")

    return StatsResponse(
        stats=engine.store.get_stats_by_complexity("adaptive"),
        comparison=engine.store.get_comparison_stats(),
        total_executions=engine.store.get_total_count(),
    )


@router.get("/recent")
async def get_recent(limit: int = 20):
    """Get recent execution records."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")

    return engine.store.get_recent(limit)


@router.get("/memory")
async def get_memory():
    """Get current memory status."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")

    state = engine.memory.get_state(force_refresh=True)
    return {
        "status": engine.memory.format_status(),
        "tier": state.memory_tier.value,
        "used_percent": state.memory_used_percent,
        "available_mb": round(state.memory_available_mb, 0),
        "process_rss_mb": round(state.process_rss_mb, 0),
        "swap_used_mb": round(state.swap_used_mb, 0),
    }


# ── HEALTH CHECK ENDPOINTS ──────────────────────────────────────

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    engine = _get_engine()
    if engine is None:
        return {"status": "unhealthy", "reason": "Engine not initialized"}
    
    return {
        "status": "healthy",
        "engine": "initialized",
        "timestamp": time.time(),
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check - is server ready for requests?"""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Check memory
    if memory_optimizer.is_memory_critical():
        raise HTTPException(status_code=503, detail="Memory critical")
    
    return {"ready": True, "message": "Server ready for requests"}


@router.get("/health/live")
async def liveness_check():
    """Liveness check - is server alive?"""
    return {"alive": True, "message": "Server is alive"}


@router.get("/status/loader")
async def get_loader_status():
    """Get model loader status (warming up, ready, error)."""
    from api.server import loader
    
    if loader is None:
        return {"state": "uninitialized", "progress": 0.0, "ready": False}
    
    return loader.get_status()


# ── METRICS ENDPOINTS ────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="ARIA engine not initialized")
    
    try:
        return {
            "performance": performance_monitor.get_stats(),
            "cache": response_cache.get_stats(),
            "rate_limit": rate_limiter.get_stats(),
            "memory": memory_optimizer.get_memory_status(),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/performance")
async def get_performance_metrics():
    """Get detailed performance metrics."""
    return performance_monitor.get_stats()


@router.get("/metrics/cache")
async def get_cache_metrics():
    """Get cache statistics."""
    return response_cache.get_stats()


@router.get("/metrics/rate-limit")
async def get_rate_limit_metrics():
    """Get rate limiter statistics."""
    return rate_limiter.get_stats()

