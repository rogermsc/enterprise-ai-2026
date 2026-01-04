"""Evaluation Runner - Execute evaluation suites.

Runs test suites against agents and collects metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

from eval.datasets import TestCase, TestSuite
from eval.metrics import Metric

logger = structlog.get_logger()


@dataclass
class EvalResult:
    """Result of a single test case evaluation."""
    test_case_id: str
    passed: bool
    expected: str
    actual: str
    metrics: dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: float = 0.0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvalSuiteResult:
    """Result of running a full test suite."""
    suite_id: str
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    results: list[EvalResult] = field(default_factory=list)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = 0.0


class EvalRunner:
    """Evaluation runner for agent testing.

    Features:
    - Parallel test execution
    - Multiple metric calculation
    - Result persistence
    - Regression detection
    """

    def __init__(self, metrics: Optional[list[Metric]] = None):
        self._metrics = metrics or []
        self._results_history: list[EvalSuiteResult] = []

    def add_metric(self, metric: Metric) -> None:
        """Add a metric calculator."""
        self._metrics.append(metric)

    async def run_suite(
        self,
        suite: TestSuite,
        agent_executor: Any,  # Callable to execute agent
    ) -> EvalSuiteResult:
        """Run a full test suite.

        Args:
            suite: Test suite to run
            agent_executor: Function to execute agent with input

        Returns:
            Suite evaluation results
        """
        logger.info(
            "eval_suite_started",
            suite_id=suite.id,
            suite_name=suite.name,
            test_count=len(suite.test_cases),
        )

        start_time = datetime.now(timezone.utc)
        results = []

        for test_case in suite.test_cases:
            result = await self._run_test_case(test_case, agent_executor)
            results.append(result)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Calculate aggregate metrics
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        pass_rate = passed / len(results) if results else 0.0

        aggregate_metrics = self._calculate_aggregate_metrics(results)

        suite_result = EvalSuiteResult(
            suite_id=suite.id,
            suite_name=suite.name,
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            results=results,
            aggregate_metrics=aggregate_metrics,
            executed_at=start_time,
            duration_seconds=duration,
        )

        self._results_history.append(suite_result)

        logger.info(
            "eval_suite_completed",
            suite_id=suite.id,
            passed=passed,
            failed=failed,
            pass_rate=f"{pass_rate:.2%}",
            duration_seconds=duration,
        )

        return suite_result

    async def _run_test_case(
        self,
        test_case: TestCase,
        agent_executor: Any,
    ) -> EvalResult:
        """Run a single test case."""
        import time

        logger.debug("eval_test_case_started", test_case_id=test_case.id)

        start = time.perf_counter()

        try:
            # Execute agent
            actual = await agent_executor(test_case.input)
            latency_ms = (time.perf_counter() - start) * 1000

            # Check if passed
            passed = self._check_expected(actual, test_case.expected)

            # Calculate metrics
            metrics = {}
            for metric in self._metrics:
                metrics[metric.name] = metric.calculate(
                    expected=test_case.expected,
                    actual=actual,
                    test_case=test_case,
                )

            return EvalResult(
                test_case_id=test_case.id,
                passed=passed,
                expected=test_case.expected,
                actual=actual,
                metrics=metrics,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "eval_test_case_error",
                test_case_id=test_case.id,
                error=str(e),
            )
            return EvalResult(
                test_case_id=test_case.id,
                passed=False,
                expected=test_case.expected,
                actual="",
                error=str(e),
                latency_ms=latency_ms,
            )

    def _check_expected(self, actual: str, expected: str) -> bool:
        """Check if actual output matches expected."""
        # Simple exact match for now
        # In production, use semantic similarity or other matching
        return actual.strip().lower() == expected.strip().lower()

    def _calculate_aggregate_metrics(
        self, results: list[EvalResult]
    ) -> dict[str, float]:
        """Calculate aggregate metrics across all results."""
        if not results:
            return {}

        aggregates = {}

        # Aggregate each metric
        metric_values: dict[str, list[float]] = {}
        for result in results:
            for name, value in result.metrics.items():
                if name not in metric_values:
                    metric_values[name] = []
                metric_values[name].append(value)

        for name, values in metric_values.items():
            aggregates[f"{name}_mean"] = sum(values) / len(values)
            aggregates[f"{name}_min"] = min(values)
            aggregates[f"{name}_max"] = max(values)

        # Latency aggregates
        latencies = [r.latency_ms for r in results]
        aggregates["latency_p50"] = sorted(latencies)[len(latencies) // 2]
        aggregates["latency_p95"] = sorted(latencies)[int(len(latencies) * 0.95)]
        aggregates["latency_mean"] = sum(latencies) / len(latencies)

        return aggregates

    def detect_regression(
        self,
        current: EvalSuiteResult,
        threshold: float = 0.05,
    ) -> list[str]:
        """Detect regressions compared to previous run.

        Args:
            current: Current evaluation result
            threshold: Regression threshold (e.g., 0.05 = 5% drop)

        Returns:
            List of regression warnings
        """
        if len(self._results_history) < 2:
            return []

        previous = self._results_history[-2]
        warnings = []

        # Check pass rate regression
        if current.pass_rate < previous.pass_rate - threshold:
            warnings.append(
                f"Pass rate regression: {previous.pass_rate:.2%} -> {current.pass_rate:.2%}"
            )

        # Check metric regressions
        for metric_name, current_value in current.aggregate_metrics.items():
            if metric_name in previous.aggregate_metrics:
                prev_value = previous.aggregate_metrics[metric_name]
                if "latency" in metric_name.lower():
                    # Higher latency is worse
                    if current_value > prev_value * (1 + threshold):
                        warnings.append(
                            f"{metric_name} regression: {prev_value:.2f} -> {current_value:.2f}"
                        )
                else:
                    # Lower is worse for most metrics
                    if current_value < prev_value * (1 - threshold):
                        warnings.append(
                            f"{metric_name} regression: {prev_value:.2f} -> {current_value:.2f}"
                        )

        return warnings
