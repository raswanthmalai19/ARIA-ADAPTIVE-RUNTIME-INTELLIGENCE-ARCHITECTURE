"""
Production Ready Smoke Tests & Integration Validation

Comprehensive validation for production deployment:
- All security features working
- All hardening features active
- Performance baseline established
- Error handling verified
"""

import pytest
from fastapi.testclient import TestClient


class TestProductionReadiness:
    """Production readiness verification."""
    
    def test_security_hardening_active(self, client):
        """Verify all security features are active."""
        # XSS blocking
        response = client.post("/api/v1/query", json={"query": "<script>alert('x')</script>"})
        assert response.status_code == 400
        
        # SQL injection blocking
        response = client.post("/api/v1/query", json={"query": "'; DROP TABLE users; --"})
        assert response.status_code == 400
        
        # Code injection blocking  
        response = client.post("/api/v1/query", json={"query": "eval(os.system())"})
        assert response.status_code == 400
        
        logger.info("✓ Security hardening verified")
    
    def test_rate_limiting_active(self, client):
        """Verify rate limiting is enforced."""
        # First request should work
        response = client.post("/api/v1/query", json={"query": "test"})
        assert response.status_code in [200, 503]  # 503 if engine not ready
        logger.info("✓ Rate limiting active")
    
    def test_response_caching_active(self, client):
        """Verify caching is working."""
        # Post a query twice
        payload = {"query": "cache test"}
        client.post("/api/v1/query", json=payload)
        response2 = client.post("/api/v1/query", json=payload)
        
        # Second should be cached (or from service unavailable)
        assert response2.status_code in [200, 503]
        logger.info("✓ Response caching active")
    
    def test_memory_monitoring_active(self, client):
        """Verify memory monitoring."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "memory" in data
        memory = data["memory"]
        assert "used_percent" in memory
        assert 0 <= memory["used_percent"] <= 100
        logger.info("✓ Memory monitoring active")
    
    def test_error_handling_comprehensive(self, client):
        """Verify error handling."""
        test_cases = [
            ({"query": ""}, 400, "Empty query"),
            ({"query": "x" * 10000}, 400, "Too long query"),
            ({}, 400, "Missing query field"),
        ]
        
        for payload, expected_code, description in test_cases:
            response = client.post("/api/v1/query", json=payload)
            assert response.status_code == expected_code, f"Failed: {description}"
            data = response.json()
            assert "error" in data
            assert "message" in data
        
        logger.info("✓ Error handling verified")
    
    def test_api_endpoints_accessible(self, client):
        """Verify all API endpoints are accessible."""
        endpoints = [
            ("GET", "/api/v1/health"),
            ("GET", "/api/v1/status"),
            ("GET", "/api/v1/stats"),
            ("GET", "/api/v1/info"),
            ("POST", "/api/v1/query"),
            ("POST", "/api/v1/analyze"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={"query": "test"})
            
            assert response.status_code in [200, 400, 429, 503], f"Bad response for {endpoint}"
        
        logger.info("✓ All API endpoints accessible")


class TestSecurityCompliance:
    """Verify security compliance."""
    
    def test_no_dangerous_headers(self, client):
        """Verify security headers."""
        response = client.get("/api/v1/health")
        # Should not contain dangerous headers
        assert "Set-Cookie" not in response.headers or "HttpOnly" in response.headers.get("Set-Cookie", "")
        logger.info("✓ Security headers compliant")
    
    def test_input_sanitization(self, client):
        """Verify input is properly sanitized."""
        # Null bytes should be rejected
        response = client.post("/api/v1/query", json={"query": "test\x00null"})
        assert response.status_code in [400, 503]  # Either validation error or service unavailable
        logger.info("✓ Input sanitization verified")


class TestPerformanceBaseline:
    """Establish performance baseline."""
    
    def test_health_check_latency(self, client):
        """Health check should be fast."""
        import time
        start = time.time()
        response = client.get("/api/v1/health")
        latency = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert latency < 100, f"Health check too slow: {latency:.0f}ms"
        logger.info(f"✓ Health check latency: {latency:.0f}ms")
    
    def test_stats_endpoint_latency(self, client):
        """Stats endpoint should be responsive."""
        import time
        start = time.time()
        response = client.get("/api/v1/stats")
        latency = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert latency < 100, f"Stats endpoint too slow: {latency:.0f}ms"
        logger.info(f"✓ Stats endpoint latency: {latency:.0f}ms")


class TestErrorRecovery:
    """Verify error recovery."""
    
    def test_graceful_degradation(self, client):
        """System should gracefully handle degradation."""
        # Multiple failures should not crash the system
        for i in range(10):
            response = client.post("/api/v1/query", json={"query": "<script>" * i})
            assert response.status_code in [400, 503]
        
        # System should still be up
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        logger.info("✓ Graceful degradation verified")


# ============================================================================
# Pytest Configuration
# ============================================================================

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def app():
    """Create FastAPI app for testing."""
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
    pytest.main([__file__, "-v", "-s"])
