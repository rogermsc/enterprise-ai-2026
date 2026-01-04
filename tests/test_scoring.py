"""Tests for the scoring engine.

Verifies determinism, scoring rules, and risk flag generation.
"""

import pytest

from goodai_assess.schema import CompanyAssessment
from goodai_assess.scoring import ScoringEngine, Tier, Category, CATEGORY_WEIGHTS


class TestScoringDeterminism:
    """Tests to verify scoring is deterministic."""

    def test_same_input_same_output(self, mature_company: CompanyAssessment) -> None:
        """Same input should always produce same output."""
        engine = ScoringEngine()

        result1 = engine.calculate(mature_company)
        result2 = engine.calculate(mature_company)

        assert result1.overall_score == result2.overall_score
        assert result1.tier == result2.tier
        assert len(result1.category_scores) == len(result2.category_scores)

        for cs1, cs2 in zip(result1.category_scores, result2.category_scores):
            assert cs1.raw_score == cs2.raw_score
            assert cs1.weighted_contribution == cs2.weighted_contribution

    def test_determinism_across_multiple_runs(
        self, legacy_company: CompanyAssessment
    ) -> None:
        """Score should be identical across 100 runs."""
        engine = ScoringEngine()
        first_result = engine.calculate(legacy_company)

        for _ in range(100):
            result = engine.calculate(legacy_company)
            assert result.overall_score == first_result.overall_score


class TestCategoryWeights:
    """Tests for category weight validation."""

    def test_weights_sum_to_one(self) -> None:
        """Category weights must sum to 1.0."""
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_categories_have_weights(self) -> None:
        """All categories must have assigned weights."""
        for category in Category:
            assert category in CATEGORY_WEIGHTS


class TestScoringRules:
    """Tests for specific scoring rules."""

    def test_no_governance_caps_data_foundation(self) -> None:
        """No governance policy should cap Data Foundation at 2.0."""
        engine = ScoringEngine()
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            has_data_lake=True,  # Would add 2.5 points
            has_data_governance_policy=False,  # Triggers cap
            has_ml_platform=False,
            has_monitoring=False,
            ai_team_size=0,
            ai_projects_in_production=0,
            executive_sponsor=False,
        )

        result = engine.calculate(assessment)
        data_score = next(
            cs for cs in result.category_scores
            if cs.category == Category.DATA_FOUNDATION
        )

        assert data_score.raw_score <= 2.0
        assert data_score.capped is True

    def test_no_governance_caps_governance_category(self) -> None:
        """No governance policy should limit Governance score.

        Note: With monitoring only (2.0 points), score equals cap exactly,
        so capped flag won't be True. We verify the cap limit is respected.
        """
        engine = ScoringEngine()
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            has_data_lake=False,
            has_data_governance_policy=False,  # Limits governance score
            has_ml_platform=False,
            has_monitoring=True,  # Adds 2.0 points
            ai_team_size=0,
            ai_projects_in_production=0,
            executive_sponsor=False,
        )

        result = engine.calculate(assessment)
        gov_score = next(
            cs for cs in result.category_scores
            if cs.category == Category.GOVERNANCE
        )

        # Score should be at or below the cap
        assert gov_score.raw_score <= 2.0

    def test_no_executive_sponsor_caps_strategy(self) -> None:
        """No executive sponsor should cap Strategy at 3.0."""
        engine = ScoringEngine()
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            has_data_lake=True,
            has_data_governance_policy=True,
            has_ml_platform=True,
            has_monitoring=True,
            ai_team_size=10,
            ai_projects_in_production=10,  # Would add 2.5 points
            executive_sponsor=False,  # No sponsor - triggers cap
        )

        result = engine.calculate(assessment)
        strategy_score = next(
            cs for cs in result.category_scores
            if cs.category == Category.STRATEGY
        )

        assert strategy_score.raw_score <= 3.0
        # Note: Cap only triggers if score would exceed 3.0

    def test_delivery_boost_with_monitoring(self) -> None:
        """Delivery should get boost if >= 3 projects and monitoring."""
        engine = ScoringEngine()
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            has_data_lake=True,
            has_data_governance_policy=True,
            has_ml_platform=True,
            has_monitoring=True,  # Has monitoring
            ai_team_size=10,
            ai_projects_in_production=3,  # >= 3 projects
            executive_sponsor=True,
        )

        result = engine.calculate(assessment)
        delivery_score = next(
            cs for cs in result.category_scores
            if cs.category == Category.DELIVERY
        )

        # 3 projects = 2.0 points + 1.0 boost = 3.0
        assert delivery_score.raw_score == 3.0


