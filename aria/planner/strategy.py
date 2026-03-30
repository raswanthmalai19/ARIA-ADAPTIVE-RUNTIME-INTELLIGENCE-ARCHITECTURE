"""
ARIA Execution Strategy Planner

Maps query complexity profiles and hardware state into concrete
execution strategies. This is where ARIA's adaptive intelligence
makes its core decisions.
"""

from __future__ import annotations

import logging
from typing import Optional

from aria.types import (
    ComplexityLevel, ExecutionStrategy, HardwareState,
    MemoryTier, QueryProfile,
)
from aria.config import ARIAConfig, get_config

logger = logging.getLogger("aria.planner")


class StrategyPlanner:
    """
    Maps QueryProfile + HardwareState → ExecutionStrategy.

    The planner is deterministic: same inputs always produce same outputs.
    Hardware-aware overrides are applied transparently with clear logging.
    """

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()
        self._strategy_table = self._build_strategy_table()

    def plan(
        self,
        profile: QueryProfile,
        hardware: HardwareState,
    ) -> ExecutionStrategy:
        """
        Decide the execution strategy for a given query and hardware state.

        Args:
            profile: Classified query profile from the Analyzer.
            hardware: Current hardware state from the Memory Manager.

        Returns:
            ExecutionStrategy with concrete parameters for model execution.
        """
        # Start with the base strategy for this complexity level
        base_level = profile.complexity_level
        strategy = self._strategy_table[base_level]

        logger.debug(
            "Base strategy: %s (score=%.3f, confidence=%.3f)",
            base_level.value, profile.complexity_score, profile.confidence,
        )

        # ── Conservative Classification ──
        # When confidence is low, upgrade complexity (better safe than sorry)
        if not profile.is_high_confidence and base_level != ComplexityLevel.EXPERT:
            upgraded_level = base_level.upgrade()
            strategy = self._strategy_table[upgraded_level]
            strategy = ExecutionStrategy(
                complexity_level=upgraded_level,
                max_tokens=strategy.max_tokens,
                temperature=strategy.temperature,
                top_p=strategy.top_p,
                repetition_penalty=strategy.repetition_penalty,
                source="planner_confidence_upgrade",
            )
            logger.info(
                "Low confidence (%.2f) — upgraded %s → %s",
                profile.confidence, base_level.value, upgraded_level.value,
            )

        # ── Hardware-Aware Overrides ──
        strategy = self._apply_hardware_overrides(strategy, hardware)

        return strategy

    def get_baseline_strategy(self) -> ExecutionStrategy:
        """
        Return the full/fixed execution strategy (used as benchmark baseline).

        This represents 'no adaptation' — always runs at EXPERT level
        regardless of query complexity.
        """
        return ExecutionStrategy(
            complexity_level=ComplexityLevel.EXPERT,
            max_tokens=self.config.strategy.expert_max_tokens,
            temperature=self.config.strategy.expert_temperature,
            top_p=self.config.strategy.expert_top_p,
            repetition_penalty=self.config.strategy.expert_repetition_penalty,
            source="baseline_fixed",
        )

    def get_strategy_for_level(self, level: ComplexityLevel) -> ExecutionStrategy:
        """Get the strategy for a specific complexity level (for fallback use)."""
        return ExecutionStrategy(**{
            **self._strategy_table[level].__dict__,
            "source": "direct_level_request",
        })

    def _apply_hardware_overrides(
        self,
        strategy: ExecutionStrategy,
        hardware: HardwareState,
    ) -> ExecutionStrategy:
        """
        Apply hardware-aware constraints to the strategy.

        Memory pressure levels cause progressive degradation:
        - YELLOW: Log warning, no changes
        - ORANGE: Cap at MODERATE, reduce max_tokens
        - RED: Force SIMPLE, drastically reduce max_tokens
        """
        if hardware.memory_tier == MemoryTier.GREEN:
            return strategy

        if hardware.memory_tier == MemoryTier.YELLOW:
            logger.warning(
                "Memory pressure YELLOW (%.1f%%) — proceeding with caution",
                hardware.memory_used_percent,
            )
            return strategy

        if hardware.memory_tier == MemoryTier.ORANGE:
            # Cap at MODERATE
            if strategy.complexity_level.rank > ComplexityLevel.MODERATE.rank:
                capped = self._strategy_table[ComplexityLevel.MODERATE]
                logger.warning(
                    "Memory pressure ORANGE (%.1f%%) — capping %s → MODERATE",
                    hardware.memory_used_percent,
                    strategy.complexity_level.value,
                )
                return ExecutionStrategy(
                    complexity_level=ComplexityLevel.MODERATE,
                    max_tokens=int(capped.max_tokens * 0.75),
                    temperature=capped.temperature,
                    top_p=capped.top_p,
                    repetition_penalty=capped.repetition_penalty,
                    source="memory_override_orange",
                )
            # Even if already moderate or below, reduce tokens
            return ExecutionStrategy(
                complexity_level=strategy.complexity_level,
                max_tokens=int(strategy.max_tokens * 0.75),
                temperature=strategy.temperature,
                top_p=strategy.top_p,
                repetition_penalty=strategy.repetition_penalty,
                source="memory_override_orange",
            )

        if hardware.memory_tier == MemoryTier.RED:
            # Emergency mode: force SIMPLE with minimal tokens
            logger.critical(
                "Memory pressure RED (%.1f%%) — emergency mode, forcing SIMPLE",
                hardware.memory_used_percent,
            )
            simple = self._strategy_table[ComplexityLevel.SIMPLE]
            return ExecutionStrategy(
                complexity_level=ComplexityLevel.SIMPLE,
                max_tokens=max(int(simple.max_tokens * 0.5), 32),
                temperature=simple.temperature,
                top_p=simple.top_p,
                repetition_penalty=simple.repetition_penalty,
                source="memory_override_red",
            )

        return strategy

    def _build_strategy_table(self) -> dict[ComplexityLevel, ExecutionStrategy]:
        """Build the strategy lookup table from configuration."""
        cfg = self.config.strategy
        return {
            ComplexityLevel.SIMPLE: ExecutionStrategy(
                complexity_level=ComplexityLevel.SIMPLE,
                max_tokens=cfg.simple_max_tokens,
                temperature=cfg.simple_temperature,
                top_p=cfg.simple_top_p,
                repetition_penalty=cfg.simple_repetition_penalty,
                source="planner",
            ),
            ComplexityLevel.MODERATE: ExecutionStrategy(
                complexity_level=ComplexityLevel.MODERATE,
                max_tokens=cfg.moderate_max_tokens,
                temperature=cfg.moderate_temperature,
                top_p=cfg.moderate_top_p,
                repetition_penalty=cfg.moderate_repetition_penalty,
                source="planner",
            ),
            ComplexityLevel.COMPLEX: ExecutionStrategy(
                complexity_level=ComplexityLevel.COMPLEX,
                max_tokens=cfg.complex_max_tokens,
                temperature=cfg.complex_temperature,
                top_p=cfg.complex_top_p,
                repetition_penalty=cfg.complex_repetition_penalty,
                source="planner",
            ),
            ComplexityLevel.EXPERT: ExecutionStrategy(
                complexity_level=ComplexityLevel.EXPERT,
                max_tokens=cfg.expert_max_tokens,
                temperature=cfg.expert_temperature,
                top_p=cfg.expert_top_p,
                repetition_penalty=cfg.expert_repetition_penalty,
                source="planner",
            ),
        }
