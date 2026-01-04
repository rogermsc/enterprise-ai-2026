"""Deterministic scoring engine for AI readiness assessment.

Implements transparent, auditable scoring rules with weighted categories.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from goodai_assess.schema import CompanyAssessment


class Tier(str, Enum):
    """AI readiness tiers based on overall score."""

    EMERGING = "Emerging"  # 0-39
    PILOT = "Pilot"  # 40-59
    BUILD = "Build"  # 60-74
    SCALE = "Scale"  # 75-89
    LEAD = "Lead"  # 90-100

    @classmethod
    def from_score(cls, score: float) -> "Tier":
        """Determine tier from overall score.

        Args:
            score: Overall score from 0-100.

        Returns:
            The corresponding tier.
        """
        if score < 40:
            return cls.EMERGING
        elif score < 60:
            return cls.PILOT
        elif score < 75:
            return cls.BUILD
        elif score < 90:
            return cls.SCALE
        else:
            return cls.LEAD


class Category(str, Enum):
    """Assessment categories with their weights."""

    STRATEGY = "Strategy"
    DATA_FOUNDATION = "Data Foundation"
    INFRASTRUCTURE = "Infrastructure"
    GOVERNANCE = "Governance"
    DELIVERY = "Delivery"
    ADOPTION = "Adoption"


# Category weights (must sum to 1.0)
CATEGORY_WEIGHTS: dict[Category, float] = {
    Category.STRATEGY: 0.20,
    Category.DATA_FOUNDATION: 0.25,
    Category.INFRASTRUCTURE: 0.20,
    Category.GOVERNANCE: 0.15,
    Category.DELIVERY: 0.10,
    Category.ADOPTION: 0.10,
}


@dataclass
class CategoryScore:
    """Score for a single category."""

    category: Category
    raw_score: float  # 0-5 scale
    weight: float
    weighted_contribution: float  # Contribution to overall score
    capped: bool = False  # Whether score was capped due to a rule
    cap_reason: Optional[str] = None


@dataclass
class RiskFlag:
    """A risk flag identified during assessment."""

    severity: str  # "High", "Medium", "Low"
    category: str
    message: str


@dataclass
class Recommendation:
    """A recommendation based on assessment results."""

    priority: int  # 1-5, where 1 is highest
    category: str
    action: str
    rationale: str


@dataclass
class AssessmentResult:
    """Complete assessment result with all scores and analysis."""

    company_name: str
    industry: str
    overall_score: float  # 0-100
    tier: Tier
    category_scores: list[CategoryScore]
    risk_flags: list[RiskFlag] = field(default_factory=list)
    critical_gaps: list[str] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)


class ScoringEngine:
    """Deterministic scoring engine for AI readiness assessment.

    All scoring rules are transparent and auditable. Same input will
    always produce the same output.
    """

    # Thresholds
    HIGH_CLOUD_SPEND_THRESHOLD = 10000  # $10k/month
    LARGE_TEAM_THRESHOLD = 10  # AI team members
    PRODUCTION_PROJECTS_BOOST_THRESHOLD = 3

    def __init__(self) -> None:
        """Initialize the scoring engine."""
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validate that category weights sum to 1.0."""
        total = sum(CATEGORY_WEIGHTS.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Category weights must sum to 1.0, got {total}")

    def calculate(self, assessment: CompanyAssessment) -> AssessmentResult:
        """Calculate the complete assessment result.

        Args:
            assessment: Validated company assessment input.

        Returns:
            Complete assessment result with scores, flags, and recommendations.
        """
        # Calculate all category scores
        category_scores = self._calculate_all_categories(assessment)

        # Calculate overall score (weighted average, scaled to 0-100)
        overall_score = sum(cs.weighted_contribution for cs in category_scores)

        # Determine tier
        tier = Tier.from_score(overall_score)

        # Identify risk flags
        risk_flags = self._identify_risks(assessment, category_scores)

        # Identify critical gaps (categories scoring < 3.0)
        critical_gaps = [
            cs.category.value
            for cs in category_scores
            if cs.raw_score < 3.0
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            assessment, category_scores, risk_flags
        )

        return AssessmentResult(
            company_name=assessment.company_name,
            industry=assessment.industry,
            overall_score=round(overall_score, 1),
            tier=tier,
            category_scores=category_scores,
            risk_flags=risk_flags,
            critical_gaps=critical_gaps,
            recommendations=recommendations[:5],  # Top 5 only
        )

    def _calculate_all_categories(
        self, assessment: CompanyAssessment
    ) -> list[CategoryScore]:
        """Calculate scores for all categories."""
        scores = []

        # Strategy (20%)
        scores.append(self._score_strategy(assessment))

        # Data Foundation (25%)
        scores.append(self._score_data_foundation(assessment))

        # Infrastructure (20%)
        scores.append(self._score_infrastructure(assessment))

        # Governance (15%)
        scores.append(self._score_governance(assessment))

        # Delivery (10%)
        scores.append(self._score_delivery(assessment))

        # Adoption (10%)
        scores.append(self._score_adoption(assessment))

        return scores

    def _score_strategy(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Strategy category (20% weight).

        Factors:
        - Executive sponsor presence
        - AI projects in production (signals strategic commitment)
        """
        category = Category.STRATEGY
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0
        capped = False
        cap_reason = None

        # Executive sponsor: 2.5 points
        if assessment.executive_sponsor:
            score += 2.5

        # AI projects in production: up to 2.5 points
        if assessment.ai_projects_in_production >= 5:
            score += 2.5
        elif assessment.ai_projects_in_production >= 3:
            score += 2.0
        elif assessment.ai_projects_in_production >= 1:
            score += 1.0

        # Cap rule: No executive sponsor caps Strategy at 3.0
        if not assessment.executive_sponsor and score > 3.0:
            score = 3.0
            capped = True
            cap_reason = "No executive sponsor limits strategic maturity"

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
            capped=capped,
            cap_reason=cap_reason,
        )

    def _score_data_foundation(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Data Foundation category (25% weight).

        Factors:
        - Data lake presence
        - Data governance policy
        """
        category = Category.DATA_FOUNDATION
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0
        capped = False
        cap_reason = None

        # Data lake: 2.5 points
        if assessment.has_data_lake:
            score += 2.5

        # Data governance policy: 2.5 points
        if assessment.has_data_governance_policy:
            score += 2.5

        # Cap rule: No governance policy caps Data Foundation at 2.0
        if not assessment.has_data_governance_policy and score > 2.0:
            score = 2.0
            capped = True
            cap_reason = "No data governance policy limits data foundation maturity"

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
            capped=capped,
            cap_reason=cap_reason,
        )

    def _score_infrastructure(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Infrastructure category (20% weight).

        Factors:
        - Cloud provider presence
        - ML platform
        - Monitoring capability
        """
        category = Category.INFRASTRUCTURE
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0

        # Cloud provider: 1.5 points
        if assessment.cloud_provider:
            score += 1.5

        # ML platform: 2.0 points
        if assessment.has_ml_platform:
            score += 2.0

        # Monitoring: 1.5 points
        if assessment.has_monitoring:
            score += 1.5

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
        )

    def _score_governance(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Governance category (15% weight).

        Factors:
        - Data governance policy
        - Risk controls (inferred from monitoring)
        """
        category = Category.GOVERNANCE
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0
        capped = False
        cap_reason = None

        # Data governance policy: 3.0 points
        if assessment.has_data_governance_policy:
            score += 3.0

        # Monitoring (implies risk controls): 2.0 points
        if assessment.has_monitoring:
            score += 2.0

        # Cap rule: No governance policy caps Governance at 2.0
        if not assessment.has_data_governance_policy and score > 2.0:
            score = 2.0
            capped = True
            cap_reason = "No data governance policy limits governance maturity"

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
            capped=capped,
            cap_reason=cap_reason,
        )

    def _score_delivery(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Delivery category (10% weight).

        Factors:
        - Number of AI projects in production
        - Boost if has monitoring and >= 3 projects
        """
        category = Category.DELIVERY
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0

        # Projects in production: up to 4.0 points
        projects = assessment.ai_projects_in_production
        if projects >= 10:
            score += 4.0
        elif projects >= 5:
            score += 3.0
        elif projects >= 3:
            score += 2.0
        elif projects >= 1:
            score += 1.0

        # Boost: If >= 3 projects and monitoring, add 1.0
        if projects >= self.PRODUCTION_PROJECTS_BOOST_THRESHOLD and assessment.has_monitoring:
            score += 1.0

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
        )

    def _score_adoption(self, assessment: CompanyAssessment) -> CategoryScore:
        """Score the Adoption category (10% weight).

        Factors:
        - AI team size relative to employee count
        """
        category = Category.ADOPTION
        weight = CATEGORY_WEIGHTS[category]
        score = 0.0

        # Calculate AI team ratio
        if assessment.employee_count > 0:
            ratio = assessment.ai_team_size / assessment.employee_count

            # Scoring based on ratio thresholds
            if ratio >= 0.02:  # 2% or more of workforce in AI
                score = 5.0
            elif ratio >= 0.01:  # 1-2%
                score = 4.0
            elif ratio >= 0.005:  # 0.5-1%
                score = 3.0
            elif ratio >= 0.002:  # 0.2-0.5%
                score = 2.0
            elif assessment.ai_team_size > 0:
                score = 1.0

        # Also consider absolute team size for smaller companies
        if assessment.ai_team_size >= self.LARGE_TEAM_THRESHOLD:
            score = max(score, 3.0)
        elif assessment.ai_team_size >= 5:
            score = max(score, 2.0)

        # Ensure score is in valid range
        score = min(5.0, max(0.0, score))

        weighted_contribution = (score / 5.0) * weight * 100

        return CategoryScore(
            category=category,
            raw_score=round(score, 2),
            weight=weight,
            weighted_contribution=round(weighted_contribution, 2),
        )

    def _identify_risks(
        self,
        assessment: CompanyAssessment,
        category_scores: list[CategoryScore],
    ) -> list[RiskFlag]:
        """Identify risk flags based on assessment data."""
        risks = []

        # High Risk: Cloud spend > $10k but no monitoring
        cloud_spend = assessment.cloud_monthly_spend_usd or 0
        if cloud_spend > self.HIGH_CLOUD_SPEND_THRESHOLD and not assessment.has_monitoring:
            risks.append(
                RiskFlag(
                    severity="High",
                    category="Infrastructure",
                    message=f"Cloud spend ${cloud_spend:,}/month without production monitoring",
                )
            )

        # Sustainability Risk: No AI team but has production projects
        if assessment.ai_team_size == 0 and assessment.ai_projects_in_production > 0:
            risks.append(
                RiskFlag(
                    severity="High",
                    category="Adoption",
                    message=f"{assessment.ai_projects_in_production} AI project(s) in production with no dedicated AI team",
                )
            )

        # Medium Risk: No executive sponsor with significant AI investment
        if not assessment.executive_sponsor and assessment.ai_projects_in_production >= 3:
            risks.append(
                RiskFlag(
                    severity="Medium",
                    category="Strategy",
                    message="Multiple production AI projects without executive sponsorship",
                )
            )

        # Medium Risk: No ML platform but has production projects
        if not assessment.has_ml_platform and assessment.ai_projects_in_production >= 2:
            risks.append(
                RiskFlag(
                    severity="Medium",
                    category="Infrastructure",
                    message="Production AI projects without standardized ML platform",
                )
            )

        # Low Risk: Large cloud spend without data lake
        if cloud_spend > self.HIGH_CLOUD_SPEND_THRESHOLD and not assessment.has_data_lake:
            risks.append(
                RiskFlag(
                    severity="Low",
                    category="Data Foundation",
                    message="Significant cloud spend without centralized data lake",
                )
            )

        return risks

    def _generate_recommendations(
        self,
        assessment: CompanyAssessment,
        category_scores: list[CategoryScore],
        risk_flags: list[RiskFlag],
    ) -> list[Recommendation]:
        """Generate prioritized recommendations based on gaps and risks."""
        recommendations = []
        priority = 1

        # Sort categories by score (lowest first)
        sorted_scores = sorted(category_scores, key=lambda x: x.raw_score)

        # Address critical gaps first (scores < 3.0)
        for cs in sorted_scores:
            if cs.raw_score < 3.0:
                rec = self._get_category_recommendation(cs.category, assessment)
                if rec:
                    recommendations.append(
                        Recommendation(
                            priority=priority,
                            category=cs.category.value,
                            action=rec["action"],
                            rationale=rec["rationale"],
                        )
                    )
                    priority += 1

        # Address high-severity risks
        for risk in risk_flags:
            if risk.severity == "High" and priority <= 5:
                recommendations.append(
                    Recommendation(
                        priority=priority,
                        category=risk.category,
                        action=self._get_risk_mitigation(risk),
                        rationale=risk.message,
                    )
                )
                priority += 1

        # Fill remaining slots with improvement recommendations
        for cs in sorted_scores:
            if cs.raw_score >= 3.0 and cs.raw_score < 4.5 and priority <= 5:
                rec = self._get_improvement_recommendation(cs.category, assessment)
                if rec:
                    recommendations.append(
                        Recommendation(
                            priority=priority,
                            category=cs.category.value,
                            action=rec["action"],
                            rationale=rec["rationale"],
                        )
                    )
                    priority += 1

        return recommendations

    def _get_category_recommendation(
        self, category: Category, assessment: CompanyAssessment
    ) -> Optional[dict[str, str]]:
        """Get specific recommendation for a low-scoring category."""
        if category == Category.STRATEGY:
            if not assessment.executive_sponsor:
                return {
                    "action": "Secure executive sponsorship for AI initiatives",
                    "rationale": "Executive alignment is critical for resource allocation and strategic direction",
                }
            return {
                "action": "Develop formal AI strategy aligned with business objectives",
                "rationale": "Clear strategic vision enables focused investment and measurable outcomes",
            }

        elif category == Category.DATA_FOUNDATION:
            if not assessment.has_data_lake:
                return {
                    "action": "Implement centralized data lake architecture",
                    "rationale": "Unified data access is foundational for AI/ML workloads",
                }
            if not assessment.has_data_governance_policy:
                return {
                    "action": "Establish formal data governance policy and data catalog",
                    "rationale": "Data quality and lineage are prerequisites for trustworthy AI",
                }
            return None

        elif category == Category.INFRASTRUCTURE:
            if not assessment.has_ml_platform:
                return {
                    "action": "Deploy standardized ML platform (e.g., MLflow, Kubeflow, SageMaker)",
                    "rationale": "ML platforms accelerate experimentation and production deployment",
                }
            if not assessment.has_monitoring:
                return {
                    "action": "Implement production monitoring and observability stack",
                    "rationale": "Monitoring enables proactive issue detection and model drift identification",
                }
            return None

        elif category == Category.GOVERNANCE:
            if not assessment.has_data_governance_policy:
                return {
                    "action": "Develop comprehensive AI governance framework",
                    "rationale": "Governance ensures responsible AI use and regulatory compliance",
                }
            return None

        elif category == Category.DELIVERY:
            if assessment.ai_projects_in_production == 0:
                return {
                    "action": "Identify and execute pilot AI project with clear success metrics",
                    "rationale": "Production deployment validates capabilities and builds organizational confidence",
                }
            return None

        elif category == Category.ADOPTION:
            if assessment.ai_team_size == 0:
                return {
                    "action": "Build dedicated AI/ML team or establish center of excellence",
                    "rationale": "Specialized expertise is required for sustainable AI operations",
                }
            return None

        return None

    def _get_improvement_recommendation(
        self, category: Category, assessment: CompanyAssessment
    ) -> Optional[dict[str, str]]:
        """Get improvement recommendation for moderate-scoring category."""
        if category == Category.STRATEGY:
            return {
                "action": "Expand AI roadmap with quarterly OKRs and success metrics",
                "rationale": "Structured goals accelerate maturity and demonstrate ROI",
            }

        elif category == Category.DATA_FOUNDATION:
            return {
                "action": "Implement data quality monitoring and automated validation",
                "rationale": "Proactive data quality management prevents downstream issues",
            }

        elif category == Category.INFRASTRUCTURE:
            return {
                "action": "Establish CI/CD pipelines for ML model deployment",
                "rationale": "Automated deployment reduces time-to-production and errors",
            }

        elif category == Category.GOVERNANCE:
            return {
                "action": "Implement model registry with versioning and lineage tracking",
                "rationale": "Model governance supports auditability and rollback capabilities",
            }

        elif category == Category.DELIVERY:
            return {
                "action": "Scale successful pilots to additional business domains",
                "rationale": "Replicating proven patterns maximizes AI investment returns",
            }

        elif category == Category.ADOPTION:
            return {
                "action": "Launch AI literacy program across business units",
                "rationale": "Broad AI understanding enables identification of new use cases",
            }

        return None

    def _get_risk_mitigation(self, risk: RiskFlag) -> str:
        """Get mitigation action for a risk flag."""
        if "monitoring" in risk.message.lower():
            return "Implement comprehensive monitoring and alerting for all production AI systems"
        elif "team" in risk.message.lower():
            return "Urgently hire or assign dedicated AI/ML resources to support production systems"
        elif "sponsor" in risk.message.lower():
            return "Engage C-level executive to sponsor and champion AI initiatives"
        elif "platform" in risk.message.lower():
            return "Evaluate and deploy ML platform to standardize development practices"
        else:
            return "Address identified risk through targeted improvement initiative"
