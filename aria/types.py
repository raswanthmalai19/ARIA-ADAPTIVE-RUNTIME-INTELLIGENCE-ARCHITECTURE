"""
ARIA Core Types

Shared data types, enums, and data classes used across all ARIA modules.
These are the fundamental building blocks of the system's type system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ─────────────────────────────────────────────
# Complexity & Task Classification
# ─────────────────────────────────────────────

class ComplexityLevel(str, Enum):
    """Query complexity classification levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"

    @property
    def rank(self) -> int:
        """Numeric rank for comparison (0=simplest, 3=most complex)."""
        return {
            ComplexityLevel.SIMPLE: 0,
            ComplexityLevel.MODERATE: 1,
            ComplexityLevel.COMPLEX: 2,
            ComplexityLevel.EXPERT: 3,
        }[self]

    def upgrade(self) -> ComplexityLevel:
        """Return the next higher complexity level, capped at EXPERT."""
        levels = list(ComplexityLevel)
        idx = levels.index(self)
        return levels[min(idx + 1, len(levels) - 1)]


class TaskType(str, Enum):
    """Classification of the query's task domain."""
    FACTUAL = "factual"          # Simple factoid / lookup questions
    REASONING = "reasoning"      # Logic, analysis, comparison
    CREATIVE = "creative"        # Writing, storytelling, brainstorming
    CODE = "code"                # Programming, debugging, algorithms
    CONVERSATION = "conversation"  # Casual chat, greetings
    MATH = "math"                # Mathematical computation, proofs
    INSTRUCTION = "instruction"  # Step-by-step guidance, how-to


# ─────────────────────────────────────────────
# Memory Tiers
# ─────────────────────────────────────────────

class MemoryTier(str, Enum):
    """System memory pressure classification."""
    GREEN = "green"    # < 60% — full capability
    YELLOW = "yellow"  # 60-80% — warn, cap complex
    ORANGE = "orange"  # 80-90% — restrict strategies
    RED = "red"        # > 90% — emergency minimal mode


# ─────────────────────────────────────────────
# Query Profile (output of Query Analyzer)
# ─────────────────────────────────────────────

@dataclass
class QueryProfile:
    """Complete analysis of an incoming query."""
    query: str
    complexity_score: float          # 0.0 to 1.0
    complexity_level: ComplexityLevel
    task_type: TaskType
    estimated_output_tokens: int     # Predicted response length
    confidence: float                # Classifier confidence 0.0–1.0
    features: dict[str, Any] = field(default_factory=dict)  # Raw features

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7


# ─────────────────────────────────────────────
# Execution Strategy (output of Planner)
# ─────────────────────────────────────────────

@dataclass
class ExecutionStrategy:
    """Parameters controlling how the model executes for a given request."""
    complexity_level: ComplexityLevel
    max_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    source: str = "planner"  # Who decided this: "planner", "memory_override", "fallback"

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity_level": self.complexity_level.value,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "source": self.source,
        }


# ─────────────────────────────────────────────
# Hardware State
# ─────────────────────────────────────────────

@dataclass
class HardwareState:
    """Snapshot of current hardware resource availability."""
    memory_total_mb: float
    memory_available_mb: float
    memory_used_percent: float
    memory_tier: MemoryTier
    process_rss_mb: float            # ARIA process memory
    swap_used_mb: float
    cpu_percent: float
    timestamp: float = field(default_factory=time.time)

    @property
    def is_constrained(self) -> bool:
        """True if memory pressure is ORANGE or RED."""
        return self.memory_tier in (MemoryTier.ORANGE, MemoryTier.RED)


# ─────────────────────────────────────────────
# Execution Result (output of full pipeline)
# ─────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """Complete result of an ARIA-processed request."""
    query: str
    response: str
    query_profile: QueryProfile
    strategy: ExecutionStrategy
    hardware_state: HardwareState
    metrics: ExecutionMetrics
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "response": self.response,
            "complexity": self.query_profile.complexity_level.value,
            "task_type": self.query_profile.task_type.value,
            "strategy": self.strategy.to_dict(),
            "metrics": self.metrics.to_dict(),
            "memory_tier": self.hardware_state.memory_tier.value,
            "fallback_triggered": self.fallback_triggered,
            "fallback_reason": self.fallback_reason,
        }


# ─────────────────────────────────────────────
# Execution Metrics
# ─────────────────────────────────────────────

@dataclass
class ExecutionMetrics:
    """Performance metrics for a single execution."""
    latency_ms: float = 0.0
    time_to_first_token_ms: float = 0.0
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_delta_mb: float = 0.0
    system_memory_pressure: float = 0.0
    analyzer_latency_ms: float = 0.0
    planner_latency_ms: float = 0.0

    # Adaptive execution tracking (breakthrough features)
    execution_mode: str = "standard"      # dynamic_layers / cascade / standard
    layers_used: int = 0                   # Number of layers actually executed
    total_layers: int = 0                  # Total layers in model
    model_used: str = ""                   # Which model was used (for cascade)

    @property
    def layer_skip_ratio(self) -> float:
        """Fraction of layers skipped (0.0 = all used, 1.0 = all skipped)."""
        if self.total_layers == 0:
            return 0.0
        return 1.0 - (self.layers_used / self.total_layers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency_ms": round(self.latency_ms, 2),
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
            "tokens_generated": self.tokens_generated,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "memory_before_mb": round(self.memory_before_mb, 2),
            "memory_after_mb": round(self.memory_after_mb, 2),
            "memory_delta_mb": round(self.memory_delta_mb, 2),
            "system_memory_pressure": round(self.system_memory_pressure, 2),
            "analyzer_latency_ms": round(self.analyzer_latency_ms, 2),
            "planner_latency_ms": round(self.planner_latency_ms, 2),
            "execution_mode": self.execution_mode,
            "layers_used": self.layers_used,
            "total_layers": self.total_layers,
            "model_used": self.model_used,
            "layer_skip_ratio": round(self.layer_skip_ratio, 3),
        }


# ─────────────────────────────────────────────
# Quality Assessment (used by Guardian)
# ─────────────────────────────────────────────

class QualityVerdict(str, Enum):
    """Output quality assessment result."""
    PASS = "pass"
    DEGRADED = "degraded"
    FAIL = "fail"


@dataclass
class QualityReport:
    """Detailed quality assessment of a model's output."""
    verdict: QualityVerdict
    score: float               # 0.0 to 1.0
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def needs_fallback(self) -> bool:
        return self.verdict == QualityVerdict.FAIL
