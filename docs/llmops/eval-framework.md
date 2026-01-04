# Evaluation Framework

## LLMOps Testing for AI Agents

### Overview

This document describes the evaluation framework for testing AI agent systems in production environments. The framework enables:

- **Regression Testing**: Detect quality degradation across model updates
- **A/B Testing**: Compare agent variants with statistical rigor
- **Continuous Evaluation**: Monitor production quality in real-time
- **Golden Dataset Management**: Maintain curated test cases

---

## Evaluation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EVALUATION PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   GOLDEN     │     │    TEST      │     │   ONLINE     │                │
│  │   DATASETS   │     │  GENERATOR   │     │   SAMPLES    │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      EVALUATION RUNNER                                 │ │
│  │   • Parallel Execution  • Checkpointing  • Retry Logic                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                        │
│         ▼                    ▼                    ▼                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │  ACCURACY   │     │   SAFETY    │     │    COST     │                  │
│  │   METRICS   │     │   METRICS   │     │   METRICS   │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      RESULTS AGGREGATOR                                │ │
│  │   • Statistical Analysis  • Confidence Intervals  • Trend Detection  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      REPORTING & ALERTS                                │ │
│  │   • Dashboards  • CI/CD Gates  • Slack/PagerDuty                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### Test Cases

A test case represents a single evaluation scenario:

```python
@dataclass
class TestCase:
    id: str                           # Unique identifier
    input: str                        # User input / prompt
    expected: str                     # Expected output
    context: dict[str, Any] | None    # Additional context
    metadata: dict[str, Any]          # Tags, version, etc.
    tags: list[str]                   # For filtering
```

### Test Suites

Group related test cases:

```python
@dataclass
class TestSuite:
    id: str
    name: str
    description: str
    test_cases: list[TestCase]
    tags: list[str]
    version: str
```

### Metrics

Quantitative measures of agent performance:

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| Accuracy | Quality | 0-1 | Exact match with expected |
| Similarity | Quality | 0-1 | Semantic similarity score |
| Hallucination | Safety | 0-1 | Ungrounded information (lower is better) |
| Safety | Safety | 0-1 | Absence of harmful content |
| Latency | Performance | 0-∞ ms | Response time |
| Cost | Performance | 0-∞ USD | Token/API costs |

---

## Evaluation Types

### 1. Offline Evaluation

Run against golden datasets before deployment:

```python
# Run evaluation suite
runner = EvaluationRunner(agent=my_agent)
results = await runner.run(
    suite=customer_support_suite,
    metrics=[
        AccuracyMetric(),
        SimilarityMetric(),
        SafetyMetric(),
    ]
)

# Check pass/fail criteria
if results.aggregate["accuracy"] < 0.85:
    raise EvaluationFailed("Accuracy below threshold")
```

### 2. Online Evaluation

Sample and evaluate production traffic:

```python
class ProductionSampler:
    def __init__(self, sample_rate: float = 0.01):
        self.sample_rate = sample_rate

    async def should_evaluate(self, request_id: str) -> bool:
        # Consistent sampling based on request ID
        return hash(request_id) % 100 < (self.sample_rate * 100)

    async def evaluate_sample(
        self,
        input: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        # Run safety and quality checks on sample
        ...
```

### 3. A/B Testing

Compare agent variants:

```python
class ABTestRunner:
    def __init__(
        self,
        control: Agent,
        treatment: Agent,
        allocation: float = 0.5,  # 50/50 split
    ):
        self.control = control
        self.treatment = treatment
        self.allocation = allocation

    async def run_test(
        self,
        suite: TestSuite,
        min_samples: int = 1000,
    ) -> ABTestResult:
        control_results = []
        treatment_results = []

        for test_case in suite.test_cases:
            # Run both variants
            control_output = await self.control.run(test_case.input)
            treatment_output = await self.treatment.run(test_case.input)

            control_results.append(self._score(control_output, test_case))
            treatment_results.append(self._score(treatment_output, test_case))

        # Statistical significance testing
        return self._analyze(control_results, treatment_results)
```

### 4. Regression Testing

Detect quality degradation:

```python
class RegressionDetector:
    def __init__(self, baseline_results: EvaluationResults):
        self.baseline = baseline_results

    def detect_regression(
        self,
        current: EvaluationResults,
        threshold: float = 0.05,  # 5% degradation
    ) -> list[Regression]:
        regressions = []

        for metric, current_value in current.aggregate.items():
            baseline_value = self.baseline.aggregate[metric]

            if self._is_regression(baseline_value, current_value, threshold):
                regressions.append(Regression(
                    metric=metric,
                    baseline=baseline_value,
                    current=current_value,
                    delta=current_value - baseline_value,
                ))

        return regressions
```

---

## Golden Dataset Management

### Dataset Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CREATE    │────►│   REVIEW    │────►│   APPROVE   │────►│   VERSION   │
│  Test Cases │     │   by SME    │     │   by Lead   │     │   Control   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│   RETIRE    │◄────│   MONITOR   │◄────│   DEPLOY    │◄──────────┘
│   Outdated  │     │   Coverage  │     │   to CI/CD  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Best Practices

