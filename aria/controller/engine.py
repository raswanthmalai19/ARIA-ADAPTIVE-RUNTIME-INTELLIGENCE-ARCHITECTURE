"""
ARIA Model Engine v2

Core inference engine with three modes of adaptive execution:
1. DYNAMIC LAYERS — Skip transformer layers for simple queries
2. CASCADE — Route to tiny/large model based on complexity
3. STANDARD — Single model with parameter tuning (fallback)

This is where ARIA's real intelligence lives — the model doesn't
just change how much output it generates, it changes HOW IT THINKS.
"""

from __future__ import annotations

import gc
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Generator

from aria.types import ComplexityLevel, ExecutionStrategy, ExecutionMetrics
from aria.config import ARIAConfig, get_config
from aria.controller.formatter import PromptFormatter
from aria.memory.monitor import MemoryMonitor

logger = logging.getLogger("aria.controller")


class ExecutionMode(str, Enum):
    """How ARIA executes the model."""
    DYNAMIC_LAYERS = "dynamic_layers"  # Skip layers based on complexity
    CASCADE = "cascade"                # Route to tiny/large model
    STANDARD = "standard"              # Single model, parameter tuning only


@dataclass
class GenerationResult:
    """Result from a single model generation."""
    text: str
    tokens_generated: int
    latency_ms: float
    tokens_per_second: float
    time_to_first_token_ms: float
    execution_mode: str = "standard"
    layers_used: int = 0
    total_layers: int = 0
    model_used: str = ""


