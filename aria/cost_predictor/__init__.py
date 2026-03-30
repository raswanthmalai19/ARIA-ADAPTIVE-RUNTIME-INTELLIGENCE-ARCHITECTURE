"""
ARIA Cost Predictor — Estimate Performance Before Running

Predict latency, tokens, and cost BEFORE execution.
Users can choose to run expensive queries or wait for batch jobs.

Competitive advantage:
- Ollama: No cost prediction → Users surprised by latency/cost
- ARIA: Accurate predictions → Users make informed decisions
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger("aria.cost_predictor")


class Tier(str, Enum):
    """Execution tier."""
    INSTANT = "instant"          # <100ms
    FAST = "fast"                # 100-500ms
    MODERATE = "moderate"        # 500ms-2s
    SLOW = "slow"                # 2s+


@dataclass
class CostPrediction:
    """Predicted cost of a query."""
    query: str
    estimated_latency_ms: float
    estimated_tokens: int
    estimated_cost_usd: float  # For API users
    tier: Tier
    confidence: float  # How confident in this prediction (0-1)
    reasoning: str
    recommended_action: str  # "run_now", "batch_later", "escalate_to_larger_model"


class CostPredictor:
    """
    Predict query execution cost before running.

    Uses query features to estimate:
    - Latency
    - Tokens used
    - Cost (if using API)
    """

    def __init__(self):
        # Historical patterns (learned from system)
        self.feature_weights = {
            "query_length": 0.3,       # Longer queries ~linearly more latency
            "complexity": 0.4,         # Complexity is primary driver
            "num_examples": 0.15,      # Few-shot examples add tokens
            "reasoning_words": 0.15,   # "explain", "step", "why" → more tokens
        }

        # Average token generation rate (tokens/second)
        self.tokens_per_second = {
            Tier.INSTANT: 500,    # Very simple: ~250 tokens/s
            Tier.FAST: 100,       # Simple: ~100 tokens/s
            Tier.MODERATE: 50,    # Moderate: ~50 tokens/s
            Tier.SLOW: 20,        # Complex: ~20 tokens/s
        }

        # Cost per 1M tokens (for API pricing, adjust to your model)
        self.cost_per_1m_tokens = 0.10  # Adjust for your model

        logger.info("CostPredictor initialized")

    def _extract_features(self, query: str) -> Dict[str, float]:
        """Extract features from query."""
        features = {
            "query_length": len(query),
            "complexity": self._estimate_complexity(query),
            "num_examples": query.lower().count("example"),
            "reasoning_words": sum(
                query.lower().count(word)
                for word in ["explain", "why", "step", "reason", "how", "analyze"]
            ),
        }
        return features

    def _estimate_complexity(self, query: str) -> float:
        """
        Estimate query complexity 0-1 based on keywords.

        Simple: 0-0.25 (hello, what time)
        Moderate: 0.25-0.75 (summarize, list)
        Complex: 0.75-1.0 (explain, design, code)
        """
        keywords_simple = ["hello", "hi", "time", "date", "what", "who", "where"]
        keywords_complex = [
            "explain", "design", "code", "architecture",
            "algorithm", "quantum", "physics", "math",
            "analyze", "evaluate", "compare"
        ]

        query_lower = query.lower()
        simple_score = sum(1 for kw in keywords_simple if kw in query_lower)
        complex_score = sum(1 for kw in keywords_complex if kw in query_lower)

        complexity = complex_score / (simple_score + complex_score + 1)
        return min(1.0, complexity)

    def predict(self, query: str, model_tier: str = "standard") -> CostPrediction:
        """
        Predict execution cost.

        Args:
            query: Input query
            model_tier: "tiny" (0.5B), "standard" (3B), "large" (7B+)

        Returns:
            CostPrediction with estimates
        """
        features = self._extract_features(query)
        complexity = features["complexity"]

        # Estimate tier based on complexity
        if complexity < 0.25:
            predicted_tier = Tier.INSTANT
        elif complexity < 0.50:
            predicted_tier = Tier.FAST
        elif complexity < 0.75:
            predicted_tier = Tier.MODERATE
        else:
            predicted_tier = Tier.SLOW

        # Model tier adjustment
        tier_multiplier = {
            "tiny": 0.5,       # 0.5B model → 2x faster, less accurate
            "standard": 1.0,   # 3B model → baseline
            "large": 1.5,      # 7B model → slower, more accurate
        }
        multiplier = tier_multiplier.get(model_tier, 1.0)

        # Base latencies (in ms)
        base_latencies = {
            Tier.INSTANT: 100,
            Tier.FAST: 300,
            Tier.MODERATE: 1200,
            Tier.SLOW: 5000,
        }

        estimated_latency = base_latencies[predicted_tier] * multiplier

        # Estimate tokens (typically 1 token per 4 chars, longer queries have lower ratio)
        base_tokens = len(query) / 4 + 50  # Base response ~50 tokens
        complexity_multiplier = 1.0 + (complexity * 2)  # Complex → more tokens
        estimated_tokens = int(base_tokens * complexity_multiplier)

        # Cost estimation
        estimated_cost = (estimated_tokens / 1_000_000) * self.cost_per_1m_tokens

        # Determine recommendation
        if predicted_tier == Tier.INSTANT:
            recommended_action = "run_now"
            reasoning = "Fast execution expected - run immediately"
            confidence = 0.90
        elif predicted_tier == Tier.FAST:
            recommended_action = "run_now"
            reasoning = "Reasonable latency - safe to run"
            confidence = 0.85
        elif predicted_tier in [Tier.MODERATE, Tier.SLOW]:
            if estimated_tokens > 500:
                recommended_action = "batch_later"
                reasoning = f"High token count ({estimated_tokens}) - consider batching with other queries"
            else:
                recommended_action = "run_now"
                reasoning = "Acceptable latency for one-off query"

            confidence = 0.75
        else:
            recommended_action = "escalate_to_larger_model"
            reasoning = "Very complex query - larger model may be needed"
            confidence = 0.70

        return CostPrediction(
            query=query,
            estimated_latency_ms=estimated_latency,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            tier=predicted_tier,
            confidence=confidence,
            reasoning=reasoning,
            recommended_action=recommended_action
        )

    def format_prediction(self, prediction: CostPrediction) -> str:
        """Format prediction for user display."""
        return f"""
Cost Prediction:
  Estimated Latency: {prediction.estimated_latency_ms:.0f}ms ({prediction.tier.value})
  Estimated Tokens: {prediction.estimated_tokens}
  Estimated Cost: ${prediction.estimated_cost_usd:.6f}
  Confidence: {prediction.confidence*100:.0f}%
  Recommendation: {prediction.recommended_action}
  Reason: {prediction.reasoning}
"""

    def should_run_now(self, prediction: CostPrediction) -> bool:
        """Should user run this query now?"""
        return prediction.recommended_action == "run_now"

    def should_batch(self, prediction: CostPrediction) -> bool:
        """Should user batch this query?"""
        return prediction.recommended_action == "batch_later"
