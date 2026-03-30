"""
ARIA Memory Monitor

Tracks system and process memory usage in real time.
Classifies memory pressure into tiers (GREEN/YELLOW/ORANGE/RED)
to inform the Execution Planner's hardware-aware decisions.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import psutil

from aria.types import HardwareState, MemoryTier
from aria.config import ARIAConfig, get_config

logger = logging.getLogger("aria.memory")


class MemoryMonitor:
    """
    Monitors system and process-level memory usage.

    Provides real-time HardwareState snapshots that the Execution Planner
    uses to make hardware-aware decisions. Cached briefly to avoid
    excessive system calls.
    """

    def __init__(self, config: Optional[ARIAConfig] = None):
        self.config = config or get_config()
        self._process = psutil.Process(os.getpid())
        self._cache: Optional[HardwareState] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 0.5  # Cache for 500ms

    def get_state(self, force_refresh: bool = False) -> HardwareState:
        """
        Get current hardware state.

        Uses a brief cache to avoid excessive psutil calls
        during rapid successive requests.
        """
        now = time.time()
        if (
            not force_refresh
            and self._cache is not None
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            return self._cache

        state = self._snapshot()
        self._cache = state
        self._cache_timestamp = now
        return state

    def get_process_rss_mb(self) -> float:
        """Get current process RSS (Resident Set Size) in MB."""
        try:
            return self._process.memory_info().rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0

    def classify_tier(self, used_percent: float) -> MemoryTier:
        """Classify memory usage percentage into a tier."""
        cfg = self.config.memory
        if used_percent >= cfg.red_threshold:
            return MemoryTier.RED
        elif used_percent >= cfg.orange_threshold:
            return MemoryTier.ORANGE
        elif used_percent >= cfg.yellow_threshold:
            return MemoryTier.YELLOW
        else:
            return MemoryTier.GREEN

    def _snapshot(self) -> HardwareState:
        """Take a fresh snapshot of system resources."""
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            process_rss = self._process.memory_info().rss / (1024 * 1024)
            cpu_percent = psutil.cpu_percent(interval=None)

            used_percent = vm.percent
            tier = self.classify_tier(used_percent)

            state = HardwareState(
                memory_total_mb=vm.total / (1024 * 1024),
                memory_available_mb=vm.available / (1024 * 1024),
                memory_used_percent=used_percent,
                memory_tier=tier,
                process_rss_mb=process_rss,
                swap_used_mb=swap.used / (1024 * 1024),
                cpu_percent=cpu_percent,
            )

            # Log tier transitions
            if tier in (MemoryTier.ORANGE, MemoryTier.RED):
                logger.warning(
                    "Memory pressure %s: %.1f%% used (%.0f MB available, "
                    "process RSS: %.0f MB, swap: %.0f MB)",
                    tier.value.upper(),
                    used_percent,
                    state.memory_available_mb,
                    process_rss,
                    state.swap_used_mb,
                )

            return state

        except Exception as e:
            logger.error("Failed to read hardware state: %s", e)
            # Return a safe default (GREEN) so the system continues running
            return HardwareState(
                memory_total_mb=8192.0,
                memory_available_mb=4096.0,
                memory_used_percent=50.0,
                memory_tier=MemoryTier.GREEN,
                process_rss_mb=0.0,
                swap_used_mb=0.0,
                cpu_percent=0.0,
            )

    def format_status(self) -> str:
        """Format a human-readable memory status string."""
        state = self.get_state()
        tier_emoji = {
            MemoryTier.GREEN: "🟢",
            MemoryTier.YELLOW: "🟡",
            MemoryTier.ORANGE: "🟠",
            MemoryTier.RED: "🔴",
        }
        return (
            f"{tier_emoji[state.memory_tier]} Memory: {state.memory_used_percent:.1f}% "
            f"({state.memory_available_mb:.0f} MB free) │ "
            f"Process: {state.process_rss_mb:.0f} MB │ "
            f"Swap: {state.swap_used_mb:.0f} MB │ "
            f"CPU: {state.cpu_percent:.0f}%"
        )
