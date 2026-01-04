"""Output formatting and report generation.

Provides Rich terminal output and JSON serialization for assessment results.
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from goodai_assess.scoring import AssessmentResult, CategoryScore, Tier


def result_to_dict(result: AssessmentResult) -> dict[str, Any]:
    """Convert assessment result to dictionary for JSON serialization.

    Args:
        result: The assessment result to convert.

    Returns:
        Dictionary representation suitable for JSON output.
    """
    return {
        "company_name": result.company_name,
        "industry": result.industry,
        "overall_score": result.overall_score,
        "tier": result.tier.value,
        "category_scores": [
            {
                "category": cs.category.value,
                "raw_score": cs.raw_score,
                "weight": cs.weight,
                "weighted_contribution": cs.weighted_contribution,
                "capped": cs.capped,
                "cap_reason": cs.cap_reason,
            }
            for cs in result.category_scores
        ],
        "risk_flags": [
            {
                "severity": rf.severity,
                "category": rf.category,
                "message": rf.message,
            }
            for rf in result.risk_flags
        ],
        "critical_gaps": result.critical_gaps,
        "recommendations": [
            {
                "priority": rec.priority,
                "category": rec.category,
                "action": rec.action,
                "rationale": rec.rationale,
            }
            for rec in result.recommendations
        ],
    }


def result_to_json(result: AssessmentResult, indent: int = 2) -> str:
    """Convert assessment result to JSON string.

    Args:
        result: The assessment result to convert.
        indent: JSON indentation level.

    Returns:
        JSON string representation.
    """
    return json.dumps(result_to_dict(result), indent=indent)


def get_tier_color(tier: Tier) -> str:
    """Get the display color for a tier.

    Args:
        tier: The tier to get color for.

    Returns:
        Rich color name.
    """
    colors = {
        Tier.EMERGING: "red",
        Tier.PILOT: "yellow",
        Tier.BUILD: "blue",
        Tier.SCALE: "green",
        Tier.LEAD: "bright_green",
    }
    return colors.get(tier, "white")


def get_score_color(score: float) -> str:
    """Get the display color for a score (0-5 scale).

    Args:
        score: The score to get color for.

    Returns:
        Rich color name.
    """
    if score >= 4.0:
        return "green"
    elif score >= 3.0:
        return "blue"
    elif score >= 2.0:
        return "yellow"
    else:
        return "red"


def create_score_bar(score: float, max_score: float = 5.0, width: int = 20) -> Text:
    """Create a visual score bar.

    Args:
        score: The current score.
        max_score: Maximum possible score.
        width: Width of the bar in characters.

    Returns:
        Rich Text object with colored bar.
    """
    filled = int((score / max_score) * width)
    empty = width - filled

    color = get_score_color(score)
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append(f" {score:.1f}/{max_score:.0f}", style="bold " + color)

    return bar


def render_pretty_report(result: AssessmentResult, console: Console | None = None) -> None:
    """Render a formatted Rich report to the console.

    Args:
        result: The assessment result to render.
        console: Optional Rich console (defaults to new Console).
    """
    if console is None:
        console = Console()

    # Header
    console.print()
    header_text = Text()
    header_text.append("Good AI ", style="bold bright_blue")
    header_text.append("Enterprise AI Readiness Assessment", style="bold white")
    console.print(Panel(header_text, box=box.DOUBLE, padding=(0, 2)))

    # Company info
    console.print()
    console.print(f"  [bold]Company:[/bold] {result.company_name}")
    console.print(f"  [bold]Industry:[/bold] {result.industry}")
    console.print()

    # Overall score
    tier_color = get_tier_color(result.tier)
    score_text = Text()
    score_text.append("Overall Score: ", style="bold")
    score_text.append(f"{result.overall_score:.1f}", style=f"bold {tier_color}")
    score_text.append("/100  |  Tier: ", style="bold")
    score_text.append(result.tier.value, style=f"bold {tier_color}")

    console.print(Panel(score_text, title="Assessment Result", box=box.ROUNDED))
    console.print()

    # Category breakdown
    category_table = Table(
        title="Category Breakdown",
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
    )
    category_table.add_column("Category", style="bold", width=18)
    category_table.add_column("Score", width=30)
    category_table.add_column("Weight", justify="center", width=8)
    category_table.add_column("Contribution", justify="right", width=12)
    category_table.add_column("Status", width=20)

    for cs in result.category_scores:
        status = ""
        if cs.capped:
            status = f"[yellow]Capped[/yellow]"
        elif cs.raw_score < 3.0:
            status = "[red]Critical Gap[/red]"
        elif cs.raw_score >= 4.5:
            status = "[green]Strong[/green]"

        category_table.add_row(
            cs.category.value,
            create_score_bar(cs.raw_score),
            f"{cs.weight:.0%}",
            f"{cs.weighted_contribution:.1f}",
            status,
        )

    console.print(category_table)
    console.print()

    # Critical gaps
    if result.critical_gaps:
        gaps_panel = Panel(
            "\n".join(f"  [red]•[/red] {gap}" for gap in result.critical_gaps),
            title="[bold red]Critical Gaps (Score < 3.0)[/bold red]",
            box=box.ROUNDED,
            border_style="red",
        )
        console.print(gaps_panel)
        console.print()

    # Risk flags
    if result.risk_flags:
        risk_lines = []
        for risk in result.risk_flags:
            severity_style = {
                "High": "bold red",
                "Medium": "yellow",
                "Low": "dim",
            }.get(risk.severity, "white")
            risk_lines.append(
                f"  [{severity_style}][{risk.severity}][/{severity_style}] "
                f"[bold]{risk.category}:[/bold] {risk.message}"
            )

        risks_panel = Panel(
            "\n".join(risk_lines),
            title="[bold yellow]Risk Flags[/bold yellow]",
            box=box.ROUNDED,
            border_style="yellow",
        )
        console.print(risks_panel)
        console.print()

    # Recommendations
    if result.recommendations:
        rec_table = Table(
            title="Top Recommendations",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold cyan",
        )
        rec_table.add_column("#", justify="center", width=3)
        rec_table.add_column("Category", width=16)
        rec_table.add_column("Action", width=50)

        for rec in result.recommendations:
            rec_table.add_row(
                str(rec.priority),
                rec.category,
                rec.action,
            )

        console.print(rec_table)
        console.print()

    # Footer
    footer = Text()
    footer.append("Assessment generated by ", style="dim")
    footer.append("Good AI", style="bold bright_blue")
    footer.append(" | ", style="dim")
    footer.append("wearegoodai.com", style="dim underline")

    console.print(Panel(footer, box=box.SIMPLE, padding=(0, 2)))
    console.print()
