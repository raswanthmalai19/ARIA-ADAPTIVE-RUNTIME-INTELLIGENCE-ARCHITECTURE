"""
ARIA Fallback Manager

Implements the fallback cascade: when adaptive execution produces
poor quality output, automatically escalate to higher tiers.
Includes a circuit breaker for sustained failures.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from collections import deque

from aria.types import (
    ComplexityLevel, ExecutionStrategy, QualityReport, QualityVerdict,
)
from aria.config import ARIAConfig, get_config

logger = logging.getLogger("aria.guardian.fallback")


class FallbackManager:
    """
    Manages fallback escalation and circuit breaking.

    Fallback Cascade:
      1. Primary strategy (from Planner)
      2. Upgraded strategy (+1 complexity tier)
      3. Full strategy (EXPERT mode)
      4. Safety response (hard-coded safe message)

    Circuit Breaker:
      If N consecutive requests trigger fallbacks, temporarily
      disable adaptation and run everything at EXPERT level.
    """

    SAFETY_RESPONSE = (
        "I apologize, but I'm unable to provide a quality response "
        "under the current resource constraints. Please try again "
        "with a simpler query, or free up system memory by closing "
        "other applications."
    )

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_open_until: float = 0.0
        self._failure_history: deque = deque(maxlen=20)

    @property
    def is_circuit_open(self) -> bool:
        """Check if the circuit breaker is currently active."""
        if self._circuit_open and time.time() > self._circuit_open_until:
            # Circuit timeout expired, reset
            self._circuit_open = False
            self._consecutive_failures = 0
            logger.info("Circuit breaker reset — resuming adaptive mode")
        return self._circuit_open

    def should_force_expert(self) -> bool:
        """
        Whether the circuit breaker mandates EXPERT-only execution.

        When the circuit is open, all queries run at EXPERT level
        to maintain quality until the system stabilizes.
        """
        return self.is_circuit_open

    def get_fallback_strategy(
        self,
        current_strategy: ExecutionStrategy,
        attempt: int,
        strategy_table: dict[ComplexityLevel, ExecutionStrategy],
    ) -> Optional[ExecutionStrategy]:
        """
        Get the next fallback strategy for a failed attempt.

        Args:
            current_strategy: The strategy that just failed.
            attempt: Current attempt number (0-based).
            strategy_table: Available strategies by complexity level.

        Returns:
            A new ExecutionStrategy to try, or None if all fallbacks exhausted.
        """
        max_attempts = self.config.guardian.max_fallback_attempts

        if attempt >= max_attempts:
            logger.warning(
                "All %d fallback attempts exhausted", max_attempts
            )
            return None

        # Upgrade to the next tier
        current_level = current_strategy.complexity_level
        next_level = current_level.upgrade()

        if next_level == current_level and current_level == ComplexityLevel.EXPERT:
            # Already at EXPERT, can't upgrade further
            logger.warning("Already at EXPERT level — no further fallback available")
            return None

        # If not at EXPERT yet, try EXPERT directly on second attempt
        if attempt >= 1:
            next_level = ComplexityLevel.EXPERT

        fallback = strategy_table.get(next_level)
        if fallback is None:
            return None

        logger.info(
            "Fallback attempt %d: %s → %s",
            attempt + 1,
            current_level.value,
            next_level.value,
        )

        return ExecutionStrategy(
            complexity_level=next_level,
            max_tokens=fallback.max_tokens,
            temperature=fallback.temperature,
            top_p=fallback.top_p,
            repetition_penalty=fallback.repetition_penalty,
            source=f"fallback_attempt_{attempt + 1}",
        )

    def record_success(self) -> None:
        """Record a successful execution — resets failure counter."""
        self._consecutive_failures = 0
        self._failure_history.append(("success", time.time()))

    def record_failure(self, reason: str = "") -> None:
        """
        Record a failed execution.

        If consecutive failures exceed the threshold, open the circuit breaker.
        """
        self._consecutive_failures += 1
        self._failure_history.append(("failure", time.time()))

        logger.warning(
            "Failure recorded (%d consecutive): %s",
            self._consecutive_failures, reason,
        )

        threshold = self.config.guardian.circuit_breaker_threshold
        if self._consecutive_failures >= threshold:
            self._open_circuit()

    def _open_circuit(self) -> None:
        """
        Open the circuit breaker.

        While open, all queries run at EXPERT level (no adaptation).
        Auto-resets after 60 seconds.
        """
        self._circuit_open = True
        self._circuit_open_until = time.time() + 60.0  # 60 second cooldown

        logger.critical(
            "⚠️ CIRCUIT BREAKER OPEN — %d consecutive failures. "
            "All queries will run at EXPERT level for 60 seconds.",
            self._consecutive_failures,
        )

    def get_safety_response(self) -> str:
        """Return the hard-coded safety response for total failure."""
        return self.SAFETY_RESPONSE

    def get_status(self) -> dict:
        """Get the current fallback system status."""
        recent_failures = sum(
            1 for event, _ in self._failure_history
            if event == "failure"
        )
        return {
            "consecutive_failures": self._consecutive_failures,
            "circuit_open": self.is_circuit_open,
            "circuit_resets_in": max(
                0, self._circuit_open_until - time.time()
            ) if self._circuit_open else 0,
            "recent_failure_rate": recent_failures / max(len(self._failure_history), 1),
            "total_events": len(self._failure_history),
        }
