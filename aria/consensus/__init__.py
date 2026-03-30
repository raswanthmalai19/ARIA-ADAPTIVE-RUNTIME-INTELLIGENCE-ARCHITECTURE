"""
ARIA Multi-Model Consensus — Quality Assurance Through Ensemble

For critical queries (classification, decisions, medical, legal), run multiple
models concurrently and validate consensus. If models disagree, escalate to human review.

Competitive advantage:
- Ollama: Single model per inference → Can have wrong answers
- ARIA: Multi-model consensus → Verify answer quality through agreement
"""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("aria.consensus")


class ConsensusLevel(str, Enum):
    """Consensus strength."""
    UNANIMOUS = "unanimous"      # All models agree
    STRONG = "strong"            # 80%+ models agree
    WEAK = "weak"                # 50-80% models agree
    CONFLICTED = "conflicted"    # Models disagree


@dataclass
class ModelVote:
    """Single model's response."""
    model_name: str
    response: str
    confidence: float
    latency_ms: float
    tokens_generated: int


@dataclass
class ConsensusResult:
    """Result from multi-model consensus run."""
    primary_response: str
    consensus_level: ConsensusLevel
    agreement_score: float  # 0-1, how much models agree
    votes: List[ModelVote]
    latency_ms: float
    total_tokens: int
    recommended_manual_review: bool


class MultiModelConsensus:
    """
    Run queries across multiple models and reach consensus.

    When critical decisions are needed, run models in parallel and check agreement.
    """

    def __init__(self, models: Optional[List[str]] = None, timeout_seconds: int = 30):
        """
        Args:
            models: List of model names. If None, use default ensemble
            timeout_seconds: Max time to wait for all model responses
        """
        # Default: small + medium models for fast ensemble consensus
        self.models = models or [
            "qwen2.5-0.5b",  # Fast & lean
            "qwen2.5-3b",    # Standard
        ]
        self.timeout_seconds = timeout_seconds
        logger.info(f"MultiModelConsensus initialized with models: {self.models}")

    async def _run_single_model(self, query: str, model_name: str) -> ModelVote:
        """Simulate single model inference. In production, calls actual models."""
        # Placeholder: In real implementation, call the actual model
        start = time.time()

        # Simulate inference
        await asyncio.sleep(0.1)
        response = f"Response from {model_name}"
        latency = (time.time() - start) * 1000

        return ModelVote(
            model_name=model_name,
            response=response,
            confidence=0.95,
            latency_ms=latency,
            tokens_generated=50
        )

    async def guess(self, query: str, critical: bool = False) -> ConsensusResult:
        """
        Query multiple models and reach consensus.

        Args:
            query: Input query
            critical: If True, require unanimous/strong consensus. Else use weak consensus.

        Returns:
            ConsensusResult with agreement analysis
        """
        start_time = time.time()

        try:
            # Run all models in parallel
            tasks = [self._run_single_model(query, model) for model in self.models]
            votes = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Consensus timeout after {self.timeout_seconds}s")
            votes = []

        if not votes:
            raise RuntimeError("No model responses received")

        # Analyze agreement
        latency_ms = (time.time() - start_time) * 1000
        total_tokens = sum(v.tokens_generated for v in votes)

        # Simple consensus: majority vote on response
        responses = [v.response for v in votes]
        most_common = max(set(responses), key=responses.count) if responses else ""
        agreement_count = responses.count(most_common)
        agreement_score = agreement_count / len(votes) if votes else 0

        # Determine consensus level
        if agreement_score >= 0.99:
            consensus_level = ConsensusLevel.UNANIMOUS
        elif agreement_score >= 0.80:
            consensus_level = ConsensusLevel.STRONG
        elif agreement_score >= 0.50:
            consensus_level = ConsensusLevel.WEAK
        else:
            consensus_level = ConsensusLevel.CONFLICTED

        # For critical queries, recommend manual review if not unanimous
        recommend_manual = critical and consensus_level != ConsensusLevel.UNANIMOUS

        result = ConsensusResult(
            primary_response=most_common,
            consensus_level=consensus_level,
            agreement_score=agreement_score,
            votes=votes,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
            recommended_manual_review=recommend_manual
        )

        logger.info(
            f"Consensus: {consensus_level.value} ({agreement_score*100:.0f}%) "
            f"latency={latency_ms:.0f}ms tokens={total_tokens}"
        )

        return result

    def calculate_confidence(self, result: ConsensusResult) -> float:
        """
        Calculate final confidence based on model agreement.

        Unanimous (all agree): 99%
        Strong (80%+ agree): 90%
        Weak (50%+ agree): 70%
        Conflicted (disagree): 40%
        """
        confidence_map = {
            ConsensusLevel.UNANIMOUS: 0.99,
            ConsensusLevel.STRONG: 0.90,
            ConsensusLevel.WEAK: 0.70,
            ConsensusLevel.CONFLICTED: 0.40,
        }
        return confidence_map.get(result.consensus_level, 0.50)

    def should_escalate(self, result: ConsensusResult, critical: bool = False) -> bool:
        """
        Should this result be escalated to human review?

        Returns True if:
        - Critical query + not unanimous
        - Conflicted models
        - Confidence < 70%
        """
        if critical and result.consensus_level != ConsensusLevel.UNANIMOUS:
            return True

        if result.consensus_level == ConsensusLevel.CONFLICTED:
            return True

        confidence = self.calculate_confidence(result)
        if confidence < 0.70:
            return True

        return False

    def format_report(self, result: ConsensusResult) -> str:
        """Format consensus report for logging/display."""
        report = f"""
Multi-Model Consensus Report:
  Consensus Level: {result.consensus_level.value.upper()}
  Agreement: {result.agreement_score*100:.0f}%
  Latency: {result.latency_ms:.0f}ms
  Total Tokens: {result.total_tokens}
  Confidence: {self.calculate_confidence(result)*100:.0f}%
  Manual Review Recommended: {'Yes' if result.recommended_manual_review else 'No'}

Model Votes:
"""
        for vote in result.votes:
            report += f"  - {vote.model_name}: {vote.response[:60]}... (conf={vote.confidence*100:.0f}%)\n"

        return report
