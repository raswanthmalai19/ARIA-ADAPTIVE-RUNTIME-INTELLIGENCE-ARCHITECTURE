"""
ARIA Benchmark Datasets

Curated test queries organized by expected complexity level.
Used for validating the classifier and benchmarking adaptive vs baseline.
"""

from __future__ import annotations

from typing import NamedTuple


class BenchmarkQuery(NamedTuple):
    """A benchmark query with its expected complexity."""
    query: str
    expected_complexity: str  # simple, moderate, complex, expert
    category: str             # descriptive category


# ─────────────────────────────────────────────
# Benchmark Query Sets
# ─────────────────────────────────────────────

SIMPLE_QUERIES = [
    BenchmarkQuery("Hello!", "simple", "greeting"),
    BenchmarkQuery("Hi there, how are you?", "simple", "greeting"),
    BenchmarkQuery("What is the capital of France?", "simple", "factual"),
    BenchmarkQuery("What is 2 + 2?", "simple", "math"),
    BenchmarkQuery("Who wrote Romeo and Juliet?", "simple", "factual"),
    BenchmarkQuery("What color is the sky?", "simple", "factual"),
    BenchmarkQuery("Thank you!", "simple", "greeting"),
    BenchmarkQuery("What year did World War 2 end?", "simple", "factual"),
    BenchmarkQuery("Define photosynthesis.", "simple", "factual"),
    BenchmarkQuery("What is the largest planet in our solar system?", "simple", "factual"),
    BenchmarkQuery("How many continents are there?", "simple", "factual"),
    BenchmarkQuery("What is HTML?", "simple", "factual"),
]

MODERATE_QUERIES = [
    BenchmarkQuery(
        "Explain how photosynthesis works in plants.",
        "moderate", "science"
    ),
    BenchmarkQuery(
        "Summarize the main causes of the French Revolution.",
        "moderate", "history"
    ),
    BenchmarkQuery(
        "What are the differences between TCP and UDP?",
        "moderate", "technology"
    ),
    BenchmarkQuery(
        "How does a binary search algorithm work?",
        "moderate", "computing"
    ),
    BenchmarkQuery(
        "Explain the concept of supply and demand in economics.",
        "moderate", "economics"
    ),
    BenchmarkQuery(
        "What are the advantages and disadvantages of solar energy?",
        "moderate", "energy"
    ),
    BenchmarkQuery(
        "How does machine learning differ from traditional programming?",
        "moderate", "ai"
    ),
    BenchmarkQuery(
        "Describe the water cycle and its main stages.",
        "moderate", "science"
    ),
    BenchmarkQuery(
        "What is the significance of the Turing Test?",
        "moderate", "computing"
    ),
    BenchmarkQuery(
        "Explain the difference between RAM and ROM.",
        "moderate", "technology"
    ),
]

COMPLEX_QUERIES = [
    BenchmarkQuery(
        "Compare and contrast microservices architecture with monolithic architecture. "
        "Discuss the trade-offs in terms of scalability, maintainability, and deployment.",
        "complex", "architecture"
    ),
    BenchmarkQuery(
        "Explain how transformer neural networks work, including the self-attention "
        "mechanism, positional encoding, and multi-head attention.",
        "complex", "ai"
    ),
    BenchmarkQuery(
        "Analyze the economic implications of universal basic income. Discuss both "
        "the potential benefits and risks from multiple perspectives.",
        "complex", "economics"
    ),
    BenchmarkQuery(
        "Explain the CAP theorem in distributed systems and provide real-world "
        "examples of how different databases make trade-offs between consistency, "
        "availability, and partition tolerance.",
        "complex", "systems"
    ),
    BenchmarkQuery(
        "Describe how garbage collection works in modern programming languages. "
        "Compare mark-and-sweep, generational, and reference counting approaches.",
        "complex", "computing"
    ),
    BenchmarkQuery(
        "What are the ethical implications of AI in healthcare? Discuss privacy, "
        "bias, accountability, and the balance between automation and human oversight.",
        "complex", "ethics"
    ),
    BenchmarkQuery(
        "Explain the differences between REST, GraphQL, and gRPC APIs. When would "
        "you choose each, and what are the performance trade-offs?",
        "complex", "api_design"
    ),
    BenchmarkQuery(
        "How does quantum computing work? Explain qubits, superposition, entanglement, "
        "and discuss potential applications in cryptography.",
        "complex", "quantum"
    ),
]

EXPERT_QUERIES = [
    BenchmarkQuery(
        "Write a Python function that implements a least recently used (LRU) cache "
        "with O(1) get and put operations. Include proper error handling, type hints, "
        "and comprehensive docstrings. Also write unit tests for edge cases.",
        "expert", "code"
    ),
    BenchmarkQuery(
        "Design a complete system architecture for a real-time collaborative document "
        "editor like Google Docs. Include the data model, conflict resolution strategy "
        "(CRDTs vs OT), networking layer, and scalability considerations. Provide "
        "detailed technical trade-offs for each design decision.",
        "expert", "system_design"
    ),
    BenchmarkQuery(
        "Implement a Python decorator that adds retry logic with exponential backoff, "
        "jitter, and configurable maximum retries. It should handle specific exception "
        "types, log retry attempts, and support both synchronous and asynchronous functions. "
        "Include comprehensive examples and tests.",
        "expert", "code"
    ),
    BenchmarkQuery(
        "Write a detailed technical analysis of how modern language models handle "
        "context windows. Explain the attention mechanism's quadratic complexity, "
        "evaluate solutions like sparse attention, sliding window attention, and "
        "FlashAttention. Include mathematical formulations where appropriate and "
        "discuss practical implications for deployment on limited hardware.",
        "expert", "research"
    ),
    BenchmarkQuery(
        "Design and implement a comprehensive rate limiter for a web API that supports "
        "multiple strategies: fixed window, sliding window, token bucket, and leaky "
        "bucket. Write production-quality Python code with Redis as the backing store, "
        "including distributed locking and graceful degradation.",
        "expert", "code"
    ),
    BenchmarkQuery(
        "Create a step-by-step guide to building a CI/CD pipeline for a microservices "
        "application. Cover containerization with Docker, orchestration with Kubernetes, "
        "automated testing strategies, blue-green deployments, canary releases, "
        "monitoring and alerting setup, and security best practices. Include specific "
        "tool recommendations and configuration examples.",
        "expert", "devops"
    ),
]


def get_benchmark_queries(
    levels: list[str] | None = None,
) -> list[BenchmarkQuery]:
    """
    Get benchmark queries, optionally filtered by complexity level.

    Args:
        levels: List of levels to include. None = all levels.

    Returns:
        List of BenchmarkQuery tuples.
    """
    all_queries = {
        "simple": SIMPLE_QUERIES,
        "moderate": MODERATE_QUERIES,
        "complex": COMPLEX_QUERIES,
        "expert": EXPERT_QUERIES,
    }

    if levels is None:
        levels = list(all_queries.keys())

    result = []
    for level in levels:
        result.extend(all_queries.get(level, []))

    return result


def get_sample_queries(n_per_level: int = 3) -> list[BenchmarkQuery]:
    """Get a small sample of queries for quick testing."""
    result = []
    for queries in [SIMPLE_QUERIES, MODERATE_QUERIES, COMPLEX_QUERIES, EXPERT_QUERIES]:
        result.extend(queries[:n_per_level])
    return result
