"""
ARIA Metrics Store

SQLite-based persistent storage for execution metrics.
Enables historical analysis, trend tracking, and benchmark comparisons.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from aria.types import (
    ComplexityLevel, ExecutionMetrics, ExecutionResult,
)
from aria.config import ARIAConfig, get_config

logger = logging.getLogger("aria.monitor.store")


class MetricsStore:
    """
    Persistent SQLite storage for ARIA execution metrics.

    Stores every request's metrics for historical analysis,
    benchmarking, and dashboard display.
    """

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()
        self._db_path = self.config.metrics_db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database and create tables if needed."""
        try:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    query TEXT NOT NULL,
                    complexity_level TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    complexity_score REAL,
                    strategy_source TEXT,
                    max_tokens INTEGER,
                    temperature REAL,
                    latency_ms REAL,
                    time_to_first_token_ms REAL,
                    tokens_generated INTEGER,
                    tokens_per_second REAL,
                    memory_before_mb REAL,
                    memory_after_mb REAL,
                    memory_delta_mb REAL,
                    system_memory_pressure REAL,
                    memory_tier TEXT,
                    fallback_triggered INTEGER DEFAULT 0,
                    fallback_reason TEXT,
                    response_length INTEGER,
                    mode TEXT DEFAULT 'adaptive',
                    execution_mode TEXT DEFAULT 'standard',
                    layers_used INTEGER DEFAULT 0,
                    total_layers INTEGER DEFAULT 0,
                    model_used TEXT DEFAULT ''
                )
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON executions(timestamp)
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_complexity
                ON executions(complexity_level)
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mode
                ON executions(mode)
            """)

            self._conn.commit()
            logger.debug("Metrics store initialized: %s", self._db_path)

        except Exception as e:
            logger.error("Failed to initialize metrics store: %s", e)

    def record(self, result: ExecutionResult, mode: str = "adaptive") -> None:
        """
        Record a complete execution result.

        Args:
            result: The full execution result from ARIA.
            mode: Either 'adaptive' or 'baseline' (for benchmarks).
        """
        if self._conn is None:
            return

        try:
            self._conn.execute("""
                INSERT INTO executions (
                    timestamp, query, complexity_level, task_type,
                    complexity_score, strategy_source, max_tokens,
                    temperature, latency_ms, time_to_first_token_ms,
                    tokens_generated, tokens_per_second,
                    memory_before_mb, memory_after_mb, memory_delta_mb,
                    system_memory_pressure, memory_tier,
                    fallback_triggered, fallback_reason,
                    response_length, mode,
                    execution_mode, layers_used, total_layers, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                time.time(),
                result.query[:500],
                result.query_profile.complexity_level.value,
                result.query_profile.task_type.value,
                result.query_profile.complexity_score,
                result.strategy.source,
                result.strategy.max_tokens,
                result.strategy.temperature,
                result.metrics.latency_ms,
                result.metrics.time_to_first_token_ms,
                result.metrics.tokens_generated,
                result.metrics.tokens_per_second,
                result.metrics.memory_before_mb,
                result.metrics.memory_after_mb,
                result.metrics.memory_delta_mb,
                result.metrics.system_memory_pressure,
                result.hardware_state.memory_tier.value,
                1 if result.fallback_triggered else 0,
                result.fallback_reason,
                len(result.response),
                mode,
                result.metrics.execution_mode,
                result.metrics.layers_used,
                result.metrics.total_layers,
                result.metrics.model_used,
            ))
            self._conn.commit()

        except Exception as e:
            logger.error("Failed to record metrics: %s", e)

    def get_recent(self, limit: int = 50, mode: Optional[str] = None) -> list[dict]:
        """Get recent execution records."""
        if self._conn is None:
            return []

        try:
            if mode:
                rows = self._conn.execute(
                    "SELECT * FROM executions WHERE mode = ? "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (mode, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM executions ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error("Failed to fetch recent metrics: %s", e)
            return []

    def get_stats_by_complexity(self, mode: str = "adaptive") -> dict:
        """Get aggregated statistics grouped by complexity level."""
        if self._conn is None:
            return {}

        try:
            rows = self._conn.execute("""
                SELECT
                    complexity_level,
                    COUNT(*) as count,
                    AVG(latency_ms) as avg_latency_ms,
                    AVG(tokens_per_second) as avg_tps,
                    AVG(tokens_generated) as avg_tokens,
                    AVG(memory_delta_mb) as avg_memory_delta_mb,
                    AVG(time_to_first_token_ms) as avg_ttft_ms,
                    MIN(latency_ms) as min_latency_ms,
                    MAX(latency_ms) as max_latency_ms
                FROM executions
                WHERE mode = ?
                GROUP BY complexity_level
                ORDER BY complexity_level
            """, (mode,)).fetchall()

            return {
                row["complexity_level"]: dict(row)
                for row in rows
            }

        except Exception as e:
            logger.error("Failed to compute stats: %s", e)
            return {}

    def get_comparison_stats(self) -> dict:
        """Get side-by-side adaptive vs baseline stats for benchmarking."""
        adaptive = self.get_stats_by_complexity("adaptive")
        baseline = self.get_stats_by_complexity("baseline")
        return {"adaptive": adaptive, "baseline": baseline}

    def get_total_count(self) -> int:
        """Get total number of recorded executions."""
        if self._conn is None:
            return 0
        try:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM executions"
            ).fetchone()
            return row["cnt"] if row else 0
        except Exception:
            return 0

    def clear(self) -> None:
        """Clear all stored metrics (use with caution)."""
        if self._conn is None:
            return
        self._conn.execute("DELETE FROM executions")
        self._conn.commit()
        logger.info("All metrics cleared")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
