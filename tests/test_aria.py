"""
ARIA Test Suite

Tests for the Query Analyzer, Execution Planner, Memory Manager,
and Stability Guardian modules.
"""

import pytest
from aria.types import (
    ComplexityLevel, TaskType, MemoryTier,
    HardwareState, QueryProfile, ExecutionStrategy,
    QualityReport, QualityVerdict,
)
from aria.config import get_config
from aria.analyzer.classifier import QueryClassifier
from aria.analyzer.features import extract_features
from aria.planner.strategy import StrategyPlanner
from aria.memory.monitor import MemoryMonitor
from aria.guardian.validator import OutputValidator
from aria.guardian.fallback import FallbackManager
from aria.monitor.store import MetricsStore


# ═══════════════════════════════════════════
# Query Analyzer Tests
# ═══════════════════════════════════════════

class TestFeatureExtraction:
    """Test the feature extraction pipeline."""

    def test_empty_query(self):
        f = extract_features("")
        assert f.word_count == 0
        assert f.char_count == 0

    def test_greeting_detection(self):
        f = extract_features("Hello!")
        assert f.is_greeting is True

    def test_non_greeting(self):
        f = extract_features("Explain quantum computing in detail")
        assert f.is_greeting is False

    def test_code_detection(self):
        f = extract_features("Write a Python function to sort an array")
        assert f.code_keyword_count > 0

    def test_math_detection(self):
        f = extract_features("Calculate the integral of x squared")
        assert f.math_keyword_count > 0

    def test_word_count(self):
        f = extract_features("one two three four five")
        assert f.word_count == 5

    def test_question_mark(self):
        f = extract_features("What is life?")
        assert f.has_question_mark is True

    def test_code_block_detection(self):
        f = extract_features("Here is code:\n```python\nprint('hello')\n```")
        assert f.has_code_block is True

    def test_complexity_markers(self):
        f = extract_features("Give me a detailed step-by-step comprehensive guide")
        assert f.complexity_marker_count >= 2


class TestQueryClassifier:
    """Test the query classifier."""

    def setup_method(self):
        self.classifier = QueryClassifier()

    def test_greeting_is_simple(self):
        profile = self.classifier.classify("Hello!")
        assert profile.complexity_level == ComplexityLevel.SIMPLE
        assert profile.task_type == TaskType.CONVERSATION

    def test_factual_query(self):
        profile = self.classifier.classify("What is the capital of France?")
        assert profile.complexity_level == ComplexityLevel.SIMPLE

    def test_moderate_query(self):
        profile = self.classifier.classify(
            "Explain how photosynthesis works and what are its main stages"
        )
        assert profile.complexity_level in (ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE)

    def test_complex_query(self):
        profile = self.classifier.classify(
            "Compare and contrast microservices architecture with monolithic "
            "architecture. Discuss the trade-offs in terms of scalability, "
            "maintainability, deployment, and operational complexity."
        )
        assert profile.complexity_level.rank >= ComplexityLevel.MODERATE.rank

    def test_code_task_detection(self):
        profile = self.classifier.classify(
            "Write a Python function that implements binary search"
        )
        assert profile.task_type == TaskType.CODE

    def test_math_task_detection(self):
        profile = self.classifier.classify("Calculate the derivative of x^3 + 2x")
        assert profile.task_type == TaskType.MATH

    def test_confidence_high_for_greeting(self):
        profile = self.classifier.classify("Hi!")
        assert profile.confidence >= 0.8

    def test_empty_query(self):
        profile = self.classifier.classify("")
        assert profile.complexity_level == ComplexityLevel.SIMPLE

    def test_score_range(self):
        profile = self.classifier.classify("Tell me about machine learning")
        assert 0.0 <= profile.complexity_score <= 1.0

    def test_classifier_latency(self):
        """Classifier should complete in under 10ms."""
        for _ in range(100):
            self.classifier.classify("What is photosynthesis?")
        assert self.classifier.avg_latency_ms < 10.0


# ═══════════════════════════════════════════
# Execution Planner Tests
# ═══════════════════════════════════════════

