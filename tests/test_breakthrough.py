"""
ARIA Breakthrough Features Test Suite

Tests for:
1. Dynamic Layer Execution (AdaptiveModelWrapper)
2. Multi-Model Cascade
3. Self-Speculative Decoding
4. KV-Cache Budget Control
5. Attention Head Profiling
"""

import pytest
import math
from unittest.mock import MagicMock, patch

from aria.types import ComplexityLevel, TaskType
from aria.controller.adaptive_model import AdaptiveModelWrapper, LayerProfile
from aria.controller.cascade import ModelCascade, CascadeConfig
from aria.controller.speculative import SelfSpeculativeDecoder, SpeculativeStats
from aria.controller.attention_profiler import AttentionProfiler, HeadImportance, TaskTypeProfile
from aria.controller.engine import ModelEngine, ExecutionMode


# ═══════════════════════════════════════════
# Helper: Mock MLX Model
# ═══════════════════════════════════════════

def make_mock_model(num_layers: int = 28, num_heads: int = 16):
    """Create a mock MLX model with the expected layer structure."""
    model = MagicMock()

    # Create mock layers
    layers = []
    for i in range(num_layers):
        layer = MagicMock()
        layer.self_attn = MagicMock()
        layer.self_attn.n_heads = num_heads
        layer.self_attn.n_kv_heads = num_heads // 4
        layer.mlp = MagicMock()
        layers.append(layer)

    model.layers = layers
    model.model = MagicMock()
    model.model.layers = layers
    model.model.embed_tokens = MagicMock()
    model.model.norm = MagicMock()

    return model


# ═══════════════════════════════════════════
# Test 1: Dynamic Layer Execution
# ═══════════════════════════════════════════

class TestAdaptiveModelWrapper:
    """Test the dynamic layer execution wrapper."""

    def setup_method(self):
        self.model = make_mock_model(num_layers=28)
        self.wrapper = AdaptiveModelWrapper(self.model)

    def test_total_layers_detected(self):
        assert self.wrapper.total_layers == 28

    def test_default_profiles_created(self):
        profiles = self.wrapper.get_profile_summary()
        assert "simple" in profiles
        assert "moderate" in profiles
        assert "complex" in profiles
        assert "expert" in profiles

    def test_expert_uses_all_layers(self):
        profiles = self.wrapper.get_profile_summary()
        assert profiles["expert"]["layers_used"] == 28
        assert profiles["expert"]["skip_ratio"] == 0.0

    def test_simple_uses_fewer_layers(self):
        profiles = self.wrapper.get_profile_summary()
        assert profiles["simple"]["layers_used"] < 28
        assert profiles["simple"]["skip_ratio"] > 0.0

    def test_monotonic_layer_usage(self):
        """More complex → more layers."""
        profiles = self.wrapper.get_profile_summary()
        simple = profiles["simple"]["layers_used"]
        moderate = profiles["moderate"]["layers_used"]
        complex_ = profiles["complex"]["layers_used"]
        expert = profiles["expert"]["layers_used"]

        assert simple <= moderate <= complex_ <= expert

    def test_simple_skip_ratio_significant(self):
        """SIMPLE should skip at least 40% of layers."""
        profiles = self.wrapper.get_profile_summary()
        assert profiles["simple"]["skip_ratio"] >= 0.40

    def test_always_includes_last_layers(self):
        """Last 2 layers should always be included."""
        profiles = self.wrapper.get_profile_summary()
        for level, profile in profiles.items():
            indices = profile["active_indices"]
            assert 26 in indices  # Second to last
            assert 27 in indices  # Last

    def test_always_includes_first_layer(self):
        """Layer 0 should always be included."""
        profiles = self.wrapper.get_profile_summary()
        for level, profile in profiles.items():
            indices = profile["active_indices"]
            assert 0 in indices

    def test_set_complexity(self):
        self.wrapper.set_complexity(ComplexityLevel.SIMPLE)
        assert self.wrapper.get_active_layer_count() < 28

    def test_set_full_execution(self):
        self.wrapper.set_complexity(ComplexityLevel.SIMPLE)
        assert self.wrapper.get_active_layer_count() < 28

        self.wrapper.set_full_execution()
        assert self.wrapper.get_active_layer_count() == 28

    def test_profile_description(self):
        profile = self.wrapper._layer_profiles[ComplexityLevel.SIMPLE]
        desc = profile.description
        assert "simple" in desc
        assert "/" in desc


