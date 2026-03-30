"""
ARIA Multi-Model Cascade

Routes queries to different-sized models based on complexity.
Simple queries go to a tiny model (fast), complex queries to a large model.

This is a runtime optimization — not just routing, but intelligent
model selection that dramatically reduces latency for simple queries
while maintaining quality for complex ones.

On 8GB M1:
  - Qwen2.5-0.5B-4bit: ~350MB, ~80+ tok/s
  - Qwen2.5-3B-4bit:   ~1.8GB, ~15-25 tok/s
  - Both loaded:        ~2.1GB — fits comfortably
"""

from __future__ import annotations

import gc
import logging
import time
from dataclasses import dataclass
from typing import Optional

from aria.types import ComplexityLevel, ExecutionStrategy
from aria.config import ARIAConfig, get_config
from aria.controller.formatter import PromptFormatter
from aria.memory.monitor import MemoryMonitor

logger = logging.getLogger("aria.controller.cascade")


@dataclass
class CascadeConfig:
    """Configuration for multi-model cascade."""
    # Model names
    tiny_model: str = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    large_model: str = "mlx-community/Qwen2.5-3B-Instruct-4bit"

    # Routing thresholds
    # SIMPLE → tiny model, everything else → large model
    tiny_model_max_complexity: ComplexityLevel = ComplexityLevel.SIMPLE

    # Memory safety: unload large model if memory pressure is critical
    unload_large_on_red: bool = True


class ModelCascade:
    """
    Manages two models of different sizes and routes queries
    to the appropriate one based on complexity.

    Architecture:
        Query → Classifier → SIMPLE? → Tiny Model (0.5B) → Fast response
                           → MODERATE+ → Large Model (3B) → Quality response

    The tiny model stays permanently loaded (~350MB).
    The large model is loaded on demand and can be unloaded under memory pressure.
    """

    def __init__(
        self,
        config: Optional[ARIAConfig] = None,
        cascade_config: Optional[CascadeConfig] = None,
    ):
        self.config = config or get_config()
        self.cascade = cascade_config or CascadeConfig()
        self._memory = MemoryMonitor(self.config)

        # Model slots
        self._tiny_model = None
        self._tiny_tokenizer = None
        self._tiny_loaded = False

        self._large_model = None
        self._large_tokenizer = None
        self._large_loaded = False

        # Formatters per model
        self._tiny_formatter = PromptFormatter()
        self._large_formatter = PromptFormatter()

        # Stats
        self._tiny_calls = 0
        self._large_calls = 0

    @property
    def is_tiny_loaded(self) -> bool:
        return self._tiny_loaded

    @property
    def is_large_loaded(self) -> bool:
        return self._large_loaded

    @property
    def routing_stats(self) -> dict:
        total = self._tiny_calls + self._large_calls
        return {
            "tiny_calls": self._tiny_calls,
            "large_calls": self._large_calls,
            "tiny_ratio": self._tiny_calls / max(total, 1),
            "large_ratio": self._large_calls / max(total, 1),
        }

    def load_tiny(self) -> None:
        """Load the tiny/fast model."""
        if self._tiny_loaded:
            return

        logger.info("Loading tiny model: %s", self.cascade.tiny_model)
        start = time.perf_counter()

        try:
            from mlx_lm import load
            self._tiny_model, self._tiny_tokenizer = load(self.cascade.tiny_model)
            self._tiny_formatter.set_tokenizer(self._tiny_tokenizer)
            self._tiny_loaded = True

            elapsed = (time.perf_counter() - start) * 1000
            rss = self._memory.get_process_rss_mb()
            logger.info(
                "Tiny model loaded in %.0fms (RSS: %.0fMB)", elapsed, rss
            )
        except Exception as e:
            logger.error("Failed to load tiny model: %s", e)
            raise

    def load_large(self) -> None:
        """Load the large/quality model."""
        if self._large_loaded:
            return

        logger.info("Loading large model: %s", self.cascade.large_model)
        start = time.perf_counter()

        try:
            from mlx_lm import load
            self._large_model, self._large_tokenizer = load(self.cascade.large_model)
            self._large_formatter.set_tokenizer(self._large_tokenizer)
            self._large_loaded = True

            elapsed = (time.perf_counter() - start) * 1000
            rss = self._memory.get_process_rss_mb()
            logger.info(
                "Large model loaded in %.0fms (RSS: %.0fMB)", elapsed, rss
            )
        except Exception as e:
            logger.error("Failed to load large model: %s", e)
            raise

    def unload_large(self) -> None:
        """Unload large model to reclaim memory."""
        if self._large_loaded:
            logger.info("Unloading large model to save memory")
            self._large_model = None
            self._large_tokenizer = None
            self._large_loaded = False
            self._large_formatter.set_tokenizer(None)
            gc.collect()

    def route(self, complexity: ComplexityLevel) -> str:
        """
        Determine which model to use for a given complexity.

        Returns 'tiny' or 'large'.
        """
        if complexity.rank <= self.cascade.tiny_model_max_complexity.rank:
            return "tiny"
        return "large"

    def get_model_and_tokenizer(
        self, complexity: ComplexityLevel
    ) -> tuple:
        """
        Get the appropriate model, tokenizer, and formatter for the complexity.

        Returns (model, tokenizer, formatter, model_name).
        Loads models on demand.
        """
        route = self.route(complexity)

        if route == "tiny":
            if not self._tiny_loaded:
                self.load_tiny()
            self._tiny_calls += 1
            return (
                self._tiny_model,
                self._tiny_tokenizer,
                self._tiny_formatter,
                "tiny",
            )
        else:
            if not self._large_loaded:
                self.load_large()
            self._large_calls += 1
            return (
                self._large_model,
                self._large_tokenizer,
                self._large_formatter,
                "large",
            )

    def initialize(self) -> None:
        """Pre-load both models."""
        self.load_tiny()
        self.load_large()
        logger.info(
            "Cascade initialized: tiny=%s, large=%s | %s",
            self.cascade.tiny_model.split("/")[-1],
            self.cascade.large_model.split("/")[-1],
            self._memory.format_status(),
        )

    def shutdown(self) -> None:
        """Unload all models."""
        self.unload_large()
        if self._tiny_loaded:
            self._tiny_model = None
            self._tiny_tokenizer = None
            self._tiny_loaded = False
            gc.collect()
