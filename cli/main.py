"""
ARIA CLI — Command Line Interface

Professional CLI for interacting with the ARIA engine.
Supports interactive chat, single queries, benchmarking,
and system status display.
"""

from __future__ import annotations

import sys
import json
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich import box

console = Console()


# ─────────────────────────────────────────────
# Rich display helpers
# ─────────────────────────────────────────────

BANNER = """
[bold cyan]
    █████╗  ██████╗  ██╗  █████╗ 
   ██╔══██╗ ██╔══██╗ ██║ ██╔══██╗
   ███████║ ██████╔╝ ██║ ███████║
   ██╔══██║ ██╔══██╗ ██║ ██╔══██║
   ██║  ██║ ██║  ██║ ██║ ██║  ██║
   ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝ ╚═╝  ╚═╝
[/bold cyan]
[dim]Adaptive Runtime Intelligence Architecture[/dim]
[dim]v0.2.0 — Dynamic Layer Execution • Multi-Model Cascade • Self-Speculative Decoding[/dim]
"""

TIER_COLORS = {
    "simple": "green",
    "moderate": "yellow",
    "complex": "red",
    "expert": "magenta",
}

TIER_ICONS = {
    "simple": "⚡",
    "moderate": "🔄",
    "complex": "🧠",
    "expert": "🔬",
}


def display_result(result, verbose: bool = False) -> None:
    """Display an ARIA execution result with rich formatting."""
    level = result.query_profile.complexity_level.value
    color = TIER_COLORS.get(level, "white")
    icon = TIER_ICONS.get(level, "")

    # Strategy info with adaptive execution details
    m = result.metrics
    mode_label = m.execution_mode.upper() if m.execution_mode else "STANDARD"
    
    adaptive_detail = ""
    if m.execution_mode == "dynamic_layers" and m.total_layers > 0:
        adaptive_detail = f" │ 🔧 {m.layers_used}/{m.total_layers} layers ({m.layer_skip_ratio:.0%} skipped)"
    elif m.execution_mode == "cascade" and m.model_used:
        adaptive_detail = f" │ 🔀 {m.model_used} model"

    strategy_info = (
        f"{icon} [{color}]{level.upper()}[/{color}] │ "
        f"{mode_label}{adaptive_detail} │ "
        f"source={result.strategy.source}"
    )

    # Metrics info
    metrics_info = (
        f"⏱ {m.latency_ms:.0f}ms │ "
        f"📊 {m.tokens_per_second:.1f} tok/s │ "
        f"📝 {m.tokens_generated} tokens │ "
        f"💾 Δ{m.memory_delta_mb:+.1f}MB"
    )

    # Fallback info
    if result.fallback_triggered:
        fallback_text = f"\n[yellow]⚠ Fallback: {result.fallback_reason}[/yellow]"
    else:
        fallback_text = ""

    # Build panel
    panel_content = f"{result.response}"

    console.print(Panel(
        panel_content,
        title=strategy_info,
        subtitle=metrics_info,
        border_style=color,
        padding=(1, 2),
    ))

    if fallback_text:
        console.print(fallback_text)

    if verbose:
        console.print(f"\n[dim]Task Type: {result.query_profile.task_type.value}[/dim]")
        console.print(f"[dim]Complexity Score: {result.query_profile.complexity_score:.3f}[/dim]")
        console.print(f"[dim]Confidence: {result.query_profile.confidence:.3f}[/dim]")
        console.print(f"[dim]Memory Tier: {result.hardware_state.memory_tier.value}[/dim]")
        console.print(f"[dim]TTFT: {m.time_to_first_token_ms:.0f}ms[/dim]")
        console.print(f"[dim]Analyzer: {m.analyzer_latency_ms:.2f}ms, Planner: {m.planner_latency_ms:.2f}ms[/dim]")
        console.print(f"[dim]Execution Mode: {m.execution_mode}[/dim]")
        if m.total_layers > 0:
            console.print(f"[dim]Layers: {m.layers_used}/{m.total_layers} ({m.layer_skip_ratio:.0%} skipped)[/dim]")
        if m.model_used:
            console.print(f"[dim]Model Used: {m.model_used}[/dim]")


# ─────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────

