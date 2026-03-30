"""
ARIA Output Validator

Validates model output quality to detect degraded or failed generations.
This is the core of ARIA's trustworthiness — ensuring adaptive execution
doesn't silently produce garbage.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Optional

from aria.types import (
    ComplexityLevel, QualityReport, QualityVerdict, QueryProfile,
)
from aria.config import ARIAConfig, get_config

logger = logging.getLogger("aria.guardian.validator")


class OutputValidator:
    """
    Validates model output quality using heuristic checks.

    Checks performed:
    1. Empty/truncated output detection
    2. N-gram repetition detection
    3. Coherence heuristics (sentence completion, structure)
    4. Length adequacy (response vs expected)
    """

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()

    def validate(
        self,
        response: str,
        profile: QueryProfile,
    ) -> QualityReport:
        """
        Validate a model's response against quality criteria.

        Args:
            response: The generated text.
            profile: The query profile (used for context-aware validation).

        Returns:
            QualityReport with verdict, score, and detailed checks.
        """
        checks_passed = []
        checks_failed = []
        scores = []

        # ── Check 1: Non-Empty ──
        if self._check_non_empty(response, profile):
            checks_passed.append("non_empty")
            scores.append(1.0)
        else:
            checks_failed.append("non_empty")
            scores.append(0.0)

        # ── Check 2: Minimum Length ──
        if self._check_minimum_length(response, profile):
            checks_passed.append("minimum_length")
            scores.append(1.0)
        else:
            checks_failed.append("minimum_length")
            scores.append(0.2)

        # ── Check 3: Repetition ──
        rep_score = self._check_repetition(response)
        if rep_score >= 0.6:
            checks_passed.append("low_repetition")
        else:
            checks_failed.append("high_repetition")
        scores.append(rep_score)

        # ── Check 4: Coherence ──
        coh_score = self._check_coherence(response)
        if coh_score >= 0.5:
            checks_passed.append("coherent")
        else:
            checks_failed.append("incoherent")
        scores.append(coh_score)

        # ── Check 5: Not just echoing the query ──
        if self._check_not_echo(response, profile.query):
            checks_passed.append("not_echo")
            scores.append(1.0)
        else:
            checks_failed.append("echo_detected")
            scores.append(0.1)

        # Aggregate score
        total_score = sum(scores) / len(scores) if scores else 0.0

        # Determine verdict
        if "non_empty" in checks_failed:
            verdict = QualityVerdict.FAIL
            reason = "Response is empty or whitespace-only"
        elif total_score < 0.4:
            verdict = QualityVerdict.FAIL
            reason = f"Quality score too low: {total_score:.2f}"
        elif total_score < 0.65:
            verdict = QualityVerdict.DEGRADED
            reason = f"Quality below threshold: {total_score:.2f}"
        else:
            verdict = QualityVerdict.PASS
            reason = "All quality checks passed"

        report = QualityReport(
            verdict=verdict,
            score=round(total_score, 3),
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            reason=reason,
        )

        if verdict != QualityVerdict.PASS:
            logger.warning(
                "Quality %s (score=%.2f): %s | passed=%s, failed=%s",
                verdict.value, total_score, reason,
                checks_passed, checks_failed,
            )
        else:
            logger.debug(
                "Quality PASS (score=%.2f): %s",
                total_score, checks_passed,
            )

        return report

    def _check_non_empty(self, response: str, profile: QueryProfile) -> bool:
        """Check that the response is not empty."""
        return len(response.strip()) > 0

    def _check_minimum_length(
        self, response: str, profile: QueryProfile
    ) -> bool:
        """Check that the response meets minimum length for its complexity."""
        min_tokens = self.config.guardian.min_response_tokens
        words = response.strip().split()

        # Adjust minimum based on complexity
        if profile.complexity_level == ComplexityLevel.SIMPLE:
            threshold = max(min_tokens // 3, 3)
        elif profile.complexity_level == ComplexityLevel.MODERATE:
            threshold = min_tokens // 2
        else:
            threshold = min_tokens

        return len(words) >= threshold

    def _check_repetition(self, response: str) -> float:
        """
        Check for excessive n-gram repetition.

        Returns a score from 0 (all repeated) to 1 (no repetition).
        """
        words = response.lower().split()
        if len(words) < 10:
            return 1.0  # Too short to check meaningfully

        # Check trigram repetition
        trigrams = [
            " ".join(words[i:i + 3])
            for i in range(len(words) - 2)
        ]

        if not trigrams:
            return 1.0

        counter = Counter(trigrams)
        total = len(trigrams)
        repeated = sum(count - 1 for count in counter.values() if count > 1)

        repetition_ratio = repeated / total
        max_ratio = self.config.guardian.max_repetition_ratio

        if repetition_ratio > max_ratio:
            return max(0.0, 1.0 - (repetition_ratio / max_ratio))

        return 1.0 - (repetition_ratio * 0.3)

    def _check_coherence(self, response: str) -> float:
        """
        Basic coherence check using structural heuristics.

        Checks:
        - Sentence-ending punctuation exists
        - Response doesn't end mid-word
        - Has some alphanumeric content
        """
        text = response.strip()
        if not text:
            return 0.0

        score = 0.5  # Base score

        # Has sentence-ending punctuation
        if text[-1] in ".!?":
            score += 0.2
        elif text[-1] in ":;,":
            score += 0.05  # Partial credit for other punctuation

        # Has alphanumeric content (not just symbols)
        alpha_count = sum(1 for c in text if c.isalnum())
        if alpha_count / max(len(text), 1) > 0.5:
            score += 0.15

        # Multiple words (not a single fragment)
        if len(text.split()) >= 3:
            score += 0.15

        return min(score, 1.0)

    def _check_not_echo(self, response: str, query: str) -> bool:
        """Check that the response isn't just echoing back the query."""
        if not response.strip() or not query.strip():
            return True

        response_lower = response.strip().lower()
        query_lower = query.strip().lower()

        # Exact echo
        if response_lower == query_lower:
            return False

        # Response is mostly the query (>80% overlap)
        if len(query_lower) > 10:
            if query_lower in response_lower:
                query_ratio = len(query_lower) / max(len(response_lower), 1)
                if query_ratio > 0.8:
                    return False

        return True
