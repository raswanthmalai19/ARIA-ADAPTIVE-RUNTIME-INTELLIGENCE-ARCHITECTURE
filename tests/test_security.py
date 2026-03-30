"""
Sprint B - Security & Hardening Tests

Tests for:
- Input validation and sanitization
- Rate limiting
- Response caching
- Error handling
- SQL injection prevention
- XSS prevention
- CSRF protection (where applicable)
"""

import pytest
from aria.hardening import (
    InputValidator,
    RateLimiter,
    ResponseCache,
    MemoryOptimizer,
    PerformanceMonitor,
)
from aria.config import ARIAConfig


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_valid_query_accepted(self):
        """Normal queries should pass validation."""
        valid, msg = InputValidator.validate_query("What is machine learning?")
        assert valid is True
        assert msg is None

    def test_empty_query_rejected(self):
        """Empty queries should be rejected."""
        valid, msg = InputValidator.validate_query("")
        assert valid is False
        assert msg is not None

    def test_query_too_long_rejected(self):
        """Queries exceeding max length should be rejected."""
        long_query = "a" * (InputValidator.MAX_QUERY_LENGTH + 1)
        valid, msg = InputValidator.validate_query(long_query)
        assert valid is False

    def test_script_tag_blocked(self):
        """XSS attempt with <script> should be blocked."""
        query = "Test <script>alert('xss')</script>"
        valid, msg = InputValidator.validate_query(query)
        assert valid is False
        assert "unsafe" in msg.lower()

    def test_javascript_protocol_blocked(self):
        """javascript: protocol should be blocked."""
        query = "Click <a href='javascript:alert(1)'>here</a>"
        valid, msg = InputValidator.validate_query(query)
        assert valid is False

    def test_event_handler_blocked(self):
        """HTML event handlers should be blocked."""
        query = "<img src=x onerror=alert(1)>"
        valid, msg = InputValidator.validate_query(query)
        assert valid is False

    def test_eval_exec_blocked(self):
        """eval() and exec() should be blocked."""
        query1 = "test eval(code)"
        valid1, _ = InputValidator.validate_query(query1)
        assert valid1 is False

    def test_query_at_boundary(self):
        """Query at max length should be accepted."""
        query = "a" * InputValidator.MAX_QUERY_LENGTH
        valid, msg = InputValidator.validate_query(query)
        assert valid is True

    def test_unicode_handling(self):
        """Unicode characters should be accepted."""
        query = "What is the meaning of 世界 (world)?"
        valid, msg = InputValidator.validate_query(query)
        assert valid is True

    def test_special_chars_allowed(self):
        """Normal special characters should be allowed."""
        query = "How do I use @mentions, #hashtags, and $variables?"
        valid, msg = InputValidator.validate_query(query)
        assert valid is True


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_init(self):
        """Rate limiter should initialize."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter is not None

    def test_first_request_allowed(self):
        """First request from a client should be allowed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        client_ip = "192.168.1.1"
        allowed = limiter.is_allowed(client_ip)
        assert allowed is True

    def test_rate_limit_enforced(self):
        """Requests exceeding rate limit should be blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        client_ip = "10.0.0.1"
        
        # First 2 should pass
        assert limiter.is_allowed(client_ip) is True
        assert limiter.is_allowed(client_ip) is True
        
        # Third should fail
        assert limiter.is_allowed(client_ip) is False

    def test_different_clients_isolated(self):
        """Rate limiting should be per-client."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # Client A hits limit
        assert limiter.is_allowed("10.0.0.1") is True
        assert limiter.is_allowed("10.0.0.1") is True
        assert limiter.is_allowed("10.0.0.1") is False
        
        # Client B should still be allowed
        assert limiter.is_allowed("10.0.0.2") is True