class TestStrategyPlanner:
    """Test the execution strategy planner."""

    def setup_method(self):
        self.planner = StrategyPlanner()

    def _make_profile(self, level: ComplexityLevel, confidence: float = 0.8) -> QueryProfile:
        return QueryProfile(
            query="test",
            complexity_score=0.5,
            complexity_level=level,
            task_type=TaskType.FACTUAL,
            estimated_output_tokens=100,
            confidence=confidence,
        )

    def _make_hardware(self, tier: MemoryTier = MemoryTier.GREEN) -> HardwareState:
        percent_map = {
            MemoryTier.GREEN: 40.0,
            MemoryTier.YELLOW: 70.0,
            MemoryTier.ORANGE: 85.0,
            MemoryTier.RED: 95.0,
        }
        return HardwareState(
            memory_total_mb=8192,
            memory_available_mb=4000,
            memory_used_percent=percent_map[tier],
            memory_tier=tier,
            process_rss_mb=500,
            swap_used_mb=0,
            cpu_percent=30,
        )

    def test_simple_query_gets_simple_strategy(self):
        strategy = self.planner.plan(
            self._make_profile(ComplexityLevel.SIMPLE),
            self._make_hardware(),
        )
        assert strategy.complexity_level == ComplexityLevel.SIMPLE
        assert strategy.max_tokens == 128

    def test_expert_query_gets_expert_strategy(self):
        strategy = self.planner.plan(
            self._make_profile(ComplexityLevel.EXPERT),
            self._make_hardware(),
        )
        assert strategy.complexity_level == ComplexityLevel.EXPERT
        assert strategy.max_tokens == 1024

    def test_low_confidence_upgrades(self):
        strategy = self.planner.plan(
            self._make_profile(ComplexityLevel.SIMPLE, confidence=0.4),
            self._make_hardware(),
        )
        assert strategy.complexity_level == ComplexityLevel.MODERATE

    def test_orange_memory_caps_strategy(self):
        strategy = self.planner.plan(
            self._make_profile(ComplexityLevel.EXPERT),
            self._make_hardware(MemoryTier.ORANGE),
        )
        assert strategy.complexity_level == ComplexityLevel.MODERATE
        assert "memory_override" in strategy.source

    def test_red_memory_forces_simple(self):
        strategy = self.planner.plan(
            self._make_profile(ComplexityLevel.EXPERT),
            self._make_hardware(MemoryTier.RED),
        )
        assert strategy.complexity_level == ComplexityLevel.SIMPLE
        assert strategy.source == "memory_override_red"

    def test_baseline_strategy(self):
        baseline = self.planner.get_baseline_strategy()
        assert baseline.complexity_level == ComplexityLevel.EXPERT
        assert baseline.source == "baseline_fixed"

    def test_deterministic_behavior(self):
        """Same inputs should always produce same outputs."""
        profile = self._make_profile(ComplexityLevel.MODERATE)
        hw = self._make_hardware()
        s1 = self.planner.plan(profile, hw)
        s2 = self.planner.plan(profile, hw)
        assert s1.max_tokens == s2.max_tokens
        assert s1.temperature == s2.temperature


# ═══════════════════════════════════════════
# Memory Manager Tests
# ═══════════════════════════════════════════

class TestMemoryMonitor:
    """Test the memory monitoring system."""

    def setup_method(self):
        self.monitor = MemoryMonitor()

    def test_get_state(self):
        state = self.monitor.get_state()
        assert state.memory_total_mb > 0
        assert state.memory_used_percent >= 0
        assert state.memory_tier in MemoryTier

    def test_get_process_rss(self):
        rss = self.monitor.get_process_rss_mb()
        assert rss > 0

    def test_tier_classification(self):
        assert self.monitor.classify_tier(30.0) == MemoryTier.GREEN
        assert self.monitor.classify_tier(70.0) == MemoryTier.YELLOW
        assert self.monitor.classify_tier(85.0) == MemoryTier.ORANGE
        assert self.monitor.classify_tier(95.0) == MemoryTier.RED

    def test_format_status(self):
        status = self.monitor.format_status()
        assert "Memory" in status

    def test_caching(self):
        s1 = self.monitor.get_state()
        s2 = self.monitor.get_state()
        # Should be the same cached object
        assert s1.timestamp == s2.timestamp


