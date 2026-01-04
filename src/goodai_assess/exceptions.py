"""Custom exceptions for the Good AI Assessment Engine.

Provides clean error handling with meaningful messages for CLI users.
"""

from typing import Any


class AssessmentError(Exception):
    """Base exception for all assessment errors."""

    def __init__(self, message: str, details: Any = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional additional details about the error.
        """
        super().__init__(message)
        self.message = message
        self.details = details


class FileNotFoundError(AssessmentError):
    """Raised when the input file cannot be found."""

    def __init__(self, filepath: str) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the file that was not found.
        """
        message = f"File not found: {filepath}"
        super().__init__(message, details={"filepath": filepath})
        self.filepath = filepath


class InvalidJSONError(AssessmentError):
    """Raised when the input file contains invalid JSON."""

    def __init__(self, filepath: str, parse_error: str, line: int | None = None, column: int | None = None) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the file with invalid JSON.
            parse_error: The JSON parse error message.
            line: Line number where the error occurred (if available).
            column: Column number where the error occurred (if available).
        """
        location = ""
        if line is not None:
            location = f" at line {line}"
            if column is not None:
                location += f", column {column}"

        message = f"Invalid JSON in {filepath}{location}: {parse_error}"
        super().__init__(
            message,
            details={
                "filepath": filepath,
                "parse_error": parse_error,
                "line": line,
                "column": column,
            },
        )
        self.filepath = filepath
        self.parse_error = parse_error
        self.line = line
        self.column = column


class SchemaValidationError(AssessmentError):
    """Raised when the input data fails schema validation."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        """Initialize the exception.

        Args:
            errors: List of validation error dictionaries from Pydantic.
        """
        error_messages = []
        for error in errors:
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Unknown error")
            error_messages.append(f"  - {loc}: {msg}")

        message = "Schema validation failed:\n" + "\n".join(error_messages)
        super().__init__(message, details={"errors": errors})
        self.errors = errors
