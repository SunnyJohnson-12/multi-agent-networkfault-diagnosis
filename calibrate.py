#!/usr/bin/env python3
"""CLI utility to evaluate and calibrate diagnostic confidence against ground truth Monte Carlo variants."""

import sys
import os
import argparse
import asyncio

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from app.services.calibration import CalibrationEngine, CALIBRATION_JSON, CALIBRATION_MD


async def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Network Diagnostic Calibration Engine")
    parser.add_argument("--runs", type=int, default=120, help="Total number of randomized Monte Carlo runs (default: 120)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    args = parser.parse_args()

    console = Console()
    console.print(
        Panel.fit(
            f"[bold cyan]Multi-Agent Network Fault Diagnosis — Calibration Engine[/bold cyan]\n"
            f"[dim]Running {args.runs} randomized Monte Carlo evaluations across all fault classes (Seed: {args.seed})...[/dim]",
            border_style="cyan",
        )
    )

    with console.status("[bold green]Executing multi-agent evaluation pipeline...[/bold green]", spinner="dots"):
        report = await CalibrationEngine.run_calibration(num_runs=args.runs, seed=args.seed)

    # 1. Headline Results
    console.print()
    console.print(
        Panel(
            f"[bold white]{report.headline}[/bold white]\n\n"
            f"• [green]Overall Accuracy:[/green] [bold]{report.overall_accuracy * 100:.1f}%[/bold]\n"
            f"• [cyan]Expected Calibration Error (ECE):[/cyan] [bold]{report.expected_calibration_error:.4f}[/bold]\n"
            f"• [green]Mean Conf on Correct Answers:[/green] {report.mean_confidence_correct * 100:.1f}%\n"
            f"• [yellow]Mean Conf on Wrong Answers:[/yellow] {report.mean_confidence_incorrect * 100:.1f}%\n"
            f"• [magenta]Abstain / Ambiguity Catch Rate:[/magenta] {report.abstain_rate * 100:.1f}%",
            title="🎯 Reliability & Calibration Summary",
            border_style="green",
        )
    )

    # 2. Per-Class Accuracy Table
    class_table = Table(title="Per-Class Ground Truth Accuracy", border_style="blue")
    class_table.add_column("Fault Class", style="cyan")
    class_table.add_column("Accuracy", justify="right", style="green")

    for cls_name, acc in report.per_class_accuracy.items():
        class_table.add_row(cls_name, f"{acc * 100:.1f}%")
    console.print(class_table)

    # 3. Reliability Diagram Table
    rel_table = Table(title="Reliability Diagram (10 Confidence Bins)", border_style="cyan")
    rel_table.add_column("Bin Range", justify="center")
    rel_table.add_column("Samples", justify="right")
    rel_table.add_column("Mean Conf", justify="right", style="yellow")
    rel_table.add_column("Empirical Acc", justify="right", style="green")
    rel_table.add_column("|Gap|", justify="right", style="red")

    for b in report.reliability_diagram:
        gap = abs(b.empirical_accuracy - b.mean_confidence) if b.sample_count > 0 else 0.0
        rel_table.add_row(
            b.bin_range,
            str(b.sample_count),
            f"{b.mean_confidence:.2f}",
            f"{b.empirical_accuracy:.2f}",
            f"{gap:.2f}",
        )
    console.print(rel_table)

    console.print(f"[dim]Reports saved to: {CALIBRATION_JSON} and {CALIBRATION_MD}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
