"""
ARIA Query Classifier

Multi-signal classifier that determines query complexity and task type.
Uses a weighted scoring system across lexical, structural, and domain features.
No ML model required — runs in <2ms.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from aria.types import ComplexityLevel, TaskType, QueryProfile
from aria.analyzer.features import QueryFeatures, extract_features

logger = logging.getLogger("aria.analyzer")


# ─────────────────────────────────────────────
# Scoring Weights
# ─────────────────────────────────────────────

# Weights for final complexity score
_WEIGHTS = {
    "length": 0.20,           # How long the query is
    "vocabulary": 0.10,       # Vocabulary diversity
    "domain": 0.25,           # Domain keyword density
    "structure": 0.20,        # Structural complexity
    "complexity_markers": 0.15,  # Explicit complexity markers
    "multi_part": 0.10,       # Multi-part request
}

# Thresholds for complexity level mapping
_COMPLEXITY_THRESHOLDS = {
    ComplexityLevel.SIMPLE: 0.25,     # score < 0.25
    ComplexityLevel.MODERATE: 0.50,   # 0.25 <= score < 0.50
    ComplexityLevel.COMPLEX: 0.75,    # 0.50 <= score < 0.75
    # EXPERT: score >= 0.75
}


class QueryClassifier:
    """
    Classifies incoming queries by complexity level and task type.

    Uses a multi-signal weighted scoring approach:
    1. Extract features from the query (lexical, structural, domain)
    2. Compute a weighted complexity score
    3. Map score to complexity level
    4. Determine task type from keyword dominance
    5. Estimate expected output length

    All operations run in <2ms with no external dependencies.
    """

    def __init__(self):
        self._call_count = 0
        self._total_latency_ms = 0.0

    def classify(self, query: str) -> QueryProfile:
        """
        Classify a query and return a complete QueryProfile.

        Args:
            query: The raw user query string.

        Returns:
            QueryProfile with complexity, task type, and metadata.
        """
        start = time.perf_counter()

        # Extract features
        features = extract_features(query)

        # Handle empty/trivial input
        if features.word_count == 0:
            profile = QueryProfile(
                query=query,
                complexity_score=0.0,
                complexity_level=ComplexityLevel.SIMPLE,
                task_type=TaskType.CONVERSATION,
                estimated_output_tokens=32,
                confidence=1.0,
                features=features.to_dict(),
            )
            self._record_latency(start)
            return profile

        # Fast-path: greetings
        if features.is_greeting and features.word_count <= 5:
            profile = QueryProfile(
                query=query,
                complexity_score=0.05,
                complexity_level=ComplexityLevel.SIMPLE,
                task_type=TaskType.CONVERSATION,
                estimated_output_tokens=32,
                confidence=0.95,
                features=features.to_dict(),
            )
            self._record_latency(start)
            return profile

        # Compute weighted complexity score
        complexity_score = self._compute_complexity_score(features)

        # Map to complexity level
        complexity_level = self._score_to_level(complexity_score)

        # Determine task type
        task_type = self._determine_task_type(features)

        # Estimate output tokens
        estimated_tokens = self._estimate_output_tokens(
            complexity_level, task_type, features
        )

        # Compute confidence
        confidence = self._compute_confidence(features, complexity_score)

        profile = QueryProfile(
            query=query,
            complexity_score=round(complexity_score, 4),
            complexity_level=complexity_level,
            task_type=task_type,
            estimated_output_tokens=estimated_tokens,
            confidence=round(confidence, 4),
            features=features.to_dict(),
        )

        self._record_latency(start)

        logger.debug(
            "Query classified: level=%s, type=%s, score=%.3f, confidence=%.3f",
            complexity_level.value, task_type.value,
            complexity_score, confidence,
        )

        return profile

    def _compute_complexity_score(self, f: QueryFeatures) -> float:
        """Compute the weighted complexity score from features."""
        scores = {}

        # Length score: normalized word count (0-100 words → 0-1)
        scores["length"] = min(f.word_count / 80.0, 1.0)

        # Vocabulary score: richness (diversity of word choice)
        scores["vocabulary"] = f.vocabulary_richness if f.word_count > 3 else 0.3

        # Domain score: keyword density
        scores["domain"] = f.domain_score

        # Structure score: structural complexity
        scores["structure"] = f.structural_complexity

        # Complexity markers: explicit indicators of complex requests
        scores["complexity_markers"] = min(f.complexity_marker_count / 3.0, 1.0)

        # Multi-part: number of sub-requests detected
        scores["multi_part"] = min(f.multi_part_count / 3.0, 1.0)

        # Weighted sum
        total = sum(
            scores[key] * _WEIGHTS[key]
            for key in _WEIGHTS
        )

        # Boost for code blocks (strong signal)
        if f.has_code_block:
            total = min(total + 0.15, 1.0)

        return min(max(total, 0.0), 1.0)

    def _score_to_level(self, score: float) -> ComplexityLevel:
        """Map a continuous score to a discrete complexity level."""
        if score < _COMPLEXITY_THRESHOLDS[ComplexityLevel.SIMPLE]:
            return ComplexityLevel.SIMPLE
        elif score < _COMPLEXITY_THRESHOLDS[ComplexityLevel.MODERATE]:
            return ComplexityLevel.MODERATE
        elif score < _COMPLEXITY_THRESHOLDS[ComplexityLevel.COMPLEX]:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.EXPERT

    def _determine_task_type(self, f: QueryFeatures) -> TaskType:
        """Determine the dominant task type from keyword features."""
        # Score each task type by keyword presence
        type_scores = {
            TaskType.CODE: f.code_keyword_count * 1.5,  # Boost code detection
            TaskType.MATH: f.math_keyword_count * 1.3,
            TaskType.REASONING: f.reasoning_keyword_count * 1.0,
            TaskType.CREATIVE: f.creative_keyword_count * 1.0,
        }

        # Check for greeting first
        if f.is_greeting and f.word_count <= 8:
            return TaskType.CONVERSATION

        # Check for code blocks (strong signal)
        if f.has_code_block:
            return TaskType.CODE

        # Find dominant type
        if max(type_scores.values()) > 0:
            dominant = max(type_scores, key=type_scores.get)
            return dominant

        # Default classification based on structure
        if f.has_question_mark and f.word_count <= 15:
            return TaskType.FACTUAL
        elif f.has_question_mark:
            return TaskType.REASONING
        elif f.word_count > 30:
            return TaskType.INSTRUCTION
        else:
            return TaskType.FACTUAL

    def _estimate_output_tokens(
        self,
        level: ComplexityLevel,
        task_type: TaskType,
        f: QueryFeatures,
    ) -> int:
        """Estimate expected output length in tokens."""
        base_estimates = {
            ComplexityLevel.SIMPLE: 64,
            ComplexityLevel.MODERATE: 192,
            ComplexityLevel.COMPLEX: 384,
            ComplexityLevel.EXPERT: 768,
        }

        base = base_estimates[level]

        # Task-type multipliers
        multipliers = {
            TaskType.CONVERSATION: 0.5,
            TaskType.FACTUAL: 0.7,
            TaskType.MATH: 0.8,
            TaskType.REASONING: 1.2,
            TaskType.CREATIVE: 1.3,
            TaskType.CODE: 1.5,
            TaskType.INSTRUCTION: 1.3,
        }

        return int(base * multipliers.get(task_type, 1.0))

    def _compute_confidence(self, f: QueryFeatures, score: float) -> float:
        """
        Compute classifier confidence.

        High confidence when:
        - Clear greeting (very obvious)
        - Strong domain keyword presence
        - Score is clearly in one tier (not near boundary)

        Low confidence when:
        - Score is near a tier boundary
        - Few distinctive features
        - Short ambiguous queries
        """
        confidence = 0.6  # Base confidence

        # Boost for strong keyword signals
        total_keywords = (
            f.reasoning_keyword_count +
            f.code_keyword_count +
            f.math_keyword_count +
            f.creative_keyword_count
        )
        if total_keywords >= 3:
            confidence += 0.2
        elif total_keywords >= 1:
            confidence += 0.1

        # Boost for structural signals
        if f.has_code_block:
            confidence += 0.15
        if f.complexity_marker_count >= 2:
            confidence += 0.1

        # Penalty for boundary scores (near tier transitions)
        for threshold in _COMPLEXITY_THRESHOLDS.values():
            distance = abs(score - threshold)
            if distance < 0.05:
                confidence -= 0.15
                break

        # Penalty for very short, ambiguous queries
        if f.word_count <= 3 and not f.is_greeting:
            confidence -= 0.1

        # Boost for greetings (very clear)
        if f.is_greeting:
            confidence += 0.2

        return min(max(confidence, 0.3), 1.0)

    def _record_latency(self, start: float) -> None:
        """Record classification latency for monitoring."""
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._call_count += 1
        self._total_latency_ms += elapsed_ms

    @property
    def avg_latency_ms(self) -> float:
        """Average classification latency in milliseconds."""
        if self._call_count == 0:
            return 0.0
        return self._total_latency_ms / self._call_count
