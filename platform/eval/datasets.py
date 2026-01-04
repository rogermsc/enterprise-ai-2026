"""Evaluation Test Datasets.

Defines test case and test suite structures for evaluation.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4


@dataclass
class TestCase:
    """A single test case for evaluation."""
    id: str
    input: str
    expected: str
    context: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        input: str,
        expected: str,
        **kwargs,
    ) -> "TestCase":
        """Create a test case with auto-generated ID."""
        return cls(
            id=str(uuid4())[:8],
            input=input,
            expected=expected,
            **kwargs,
        )


@dataclass
class TestSuite:
    """Collection of test cases."""
    id: str
    name: str
    description: str
    test_cases: list[TestCase] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def add_test(self, test_case: TestCase) -> None:
        """Add a test case to the suite."""
        self.test_cases.append(test_case)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        **kwargs,
    ) -> "TestSuite":
        """Create a test suite with auto-generated ID."""
        return cls(
            id=str(uuid4())[:8],
            name=name,
            description=description,
            **kwargs,
        )


# ============================================================================
# Example Golden Datasets
# ============================================================================


def create_customer_support_suite() -> TestSuite:
    """Create evaluation suite for customer support agent."""
    suite = TestSuite.create(
        name="Customer Support Golden Dataset",
        description="Core test cases for customer support agent",
        tags=["customer-support", "golden"],
    )

    suite.add_test(TestCase.create(
        input="I forgot my password",
        expected="I can help you reset your password. Please click the 'Forgot Password' link on the login page, and we'll send a reset link to your email.",
        tags=["password", "common"],
    ))

    suite.add_test(TestCase.create(
        input="How do I cancel my subscription?",
        expected="To cancel your subscription, go to Settings > Subscription > Cancel. Your access will continue until the end of the billing period.",
        tags=["subscription", "cancellation"],
    ))

    suite.add_test(TestCase.create(
        input="I was charged twice",
        expected="I'm sorry to hear about the duplicate charge. Let me look into this for you. Can you provide your order number so I can investigate?",
        tags=["billing", "escalation"],
    ))

    suite.add_test(TestCase.create(
        input="Your product is terrible and I hate it",
        expected="I'm sorry to hear you're having a frustrating experience. I'd like to help resolve any issues you're facing. Can you tell me more about what's not working for you?",
        tags=["sentiment", "negative"],
    ))

    suite.add_test(TestCase.create(
        input="Is my data secure?",
        expected="Yes, we take data security seriously. We use encryption at rest and in transit, and comply with SOC 2 Type II and GDPR requirements.",
        tags=["security", "compliance"],
    ))

    return suite


def create_data_analysis_suite() -> TestSuite:
    """Create evaluation suite for data analysis agent."""
    suite = TestSuite.create(
        name="Data Analysis Golden Dataset",
        description="Core test cases for data analysis agent",
        tags=["data-analysis", "golden"],
    )

    suite.add_test(TestCase.create(
        input="Show me revenue for Q1 2024",
        expected="Q1 2024 Revenue: $2.4M (up 15% YoY)",
        context={"available_data": ["revenue", "users", "transactions"]},
        tags=["revenue", "quarterly"],
    ))

    suite.add_test(TestCase.create(
        input="What's our churn rate?",
        expected="Current monthly churn rate: 3.2%, which is below industry average of 5%",
        tags=["churn", "metrics"],
    ))

    return suite
