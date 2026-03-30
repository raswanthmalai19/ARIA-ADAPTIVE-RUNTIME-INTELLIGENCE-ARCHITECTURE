"""
ARIA Engine v2 — The Orchestrator (with Breakthrough Features)

This is the central nervous system of ARIA. It wires together all modules
into a single coherent execution pipeline with the 5 breakthrough features:

1. Dynamic Layer Execution — skip layers for simple queries
2. Multi-Model Cascade — route to tiny/large model
3. Self-Speculative Decoding — early layers as draft
4. KV-Cache Budget Control — limit memory per complexity
5. Attention-Aware Routing — profile and mask dormant heads

One call to engine.process(query) runs the full adaptive pipeline.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from aria.config import ARIAConfig, get_config, setup_logging
from aria.types import (
    ComplexityLevel, ExecutionResult, ExecutionMetrics,
    ExecutionStrategy, QualityVerdict,
)
from aria.analyzer.classifier import QueryClassifier
from aria.planner.strategy import StrategyPlanner
from aria.controller.engine import ModelEngine, ExecutionMode
from aria.memory.monitor import MemoryMonitor
from aria.monitor.tracker import MetricsTracker
from aria.monitor.store import MetricsStore
from aria.monitor.reporter import MetricsReporter
from aria.guardian.validator import OutputValidator
from aria.guardian.fallback import FallbackManager
from aria.cache.memoizer import InferenceMemoizer
from aria.consensus import MultiModelConsensus
from aria.cost_predictor import CostPredictor

logger = logging.getLogger("aria.engine")


class ARIAEngine:
    """
    The core ARIA runtime engine.

    Orchestrates the full adaptive inference pipeline:
      Query → Analyze → Plan → Execute (with layer/model adaptation) → Validate → Report

    With fallback cascade:
      If quality is poor → auto-escalate to higher tier → retry

    Execution modes:
      - dynamic_layers: Skip transformer layers based on complexity (default, most novel)
      - cascade: Route between tiny (0.5B) and large (3B) models
      - standard: Single model with parameter tuning only (baseline comparison)
    """

    def __init__(
        self,
        config: Optional[ARIAConfig] = None,
        execution_mode: str = "dynamic_layers",
    ):
        self.config = config or get_config()
        self._logger = setup_logging(self.config)

        # Initialize all modules
        self.analyzer = QueryClassifier()
        self.planner = StrategyPlanner(self.config)
        self.controller = ModelEngine(self.config)
        self.memory = MemoryMonitor(self.config)
        self.store = MetricsStore(self.config)
        self.reporter = MetricsReporter(self.store)
        self.validator = OutputValidator(self.config)
        self.fallback = FallbackManager(self.config)

        # Initialize new competitive features
        self.cache = InferenceMemoizer(max_cache_size=1000, ttl_seconds=3600)
        self.consensus = MultiModelConsensus()
        self.cost_predictor = CostPredictor()

        # Set execution mode
        mode_map = {
            "dynamic_layers": ExecutionMode.DYNAMIC_LAYERS,
            "cascade": ExecutionMode.CASCADE,
            "standard": ExecutionMode.STANDARD,
        }
        self._execution_mode = mode_map.get(execution_mode, ExecutionMode.DYNAMIC_LAYERS)
        self.controller.set_execution_mode(self._execution_mode)

        self._initialized = False

        logger.info("ARIA Engine v2 initialized")
        logger.info("Execution mode: %s", self._execution_mode.value)
        logger.info("Model: %s", self.config.model.name)
        logger.info(self.memory.format_status())

    def initialize(self) -> None:
        """
        Pre-load the model(s). Call before first query for faster
        first response, or let it auto-load on first process() call.
        """
        if not self._initialized:
            logger.info("Pre-loading model(s) [mode: %s]...", self._execution_mode.value)
            self.controller.load_model()
            self._initialized = True

            # Log adaptive feature info
            info = self.controller.get_adaptive_info()
            if "layer_profiles" in info:
                for level, profile in info["layer_profiles"].items():
                    logger.info(
                        "  Layer profile %s: %d/%d layers (%.0f%% skip)",
                        level, profile["layers_used"],
                        profile["total_layers"],
                        profile["skip_ratio"] * 100,
                    )

            logger.info("ARIA ready. %s", self.memory.format_status())

    def process(self, query: str, mode: str = "adaptive") -> ExecutionResult:
        """
        Process a query through the full ARIA pipeline.

        Args:
            query: The user's query string.
            mode: 'adaptive' (ARIA decides) or 'baseline' (fixed EXPERT mode).

        Returns:
            ExecutionResult with response, metrics, and all metadata.
        """
        # Ensure model is loaded
        if not self._initialized:
            self.initialize()

        # Start metrics tracking
        tracker = MetricsTracker(self.memory)
        tracker.start()

        # ── Step 1: Analyze Query ──
        analyze_start = time.perf_counter()
        profile = self.analyzer.classify(query)
        analyze_ms = (time.perf_counter() - analyze_start) * 1000
        tracker.record_analyzer(analyze_ms)

        logger.info(
            "Query analyzed: %s/%s (score=%.3f, confidence=%.3f) in %.1fms",
            profile.complexity_level.value,
            profile.task_type.value,
            profile.complexity_score,
            profile.confidence,
            analyze_ms,
        )

        # ── Step 2: Get Hardware State ──
        hardware = self.memory.get_state(force_refresh=True)

        # ── Step 3: Plan Execution Strategy ──
        plan_start = time.perf_counter()

        if mode == "baseline":
            strategy = self.planner.get_baseline_strategy()
        elif self.fallback.should_force_expert():
            strategy = self.planner.get_strategy_for_level(ComplexityLevel.EXPERT)
            strategy = ExecutionStrategy(
                complexity_level=ComplexityLevel.EXPERT,
                max_tokens=strategy.max_tokens,
                temperature=strategy.temperature,
                top_p=strategy.top_p,
                repetition_penalty=strategy.repetition_penalty,
                source="circuit_breaker_forced",
            )
            logger.warning("Circuit breaker active — forcing EXPERT strategy")
        else:
            strategy = self.planner.plan(profile, hardware)

        plan_ms = (time.perf_counter() - plan_start) * 1000
        tracker.record_planner(plan_ms)

        logger.info(
            "Strategy: %s (max_tokens=%d, temp=%.2f, source=%s) in %.1fms",
            strategy.complexity_level.value,
            strategy.max_tokens,
            strategy.temperature,
            strategy.source,
            plan_ms,
        )

        # ── Step 4: Execute with Fallback Cascade ──
        result = self._execute_with_fallback(
            query, profile, strategy, hardware, tracker, mode
        )

        # ── Step 5: Store Metrics ──
        self.store.record(result, mode=mode)

        return result

    def _execute_with_fallback(
        self,
        query: str,
        profile,
        strategy: ExecutionStrategy,
        hardware,
        tracker: MetricsTracker,
        mode: str,
    ) -> ExecutionResult:
        """
        Execute model generation with fallback cascade.

        If the output quality is FAIL, automatically upgrade to
        a higher tier and retry.
        """
        current_strategy = strategy
        fallback_triggered = False
        fallback_reason = None
        max_attempts = self.config.guardian.max_fallback_attempts + 1

        for attempt in range(max_attempts):
            # Generate response
            gen_result = self.controller.generate(
                query,
                current_strategy,
                task_type=profile.task_type.value,
            )

            tracker.record_generation(
                gen_result.tokens_generated,
                gen_result.latency_ms,
                gen_result.time_to_first_token_ms,
            )

            # Validate output quality
            quality = self.validator.validate(gen_result.text, profile)

            if quality.verdict == QualityVerdict.PASS or quality.verdict == QualityVerdict.DEGRADED:
                # Acceptable quality — success
                if attempt > 0:
                    fallback_triggered = True
                    fallback_reason = (
                        f"Upgraded to {current_strategy.complexity_level.value} "
                        f"after {attempt} attempt(s)"
                    )
                    logger.info("Fallback succeeded: %s", fallback_reason)

                self.fallback.record_success()

                metrics = tracker.finalize()

                # Enrich metrics with adaptive execution info
                metrics.execution_mode = gen_result.execution_mode
                metrics.layers_used = gen_result.layers_used
                metrics.total_layers = gen_result.total_layers
                metrics.model_used = gen_result.model_used

                return ExecutionResult(
                    query=query,
                    response=gen_result.text,
                    query_profile=profile,
                    strategy=current_strategy,
                    hardware_state=hardware,
                    metrics=metrics,
                    fallback_triggered=fallback_triggered,
                    fallback_reason=fallback_reason,
                )

            # Quality FAIL — try fallback
            logger.warning(
                "Quality FAIL on attempt %d (score=%.2f): %s",
                attempt + 1, quality.score, quality.reason,
            )

            # Get fallback strategy
            strategy_table = {
                level: self.planner.get_strategy_for_level(level)
                for level in ComplexityLevel
            }

            next_strategy = self.fallback.get_fallback_strategy(
                current_strategy, attempt, strategy_table
            )

            if next_strategy is None:
                break

            current_strategy = next_strategy

        # Total failure — return safety response
        self.fallback.record_failure(f"All attempts failed for query: {query[:100]}")

        metrics = tracker.finalize()

        return ExecutionResult(
            query=query,
            response=self.fallback.get_safety_response(),
            query_profile=profile,
            strategy=current_strategy,
            hardware_state=hardware,
            metrics=metrics,
            fallback_triggered=True,
            fallback_reason="All fallback attempts exhausted — safety response returned",
        )

    def get_status(self) -> dict:
        """Get comprehensive system status."""
        status = {
            "model_loaded": self.controller.is_loaded,
            "model_name": self.config.model.name,
            "execution_mode": self._execution_mode.value,
            "memory": {
                "status": self.memory.format_status(),
                "state": self.memory.get_state().memory_tier.value,
            },
            "guardian": self.fallback.get_status(),
            "metrics": {
                "total_executions": self.store.get_total_count(),
                "analyzer_avg_latency_ms": round(self.analyzer.avg_latency_ms, 3),
            },
        }

        # Add adaptive execution info
        if self.controller.is_loaded:
            status["adaptive"] = self.controller.get_adaptive_info()

        return status

    def shutdown(self) -> None:
        """Clean shutdown of all resources."""
        logger.info("Shutting down ARIA Engine...")
        self.controller.unload_model()
        self.store.close()
        logger.info("ARIA Engine shutdown complete")
