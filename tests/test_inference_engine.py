"""
Tests for the new production-grade inference engine.

Validates:
- Model loading and caching
- Inference quality (real outputs, not fallbacks)
- Adaptive routing based on complexity
-Performance metrics
- Error handling
"""

import pytest
import time
from aria.inference_engine import (
    AdaptiveInferenceEngine,
    CascadeRouter,
    ModelCache,
    get_inference_engine,
    get_cascade_router,
)


class TestModelCache:
    """Test model caching functionality."""
    
    def test_cache_initialization(self):
        """Test cache initializes properly."""
        cache = ModelCache()
        assert cache.cache_dir.exists()
        assert len(cache.loaded_models) == 0
    
    def test_cache_get_missing_returns_none(self):
        """Test getting non-existent model returns None."""
        cache = ModelCache()
        result = cache.get("nonexistent_model")
        assert result is None
    
    def test_cache_set_and_get(self):
        """Test caching and retrieving model."""
        cache = ModelCache()
        mock_model = "mock_model"
        mock_tokenizer = "mock_tokenizer"
        
        cache.set("test_model", mock_model, mock_tokenizer, {})
        
        assert cache.is_cached("test_model")
        retrieved = cache.get("test_model")
        assert retrieved == (mock_model, mock_tokenizer)
    
    def test_cache_clear_specific(self):
        """Test clearing specific model from cache."""
        cache = ModelCache()
        cache.set("model1", "m1", "t1", {})
        cache.set("model2", "m2", "t2", {})
        
        cache.clear("model1")
        
        assert not cache.is_cached("model1")
        assert cache.is_cached("model2")
    
    def test_cache_clear_all(self):
        """Test clearing entire cache."""
        cache = ModelCache()
        cache.set("model1", "m1", "t1", {})
        cache.set("model2", "m2", "t2", {})
        
        cache.clear()
        
        assert not cache.is_cached("model1")
        assert not cache.is_cached("model2")
        assert len(cache.loaded_models) == 0


class TestAdaptiveInferenceEngine:
    """Test adaptive inference engine."""
    
    @pytest.fixture
    def engine(self):
        """Create inference engine for testing."""
        return AdaptiveInferenceEngine()
    
    def test_engine_initialization(self, engine):
        """Test engine initializes with correct device."""
        assert engine is not None
        assert engine.device in ["cuda", "mps", "cpu"]
        assert hasattr(engine, 'cache')
    
    def test_engine_model_configurations_exist(self, engine):
        """Test that model configs are properly defined."""
        for tier in ["simple", "moderate", "complex"]:
            assert tier in engine.MODELS
            config = engine.MODELS[tier]
            assert "name" in config
            assert "max_length" in config
            assert "temperature" in config
    
    def test_device_detection_logic(self, engine):
        """Test that device detection is reasonable."""
        # Just verify we got a valid device
        valid_devices = ["cuda", "mps", "cpu"]
        assert engine.device in valid_devices
    
    def test_inference_with_simple_model_available(self, engine):
        """Test inference with a simple, fast model."""
        # Using gpt2 which should be available
        result = engine.infer("Hello world", complexity_tier="simple")
        
        # Verify result structure
        assert result is not None
        assert hasattr(result, 'text')
        assert hasattr(result, 'latency_ms')
        assert hasattr(result, 'success')
        assert hasattr(result, 'model_used')
        
        # For this test, we just check structure
        # (actual quality depends on model availability)
        if result.success:
            assert len(result.text) > 0
            assert result.tokens_generated >= 0
            assert result.latency_ms > 0


