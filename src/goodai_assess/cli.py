"""Command-line interface for Good AI Assessment Engine.

Provides the `goodai-assess` CLI command with JSON and Rich output options.
"""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError
from rich.console import Console

from goodai_assess.exceptions import (
    FileNotFoundError as AssessmentFileNotFoundError,
    InvalidJSONError,
    SchemaValidationError,
)
from goodai_assess.schema import CompanyAssessment
from goodai_assess.scoring import ScoringEngine
from goodai_assess.report import render_pretty_report, result_to_json


# Exit codes
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_FILE_ERROR = 2

app = typer.Typer(
    name="goodai-assess",
    help="Good AI Enterprise AI Readiness Assessment Engine",
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from goodai_assess import __version__
        console = Console()
        console.print(f"goodai-assess version {__version__}")
        raise typer.Exit()


@app.command()
def assess(
    filepath: Annotated[
        Path,
        typer.Argument(
            help="Path to JSON file containing company assessment data",
            exists=False,  # We handle file existence ourselves for better error messages
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output results as JSON (machine-readable)",
        ),
    ] = False,
    pretty: Annotated[
        bool,
        typer.Option(
            "--pretty",
            "-p",
            help="Output results with Rich formatting (default)",
        ),
    ] = True,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """Assess enterprise AI readiness from a JSON input file.

    The input file must contain a valid CompanyAssessment JSON object.
    See documentation for the required schema.

    Examples:
        goodai-assess data/company.json
        goodai-assess data/company.json --json
        goodai-assess data/company.json --pretty
    """
    console = Console(stderr=True)
    output_console = Console()

    try:
        # Load and validate input file
        assessment = _load_assessment(filepath)

        # Calculate scores
        engine = ScoringEngine()
        result = engine.calculate(assessment)

        # Output results
        if json_output:
            # Use plain print for JSON to avoid Rich formatting/wrapping
            print(result_to_json(result))
        else:
            render_pretty_report(result, output_console)

        raise typer.Exit(EXIT_SUCCESS)

    except AssessmentFileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e.message}")
        console.print()
        console.print("[dim]Usage: goodai-assess <path_to_json>[/dim]")
        console.print("[dim]Example: goodai-assess data/company.json[/dim]")
        raise typer.Exit(EXIT_FILE_ERROR)

    except InvalidJSONError as e:
        console.print(f"[bold red]Error:[/bold red] {e.message}")
        if e.line is not None:
            console.print(f"[dim]Check the JSON syntax at line {e.line}[/dim]")
        raise typer.Exit(EXIT_FILE_ERROR)

    except SchemaValidationError as e:
        console.print("[bold red]Error:[/bold red] Invalid assessment data")
        console.print()
        for error in e.errors:
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Unknown error")
            console.print(f"  [red]•[/red] {loc}: {msg}")
        console.print()
        console.print("[dim]See documentation for required schema fields[/dim]")
        raise typer.Exit(EXIT_VALIDATION_ERROR)


def _load_assessment(filepath: Path) -> CompanyAssessment:
    """Load and validate assessment from JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Validated CompanyAssessment object.

    Raises:
        AssessmentFileNotFoundError: If file doesn't exist.
        InvalidJSONError: If file contains invalid JSON.
        SchemaValidationError: If data fails schema validation.
    """
    # Check file exists
    if not filepath.exists():
        raise AssessmentFileNotFoundError(str(filepath))

    # Read file content
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        raise AssessmentFileNotFoundError(str(filepath)) from e

    # Parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise InvalidJSONError(
            filepath=str(filepath),
            parse_error=e.msg,
            line=e.lineno,
            column=e.colno,
        ) from e

    # Validate schema
    try:
        return CompanyAssessment.model_validate(data)
    except ValidationError as e:
        raise SchemaValidationError(e.errors()) from e


if __name__ == "__main__":
    app()
