"""
ARIA Benchmark Runner

Runs adaptive vs baseline comparisons and classifier accuracy tests.
Produces detailed performance reports.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich import box

from benchmarks.datasets import get_benchmark_queries, BenchmarkQuery

logger = logging.getLogger("aria.benchmarks")
console = Console()


class BenchmarkRunner:
    """
    Runs comprehensive benchmarks comparing adaptive vs baseline execution.

    Workflow:
    1. Run each query in adaptive mode (ARIA decides the strategy)
    2. Run same queries in baseline mode (always EXPERT)
    3. Compare latency, memory, and throughput
    4. Report classifier accuracy vs expected labels
    """

    def __init__(self, engine):
        self.engine = engine

    def run(
        self,
        queries_per_level: int = 5,
        verbose: bool = False,
    ) -> dict:
        """
        Run the full benchmark suite.

        Args:
            queries_per_level: Max queries per complexity level.
            verbose: Print individual results.

        Returns:
            Dict with benchmark results.
        """
        queries = get_benchmark_queries()

        # Limit queries per level
        level_counts = {}
        filtered = []
        for q in queries:
            level = q.expected_complexity
            count = level_counts.get(level, 0)
            if count < queries_per_level:
                filtered.append(q)
                level_counts[level] = count + 1

        total = len(filtered) * 2  # adaptive + baseline
        results = {"adaptive": [], "baseline": [], "classifier": []}

        console.print(f"\n[bold]Running {len(filtered)} queries × 2 modes = {total} executions[/bold]\n")

        # Warm-up run
        console.print("[dim]Warm-up run...[/dim]")
        try:
            self.engine.process("Hello", mode="adaptive")
        except Exception:
            pass

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            # ── Adaptive Mode ──
            task = progress.add_task("Adaptive mode...", total=len(filtered))

            for bq in filtered:
                try:
                    result = self.engine.process(bq.query, mode="adaptive")
                    results["adaptive"].append({
                        "query": bq.query[:80],
                        "expected": bq.expected_complexity,
                        "actual": result.query_profile.complexity_level.value,
                        "latency_ms": result.metrics.latency_ms,
                        "tokens": result.metrics.tokens_generated,
                        "tps": result.metrics.tokens_per_second,
                        "memory_delta": result.metrics.memory_delta_mb,
                    })

                    # Track classifier accuracy
                    results["classifier"].append({
                        "query": bq.query[:80],
                        "expected": bq.expected_complexity,
                        "actual": result.query_profile.complexity_level.value,
                        "score": result.query_profile.complexity_score,
                        "confidence": result.query_profile.confidence,
                        "correct": result.query_profile.complexity_level.value == bq.expected_complexity,
                    })

                    if verbose:
                        status = "✓" if result.query_profile.complexity_level.value == bq.expected_complexity else "✗"
                        console.print(
                            f"  {status} [{bq.expected_complexity:<8}→{result.query_profile.complexity_level.value:<8}] "
                            f"{result.metrics.latency_ms:>6.0f}ms │ {bq.query[:50]}..."
                        )

                except Exception as e:
                    logger.error("Benchmark query failed: %s", e)
                    results["adaptive"].append({
                        "query": bq.query[:80],
                        "expected": bq.expected_complexity,
                        "error": str(e),
                    })

                progress.advance(task)

            # ── Baseline Mode ──
            task2 = progress.add_task("Baseline mode...", total=len(filtered))

            for bq in filtered:
                try:
                    result = self.engine.process(bq.query, mode="baseline")
                    results["baseline"].append({
                        "query": bq.query[:80],
                        "expected": bq.expected_complexity,
                        "latency_ms": result.metrics.latency_ms,
                        "tokens": result.metrics.tokens_generated,
                        "tps": result.metrics.tokens_per_second,
                        "memory_delta": result.metrics.memory_delta_mb,
                    })

                    if verbose:
                        console.print(
                            f"  [{bq.expected_complexity:<8}] "
                            f"{result.metrics.latency_ms:>6.0f}ms │ {bq.query[:50]}..."
                        )

                except Exception as e:
                    logger.error("Baseline query failed: %s", e)

                progress.advance(task2)

        # ── Report Results ──
        self._print_classifier_report(results["classifier"])
        self._print_performance_summary(results)

        return results

    def _print_classifier_report(self, classifier_results: list[dict]) -> None:
        """Print classifier accuracy report."""
        if not classifier_results:
            return

        correct = sum(1 for r in classifier_results if r.get("correct", False))
        total = len(classifier_results)
        accuracy = (correct / total * 100) if total > 0 else 0

        console.print(f"\n[bold]Classifier Accuracy: {correct}/{total} ({accuracy:.1f}%)[/bold]")

        # Accuracy per level
        levels = ["simple", "moderate", "complex", "expert"]
        table = Table(title="Per-Level Accuracy", box=box.ROUNDED)
        table.add_column("Level", style="cyan")
        table.add_column("Correct", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Accuracy", justify="right")

        for level in levels:
            level_results = [r for r in classifier_results if r["expected"] == level]
            level_correct = sum(1 for r in level_results if r.get("correct"))
            level_total = len(level_results)
            level_acc = (level_correct / level_total * 100) if level_total > 0 else 0

            table.add_row(
                level,
                str(level_correct),
                str(level_total),
                f"{level_acc:.0f}%",
            )

        console.print(table)

        # Show misclassifications
        misses = [r for r in classifier_results if not r.get("correct")]
        if misses:
            console.print(f"\n[yellow]Misclassifications ({len(misses)}):[/yellow]")
            for m in misses[:10]:
                console.print(
                    f"  Expected={m['expected']:<8} Got={m['actual']:<8} "
                    f"Score={m['score']:.3f} │ {m['query'][:60]}..."
                )

    def _print_performance_summary(self, results: dict) -> None:
        """Print performance comparison summary."""
        adaptive = results.get("adaptive", [])
        baseline = results.get("baseline", [])

        if not adaptive or not baseline:
            return

        # Group by expected complexity
        levels = ["simple", "moderate", "complex", "expert"]

        table = Table(
            title="\nPerformance: Adaptive vs Baseline",
            box=box.ROUNDED,
        )
        table.add_column("Level", style="cyan")
        table.add_column("Adaptive (ms)", justify="right")
        table.add_column("Baseline (ms)", justify="right")
        table.add_column("Speedup", justify="right")
        table.add_column("Adaptive Tok/s", justify="right")
        table.add_column("Baseline Tok/s", justify="right")

        for level in levels:
            a_results = [r for r in adaptive if r.get("expected") == level and "latency_ms" in r]
            b_results = [r for r in baseline if r.get("expected") == level and "latency_ms" in r]

            if not a_results or not b_results:
                continue

            a_lat = sum(r["latency_ms"] for r in a_results) / len(a_results)
            b_lat = sum(r["latency_ms"] for r in b_results) / len(b_results)
            a_tps = sum(r.get("tps", 0) for r in a_results) / len(a_results)
            b_tps = sum(r.get("tps", 0) for r in b_results) / len(b_results)

            speedup = ((b_lat - a_lat) / b_lat * 100) if b_lat > 0 else 0
            speedup_style = "green" if speedup > 0 else "red"

            table.add_row(
                level,
                f"{a_lat:.0f}",
                f"{b_lat:.0f}",
                f"[{speedup_style}]{speedup:+.1f}%[/{speedup_style}]",
                f"{a_tps:.1f}",
                f"{b_tps:.1f}",
            )

        console.print(table)
