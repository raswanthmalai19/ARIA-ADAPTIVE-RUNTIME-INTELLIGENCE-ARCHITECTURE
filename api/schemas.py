"""
ARIA API Schemas

Pydantic models for request/response validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """Request to process a query through ARIA."""
    query: str = Field(..., min_length=1, max_length=4000, description="The user query")
    mode: str = Field(default="adaptive", description="Execution mode: 'adaptive' or 'baseline'")
    execution_mode: str = Field(
        default="dynamic_layers",
        description="How to execute: 'dynamic_layers', 'cascade', or 'standard'"
    )


class AnalyzeRequest(BaseModel):
    """Request to analyze a query without inference."""
    query: str = Field(..., min_length=1, max_length=4000)


class QueryResponse(BaseModel):
    """Response from ARIA query processing."""
    query: str
    response: str
    complexity: str
    task_type: str
    complexity_score: float
    confidence: float
    strategy: dict
    metrics: dict
    memory_tier: str
    fallback_triggered: bool
    fallback_reason: Optional[str] = None
    cached: bool = Field(default=False, description="Whether response was from cache")


class AnalyzeResponse(BaseModel):
    """Response from query analysis."""
    query: str
    complexity_level: str
    complexity_score: float
    task_type: str
    confidence: float
    estimated_output_tokens: int
    features: dict


class StatusResponse(BaseModel):
    """System status response."""
    model_loaded: bool
    model_name: str
    execution_mode: str = "dynamic_layers"
    memory: dict
    guardian: dict
    metrics: dict
    adaptive: Optional[dict] = None


class StatsResponse(BaseModel):
    """Statistics response."""
    stats: dict
    comparison: dict
    total_executions: int