@click.group()
@click.version_option(version="0.1.0", prog_name="ARIA")
def cli():
    """ARIA — Adaptive Runtime Intelligence Architecture"""
    pass


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed metrics")
@click.option(
    "--execution-mode", "-e",
    default="dynamic_layers",
    type=click.Choice(["dynamic_layers", "cascade", "standard"]),
    help="Execution mode: dynamic_layers (skip layers), cascade (multi-model), standard (baseline)",
)
def chat(verbose: bool, execution_mode: str):
    """Start an interactive chat session with ARIA."""
    console.print(BANNER)
    console.print(f"[dim]Loading model (mode: {execution_mode})... this may take a moment on first run.[/dim]\n")

    from aria.engine import ARIAEngine
    engine = ARIAEngine(execution_mode=execution_mode)

    try:
        engine.initialize()
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/red]")
        console.print("[dim]Make sure mlx-lm is installed: pip install mlx-lm[/dim]")
        return

    console.print("[green]✓ ARIA ready![/green]")
    console.print(engine.memory.format_status())
    console.print("\n[dim]Type your query (or 'quit' to exit, 'status' for system info)[/dim]\n")

    while True:
        try:
            query = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Shutting down ARIA...[/dim]")
                break

            if query.lower() == "status":
                status = engine.get_status()
                console.print_json(json.dumps(status, indent=2, default=str))
                continue

            if query.lower() == "stats":
                console.print(engine.reporter.summary_report())
                continue

            if query.lower() == "recent":
                console.print(engine.reporter.recent_executions_table())
                continue

            if query.lower() == "memory":
                console.print(engine.memory.format_status())
                continue

            # Process query
            result = engine.process(query)
            console.print()
            display_result(result, verbose=verbose)
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Shutting down...[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    engine.shutdown()
    console.print("[dim]Goodbye! 👋[/dim]")


@cli.command()
@click.argument("query")
@click.option("--mode", "-m", default="adaptive", type=click.Choice(["adaptive", "baseline"]))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed metrics")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.option(
    "--execution-mode", "-e",
    default="dynamic_layers",
    type=click.Choice(["dynamic_layers", "cascade", "standard"]),
)
def ask(query: str, mode: str, verbose: bool, json_output: bool, execution_mode: str):
    """Process a single query through ARIA."""
    from aria.engine import ARIAEngine

    engine = ARIAEngine(execution_mode=execution_mode)

    try:
        result = engine.process(query, mode=mode)

        if json_output:
            console.print_json(json.dumps(result.to_dict(), indent=2))
        else:
            console.print()
            display_result(result, verbose=verbose)
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        engine.shutdown()


@cli.command()
@click.option("--queries", "-n", default=10, help="Number of queries per complexity level")
@click.option("--verbose", "-v", is_flag=True, help="Show individual results")
def benchmark(queries: int, verbose: bool):
    """Run benchmarks comparing adaptive vs baseline execution."""
    console.print(BANNER)
    console.print("[bold]Running ARIA Benchmark Suite[/bold]\n")

    from aria.engine import ARIAEngine
    from benchmarks.datasets import get_benchmark_queries
    from benchmarks.runner import BenchmarkRunner

    engine = ARIAEngine()

    try:
        engine.initialize()

        runner = BenchmarkRunner(engine)
        runner.run(queries_per_level=queries, verbose=verbose)

        # Display comparison
        console.print(engine.reporter.comparison_report())
        console.print(engine.reporter.summary_report())

    except Exception as e:
        console.print(f"[red]Benchmark error: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        engine.shutdown()


@cli.command()
def status():
    """Show ARIA system status and resource usage."""
    console.print(BANNER)

    from aria.memory.monitor import MemoryMonitor
    from aria.monitor.store import MetricsStore
    from aria.monitor.reporter import MetricsReporter
    from aria.config import get_config

    config = get_config()
    memory = MemoryMonitor(config)
    store = MetricsStore(config)
    reporter = MetricsReporter(store)

    console.print(f"[bold]Model:[/bold] {config.model.name}")
    console.print(f"[bold]Memory:[/bold] {memory.format_status()}")
    console.print(f"[bold]Metrics DB:[/bold] {config.metrics_db_path}")
    console.print(f"[bold]Total Executions:[/bold] {store.get_total_count()}")
    console.print()
    console.print(reporter.summary_report())

    store.close()


@cli.command()
@click.argument("query")
def analyze(query: str):
    """Analyze a query without running inference (for testing the classifier)."""
    from aria.analyzer.classifier import QueryClassifier

    classifier = QueryClassifier()
    profile = classifier.classify(query)

    level = profile.complexity_level.value
    color = TIER_COLORS.get(level, "white")
    icon = TIER_ICONS.get(level, "")

    console.print(f"\n[bold]Query:[/bold] {query}")
    console.print(f"[bold]Complexity:[/bold] {icon} [{color}]{level.upper()}[/{color}] (score={profile.complexity_score:.3f})")
    console.print(f"[bold]Task Type:[/bold] {profile.task_type.value}")
    console.print(f"[bold]Confidence:[/bold] {profile.confidence:.3f}")
    console.print(f"[bold]Est. Output Tokens:[/bold] {profile.estimated_output_tokens}")
    console.print(f"\n[dim]Features:[/dim]")
    for k, v in profile.features.items():
        console.print(f"  [dim]{k}: {v}[/dim]")
    console.print(f"\n[dim]Classifier latency: {classifier.avg_latency_ms:.3f}ms[/dim]")


if __name__ == "__main__":
    cli()