class ModelEngine:
    """
    MLX-based model engine with adaptive execution.

    Supports three execution modes:
    - DYNAMIC_LAYERS: Patches model to skip layers per complexity
    - CASCADE: Routes between tiny (0.5B) and large (3B) models
    - STANDARD: Single model with generation parameter tuning

    The engine automatically selects the best mode based on
    configuration and available resources.
    """

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()
        self._model = None
        self._tokenizer = None
        self._formatter = PromptFormatter()
        self._memory_monitor = MemoryMonitor(self.config)
        self._model_loaded = False
        self._model_name = self.config.model.name

        # Adaptive components
        self._adaptive_wrapper = None
        self._cascade = None
        self._execution_mode = ExecutionMode.DYNAMIC_LAYERS  # Default to most novel

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    @property
    def formatter(self) -> PromptFormatter:
        return self._formatter

    @property
    def execution_mode(self) -> ExecutionMode:
        return self._execution_mode

    @property
    def adaptive_wrapper(self):
        return self._adaptive_wrapper

    @property
    def cascade(self):
        return self._cascade

    def set_execution_mode(self, mode: ExecutionMode) -> None:
        """Set the execution mode."""
        self._execution_mode = mode
        logger.info("Execution mode set to: %s", mode.value)

    def load_model(self, model_name: Optional[str] = None) -> None:
        """
        Load the model(s) based on execution mode.
        """
        if self._execution_mode == ExecutionMode.CASCADE:
            self._load_cascade()
        else:
            self._load_single(model_name)

    def _load_single(self, model_name: Optional[str] = None) -> None:
        """Load a single model for DYNAMIC_LAYERS or STANDARD mode."""
        if self._model_loaded:
            logger.info("Model already loaded: %s", self._model_name)
            return

        name = model_name or self._model_name
        logger.info("Loading model: %s ...", name)

        start = time.perf_counter()

        try:
            from mlx_lm import load
            self._model, self._tokenizer = load(name)
            self._formatter.set_tokenizer(self._tokenizer)
            self._model_loaded = True
            self._model_name = name

            elapsed = (time.perf_counter() - start) * 1000
            rss = self._memory_monitor.get_process_rss_mb()

            logger.info(
                "Model loaded in %.0f ms (RSS: %.0f MB): %s",
                elapsed, rss, name
            )

            # Initialize adaptive wrapper for dynamic layer mode
            if self._execution_mode == ExecutionMode.DYNAMIC_LAYERS:
                from aria.controller.adaptive_model import AdaptiveModelWrapper
                self._adaptive_wrapper = AdaptiveModelWrapper(self._model)
                total = self._adaptive_wrapper.total_layers
                logger.info(
                    "Adaptive layer execution enabled: %d total layers", total
                )
                for level, profile in self._adaptive_wrapper._layer_profiles.items():
                    logger.info("  %s", profile.description)

        except ImportError:
            logger.error("mlx-lm is not installed. Install with: pip install mlx-lm")
            raise
        except Exception as e:
            logger.error("Failed to load model '%s': %s", name, e)
            raise

    def _load_cascade(self) -> None:
        """Load models for CASCADE mode."""
        from aria.controller.cascade import ModelCascade, CascadeConfig

        cascade_config = CascadeConfig(
            large_model=self._model_name,
        )
        self._cascade = ModelCascade(
            config=self.config,
            cascade_config=cascade_config,
        )
        self._cascade.initialize()
        self._model_loaded = True
        logger.info("Cascade mode initialized")

    def generate(
        self,
        query: str,
        strategy: ExecutionStrategy,
        task_type: str = "factual",
    ) -> GenerationResult:
        """
        Generate a response using the model with adaptive execution.

        The actual execution path depends on the current execution mode:
        - DYNAMIC_LAYERS: Set active layers, then generate
        - CASCADE: Route to tiny/large model, then generate
        - STANDARD: Generate with parameter tuning only
        """
        if not self._model_loaded:
            self.load_model()

        if self._execution_mode == ExecutionMode.CASCADE:
            return self._generate_cascade(query, strategy, task_type)
        elif self._execution_mode == ExecutionMode.DYNAMIC_LAYERS:
            return self._generate_dynamic(query, strategy, task_type)
        else:
            return self._generate_standard(query, strategy, task_type)

    def _generate_dynamic(
        self,
        query: str,
        strategy: ExecutionStrategy,
        task_type: str,
    ) -> GenerationResult:
        """Generate with dynamic layer skipping."""
        # Set the complexity for layer selection
        if self._adaptive_wrapper:
            self._adaptive_wrapper.set_complexity(strategy.complexity_level)
            layers_used = self._adaptive_wrapper.get_active_layer_count()
            total_layers = self._adaptive_wrapper.total_layers
        else:
            layers_used = 0
            total_layers = 0

        logger.info(
            "Dynamic execution: %s → %d/%d layers",
            strategy.complexity_level.value, layers_used, total_layers,
        )

        result = self._run_generation(
            self._model, self._tokenizer, self._formatter,
            query, strategy, task_type,
        )

        result.execution_mode = "dynamic_layers"
        result.layers_used = layers_used
        result.total_layers = total_layers
        result.model_used = self._model_name.split("/")[-1]

        return result

    def _generate_cascade(
        self,
        query: str,
        strategy: ExecutionStrategy,
        task_type: str,
    ) -> GenerationResult:
        """Generate with multi-model cascade routing."""
        model, tokenizer, formatter, model_label = (
            self._cascade.get_model_and_tokenizer(strategy.complexity_level)
        )

        logger.info(
            "Cascade routing: %s → %s model",
            strategy.complexity_level.value, model_label,
        )

        result = self._run_generation(
            model, tokenizer, formatter,
            query, strategy, task_type,
        )

        result.execution_mode = "cascade"
        result.model_used = model_label

        return result

    def _generate_standard(
        self,
        query: str,
        strategy: ExecutionStrategy,
        task_type: str,
    ) -> GenerationResult:
        """Generate with standard single model (parameter tuning only)."""
        result = self._run_generation(
            self._model, self._tokenizer, self._formatter,
            query, strategy, task_type,
        )
        result.execution_mode = "standard"
        result.model_used = self._model_name.split("/")[-1]
        return result

    def _run_generation(
        self,
        model,
        tokenizer,
        formatter: PromptFormatter,
        query: str,
        strategy: ExecutionStrategy,
        task_type: str,
    ) -> GenerationResult:
        """
        Core generation using production-grade inference engine.

        Note: The passed model/tokenizer parameters are ignored.
        We use the adaptive inference engine which handles model selection,
        caching, and error recovery automatically.
        """
        # Format the prompt
        prompt = formatter.format(query, task_type=task_type)

        logger.debug(
            "Generating with AdaptiveInferenceEngine: complexity=%s",
            strategy.complexity_level.name,
        )

        start = time.perf_counter()

        # Import and use the production inference engine
        # This handles everything: model loading, caching, routing, error recovery
        from aria.inference_engine import get_cascade_router
        
        router = get_cascade_router()
        
        # Map complexity to score for routing
        complexity_scores = {
            "SIMPLE": 0.25,
            "MODERATE": 0.5,
            "COMPLEX": 0.75,
            "EXPERT": 0.95,
        }
        complexity_score = complexity_scores.get(
            strategy.complexity_level.name, 0.5
        )
        
        # Get inference result with adaptive model selection and caching
        inference_result = router.route_and_infer(
            prompt=prompt,
            complexity_score=complexity_score,
        )
        
        result = GenerationResult(
            text=inference_result.text,
            tokens_generated=inference_result.tokens_generated,
            latency_ms=inference_result.latency_ms,
            tokens_per_second=inference_result.tokens_per_second,
            time_to_first_token_ms=inference_result.time_to_first_token_ms,
            model_used=inference_result.model_used,
        )
        
        if inference_result.success:
            logger.info(
                "Generated %d tokens in %.0f ms (%.1f tok/s, TTFT: %.0f ms) using %s [%s]",
                inference_result.tokens_generated,
                inference_result.latency_ms,
                inference_result.tokens_per_second,
                inference_result.time_to_first_token_ms,
                inference_result.model_used,
                "CACHED" if inference_result.cache_hit else "FRESH",
            )
        else:
            logger.error(
                "Generation failed: %s",
                inference_result.error
            )
        
        return result


    def _get_kv_budget(self, complexity: ComplexityLevel) -> Optional[int]:
        """
        Get KV-cache size budget based on complexity.

        Feature 4: KV-Cache Budget Control
        Simple queries get a smaller KV-cache, saving memory.
        """
        budgets = {
            ComplexityLevel.SIMPLE: 256,
            ComplexityLevel.MODERATE: 512,
            ComplexityLevel.COMPLEX: 1024,
            ComplexityLevel.EXPERT: None,  # No limit
        }
        return budgets.get(complexity)

    def unload_model(self) -> None:
        """Unload all models to free memory."""
        if self._adaptive_wrapper:
            self._adaptive_wrapper.unpatch_model()
            self._adaptive_wrapper = None

        if self._cascade:
            self._cascade.shutdown()
            self._cascade = None

        if self._model_loaded:
            logger.info("Unloading model: %s", self._model_name)
            self._model = None
            self._tokenizer = None
            self._model_loaded = False
            self._formatter.set_tokenizer(None)
            gc.collect()
            logger.info("Model unloaded, memory freed")

    def get_adaptive_info(self) -> dict:
        """Get information about the adaptive execution state."""
        info = {
            "execution_mode": self._execution_mode.value,
            "model_loaded": self._model_loaded,
            "model_name": self._model_name,
        }

        if self._adaptive_wrapper:
            info["layer_profiles"] = self._adaptive_wrapper.get_profile_summary()
            current = self._adaptive_wrapper.current_profile
            if current:
                info["current_layers"] = f"{current.layers_used}/{current.total_layers}"

        if self._cascade:
            info["cascade"] = {
                "tiny_loaded": self._cascade.is_tiny_loaded,
                "large_loaded": self._cascade.is_large_loaded,
                "routing_stats": self._cascade.routing_stats,
            }

        return info