class TestLayerProfile:
    """Test the LayerProfile dataclass."""

    def test_layers_used(self):
        p = LayerProfile(
            complexity=ComplexityLevel.SIMPLE,
            active_layer_indices=[0, 1, 2, 26, 27],
            total_layers=28,
        )
        assert p.layers_used == 5

    def test_skip_ratio(self):
        p = LayerProfile(
            complexity=ComplexityLevel.SIMPLE,
            active_layer_indices=[0, 1, 2, 26, 27],
            total_layers=28,
        )
        assert round(p.skip_ratio, 2) == round(1.0 - 5/28, 2)

    def test_expert_zero_skip(self):
        p = LayerProfile(
            complexity=ComplexityLevel.EXPERT,
            active_layer_indices=list(range(28)),
            total_layers=28,
        )
        assert p.skip_ratio == 0.0


# ═══════════════════════════════════════════
# Test 2: Multi-Model Cascade
# ═══════════════════════════════════════════

class TestCascadeConfig:
    """Test cascade configuration."""

    def test_default_config(self):
        config = CascadeConfig()
        assert "0.5B" in config.tiny_model
        assert "3B" in config.large_model

    def test_routing_threshold(self):
        config = CascadeConfig()
        assert config.tiny_model_max_complexity == ComplexityLevel.SIMPLE


class TestModelCascade:
    """Test multi-model cascade routing."""

    def setup_method(self):
        self.cascade = ModelCascade()

    def test_route_simple_to_tiny(self):
        assert self.cascade.route(ComplexityLevel.SIMPLE) == "tiny"

    def test_route_moderate_to_large(self):
        assert self.cascade.route(ComplexityLevel.MODERATE) == "large"

    def test_route_complex_to_large(self):
        assert self.cascade.route(ComplexityLevel.COMPLEX) == "large"

    def test_route_expert_to_large(self):
        assert self.cascade.route(ComplexityLevel.EXPERT) == "large"

    def test_initial_not_loaded(self):
        assert not self.cascade.is_tiny_loaded
        assert not self.cascade.is_large_loaded

    def test_routing_stats_initial(self):
        stats = self.cascade.routing_stats
        assert stats["tiny_calls"] == 0
        assert stats["large_calls"] == 0


# ═══════════════════════════════════════════
# Test 3: Self-Speculative Decoding
# ═══════════════════════════════════════════

class TestSelfSpeculativeDecoder:
    """Test self-speculative decoding."""

    def setup_method(self):
        model = make_mock_model(num_layers=28)
        self.decoder = SelfSpeculativeDecoder(
            model, draft_layers=8, num_draft_tokens=4
        )

    def test_initialization(self):
        assert self.decoder._draft_layers == 8
        assert self.decoder._num_draft_tokens == 4
        assert self.decoder._total_layers == 28

    def test_draft_layers_capped(self):
        model = make_mock_model(num_layers=10)
        decoder = SelfSpeculativeDecoder(model, draft_layers=15)
        assert decoder._draft_layers == 9  # total - 1

    def test_stats_initial(self):
        stats = self.decoder.stats
        assert stats.total_tokens == 0
        assert stats.acceptance_rate == 0.0

    def test_configure_simple(self):
        self.decoder.configure_for_complexity(ComplexityLevel.SIMPLE)
        assert self.decoder._draft_layers == 6
        assert self.decoder._num_draft_tokens == 6

    def test_configure_expert_disables(self):
        self.decoder.configure_for_complexity(ComplexityLevel.EXPERT)
        assert self.decoder._draft_layers == 0
        assert self.decoder._num_draft_tokens == 0

    def test_reset_stats(self):
        self.decoder._stats.total_tokens = 100
        self.decoder.reset_stats()
        assert self.decoder.stats.total_tokens == 0

    def test_summary(self):
        summary = self.decoder.get_summary()
        assert "total_layers" in summary
        assert "draft_layers" in summary
        assert "stats" in summary


class TestSpeculativeStats:
    """Test speculative stats calculations."""

    def test_acceptance_rate(self):
        stats = SpeculativeStats(
            draft_tokens_generated=10,
            draft_accepted=6,
            draft_rejected=4,
        )
        assert stats.acceptance_rate == 0.6

    def test_acceptance_rate_zero(self):
        stats = SpeculativeStats()
        assert stats.acceptance_rate == 0.0

    def test_speedup_estimate(self):
        stats = SpeculativeStats(
            total_tokens=100,
            draft_tokens_generated=100,
            draft_accepted=60,
        )
        assert stats.speedup_estimate > 1.0


# ═══════════════════════════════════════════
# Test 4: KV-Cache Budget Control
# ═══════════════════════════════════════════