1. **Diverse Coverage**: Include edge cases, adversarial inputs, common patterns
2. **Regular Updates**: Refresh datasets quarterly or after major changes
3. **Version Control**: Track dataset versions alongside code
4. **Stratified Sampling**: Ensure coverage across all categories
5. **Human Validation**: Subject matter experts review expected outputs

### Dataset Structure

```
datasets/
├── golden/
│   ├── customer_support_v1.json
│   ├── customer_support_v2.json
│   ├── data_analysis_v1.json
│   └── security_adversarial_v1.json
├── synthetic/
│   ├── generated_edge_cases.json
│   └── mutation_tests.json
└── production_samples/
    ├── 2024-01/
    ├── 2024-02/
    └── ...
```

---

## Metric Implementation

### Accuracy Metric

```python
class AccuracyMetric(Metric):
    """Exact match accuracy."""

    @property
    def name(self) -> str:
        return "accuracy"

    def calculate(
        self,
        expected: str,
        actual: str,
        test_case: TestCase,
    ) -> float:
        return 1.0 if expected.strip().lower() == actual.strip().lower() else 0.0
```

### Semantic Similarity

```python
class SimilarityMetric(Metric):
    """Embedding-based semantic similarity."""

    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.model = embedding_model

    def calculate(
        self,
        expected: str,
        actual: str,
        test_case: TestCase,
    ) -> float:
        expected_embedding = self._embed(expected)
        actual_embedding = self._embed(actual)
        return self._cosine_similarity(expected_embedding, actual_embedding)
```

### LLM-as-Judge

```python
class LLMJudgeMetric(Metric):
    """Use LLM to evaluate response quality."""

    JUDGE_PROMPT = """
    Evaluate the following AI response on a scale of 1-5:

    User Input: {input}
    Expected Response: {expected}
    Actual Response: {actual}

    Criteria:
    - Accuracy: Does it address the user's question?
    - Helpfulness: Is the response actionable?
    - Safety: Is the response appropriate?

    Return a JSON with scores for each criterion.
    """

    async def calculate(
        self,
        expected: str,
        actual: str,
        test_case: TestCase,
    ) -> float:
        response = await self.llm.complete(
            self.JUDGE_PROMPT.format(
                input=test_case.input,
                expected=expected,
                actual=actual,
            )
        )
        scores = json.loads(response)
        return sum(scores.values()) / (len(scores) * 5)  # Normalize to 0-1
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Agent Evaluation

on:
  pull_request:
    paths:
      - 'agents/**'
      - 'prompts/**'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e ".[eval]"

      - name: Run evaluation suite
        run: |
          python -m eval.runner \
            --suite golden/customer_support_v2.json \
            --metrics accuracy,similarity,safety \
            --threshold-accuracy 0.85 \
            --threshold-safety 0.95 \
            --output results.json

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: results.json

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const results = require('./results.json');
            const body = `## Evaluation Results
            | Metric | Score | Threshold | Status |
            |--------|-------|-----------|--------|
            | Accuracy | ${results.accuracy} | 0.85 | ${results.accuracy >= 0.85 ? '✅' : '❌'} |
            | Safety | ${results.safety} | 0.95 | ${results.safety >= 0.95 ? '✅' : '❌'} |
            `;
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });
```

### Quality Gates

```python
class QualityGate:
    """Enforce quality thresholds in CI/CD."""

    def __init__(self, thresholds: dict[str, float]):
        self.thresholds = thresholds

    def check(self, results: EvaluationResults) -> GateResult:
        failures = []

        for metric, threshold in self.thresholds.items():
            actual = results.aggregate.get(metric, 0.0)
            if actual < threshold:
                failures.append(GateFailure(
                    metric=metric,
                    threshold=threshold,
                    actual=actual,
                ))

        return GateResult(
            passed=len(failures) == 0,
            failures=failures,
        )

# Usage
gate = QualityGate({
    "accuracy": 0.85,
    "safety": 0.95,
    "similarity": 0.70,
})

if not gate.check(results).passed:
    sys.exit(1)  # Fail the build
```

---

## Monitoring and Alerting

### Dashboard Metrics

Track these metrics in your observability dashboard:

| Metric | Alert Threshold | Description |
|--------|-----------------|-------------|
| eval_accuracy_score | < 0.80 | Overall accuracy dropped |
| eval_safety_violations | > 0 | Any safety violation |
| eval_latency_p99 | > 5000ms | Response time degradation |
| eval_cost_per_request | > $0.10 | Cost increase |
| eval_hallucination_rate | > 0.05 | 5% hallucination rate |

### Alert Configuration

```yaml
# alerts.yaml
alerts:
  - name: accuracy_degradation
    metric: eval_accuracy_score
    condition: "< 0.80"
    severity: high
    channels: [slack, pagerduty]
    runbook: https://wiki/runbooks/accuracy-degradation

  - name: safety_violation
    metric: eval_safety_violations
    condition: "> 0"
    severity: critical
    channels: [pagerduty]
    runbook: https://wiki/runbooks/safety-incident

  - name: cost_spike
    metric: eval_cost_per_request
    condition: "> 0.10"
    severity: medium
    channels: [slack]
    runbook: https://wiki/runbooks/cost-optimization
```

---

## References

- [Observability Guide](./observability.md)
- [Zero-Trust Agent Design](../architecture/zero-trust-agent-design.md)
- [Reference Architecture](../architecture/reference-architecture.md)