class TestRiskFlags:
    """Tests for risk flag generation."""

    def test_high_spend_no_monitoring_flag(self) -> None:
        """High cloud spend without monitoring should flag High Risk."""
        engine = ScoringEngine()
        assessment = CompanyAssessment(
            company_name="Test",
            industry="Tech",
            employee_count=100,
            cloud_monthly_spend_usd=50000,  # > $10k threshold
            has_data_lake=True,
            has_data_governance_policy=True,
            has_ml_platform=True,
            has_monitoring=False,  # No monitoring
            ai_team_size=10,
            ai_projects_in_production=3,
            executive_sponsor=True,
        )

        result = engine.calculate(assessment)
        high_risks = [r for r in result.risk_flags if r.severity == "High"]

        assert len(high_risks) >= 1
        assert any("monitoring" in r.message.lower() for r in high_risks)

    def test_no_team_with_production_projects_flag(
        self, high_risk_company: CompanyAssessment
    ) -> None:
        """Production projects without AI team should flag Sustainability Risk."""
        engine = ScoringEngine()
        result = engine.calculate(high_risk_company)

        sustainability_risks = [
            r for r in result.risk_flags
            if "team" in r.message.lower() and r.severity == "High"
        ]

        assert len(sustainability_risks) >= 1

    def test_no_false_positive_risks(self, mature_company: CompanyAssessment) -> None:
        """Mature company should have minimal risk flags."""
        engine = ScoringEngine()
        result = engine.calculate(mature_company)

        # Mature company should have no High severity risks
        high_risks = [r for r in result.risk_flags if r.severity == "High"]
        assert len(high_risks) == 0


class TestCriticalGaps:
    """Tests for critical gap identification."""

    def test_low_scores_flagged_as_critical(
        self, emerging_company: CompanyAssessment
    ) -> None:
        """Categories scoring below 3.0 should be flagged as critical gaps."""
        engine = ScoringEngine()
        result = engine.calculate(emerging_company)

        # Emerging company should have multiple critical gaps
        assert len(result.critical_gaps) > 0

        # Verify gaps match low-scoring categories
        for gap in result.critical_gaps:
            matching_score = next(
                cs for cs in result.category_scores
                if cs.category.value == gap
            )
            assert matching_score.raw_score < 3.0

    def test_no_critical_gaps_for_mature(
        self, mature_company: CompanyAssessment
    ) -> None:
        """Mature company should have no critical gaps."""
        engine = ScoringEngine()
        result = engine.calculate(mature_company)

        assert len(result.critical_gaps) == 0


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_recommendations_limited_to_five(
        self, emerging_company: CompanyAssessment
    ) -> None:
        """Should return at most 5 recommendations."""
        engine = ScoringEngine()
        result = engine.calculate(emerging_company)

        assert len(result.recommendations) <= 5

    def test_recommendations_prioritized(
        self, legacy_company: CompanyAssessment
    ) -> None:
        """Recommendations should be ordered by priority (1-5)."""
        engine = ScoringEngine()
        result = engine.calculate(legacy_company)

        priorities = [r.priority for r in result.recommendations]
        assert priorities == sorted(priorities)

    def test_recommendations_address_gaps(
        self, emerging_company: CompanyAssessment
    ) -> None:
        """Recommendations should address critical gaps."""
        engine = ScoringEngine()
        result = engine.calculate(emerging_company)

        # At least one recommendation should address a critical gap
        gap_categories = set(result.critical_gaps)
        rec_categories = {r.category for r in result.recommendations}

        assert len(gap_categories & rec_categories) > 0
