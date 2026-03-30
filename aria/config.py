"""
ARIA Central Configuration

Single source of truth for all configurable parameters.
Loads from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


def _env(key: str, default: str = "") -> str:
    """Read an environment variable with a default."""
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    """Read an integer environment variable."""
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float = 0.0) -> float:
    """Read a float environment variable."""
    return float(os.getenv(key, str(default)))


def _env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for the AI model."""
    name: str = field(
        default_factory=lambda: _env("ARIA_MODEL_NAME", "mlx-community/Qwen2.5-3B-Instruct-4bit")
    )
    max_context: int = field(
        default_factory=lambda: _env_int("ARIA_MODEL_MAX_CONTEXT", 2048)
    )


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for the API server."""
    host: str = field(default_factory=lambda: _env("ARIA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("ARIA_PORT", 8000))
    log_level: str = field(default_factory=lambda: _env("ARIA_LOG_LEVEL", "INFO"))


@dataclass(frozen=True)
class MemoryConfig:
    """Memory pressure thresholds (as percentages)."""
    yellow_threshold: int = field(
        default_factory=lambda: _env_int("ARIA_MEMORY_YELLOW", 60)
    )
    orange_threshold: int = field(
        default_factory=lambda: _env_int("ARIA_MEMORY_ORANGE", 80)
    )
    red_threshold: int = field(
        default_factory=lambda: _env_int("ARIA_MEMORY_RED", 90)
    )


@dataclass(frozen=True)
class StrategyConfig:
    """Default execution strategy parameters per complexity level."""

    # SIMPLE tier
    simple_max_tokens: int = 128
    simple_temperature: float = 0.3
    simple_top_p: float = 0.8
    simple_repetition_penalty: float = 1.0

    # MODERATE tier
    moderate_max_tokens: int = 256
    moderate_temperature: float = 0.6
    moderate_top_p: float = 0.9
    moderate_repetition_penalty: float = 1.1

    # COMPLEX tier
    complex_max_tokens: int = 512
    complex_temperature: float = 0.7
    complex_top_p: float = 0.95
    complex_repetition_penalty: float = 1.15

    # EXPERT tier
    expert_max_tokens: int = 1024
    expert_temperature: float = 0.8
    expert_top_p: float = 0.95
    expert_repetition_penalty: float = 1.2


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance monitoring settings."""
    enable_streaming: bool = field(
        default_factory=lambda: _env_bool("ARIA_ENABLE_STREAMING", True)
    )
    metrics_db: str = field(
        default_factory=lambda: _env("ARIA_METRICS_DB", "aria_metrics.db")
    )
    warmup_runs: int = 1  # Number of warm-up inferences before benchmarking


@dataclass(frozen=True)
class GuardianConfig:
    """Stability guardian parameters."""
    min_response_tokens: int = 10       # Below this = possible failure
    max_repetition_ratio: float = 0.4   # n-gram repetition threshold
    max_fallback_attempts: int = 2      # Max retry escalations
    circuit_breaker_threshold: int = 3  # Consecutive failures before lockout
    timeout_seconds: float = 120.0      # Max time for a single inference


@dataclass(frozen=True)
class ARIAConfig:
    """Master configuration aggregating all sub-configs."""
    model: ModelConfig = field(default_factory=ModelConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    guardian: GuardianConfig = field(default_factory=GuardianConfig)

    # Project paths
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
    )

    @property
    def metrics_db_path(self) -> Path:
        return self.project_root / self.performance.metrics_db

    @property
    def dashboard_dir(self) -> Path:
        return self.project_root / "dashboard"


def get_config() -> ARIAConfig:
    """Create and return the global configuration."""
    return ARIAConfig()


def setup_logging(config: Optional[ARIAConfig] = None) -> logging.Logger:
    """Configure structured logging for ARIA."""
    if config is None:
        config = get_config()

    log_level = getattr(logging, config.server.log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s │ %(name)-24s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    # Create ARIA logger
    logger = logging.getLogger("aria")
    logger.setLevel(log_level)

    return logger
