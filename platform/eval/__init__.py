"""Evaluation Framework - LLMOps Testing and Quality Assurance.

Implements comprehensive evaluation for AI agents:
- Golden dataset testing
- Regression detection
- Hallucination scoring
- Safety checks
- Performance benchmarking
"""

__version__ = "0.1.0"

from eval.runner import EvalRunner, EvalResult
from eval.metrics import Metric, AccuracyMetric, LatencyMetric, CostMetric
from eval.datasets import TestCase, TestSuite

__all__ = [
    "EvalRunner",
    "EvalResult",
    "Metric",
    "AccuracyMetric",
    "LatencyMetric",
    "CostMetric",
    "TestCase",
    "TestSuite",
]
