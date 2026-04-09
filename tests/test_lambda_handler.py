"""Tests for Lambda handler."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.lambda_function import lambda_handler, execute_agent_sync


@pytest.fixture
def mock_context():
    """Create mock Lambda context."""
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    context.function_name = "test-function"
    context.memory_limit_in_mb = 2048
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    return context


@pytest.fixture
def valid_event():
    """Create valid Lambda event."""
    return {
        "prompt": "Add a hello world function to main.py",
    }


@pytest.fixture
def api_gateway_event():
    """Create API Gateway event."""
    return {
        "body": json.dumps({
            "prompt": "Add a hello world function to main.py",
        }),
        "headers": {
            "Content-Type": "application/json",
        },
    }


def test_lambda_handler_success(valid_event, mock_context):
    """Test successful Lambda invocation."""
    with patch("src.lambda_function.get_settings") as mock_settings, \
         patch("src.lambda_function.execute_agent_sync") as mock_execute:

        mock_settings.return_value = MagicMock()
        mock_execute.return_value = {
            "success": True,
            "output": "PR created successfully",
            "pr_url": "https://REPO.com/test/test/pull/1",
        }

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["pr_url"] == "https://REPO.com/test/test/pull/1"
        assert "correlation_id" in body


def test_lambda_handler_invalid_prompt(mock_context):
    """Test Lambda invocation with invalid prompt."""
    invalid_event = {"prompt": ""}

    with patch("src.lambda_function.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock()

        response = lambda_handler(invalid_event, mock_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body


def test_lambda_handler_missing_prompt(mock_context):
    """Test Lambda invocation with missing prompt."""
    invalid_event = {}

    with patch("src.lambda_function.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock()

        response = lambda_handler(invalid_event, mock_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False


def test_lambda_handler_api_gateway_format(api_gateway_event, mock_context):
    """Test Lambda invocation with API Gateway event format."""
    with patch("src.lambda_function.get_settings") as mock_settings, \
         patch("src.lambda_function.execute_agent_sync") as mock_execute:

        mock_settings.return_value = MagicMock()
        mock_execute.return_value = {
            "success": True,
            "output": "PR created successfully",
            "pr_url": "https://REPO.com/test/test/pull/1",
        }

        response = lambda_handler(api_gateway_event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True


def test_lambda_handler_agent_failure(valid_event, mock_context):
    """Test Lambda invocation with agent execution failure."""
    with patch("src.lambda_function.get_settings") as mock_settings, \
         patch("src.lambda_function.execute_agent_sync") as mock_execute:

        mock_settings.return_value = MagicMock()
        mock_execute.return_value = {
            "success": False,
            "error": "Agent failed",
            "output": "Failed to create PR",
        }

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body


def test_lambda_handler_unexpected_error(valid_event, mock_context):
    """Test Lambda invocation with unexpected error."""
    with patch("src.lambda_function.get_settings") as mock_settings:
        mock_settings.side_effect = Exception("Unexpected error")

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body


def test_lambda_handler_custom_base_branch(mock_context):
    """Test Lambda invocation with custom base branch."""
    event = {
        "prompt": "Add a function",
        "base_branch": "develop",
    }

    with patch("src.lambda_function.get_settings") as mock_settings, \
         patch("src.lambda_function.execute_agent_sync") as mock_execute:

        mock_settings.return_value = MagicMock()
        mock_execute.return_value = {
            "success": True,
            "output": "PR created",
            "pr_url": "https://REPO.com/test/test/pull/1",
        }

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        # Verify that execute_agent_sync was called with the custom branch
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args[0][2] == "develop"  # Third argument is base_branch
