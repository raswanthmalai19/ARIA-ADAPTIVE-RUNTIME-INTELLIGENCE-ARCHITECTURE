"""
ARIA Metrics Reporter

Generates formatted reports from stored execution metrics.
Supports JSON export, formatted tables, and comparison reports.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from aria.monitor.store import MetricsStore

logger = logging.getLogger("aria.monitor.reporter")


class MetricsReporter:
    """
    Generates human-readable and machine-readable reports
    from ARIA's metrics store.
    """

    def __init__(self, store: MetricsStore):
        self._store = store

    def summary_report(self) -> str:
        """Generate a text summary of all-time adaptive execution stats."""
        stats = self._store.get_stats_by_complexity("adaptive")
        total = self._store.get_total_count()

        if not stats:
            return "No execution data recorded yet."

        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║              ARIA Performance Summary                       ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Total Executions: {total:<42}║",
            "╠═══════════════╦════════╦═══════════╦════════╦═══════════════╣",
            "║  Complexity   ║ Count  ║ Avg ms    ║ Tok/s  ║ Avg Mem Δ MB  ║",
            "╠═══════════════╬════════╬═══════════╬════════╬═══════════════╣",
        ]

        for level in ["simple", "moderate", "complex", "expert"]:
            if level in stats:
                s = stats[level]
                lines.append(
                    f"║  {level:<13}║ {s['count']:<6} ║ "
                    f"{s['avg_latency_ms']:>7.0f}   ║ {s['avg_tps']:>5.1f}  ║ "
                    f"{s['avg_memory_delta_mb']:>11.1f}  ║"
                )

        lines.append(
            "╚═══════════════╩════════╩═══════════╩════════╩═══════════════╝"
        )

        return "\n".join(lines)

    def comparison_report(self) -> str:
        """Generate an adaptive vs baseline comparison report."""
        data = self._store.get_comparison_stats()
        adaptive = data.get("adaptive", {})
        baseline = data.get("baseline", {})

        if not adaptive and not baseline:
            return "No benchmark data available. Run benchmarks first."

        lines = [
            "",
            "┌────────────────────────────────────────────────────────────────┐",
            "│            ARIA Benchmark: Adaptive vs Baseline               │",
            "├───────────────┬──────────────────┬──────────────────┬──────────┤",
            "│  Complexity   │ Adaptive (ms)    │ Baseline (ms)    │ Savings  │",
            "├───────────────┼──────────────────┼──────────────────┼──────────┤",
        ]

        for level in ["simple", "moderate", "complex", "expert"]:
            a = adaptive.get(level, {})
            b = baseline.get(level, {})

            a_lat = a.get("avg_latency_ms", 0)
            b_lat = b.get("avg_latency_ms", 0)

            if b_lat > 0:
                savings = ((b_lat - a_lat) / b_lat) * 100
                savings_str = f"{savings:>+5.1f}%"
            else:
                savings_str = "  N/A"

            a_str = f"{a_lat:>7.0f} ms" if a else "    N/A    "
            b_str = f"{b_lat:>7.0f} ms" if b else "    N/A    "

            lines.append(
                f"│  {level:<13}│ {a_str:<16} │ {b_str:<16} │ {savings_str:<8} │"
            )

        lines.append(
            "└───────────────┴──────────────────┴──────────────────┴──────────┘"
        )

        # Token efficiency comparison
        lines.append("")
        lines.append("Token Efficiency:")
        for level in ["simple", "moderate", "complex", "expert"]:
            a = adaptive.get(level, {})
            b = baseline.get(level, {})
            a_tps = a.get("avg_tps", 0)
            b_tps = b.get("avg_tps", 0)
            a_tok = a.get("avg_tokens", 0)
            b_tok = b.get("avg_tokens", 0)

            if a_tps > 0 or b_tps > 0:
                lines.append(
                    f"  {level:<12}: adaptive={a_tps:.1f} tok/s ({a_tok:.0f} tokens) │ "
                    f"baseline={b_tps:.1f} tok/s ({b_tok:.0f} tokens)"
                )

        return "\n".join(lines)

    def to_json(self, mode: str = "adaptive") -> str:
        """Export stats as JSON for programmatic consumption."""
        stats = self._store.get_stats_by_complexity(mode)
        return json.dumps(stats, indent=2)

    def recent_executions_table(self, limit: int = 10) -> str:
        """Format recent executions as a readable table."""
        records = self._store.get_recent(limit)

        if not records:
            return "No recent executions."

        lines = [
            "Recent Executions:",
            f"{'#':<4} {'Complexity':<12} {'Type':<12} {'Latency':>10} {'Tok/s':>8} {'Tokens':>7} {'Mode':<10}",
            "─" * 68,
        ]

        for i, r in enumerate(records, 1):
            lines.append(
                f"{i:<4} {r['complexity_level']:<12} {r['task_type']:<12} "
                f"{r['latency_ms']:>8.0f}ms {r['tokens_per_second']:>7.1f} "
                f"{r['tokens_generated']:>7} {r['mode']:<10}"
            )

        return "\n".join(lines)
