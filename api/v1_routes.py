"""
Enhanced ARIA API Routes with Error Handling, History, and Settings
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import logging
import time
import json
from pathlib import Path

from aria.errors import (
    ValidationError as APIValidationError,
    RateLimitError,
    ModelError,
    TimeoutError as APITimeoutError,
    ResourceError,
)
from aria.hardening import (
    input_validator,
    rate_limiter,
    response_cache,
    performance_monitor,
    memory_optimizer,
)
from aria.history import get_db as get_history_db
from aria.settings import get_settings
from aria.engine import ARIAEngine

logger = logging.getLogger("aria.routes")

# Create router
router = APIRouter(prefix="/api", tags=["api"])


# Request/Response Models
class QueryRequest(BaseModel):
    """Query request with all parameters."""
    query: str = Field(..., min_length=1, max_length=10000)
    mode: str = Field(default="adaptive", regex="^(adaptive|baseline|cascade)$")
    conversation_id: int = Field(default=None)
    model: str = Field(default=None)


class QueryResponse(BaseModel):
    """Query response with metadata."""
    response: str
    mode: str
    latency_ms: float
    tokens: int
    tokens_per_second: float
    cached: bool = False
    conversation_id: int = None


class SettingsRequest(BaseModel):
    """Settings update request."""
    temperature: float = Field(None, ge=0, le=2)
    top_p: float = Field(None, gt=0, le=1)
    max_tokens: int = Field(None, ge=1, le=8192)
    execution_mode: str = Field(None, regex="^(adaptive|baseline|cascade)$")
    theme: str = Field(None, regex="^(dark|light)$")


class HistoryRequest(BaseModel):
    """History entry request."""
    title: str = Field(default="New Conversation")
    model: str = Field(default=None)


# Initialize global engine
_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = ARIAEngine()
    return _engine


# ── QUERY ENDPOINT ──────────────────────────────────────────────
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process a query with the ARIA engine.
    
    Implements:
    - Input validation
    - Rate limiting
    - Response caching
    - Performance monitoring
    - History tracking
    - Error handling
    """
    client_id = request.client.host if hasattr(request, 'client') else "unknown"
    
    try:
        # 1. VALIDATE INPUT
        valid, error_msg = input_validator.validate_query(request.query)
        if not valid:
            logger.warning(f"Invalid input from {client_id}: {error_msg}")
            raise APIValidationError(error_msg, "Invalid query format")
        
        # 2. CHECK RATE LIMIT
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise RateLimitError()
        
        # 3. CHECK MEMORY
        if memory_optimizer.is_memory_critical():
            logger.error("Memory critical, triggering cleanup")
            memory_optimizer.cleanup()
            raise ResourceError("Server under high resource load")
        
        # 4. CHECK CACHE
        query_mode = request.mode
        if cached_response := response_cache.get(request.query, query_mode):
            logger.debug(f"Cache hit for: {request.query[:50]}...")
            return QueryResponse(
                response=cached_response.get("response"),
                mode=query_mode,
                latency_ms=cached_response.get("latency_ms", 0),
                tokens=cached_response.get("tokens", 0),
                tokens_per_second=cached_response.get("tokens_per_second", 0),
                cached=True,
                conversation_id=request.conversation_id,
            )
        
        # 5. PROCESS QUERY
        start_time = time.time()
        
        engine = get_engine()
        result = engine.process_query(
            request.query,
            mode=query_mode,
            settings=get_settings().get_all()
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # 6. SAVE TO HISTORY
        db = get_history_db()
        if request.conversation_id is None:
            request.conversation_id = db.create_conversation("Query")
        
        db.add_message(
            request.conversation_id,
            role="user",
            content=request.query,
            mode=query_mode
        )
        
        db.add_message(
            request.conversation_id,
            role="assistant",
            content=result.response,
            mode=query_mode,
            tokens=result.tokens,
            latency_ms=latency_ms
        )
        
        # 7. CACHE RESPONSE
        cache_data = {
            "response": result.response,
            "tokens": result.tokens,
            "latency_ms": latency_ms,
            "tokens_per_second": result.tokens / (latency_ms / 1000) if latency_ms > 0 else 0,
        }
        response_cache.set(request.query, query_mode, cache_data)
        
        # 8. RECORD METRICS
        performance_monitor.record(
            request.query,
            latency_ms,
            result.tokens,
            query_mode
        )
        
        logger.info(f"Query processed: {latency_ms:.0f}ms, {result.tokens} tokens")
        
        return QueryResponse(
            response=result.response,
            mode=query_mode,
            latency_ms=latency_ms,
            tokens=result.tokens,
            tokens_per_second=cache_data["tokens_per_second"],
            cached=False,
            conversation_id=request.conversation_id,
        )
    
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise


# ── SETTINGS ENDPOINTS ──────────────────────────────────────────
@router.get("/settings")
async def get_settings_endpoint():
    """Get current settings."""
    try:
        settings = get_settings()
        return {"settings": settings.get_all()}
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load settings")


@router.post("/settings")
async def update_settings(request: SettingsRequest):
    """Update settings."""
    try:
        settings = get_settings()
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if updates:
            settings.update(updates)
            logger.info(f"Settings updated: {list(updates.keys())}")
        
        return {"success": True, "settings": settings.get_all()}
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


# ── HISTORY ENDPOINTS ──────────────────────────────────────────
@router.get("/history")
async def get_history():
    """List conversations."""
    try:
        db = get_history_db()
        conversations = db.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail="Failed to load history")


@router.post("/history")
async def create_history_entry(request: HistoryRequest):
    """Create new conversation."""
    try:
        db = get_history_db()
        conv_id = db.create_conversation(request.title, request.model)
        return {"conversation_id": conv_id}
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/history/{conversation_id}")
async def get_conversation(conversation_id: int):
    """Get specific conversation."""
    try:
        db = get_history_db()
        conv = db.get_conversation(conversation_id)
        messages = db.get_messages(conversation_id)
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation": conv,
            "messages": messages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to load conversation")


@router.delete("/history/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete conversation."""
    try:
        db = get_history_db()
        success = db.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


# ── METRICS ENDPOINT ────────────────────────────────────────────
@router.get("/metrics")
async def get_metrics():
    """Get performance metrics."""
    try:
        db = get_history_db()
        perf_stats = performance_monitor.get_stats()
        cache_stats = response_cache.get_stats()
        db_stats = db.get_stats()
        memory_status = memory_optimizer.get_memory_status()
        
        return {
            "performance": perf_stats,
            "cache": cache_stats,
            "history": db_stats,
            "memory": memory_status,
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


# Export router
__all__ = ["router"]