class TestResponseCaching:
    """Test response caching."""

    def test_cache_init(self):
        """Cache should initialize."""
        cache = ResponseCache(max_cache_size=100)
        assert cache is not None

    def test_cache_miss_on_empty(self):
        """Empty cache should return None."""
        cache = ResponseCache(max_cache_size=100)
        result = cache.get("test_query", "adaptive")
        assert result is None

    def test_cache_set_and_get(self):
        """Setting and getting from cache should work."""
        cache = ResponseCache(max_cache_size=100)
        query = "What is Python?"
        response = {"response": "Python is a programming language"}
        
        cache.set(query, "adaptive", response)
        result = cache.get(query, "adaptive")
        
        assert result == response

    def test_cache_key_includes_mode(self):
        """Different modes should have different cache entries."""
        cache = ResponseCache(max_cache_size=100)
        query = "Test"
        resp1 = {"response": "adaptive response"}
        resp2 = {"response": "baseline response"}
        
        cache.set(query, "adaptive", resp1)
        cache.set(query, "baseline", resp2)
        
        assert cache.get(query, "adaptive") == resp1
        assert cache.get(query, "baseline") == resp2

    def test_cache_max_size_enforced(self):
        """Cache should respect max size."""
        cache = ResponseCache(max_cache_size=2)
        
        # Add 3 items, third should evict first
        cache.set("query1", "mode", {"data": 1})
        cache.set("query2", "mode", {"data": 2})
        cache.set("query3", "mode", {"data": 3})
        
        # First item should be evicted
        assert cache.get("query1", "mode") is None
        assert cache.get("query2", "mode") is not None
        assert cache.get("query3", "mode") is not None


class TestMemoryOptimization:
    """Test memory optimization."""

    def test_memory_monitor_init(self):
        """Memory monitor should initialize."""
        monitor = MemoryOptimizer()
        assert monitor is not None

    def test_memory_status(self):
        """Should be able to get memory status."""
        monitor = MemoryOptimizer()
        status = monitor.get_memory_status()
        assert status is not None
        assert "used_percent" in status

    def test_critical_threshold(self):
        """Should detect memory pressure."""
        monitor = MemoryOptimizer()
        # This test depends on actual system memory
        # Just verify it doesn't crash
        is_critical = monitor.is_memory_critical()
        assert isinstance(is_critical, bool)


class TestPerformanceMonitoring:
    """Test performance monitoring."""

    def test_performance_monitor_init(self):
        """Performance monitor should initialize."""
        monitor = PerformanceMonitor()
        assert monitor is not None

    def test_record_performance(self):
        """Should be able to record performance metrics."""
        monitor = PerformanceMonitor()
        monitor.record("test query", 1000.5, 50, "adaptive")
        # Just verify no crash
        assert True

    def test_get_stats(self):
        """Should be able to retrieve statistics."""
        monitor = PerformanceMonitor()
        monitor.record("query1", 2000, 100, "adaptive")
        monitor.record("query2", 1000, 50, "adaptive")
        
        stats = monitor.get_stats()
        assert stats is not None
        assert "avg_latency_ms" in stats or "total_requests" in stats


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_malicious_input_blocked_end_to_end(self):
        """End-to-end security: malicious input should be blocked."""
        validator = InputValidator()
        
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "<img src=x onerror=alert(1)>",
            "eval(os.system('rm -rf /'))",
        ]
        
        for payload in malicious_inputs:
            valid, msg = validator.validate_query(payload)
            assert valid is False, f"Malicious input not blocked: {payload}"

    def test_rate_limiter_blocks_abuse(self):
        """Rate limiter should prevent abuse."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        attacker_ip = "192.168.1.100"
        
        # Simulate attack
        allowed_count = 0
        blocked_count = 0
        for _ in range(20):
            if limiter.is_allowed(attacker_ip):
                allowed_count += 1
            else:
                blocked_count += 1
        
        assert allowed_count <= 5, "Rate limit not enforced"
        assert blocked_count >= 15, "Attack not blocked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
