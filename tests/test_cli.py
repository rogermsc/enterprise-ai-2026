"""Tests for CLI functionality.

Verifies exit codes and JSON output format.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from goodai_assess.cli import app, EXIT_SUCCESS, EXIT_VALIDATION_ERROR, EXIT_FILE_ERROR


# Get project root for data file paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

runner = CliRunner()


class TestCLIExitCodes:
    """Tests for CLI exit codes."""

    def test_successful_run_exits_zero(self) -> None:
        """Successful assessment should exit with code 0."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "company_name": "Test Co",
                    "industry": "Tech",
                    "employee_count": 100,
                    "has_data_lake": True,
                    "has_data_governance_policy": True,
                    "has_ml_platform": True,
                    "has_monitoring": True,
                    "ai_team_size": 10,
                    "ai_projects_in_production": 5,
                    "executive_sponsor": True,
                },
                f,
            )
            f.flush()

            result = runner.invoke(app, [f.name])
            assert result.exit_code == EXIT_SUCCESS

            # Cleanup
            Path(f.name).unlink()

    def test_file_not_found_exits_two(self) -> None:
        """Missing file should exit with code 2."""
        result = runner.invoke(app, ["/nonexistent/path/file.json"])
        assert result.exit_code == EXIT_FILE_ERROR
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_invalid_json_exits_two(self) -> None:
        """Invalid JSON should exit with code 2."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json }")
            f.flush()

            result = runner.invoke(app, [f.name])
            assert result.exit_code == EXIT_FILE_ERROR

            # Cleanup
            Path(f.name).unlink()

    def test_schema_validation_error_exits_one(self) -> None:
        """Schema validation failure should exit with code 1."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            # Valid JSON but missing required fields
            json.dump({"company_name": "Test"}, f)
            f.flush()

            result = runner.invoke(app, [f.name])
            assert result.exit_code == EXIT_VALIDATION_ERROR

            # Cleanup
            Path(f.name).unlink()


class TestJSONOutput:
    """Tests for --json output format."""

    def test_json_output_is_valid(self) -> None:
        """--json output should be valid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "company_name": "Test Co",
                    "industry": "Tech",
                    "employee_count": 100,
                    "has_data_lake": True,
                    "has_data_governance_policy": True,
                    "has_ml_platform": True,
                    "has_monitoring": True,
                    "ai_team_size": 10,
                    "ai_projects_in_production": 5,
                    "executive_sponsor": True,
                },
                f,
            )
            f.flush()

            result = runner.invoke(app, [f.name, "--json"])
            assert result.exit_code == EXIT_SUCCESS

            # Should be valid JSON
            output_data = json.loads(result.output)
            assert isinstance(output_data, dict)

            # Cleanup
            Path(f.name).unlink()

    def test_json_output_structure(self) -> None:
        """--json output should have expected structure."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "company_name": "Test Co",
                    "industry": "Technology",
                    "employee_count": 100,
                    "has_data_lake": True,
                    "has_data_governance_policy": True,
                    "has_ml_platform": True,
                    "has_monitoring": True,
                    "ai_team_size": 10,
                    "ai_projects_in_production": 5,
                    "executive_sponsor": True,
                },
                f,
            )
            f.flush()

            result = runner.invoke(app, [f.name, "--json"])
            output_data = json.loads(result.output)

            # Verify required fields exist
            assert "company_name" in output_data
            assert "industry" in output_data
            assert "overall_score" in output_data
            assert "tier" in output_data
            assert "category_scores" in output_data
            assert "risk_flags" in output_data
            assert "critical_gaps" in output_data
            assert "recommendations" in output_data

            # Verify types
            assert isinstance(output_data["overall_score"], (int, float))
            assert isinstance(output_data["tier"], str)
            assert isinstance(output_data["category_scores"], list)
            assert isinstance(output_data["risk_flags"], list)
            assert isinstance(output_data["critical_gaps"], list)
            assert isinstance(output_data["recommendations"], list)

            # Cleanup
            Path(f.name).unlink()

    def test_json_output_category_scores_structure(self) -> None:
        """Category scores in JSON output should have correct structure."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "company_name": "Test Co",
                    "industry": "Tech",
                    "employee_count": 100,
                    "has_data_lake": True,
                    "has_data_governance_policy": True,
                    "has_ml_platform": True,
                    "has_monitoring": True,
                    "ai_team_size": 10,
                    "ai_projects_in_production": 5,
                    "executive_sponsor": True,
                },
                f,
            )
            f.flush()

            result = runner.invoke(app, [f.name, "--json"])
            output_data = json.loads(result.output)

            # Verify category scores structure
            assert len(output_data["category_scores"]) == 6

            for cs in output_data["category_scores"]:
                assert "category" in cs
                assert "raw_score" in cs
                assert "weight" in cs
                assert "weighted_contribution" in cs
                assert "capped" in cs

                # Verify value ranges
                assert 0 <= cs["raw_score"] <= 5
                assert 0 <= cs["weight"] <= 1
                assert isinstance(cs["capped"], bool)

            # Cleanup
            Path(f.name).unlink()


class TestCLIUsage:
    """Tests for CLI usage patterns."""

    def test_help_available(self) -> None:
        """--help should display usage information."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "assess" in result.output.lower() or "json" in result.output.lower()

    def test_version_available(self) -> None:
        """--version should display version information."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_no_args_shows_help(self) -> None:
        """No arguments should show help/usage."""
        result = runner.invoke(app, [])
        # Should either show help or error about missing argument
        assert result.exit_code in [0, 2]


class TestDataFiles:
    """Tests using actual data files."""

    def test_enterprise_mature_file(self) -> None:
        """enterprise_mature.json should produce high score."""
        filepath = str(DATA_DIR / "enterprise_mature.json")
        result = runner.invoke(app, [filepath, "--json"])

        assert result.exit_code == EXIT_SUCCESS
        output_data = json.loads(result.output)
        assert output_data["overall_score"] >= 80
        assert output_data["tier"] in ["Scale", "Lead"]

    def test_traditional_legacy_file(self) -> None:
        """traditional_legacy.json should produce mid-range score."""
        filepath = str(DATA_DIR / "traditional_legacy.json")
        result = runner.invoke(app, [filepath, "--json"])

        assert result.exit_code == EXIT_SUCCESS
        output_data = json.loads(result.output)
        assert 35 <= output_data["overall_score"] <= 60
        assert output_data["tier"] in ["Emerging", "Pilot"]

    def test_startup_emerging_file(self) -> None:
        """startup_emerging.json should produce low score."""
        filepath = str(DATA_DIR / "startup_emerging.json")
        result = runner.invoke(app, [filepath, "--json"])

        assert result.exit_code == EXIT_SUCCESS
        output_data = json.loads(result.output)
        assert output_data["overall_score"] < 40
        assert output_data["tier"] == "Emerging"
