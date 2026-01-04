"""Tests for tier boundary classification.

Verifies correct tier assignment at boundary values.
"""

import pytest

from goodai_assess.scoring import Tier


class TestTierBoundaries:
    """Tests for tier boundary values."""

    def test_emerging_lower_bound(self) -> None:
        """Score of 0 should be Emerging tier."""
        assert Tier.from_score(0) == Tier.EMERGING

    def test_emerging_upper_bound(self) -> None:
        """Score of 39.9 should still be Emerging tier."""
        assert Tier.from_score(39.9) == Tier.EMERGING

    def test_pilot_lower_bound(self) -> None:
        """Score of 40 should be Pilot tier."""
        assert Tier.from_score(40) == Tier.PILOT

    def test_pilot_boundary(self) -> None:
        """Score of 39 should be Emerging, 40 should be Pilot."""
        assert Tier.from_score(39) == Tier.EMERGING
        assert Tier.from_score(40) == Tier.PILOT

    def test_pilot_upper_bound(self) -> None:
        """Score of 59.9 should still be Pilot tier."""
        assert Tier.from_score(59.9) == Tier.PILOT

    def test_build_lower_bound(self) -> None:
        """Score of 60 should be Build tier."""
        assert Tier.from_score(60) == Tier.BUILD

    def test_build_boundary(self) -> None:
        """Score of 59 should be Pilot, 60 should be Build."""
        assert Tier.from_score(59) == Tier.PILOT
        assert Tier.from_score(60) == Tier.BUILD

    def test_build_upper_bound(self) -> None:
        """Score of 74.9 should still be Build tier."""
        assert Tier.from_score(74.9) == Tier.BUILD

    def test_scale_lower_bound(self) -> None:
        """Score of 75 should be Scale tier."""
        assert Tier.from_score(75) == Tier.SCALE

    def test_scale_boundary(self) -> None:
        """Score of 74 should be Build, 75 should be Scale."""
        assert Tier.from_score(74) == Tier.BUILD
        assert Tier.from_score(75) == Tier.SCALE

    def test_scale_upper_bound(self) -> None:
        """Score of 89.9 should still be Scale tier."""
        assert Tier.from_score(89.9) == Tier.SCALE

    def test_lead_lower_bound(self) -> None:
        """Score of 90 should be Lead tier."""
        assert Tier.from_score(90) == Tier.LEAD

    def test_lead_boundary(self) -> None:
        """Score of 89 should be Scale, 90 should be Lead."""
        assert Tier.from_score(89) == Tier.SCALE
        assert Tier.from_score(90) == Tier.LEAD

    def test_lead_upper_bound(self) -> None:
        """Score of 100 should be Lead tier."""
        assert Tier.from_score(100) == Tier.LEAD


class TestTierValues:
    """Tests for tier enum values."""

    def test_tier_display_values(self) -> None:
        """Tier display values should be human-readable."""
        assert Tier.EMERGING.value == "Emerging"
        assert Tier.PILOT.value == "Pilot"
        assert Tier.BUILD.value == "Build"
        assert Tier.SCALE.value == "Scale"
        assert Tier.LEAD.value == "Lead"

    def test_all_tiers_covered(self) -> None:
        """All score ranges should map to a tier."""
        # Test representative scores in each range
        test_scores = [0, 10, 39, 40, 50, 59, 60, 70, 74, 75, 80, 89, 90, 95, 100]

        for score in test_scores:
            tier = Tier.from_score(score)
            assert tier is not None
            assert isinstance(tier, Tier)


class TestTierProgression:
    """Tests for tier ordering and progression."""

    def test_tier_ordering(self) -> None:
        """Higher scores should result in higher tiers."""
        scores_and_tiers = [
            (20, Tier.EMERGING),
            (50, Tier.PILOT),
            (65, Tier.BUILD),
            (80, Tier.SCALE),
            (95, Tier.LEAD),
        ]

        # Verify each score maps to expected tier
        for score, expected_tier in scores_and_tiers:
            assert Tier.from_score(score) == expected_tier

        # Verify tier progression
        tier_order = [Tier.EMERGING, Tier.PILOT, Tier.BUILD, Tier.SCALE, Tier.LEAD]
        for i in range(len(scores_and_tiers) - 1):
            current_tier = scores_and_tiers[i][1]
            next_tier = scores_and_tiers[i + 1][1]
            assert tier_order.index(current_tier) < tier_order.index(next_tier)