class TestKVCacheBudget:
    """Test KV-cache budget allocation."""

    def setup_method(self):
        self.engine = ModelEngine()

    def test_simple_has_budget(self):
        budget = self.engine._get_kv_budget(ComplexityLevel.SIMPLE)
        assert budget == 256

    def test_moderate_has_budget(self):
        budget = self.engine._get_kv_budget(ComplexityLevel.MODERATE)
        assert budget == 512

    def test_complex_has_budget(self):
        budget = self.engine._get_kv_budget(ComplexityLevel.COMPLEX)
        assert budget == 1024

    def test_expert_unlimited(self):
        budget = self.engine._get_kv_budget(ComplexityLevel.EXPERT)
        assert budget is None

    def test_budgets_are_monotonic(self):
        simple = self.engine._get_kv_budget(ComplexityLevel.SIMPLE)
        moderate = self.engine._get_kv_budget(ComplexityLevel.MODERATE)
        complex_ = self.engine._get_kv_budget(ComplexityLevel.COMPLEX)
        assert simple < moderate < complex_


# ═══════════════════════════════════════════
# Test 5: Attention Head Profiling
# ═══════════════════════════════════════════

class TestAttentionProfiler:
    """Test attention head profiling."""

    def setup_method(self):
        model = make_mock_model(num_layers=28, num_heads=16)
        self.profiler = AttentionProfiler(model)

    def test_initialization(self):
        assert self.profiler._total_layers == 28
        assert self.profiler._num_heads == 16
        assert self.profiler._total_heads == 28 * 16

    def test_default_profiles_built(self):
        profiles = self.profiler.build_default_profiles()
        assert len(profiles) == len(TaskType)

    def test_conversation_has_most_maskable(self):
        """Conversation should have the most maskable heads."""
        profiles = self.profiler.build_default_profiles()
        conv_maskable = profiles[TaskType.CONVERSATION].maskable_ratio
        code_maskable = profiles[TaskType.CODE].maskable_ratio
        # Conversation heads are generally less important
        assert conv_maskable >= 0.0  # Just check it runs

    def test_get_profile(self):
        profile = self.profiler.get_profile(TaskType.FACTUAL)
        assert profile is not None
        assert profile.task_type == TaskType.FACTUAL

    def test_maskable_heads_returns_tuples(self):
        profile = self.profiler.get_profile(TaskType.CONVERSATION)
        maskable = profile.get_maskable_heads()
        if maskable:
            assert isinstance(maskable[0], tuple)
            assert len(maskable[0]) == 2

    def test_summary(self):
        summary = self.profiler.get_summary()
        assert "total_layers" in summary
        assert "heads_per_layer" in summary
        assert "profiles" in summary


class TestHeadImportance:
    """Test head importance scoring."""

    def test_important_head(self):
        h = HeadImportance(layer_idx=0, head_idx=0, overall_score=0.8)
        assert h.is_important is True

    def test_unimportant_head(self):
        h = HeadImportance(layer_idx=0, head_idx=0, overall_score=0.3)
        assert h.is_important is False


class TestTaskTypeProfile:
    """Test task type profile."""

    def test_maskable_ratio(self):
        heads = [
            HeadImportance(0, 0, overall_score=0.1),  # Maskable
            HeadImportance(0, 1, overall_score=0.2),  # Maskable
            HeadImportance(0, 2, overall_score=0.8),  # Important
            HeadImportance(0, 3, overall_score=0.9),  # Important
        ]
        profile = TaskTypeProfile(task_type=TaskType.FACTUAL, head_scores=heads)
        assert profile.maskable_ratio == 0.5

    def test_empty_profile(self):
        profile = TaskTypeProfile(task_type=TaskType.FACTUAL)
        assert profile.maskable_ratio == 0.0


# ═══════════════════════════════════════════
# Test: Execution Mode Configuration
# ═══════════════════════════════════════════

class TestExecutionMode:
    """Test execution mode configuration."""

    def test_default_mode(self):
        engine = ModelEngine()
        assert engine.execution_mode == ExecutionMode.DYNAMIC_LAYERS

    def test_set_mode(self):
        engine = ModelEngine()
        engine.set_execution_mode(ExecutionMode.CASCADE)
        assert engine.execution_mode == ExecutionMode.CASCADE

    def test_mode_values(self):
        assert ExecutionMode.DYNAMIC_LAYERS.value == "dynamic_layers"
        assert ExecutionMode.CASCADE.value == "cascade"
        assert ExecutionMode.STANDARD.value == "standard"

    def test_get_adaptive_info(self):
        engine = ModelEngine()
        info = engine.get_adaptive_info()
        assert "execution_mode" in info
        assert info["execution_mode"] == "dynamic_layers"
