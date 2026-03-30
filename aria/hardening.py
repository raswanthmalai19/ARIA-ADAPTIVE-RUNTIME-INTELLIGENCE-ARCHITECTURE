"""
ARIA Production Hardening Module

Fixes critical issues:
- Input validation & sanitization
- Rate limiting
- Response caching
- Error handling improvements
- Memory optimization
"""

import hashlib
import time
import json
import logging
from typing import Optional, Dict, Any
from collections import defaultdict
from functools import lru_cache
from datetime import datetime, timedelta
import re

logger = logging.getLogger("aria.hardening")


class InputValidator:
    """Validate and sanitize user inputs."""
    
    # Security constraints
    MAX_QUERY_LENGTH = 5000
    MIN_QUERY_LENGTH = 1
    UNSAFE_PATTERNS = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onload=',
        r'eval\(',
        r'exec\(',
        r"'[^']*?(?:drop|delete|insert|update|select|union|exec|script)",  # SQL injection and command patterns
        r'--\s*$',  # SQL comment
    ]
    
    @classmethod
    def validate_query(cls, text: str) -> tuple[bool, Optional[str]]:
        """
        Validate user query.
        
        Returns: (is_valid, error_message)
        """
        # Check length
        if len(text) < cls.MIN_QUERY_LENGTH:
            return False, "Query is too short"
        
        if len(text) > cls.MAX_QUERY_LENGTH:
            return False, f"Query exceeds maximum length ({cls.MAX_QUERY_LENGTH})"
        
        # Check for unsafe patterns
        text_lower = text.lower()
        for pattern in cls.UNSAFE_PATTERNS:
            if re.search(pattern, text_lower):
                return False, "Query contains unsafe content"
        
        # Check for null bytes
        if '\x00' in text:
            return False, "Query contains invalid characters"
        
        logger.debug(f"Query validation passed: {len(text)} chars")
        return True, None
    
    @classmethod
    def sanitize_query(cls, text: str) -> str:
        """Sanitize query by removing/escaping dangerous content."""
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Trim whitespace
        text = text.strip()
        
        return text


class RateLimiter:
    """Rate limiting to prevent abuse."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client can make another request."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Remove old requests outside window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        # Record new request
        self.requests[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for this client."""
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        return max(0, self.max_requests - len(self.requests[client_id]))


class ResponseCache:
    """Cache responses to reduce redundant computations."""
    
    def __init__(self, max_cache_size: int = 1000, ttl_seconds: int = 3600):
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def _hash_query(self, text: str, mode: str) -> str:
        """Generate cache key for query."""
        key = f"{text}||{mode}".encode()
        return hashlib.sha256(key).hexdigest()
    
    def get(self, text: str, mode: str) -> Optional[Dict]:
        """Get cached response if available and fresh."""
        key = self._hash_query(text, mode)
        
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            del self.cache[key]
            return None
        
        logger.debug(f"Cache hit for: {text[:50]}...")
        entry['hits'] = entry.get('hits', 0) + 1
        return entry['response']
    
    def set(self, text: str, mode: str, response: Dict):
        """Cache a response."""
        # Prevent unbounded growth
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        key = self._hash_query(text, mode)
        self.cache[key] = {
            'response': response,
            'timestamp': time.time(),
            'hits': 0
        }
        logger.debug(f"Cached response for: {text[:50]}...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.get('hits', 0) for entry in self.cache.values())
        return {
            'size': len(self.cache),
            'max_size': self.max_cache_size,
            'total_hits': total_hits,
            'hit_rate': total_hits / (total_hits + 1) if total_hits > 0 else 0
        }


class ErrorHandler:
    """Improved error handling with better messages."""
    
    ERROR_MESSAGES = {
        'invalid_input': 'Invalid input. Please check your query.',
        'rate_limit': 'Too many requests. Please wait a moment.',
        'resource_limit': 'Server resources exhausted. Please try again.',
        'timeout': 'Request timed out. Query may be too complex.',
        'model_error': 'Model encountered an error. Please try again.',
        'unknown': 'An unexpected error occurred. Please try again.',
    }
    
    @classmethod
    def get_user_message(cls, error_type: str) -> str:
        """Get user-friendly error message."""
        return cls.ERROR_MESSAGES.get(error_type, cls.ERROR_MESSAGES['unknown'])
    
    @classmethod
    def log_error(cls, error_type: str, error: Exception, context: Dict = None):
        """Log error with context."""
        context_str = f" | Context: {json.dumps(context)}" if context else ""
        logger.error(f"{error_type}: {str(error)}{context_str}")


class MemoryOptimizer:
    """Optimize memory usage."""
    
    # Memory thresholds (in MB)
    CRITICAL_THRESHOLD = 512  # Remaining free memory
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_memory_status() -> Dict[str, float]:
        """Get current memory status."""
        import psutil
        
        vm = psutil.virtual_memory()
        return {
            'total_mb': vm.total / (1024 * 1024),
            'available_mb': vm.available / (1024 * 1024),
            'used_percent': vm.percent,
        }
    
    @staticmethod
    def is_memory_critical() -> bool:
        """Check if memory usage is critical."""
        import psutil
        
        vm = psutil.virtual_memory()
        available_mb = vm.available / (1024 * 1024)
        
        return available_mb < MemoryOptimizer.CRITICAL_THRESHOLD
    
    @staticmethod
    def cleanup() -> int:
        """Aggressive cleanup of unused memory."""
        import gc
        
        # Force garbage collection
        collected = gc.collect()
        logger.info(f"Memory cleanup: {collected} objects collected")
        
        return collected


class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    def __init__(self):
        self.metrics = []
    
    def record(self, query: str, latency_ms: float, tokens: int, mode: str):
        """Record query performance metric."""
        self.metrics.append({
            'query_length': len(query),
            'latency_ms': latency_ms,
            'tokens': tokens,
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'tokens_per_second': (tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
        })
        
        # Keep last 100 metrics
        self.metrics = self.metrics[-100:]
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        if not self.metrics:
            return {}
        
        latencies = [m['latency_ms'] for m in self.metrics]
        tps = [m['tokens_per_second'] for m in self.metrics]
        
        return {
            'avg_latency_ms': sum(latencies) / len(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'avg_tokens_per_second': sum(tps) / len(tps) if tps else 0,
            'total_queries': len(self.metrics),
        }


# Global instances
input_validator = InputValidator()
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
response_cache = ResponseCache(max_cache_size=1000, ttl_seconds=3600)
error_handler = ErrorHandler()
memory_optimizer = MemoryOptimizer()
performance_monitor = PerformanceMonitor()
