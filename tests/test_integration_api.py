"""
Sprint C & D Integration Tests

Comprehensive testing for:
- API endpoints
- Security features (rate limiting, input validation)
- Caching system
- Performance monitoring
- Memory management
- End-to-end workflows
"""

import pytest
import json
import time
import asyncio
from fastapi.testclient import TestClient

# Will be populated by fixtures
_client = None
_app = None


class TestAPIHealthAndStatus:
    """Test health check and status endpoints."""
    
    def test_health_check(self, client):
        """Health check should report system status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "engine_ready" in data
        assert "memory" in data
        assert "cache" in data
    
    def test_get_status(self, client):
        """Status endpoint should provide full system state."""
        response = client.get("/api/v1/status")
        assert response.status_code in [200, 503]  # 503 OK if engine not ready
        data = response.json()
        assert "status" in data or "error" in data
    
    def test_get_stats(self, client):
        """Stats endpoint should provide metrics."""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        assert "cache" in data
        assert "memory" in data
    
    def test_get_info(self, client):
        """Info endpoint should return API information."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ARIA"
        assert "version" in data
        assert "endpoints" in data


class TestQueryProcessing:
    """Test query processing pipeline."""
    
    def test_simple_query(self, client):
        """Process a simple query."""
        payload = {
            "query": "What is Python?",
            "mode": "adaptive"
        }
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "What is Python?"
        assert "response" in data
        assert data["cached"] == False
        assert data["complexity"] in ["simple", "medium", "complex"]
        assert "metrics" in data
        assert "latency_ms" in data["metrics"]
    
    def test_caching(self, client):
        """Second query should be cached."""
        payload = {
            "query": "Test caching",
            "mode": "adaptive"
        }
        
        # First query (cache miss)
        response1 = client.post("/api/v1/query", json=payload)
        assert response1.status_code == 200
        assert response1.json()["cached"] == False
        first_latency = response1.json()["metrics"]["latency_ms"]
        
        # Second query (cache hit)
        response2 = client.post("/api/v1/query", json=payload)
        assert response2.status_code == 200
        assert response2.json()["cached"] == True
        second_latency = response2.json()["metrics"]["latency_ms"]
        
        # Cache hit should be faster
        assert second_latency < first_latency
    
    def test_different_modes(self, client):
        """Test different execution modes."""
        query = "Test modes"
        for mode in ["adaptive", "baseline", "cascade"]:
            payload = {"query": query, "mode": mode}
            response = client.post("/api/v1/query", json=payload)
            assert response.status_code == 200
            assert response.json()["strategy"]["mode"] == mode
    
    def test_invalid_query_empty(self, client):
        """Empty query should be rejected."""
        payload = {"query": "", "mode": "adaptive"}
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_invalid_query_too_long(self, client):
        """Excessively long query should be rejected."""
        payload = {
            "query": "x" * 10000,  # Way over limit
            "mode": "adaptive"
        }
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400
        assert response.json()["error"] == "validation_error"


class TestInputSecurity:
    """Test input validation and security."""
    
    def test_xss_attack_blocked(self, client):
        """XSS attacks should be blocked."""
        malicious_queries = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:void(0)",
        ]
        for payload_text in malicious_queries:
            payload = {"query": payload_text, "mode": "adaptive"}
            response = client.post("/api/v1/query", json=payload)
            assert response.status_code == 400, f"XSS not blocked: {payload_text}"
    
    def test_code_injection_blocked(self, client):
        """Code injection attempts should be blocked."""
        malicious_queries = [
            "eval(os.system('rm -rf /'))",
            "exec('import os')",
            "'; DROP TABLE users; --",
        ]
        for payload_text in malicious_queries:
            payload = {"query": payload_text, "mode": "adaptive"}
            response = client.post("/api/v1/query", json=payload)
            assert response.status_code == 400, f"Code injection not blocked: {payload_text}"
    
    def test_sql_injection_blocked(self, client):
        """SQL injection should be blocked."""
        payload = {"query": "'; DROP TABLE users; --", "mode": "adaptive"}
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400
    
    def test_special_chars_allowed(self, client):
        """Safe special characters should be allowed."""
        safe_queries = [
            "What is 2+2? (math)",
            "Alice & Bob's test",
            "Price: $99.99, Rating: 4/5",
            "Question mark? No problem!",
        ]
        for query_text in safe_queries:
            payload = {"query": query_text, "mode": "adaptive"}
            response = client.post("/api/v1/query", json=payload)
            assert response.status_code == 200, f"Safe query rejected: {query_text}"


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforcement(self, client):
        """Exceeding rate limit should be blocked."""
        # Make many requests in quick succession
        allowed = 0
        limited = 0
        
        for i in range(150):  # More than default limit of 100
            payload = {"query": f"Query {i}", "mode": "adaptive"}
            response = client.post("/api/v1/query", json=payload)
            
            if response.status_code == 200:
                allowed += 1
            elif response.status_code == 429:
                limited += 1
                break  # Once we hit rate limit, continue checking for remaining
        
        # Should have exceeded rate limit
        assert limited > 0, "Rate limit not enforced"
        assert allowed > 0, "Some requests should have passed"
    
    def test_rate_limit_error_format(self, client):
        """Rate limit error should have proper format."""
        # Do many requests to trigger rate limit
        for i in range(110):
            payload = {"query": f"Test {i}", "mode": "adaptive"}
            response = client.post("/api/v1/query", json=payload)
            
            if response.status_code == 429:
                data = response.json()
                assert "error" in data
                assert data["error"] == "rate_limit_exceeded"
                assert "message" in data
                assert "remaining_requests" in data
                break


