"""Input validation utilities."""

import re
from typing import Any


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


def validate_prompt(prompt: str | None) -> str:
    """Validate the user prompt input.

    Args:
        prompt: User prompt string

    Returns:
        Validated prompt string

    Raises:
        ValidationError: If prompt is invalid
    """
    if not prompt:
        raise ValidationError("Prompt is required and cannot be empty")

    if not isinstance(prompt, str):
        raise ValidationError(f"Prompt must be a string, got {type(prompt).__name__}")

    prompt = prompt.strip()

    if len(prompt) == 0:
        raise ValidationError("Prompt cannot be empty after trimming whitespace")

    if len(prompt) < 5:
        raise ValidationError("Prompt is too short (minimum 5 characters)")

    if len(prompt) > 10000:
        raise ValidationError("Prompt is too long (maximum 10000 characters)")

    return prompt


def validate_branch_name(branch_name: str) -> str:
    """Validate a Git branch name.

    Args:
        branch_name: Proposed branch name

    Returns:
        Validated branch name

    Raises:
        ValidationError: If branch name is invalid
    """
    if not branch_name:
        raise ValidationError("Branch name cannot be empty")

    # Git branch name rules
    # - Cannot start with a dot or slash
    # - Cannot end with .lock
    # - Cannot contain certain special characters
    # - Cannot be named HEAD, -refs/heads, etc.

    if branch_name.startswith(".") or branch_name.startswith("/"):
        raise ValidationError("Branch name cannot start with '.' or '/'")

    if branch_name.endswith(".lock"):
        raise ValidationError("Branch name cannot end with '.lock'")

    if branch_name in ("HEAD", "refs/heads", "refs/tags"):
        raise ValidationError(f"Branch name cannot be '{branch_name}'")

    # Check for invalid characters
    invalid_chars = r'[\s~^:?*\[\]\\]'
    if re.search(invalid_chars, branch_name):
        raise ValidationError("Branch name contains invalid characters")

    # Check for consecutive dots
    if ".." in branch_name:
        raise ValidationError("Branch name cannot contain consecutive dots")

    return branch_name


def validate_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Validate Lambda event payload.

    Args:
        event: Lambda event dictionary

    Returns:
        Validated event dictionary with normalized structure

    Raises:
        ValidationError: If event structure is invalid
    """
    if not isinstance(event, dict):
        raise ValidationError(f"Event must be a dictionary, got {type(event).__name__}")

    # Handle API Gateway event format
    if "body" in event:
        # API Gateway passes body as JSON string
        import json

        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in event body: {e}")

        if not isinstance(body, dict):
            raise ValidationError("Event body must be a JSON object")

        return body

    # Direct invocation format
    return event


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Input filename

    Returns:
        Sanitized filename

    Raises:
        ValidationError: If filename is invalid or contains path traversal
    """
    if not filename:
        raise ValidationError("Filename cannot be empty")

    # Check for path traversal attempts
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise ValidationError("Filename contains invalid path components")

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[^\w\s\-./]', '', filename)

    if not sanitized:
        raise ValidationError("Filename is invalid after sanitization")

    return sanitized
