"""Good AI Assessment Engine.

Deterministic AI readiness scoring for enterprise transformation.
"""

__version__ = "1.0.0"
__author__ = "Good AI"
__email__ = "contact@wearegoodai.com"

from goodai_assess.schema import CompanyAssessment
from goodai_assess.scoring import ScoringEngine, AssessmentResult, CategoryScore
from goodai_assess.exceptions import (
    AssessmentError,
    FileNotFoundError as AssessmentFileNotFoundError,
    InvalidJSONError,
    SchemaValidationError,
)

__all__ = [
    "__version__",
    "CompanyAssessment",
    "ScoringEngine",
    "AssessmentResult",
    "CategoryScore",
    "AssessmentError",
    "AssessmentFileNotFoundError",
    "InvalidJSONError",
    "SchemaValidationError",
]