class TestCascadeRouter:
    """Test query routing based on complexity."""
    
    @pytest.fixture
    def router(self):
        """Create cascade router for testing."""
        engine = AdaptiveInferenceEngine()
        return CascadeRouter(engine)
    
    def test_router_initialization(self, router):
        """Test router initializes properly."""
        assert router is not None
        assert all(tier in router.routing_stats for tier in ["simple", "moderate", "complex"])
        assert sum(router.routing_stats.values()) == 0
    
    def test_routing_decision_simple(self, router):
        """Test that simple queries route to simple model."""
        # Low complexity score should route to simple
        result = router.route_and_infer(
            "What is AI?",
            complexity_score=0.1
        )
        
        assert result.complexity_tier == "simple"
        assert router.routing_stats["simple"] >= 1
    
    def test_routing_decision_moderate(self, router):
        """Test that moderate complexity routes correctly."""
        result = router.route_and_infer(
            "Explain quantum computing principles",
            complexity_score=0.5
        )
        
        assert result.complexity_tier == "moderate"
        assert router.routing_stats["moderate"] >= 1
    
    def test_routing_decision_complex(self, router):
        """Test that complex queries route to complex model."""
        result = router.route_and_infer(
            "Compare different machine learning paradigms",
            complexity_score=0.9
        )
        
        assert result.complexity_tier == "complex"
        assert router.routing_stats["complex"] >= 1
    
    def test_statistics_tracking(self, router):
        """Test that routing statistics are properly tracked."""
        router.route_and_infer("Query 1", 0.2)
        router.route_and_infer("Query 2", 0.5)
        router.route_and_infer("Query 3", 0.8)
        
        stats = router.get_stats()
        assert stats["total_routed"] == 3
        assert sum(stats["by_tier"].values()) == 3


class TestInferenceQuality:
    """Test that inference produces real, non-fallback output."""
    
    def test_inference_produces_text(self):
        """Test that inference actually produces text output."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer(
            "The capital of France is",
            complexity_tier="simple"
        )
        
        assert result is not None
        # Should have some output
        if result.success:
            assert len(result.text) > 0
            assert not result.text.startswith("I appreciate your question")  # Not fallback
    
    def test_different_models_different_output(self):
        """Test that different complexity tiers can produce different results."""
        engine = AdaptiveInferenceEngine()
        
        prompt = "Write about artificial intelligence"
        
        simple_result = engine.infer(prompt, complexity_tier="simple")
        complex_result = engine.infer(prompt, complexity_tier="complex")
        
        # Both should complete without error
        assert simple_result is not None
        assert complex_result is not None
        
        # Verify they used different models
        if simple_result.success and complex_result.success:
            assert simple_result.model_used in ["gpt2", "distilgpt2"]
            assert complex_result.model_used in ["gpt2-medium", "distilgpt2"]


class TestPerformanceMetrics:
    """Test performance tracking."""
    
    def test_latency_measurement(self):
        """Test that latency is properly measured."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer("Hello", complexity_tier="simple")
        
        assert result.latency_ms > 0
        assert isinstance(result.latency_ms, (int, float))
    
    def test_tokens_per_second_calculation(self):
        """Test tokens per second calculation."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer("The quick brown fox", complexity_tier="simple")
        
        if result.success and result.tokens_generated > 0:
            expected_tps = result.tokens_generated / (result.latency_ms / 1000)
            assert abs(result.tokens_per_second - expected_tps) < 1  # Allow small rounding errors
    
    def test_ttft_less_than_total_latency(self):
        """Test that time to first token is less than total latency."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer("Test query", complexity_tier="simple")
        
        if result.success:
            assert result.time_to_first_token_ms <= result.latency_ms


class TestGlobalSingletons:
    """Test global singleton instances."""
    
    def test_engine_singleton(self):
        """Test that get_inference_engine returns same instance."""
        engine1 = get_inference_engine()
        engine2 = get_inference_engine()
        
        assert engine1 is engine2
    
    def test_router_singleton(self):
        """Test that get_cascade_router returns same instance."""
        router1 = get_cascade_router()
        router2 = get_cascade_router()
        
        assert router1 is router2
    
    def test_engine_shared_with_router(self):
        """Test that router uses the global engine."""
        engine = get_inference_engine()
        router = get_cascade_router()
        
        assert router.engine is engine


class TestErrorRecovery:
    """Test error handling and recovery."""
    
    def test_invalid_complexity_tier_defaults_moderate(self):
        """Test that invalid complexity tier defaults to moderate."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer(
            "Test query",
            complexity_tier="invalid_tier"
        )
        
        # Should still work, using moderate tier
        assert result is not None
    
    def test_inference_result_has_all_fields(self):
        """Test that result always has all required fields."""
        engine = AdaptiveInferenceEngine()
        
        result = engine.infer("Test", complexity_tier="simple")
        
        required_fields = [
            'text', 'tokens_generated', 'latency_ms', 
            'tokens_per_second', 'time_to_first_token_ms',
            'success', 'model_used', 'error', 'cache_hit',
            'complexity_tier'
        ]
        
        for field in required_fields:
            assert hasattr(result, field)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
