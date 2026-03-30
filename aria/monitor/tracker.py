"""
ARIA Metrics Tracker

Collects and assembles per-request execution metrics.
Acts as the data pipeline between ARIA's execution and storage layers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from aria.types import ExecutionMetrics
from aria.memory.monitor import MemoryMonitor

logger = logging.getLogger("aria.monitor")


class MetricsTracker:
    """
    Tracks execution metrics for a single ARIA request.

    Usage:
        tracker = MetricsTracker(memory_monitor)
        tracker.start()
        # ... run analyzer, planner, controller ...
        tracker.record_analyzer(latency_ms)
        tracker.record_planner(latency_ms)
        tracker.record_generation(tokens, latency_ms, ttft_ms)
        metrics = tracker.finalize()
    """

    def __init__(self, memory_monitor: MemoryMonitor):
        self._memory_monitor = memory_monitor
        self._start_time: float = 0.0
        self._memory_before: float = 0.0
        self._analyzer_latency_ms: float = 0.0
        self._planner_latency_ms: float = 0.0
        self._tokens_generated: int = 0
        self._generation_latency_ms: float = 0.0
        self._ttft_ms: float = 0.0

    def start(self) -> None:
        """Begin tracking a new request."""
        self._start_time = time.perf_counter()
        self._memory_before = self._memory_monitor.get_process_rss_mb()

    def record_analyzer(self, latency_ms: float) -> None:
        """Record the query analyzer's execution time."""
        self._analyzer_latency_ms = latency_ms

    def record_planner(self, latency_ms: float) -> None:
        """Record the execution planner's decision time."""
        self._planner_latency_ms = latency_ms

    def record_generation(
        self,
        tokens_generated: int,
        latency_ms: float,
        ttft_ms: float,
    ) -> None:
        """Record model generation results."""
        self._tokens_generated = tokens_generated
        self._generation_latency_ms = latency_ms
        self._ttft_ms = ttft_ms

    def finalize(self) -> ExecutionMetrics:
        """
        Finalize and return the complete execution metrics.

        Should be called after all operations are complete.
        """
        end_time = time.perf_counter()
        total_latency_ms = (end_time - self._start_time) * 1000

        memory_after = self._memory_monitor.get_process_rss_mb()
        hw_state = self._memory_monitor.get_state()

        tps = 0.0
        if self._generation_latency_ms > 0:
            tps = self._tokens_generated / (self._generation_latency_ms / 1000)

        metrics = ExecutionMetrics(
            latency_ms=round(total_latency_ms, 2),
            time_to_first_token_ms=round(self._ttft_ms, 2),
            tokens_generated=self._tokens_generated,
            tokens_per_second=round(tps, 2),
            memory_before_mb=round(self._memory_before, 2),
            memory_after_mb=round(memory_after, 2),
            memory_delta_mb=round(memory_after - self._memory_before, 2),
            system_memory_pressure=round(hw_state.memory_used_percent, 2),
            analyzer_latency_ms=round(self._analyzer_latency_ms, 2),
            planner_latency_ms=round(self._planner_latency_ms, 2),
        )

        logger.debug(
            "Request metrics: total=%.0fms, gen=%.0fms, tokens=%d, "
            "tps=%.1f, mem_delta=%.1fMB",
            total_latency_ms, self._generation_latency_ms,
            self._tokens_generated, tps,
            metrics.memory_delta_mb,
        )

        return metrics
