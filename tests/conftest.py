"""Pytest fixtures for test suite."""

import pytest

from goodai_assess.schema import CompanyAssessment


@pytest.fixture
def mature_company() -> CompanyAssessment:
    """A mature enterprise with strong AI capabilities."""
    return CompanyAssessment(
        company_name="TechCorp Global",
        industry="Technology",
        employee_count=8500,
        annual_revenue_usd=2500000000,
        cloud_provider="AWS",
        cloud_monthly_spend_usd=450000,
        has_data_lake=True,
        has_data_governance_policy=True,
        has_ml_platform=True,
        has_monitoring=True,
        ai_team_size=85,
        ai_projects_in_production=12,
        executive_sponsor=True,
    )


@pytest.fixture
def legacy_company() -> CompanyAssessment:
    """A traditional company with limited AI maturity."""
    return CompanyAssessment(
        company_name="FastFreight Logistics",
        industry="Logistics & Transportation",
        employee_count=12000,
        annual_revenue_usd=850000000,
        cloud_provider="Azure",
        cloud_monthly_spend_usd=85000,
        has_data_lake=True,
        has_data_governance_policy=False,
        has_ml_platform=False,
        has_monitoring=False,
        ai_team_size=8,
        ai_projects_in_production=2,
        executive_sponsor=True,
    )


@pytest.fixture
def emerging_company() -> CompanyAssessment:
    """An early-stage company just starting AI journey."""
    return CompanyAssessment(
        company_name="DataStart AI",
        industry="FinTech",
        employee_count=45,
        annual_revenue_usd=2500000,
        cloud_provider="GCP",
        cloud_monthly_spend_usd=3500,
        has_data_lake=False,
        has_data_governance_policy=False,
        has_ml_platform=False,
        has_monitoring=False,
        ai_team_size=3,
        ai_projects_in_production=0,
        executive_sponsor=False,
    )


@pytest.fixture
def minimal_company() -> CompanyAssessment:
    """Minimal valid company for boundary testing."""
    return CompanyAssessment(
        company_name="MinimalCo",
        industry="Consulting",
        employee_count=10,
        has_data_lake=False,
        has_data_governance_policy=False,
        has_ml_platform=False,
        has_monitoring=False,
        ai_team_size=0,
        ai_projects_in_production=0,
        executive_sponsor=False,
    )


@pytest.fixture
def high_risk_company() -> CompanyAssessment:
    """Company with high-risk configuration for flag testing."""
    return CompanyAssessment(
        company_name="RiskyCorp",
        industry="Finance",
        employee_count=500,
        cloud_provider="AWS",
        cloud_monthly_spend_usd=50000,  # High spend
        has_data_lake=True,
        has_data_governance_policy=True,
        has_ml_platform=True,
        has_monitoring=False,  # No monitoring despite high spend
        ai_team_size=0,  # No team
        ai_projects_in_production=3,  # But has production projects
        executive_sponsor=False,
    )
