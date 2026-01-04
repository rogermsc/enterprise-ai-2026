"""Pydantic models for input validation.

Defines the CompanyAssessment schema used for enterprise AI readiness assessment.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CompanyAssessment(BaseModel):
    """Input schema for company AI readiness assessment.

    This model validates and structures the input data required for
    calculating an enterprise AI readiness score.
    """

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the company being assessed",
    )
    industry: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Industry sector of the company",
    )
    employee_count: int = Field(
        ...,
        ge=1,
        description="Total number of employees",
    )
    annual_revenue_usd: Optional[int] = Field(
        default=None,
        ge=0,
        description="Annual revenue in USD (optional)",
    )
    cloud_provider: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary cloud provider (e.g., AWS, Azure, GCP)",
    )
    cloud_monthly_spend_usd: Optional[int] = Field(
        default=None,
        ge=0,
        description="Monthly cloud spend in USD (optional)",
    )
    has_data_lake: bool = Field(
        ...,
        description="Whether the company has a centralized data lake",
    )
    has_data_governance_policy: bool = Field(
        ...,
        description="Whether the company has a formal data governance policy",
    )
    has_ml_platform: bool = Field(
        ...,
        description="Whether the company has an ML platform (e.g., MLflow, SageMaker)",
    )
    has_monitoring: bool = Field(
        ...,
        description="Whether the company has production monitoring for AI systems",
    )
    ai_team_size: int = Field(
        ...,
        ge=0,
        description="Number of dedicated AI/ML team members",
    )
    ai_projects_in_production: int = Field(
        ...,
        ge=0,
        description="Number of AI projects currently in production",
    )
    executive_sponsor: bool = Field(
        ...,
        description="Whether there is an executive sponsor for AI initiatives",
    )

    @field_validator("cloud_provider")
    @classmethod
    def normalize_cloud_provider(cls, v: Optional[str]) -> Optional[str]:
        """Normalize cloud provider names to standard format."""
        if v is None:
            return None
        # Normalize common variations
        normalized = v.strip().upper()
        provider_map = {
            "AWS": "AWS",
            "AMAZON": "AWS",
            "AMAZON WEB SERVICES": "AWS",
            "AZURE": "AZURE",
            "MICROSOFT": "AZURE",
            "MICROSOFT AZURE": "AZURE",
            "GCP": "GCP",
            "GOOGLE": "GCP",
            "GOOGLE CLOUD": "GCP",
            "GOOGLE CLOUD PLATFORM": "GCP",
        }
        return provider_map.get(normalized, v.strip())

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "company_name": "TechCorp Inc",
                    "industry": "Technology",
                    "employee_count": 5000,
                    "annual_revenue_usd": 500000000,
                    "cloud_provider": "AWS",
                    "cloud_monthly_spend_usd": 150000,
                    "has_data_lake": True,
                    "has_data_governance_policy": True,
                    "has_ml_platform": True,
                    "has_monitoring": True,
                    "ai_team_size": 45,
                    "ai_projects_in_production": 8,
                    "executive_sponsor": True,
                }
            ]
        }
    }
