"""
ARIA Inference Cache — Smart Result Memoization

Unique feature: Cache inference results with semantic similarity matching.
If a query is similar to a cached one, serve the cached answer instead of re-computing.

This is something Ollama doesn't have — it makes ARIA dramatically faster for repeated
or similar workloads. Big win for production systems with user traffic patterns.
"""

from aria.cache.memoizer import InferenceMemoizer

__all__ = ["InferenceMemoizer"]
