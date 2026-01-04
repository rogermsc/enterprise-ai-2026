"""Tests for schema validation.

Verifies Pydantic model validation for missing and invalid fields.
"""

import pytest
from pydantic import ValidationError

from goodai_assess.schema import CompanyAssessment


class TestRequiredFields:
    """Tests for required field validation."""

    def test_valid_minimal_input(self) -> None:
        """Minimal valid input should pass validation."""
        assessment = CompanyAssessment(
            company_name="Test Co",
            industry="Tech",
            employee_count=10,
            has_data_lake=False,
            has_data_governance_policy=False,
            has_ml_platform=False,
            has_monitoring=False,
            ai_team_size=0,
            ai_projects_in_production=0,
            executive_sponsor=False,
        )
        assert assessment.company_name == "Test Co"

    def test_missing_company_name(self) -> None:
        """Missing company_name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                # company_name missing
                industry="Tech",
                employee_count=10,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("company_name",) for e in errors)

    def test_missing_industry(self) -> None:
        """Missing industry should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                # industry missing
                employee_count=10,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("industry",) for e in errors)

    def test_missing_employee_count(self) -> None:
        """Missing employee_count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                # employee_count missing
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("employee_count",) for e in errors)

    def test_missing_boolean_fields(self) -> None:
        """Missing boolean fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=10,
                # All boolean fields missing
                ai_team_size=0,
                ai_projects_in_production=0,
            )

        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}

        assert "has_data_lake" in missing_fields
        assert "has_data_governance_policy" in missing_fields
        assert "has_ml_platform" in missing_fields
        assert "has_monitoring" in missing_fields
        assert "executive_sponsor" in missing_fields


class TestFieldConstraints:
    """Tests for field constraint validation."""

    def test_empty_company_name(self) -> None:
        """Empty company_name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="",  # Empty
                industry="Tech",
                employee_count=10,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("company_name",) for e in errors)

    def test_zero_employee_count(self) -> None:
        """Zero employee_count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=0,  # Invalid: must be >= 1
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("employee_count",) for e in errors)

    def test_negative_employee_count(self) -> None:
        """Negative employee_count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=-100,  # Negative
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("employee_count",) for e in errors)

    def test_negative_ai_team_size(self) -> None:
        """Negative ai_team_size should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=-5,  # Negative
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ai_team_size",) for e in errors)

    def test_negative_revenue(self) -> None:
        """Negative annual_revenue_usd should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                annual_revenue_usd=-1000000,  # Negative
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("annual_revenue_usd",) for e in errors)


class TestOptionalFields:
    """Tests for optional field handling."""

    def test_optional_fields_default_none(self) -> None:
        """Optional fields should default to None."""
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            has_data_lake=False,
            has_data_governance_policy=False,
            has_ml_platform=False,
            has_monitoring=False,
            ai_team_size=0,
            ai_projects_in_production=0,
            executive_sponsor=False,
        )

        assert assessment.annual_revenue_usd is None
        assert assessment.cloud_provider is None
        assert assessment.cloud_monthly_spend_usd is None

    def test_optional_fields_with_values(self) -> None:
        """Optional fields should accept valid values."""
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            annual_revenue_usd=5000000,
            cloud_provider="AWS",
            cloud_monthly_spend_usd=10000,
            has_data_lake=True,
            has_data_governance_policy=True,
            has_ml_platform=True,
            has_monitoring=True,
            ai_team_size=5,
            ai_projects_in_production=2,
            executive_sponsor=True,
        )

        assert assessment.annual_revenue_usd == 5000000
        assert assessment.cloud_provider == "AWS"
        assert assessment.cloud_monthly_spend_usd == 10000


class TestCloudProviderNormalization:
    """Tests for cloud provider name normalization."""

    def test_aws_variations(self) -> None:
        """AWS variations should be normalized."""
        for name in ["aws", "AWS", "Amazon", "Amazon Web Services"]:
            assessment = CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                cloud_provider=name,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )
            assert assessment.cloud_provider == "AWS"

    def test_azure_variations(self) -> None:
        """Azure variations should be normalized."""
        for name in ["azure", "Azure", "Microsoft", "Microsoft Azure"]:
            assessment = CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                cloud_provider=name,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )
            assert assessment.cloud_provider == "AZURE"

    def test_gcp_variations(self) -> None:
        """GCP variations should be normalized."""
        for name in ["gcp", "GCP", "Google", "Google Cloud", "Google Cloud Platform"]:
            assessment = CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                cloud_provider=name,
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )
            assert assessment.cloud_provider == "GCP"

    def test_unknown_provider_preserved(self) -> None:
        """Unknown providers should be preserved (stripped)."""
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            cloud_provider="  DigitalOcean  ",
            has_data_lake=False,
            has_data_governance_policy=False,
            has_ml_platform=False,
            has_monitoring=False,
            ai_team_size=0,
            ai_projects_in_production=0,
            executive_sponsor=False,
        )
        assert assessment.cloud_provider == "DigitalOcean"


class TestTypeValidation:
    """Tests for type validation."""

    def test_string_for_integer_field(self) -> None:
        """String value for integer field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count="not a number",  # Invalid type
                has_data_lake=False,
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("employee_count",) for e in errors)

    def test_string_for_boolean_field(self) -> None:
        """Non-boolean string for boolean field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyAssessment(
                company_name="Test",
                industry="Tech",
                employee_count=100,
                has_data_lake="maybe",  # Invalid type
                has_data_governance_policy=False,
                has_ml_platform=False,
                has_monitoring=False,
                ai_team_size=0,
                ai_projects_in_production=0,
                executive_sponsor=False,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("has_data_lake",) for e in errors)