# ═══════════════════════════════════════════
# Stability Guardian Tests
# ═══════════════════════════════════════════

class TestOutputValidator:
    """Test the output quality validator."""

    def setup_method(self):
        self.validator = OutputValidator()

    def _make_profile(self, level: ComplexityLevel = ComplexityLevel.SIMPLE) -> QueryProfile:
        return QueryProfile(
            query="Test query",
            complexity_score=0.3,
            complexity_level=level,
            task_type=TaskType.FACTUAL,
            estimated_output_tokens=100,
            confidence=0.8,
        )

    def test_good_response_passes(self):
        report = self.validator.validate(
            "The capital of France is Paris.",
            self._make_profile(),
        )
        assert report.verdict == QualityVerdict.PASS

    def test_empty_response_fails(self):
        report = self.validator.validate("", self._make_profile())
        assert report.verdict == QualityVerdict.FAIL

    def test_whitespace_only_fails(self):
        report = self.validator.validate("   \n  ", self._make_profile())
        assert report.verdict == QualityVerdict.FAIL

    def test_echo_detection(self):
        report = self.validator.validate(
            "Test query",
            self._make_profile(),
        )
        assert "echo_detected" in report.checks_failed

    def test_repetitive_response_flagged(self):
        repeated = "the same thing " * 30
        report = self.validator.validate(repeated, self._make_profile())
        assert report.score < 0.8

    def test_score_range(self):
        report = self.validator.validate(
            "A reasonable response about something.",
            self._make_profile(),
        )
        assert 0.0 <= report.score <= 1.0


class TestFallbackManager:
    """Test the fallback cascade and circuit breaker."""

    def setup_method(self):
        self.manager = FallbackManager()

    def test_initial_state(self):
        assert not self.manager.is_circuit_open
        assert not self.manager.should_force_expert()

    def test_success_resets_counter(self):
        self.manager.record_failure("test")
        self.manager.record_success()
        status = self.manager.get_status()
        assert status["consecutive_failures"] == 0

    def test_circuit_breaker_opens(self):
        for _ in range(3):
            self.manager.record_failure("test")
        assert self.manager.is_circuit_open
        assert self.manager.should_force_expert()

    def test_get_fallback_strategy(self):
        base = ExecutionStrategy(
            complexity_level=ComplexityLevel.SIMPLE,
            max_tokens=128,
            temperature=0.3,
            top_p=0.8,
            repetition_penalty=1.0,
        )
        table = {
            ComplexityLevel.SIMPLE: base,
            ComplexityLevel.MODERATE: ExecutionStrategy(
                complexity_level=ComplexityLevel.MODERATE,
                max_tokens=256, temperature=0.6,
                top_p=0.9, repetition_penalty=1.1,
            ),
            ComplexityLevel.EXPERT: ExecutionStrategy(
                complexity_level=ComplexityLevel.EXPERT,
                max_tokens=1024, temperature=0.8,
                top_p=0.95, repetition_penalty=1.2,
            ),
        }

        fallback = self.manager.get_fallback_strategy(base, 0, table)
        assert fallback is not None
        assert fallback.complexity_level == ComplexityLevel.MODERATE

    def test_safety_response(self):
        resp = self.manager.get_safety_response()
        assert len(resp) > 0


# ═══════════════════════════════════════════
# Metrics Store Tests
# ═══════════════════════════════════════════

class TestMetricsStore:
    """Test the SQLite metrics store."""

    def setup_method(self):
        import tempfile
        from aria.config import ARIAConfig, PerformanceConfig
        from pathlib import Path

        self.tmpdir = tempfile.mkdtemp()
        config = ARIAConfig(
            performance=PerformanceConfig(metrics_db="test_metrics.db")
        )
        # Override project root
        object.__setattr__(config, 'project_root', Path(self.tmpdir))
        self.store = MetricsStore(config)

    def teardown_method(self):
        self.store.close()

    def test_initial_count(self):
        assert self.store.get_total_count() == 0

    def test_get_recent_empty(self):
        recent = self.store.get_recent()
        assert len(recent) == 0

    def test_stats_empty(self):
        stats = self.store.get_stats_by_complexity()
        assert len(stats) == 0