class TestAnalyzeEndpoint:
    """Test analysis endpoint (without inference)."""
    
    def test_analyze_valid_query(self, client):
        """Analyze should classify query."""
        payload = {"query": "What is machine learning?"}
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "What is machine learning?"
        assert "complexity" in data
        assert "task_type" in data
        assert "confidence" in data
        assert "estimated_tokens" in data
    
    def test_analyze_empty_query(self, client):
        """Empty query should be rejected in analyze."""
        payload = {"query": ""}
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 400


class TestMemoryManagement:
    """Test memory monitoring and response."""
    
    def test_memory_status_in_health(self, client):
        """Health check should report memory."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "memory" in data
        memory = data["memory"]
        assert "total_mb" in memory
        assert "used_percent" in memory
        assert "available_mb" in memory
    
    def test_memory_reasonable_values(self, client):
        """Memory values should be reasonable."""
        response = client.get("/api/v1/health")
        memory = response.json()["memory"]
        
        assert 0 <= memory["used_percent"] <= 100
        assert memory["total_mb"] > 0
        assert memory["available_mb"] >= 0


class TestCachingSystem:
    """Test response caching."""
    
    def test_cache_clear(self, client):
        """Cache should be clearable."""
        # First, populate cache
        payload = {"query": "Cache test", "mode": "adaptive"}
        client.post("/api/v1/query", json=payload)
        
        # Clear cache
        response = client.post("/api/v1/cache/clear")
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_different_modes_different_cache(self, client):
        """Different modes should have separate cache entries."""
        query = "Same query"
        
        # Query in adaptive mode
        payload_adaptive = {"query": query, "mode": "adaptive"}
        response1 = client.post("/api/v1/query", json=payload_adaptive)
        assert response1.json()["cached"] == False
        
        # Query same text in baseline mode (should not be cached)
        payload_baseline = {"query": query, "mode": "baseline"}
        response2 = client.post("/api/v1/query", json=payload_baseline)
        assert response2.json()["cached"] == False
        
        # Query in adaptive mode again (should be cached)
        response3 = client.post("/api/v1/query", json=payload_adaptive)
        assert response3.json()["cached"] == True


class TestErrorHandling:
    """Test error handling and responses."""
    
    def test_error_response_format(self, client):
        """Error responses should have consistent format."""
        # Trigger validation error
        payload = {"query": ""}
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert "message" in data
    
    def test_missing_required_field(self, client):
        """Missing required fields should be handled."""
        # No query field
        payload = {"mode": "adaptive"}
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400


class TestPerformanceMetrics:
    """Test performance tracking."""
    
    def test_metrics_recorded(self, client):
        """Each query should record metrics."""
        payload = {"query": "Performance test", "mode": "adaptive"}
        response = client.post("/api/v1/query", json=payload)
        
        data = response.json()
        assert "metrics" in data
        metrics = data["metrics"]
        
        assert "latency_ms" in metrics
        assert "inference_ms" in metrics
        assert "tokens" in metrics
        assert "tokens_per_second" in metrics
        
        # Values should be reasonable
        assert metrics["latency_ms"] > 0
        assert metrics["tokens"] > 0
    
    def test_stats_endpoint_metrics(self, client):
        """Stats should include performance data."""
        # Make a query first
        payload = {"query": "Stats test", "mode": "adaptive"}
        client.post("/api/v1/query", json=payload)
        
        # Get stats
        response = client.get("/api/v1/stats")
        data = response.json()
        
        assert "performance" in data
        assert "cache" in data
        assert "memory" in data


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def app():
    """Create FastAPI app."""
    from fastapi import FastAPI
    from api.routes import router
    
    app = FastAPI()
    app.include_router(router)
    
    return app


@pytest.fixture(scope="session")
def client(app):
    """Create test client."""
    return TestClient(app)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
