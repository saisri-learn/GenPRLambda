"""AWS Lambda handler for GitHub PR automation agent."""

import json
from typing import Any

from src.agent.langchain_agent import create_and_execute_agent
from src.config.settings import get_settings
from src.mcp.client import GitHubMCPClient
from src.utils.logger import get_logger
from src.utils.validators import ValidationError, validate_event_payload, validate_prompt

# Initialize logger
logger = get_logger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler function.

    Args:
        event: Lambda event dictionary containing:
            - prompt: str (required) - User's natural language instruction
            - base_branch: str (optional) - Base branch for PR (default: from config)
        context: Lambda context object

    Returns:
        Dictionary with:
            - statusCode: int
            - body: JSON string with:
                - success: bool
                - message: str
                - pr_url: str (if successful)
                - correlation_id: str
    """
    logger.info("Lambda function invoked", stage="lambda_start")

    correlation_id = logger.correlation_id
    response_headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }

    try:
        # Load configuration
        logger.info("Loading configuration", stage="config_load")
        settings = get_settings()

        # Validate and parse event payload
        logger.info("Validating event payload", stage="validation")
        try:
            payload = validate_event_payload(event)
        except ValidationError as e:
            logger.error(f"Event validation failed: {e}", stage="validation")
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Invalid event payload",
                        "message": str(e),
                        "correlation_id": correlation_id,
                    }
                ),
            }

        # Extract and validate prompt
        prompt = payload.get("prompt")
        try:
            prompt = validate_prompt(prompt)
        except ValidationError as e:
            logger.error(f"Prompt validation failed: {e}", stage="validation")
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Invalid prompt",
                        "message": str(e),
                        "correlation_id": correlation_id,
                    }
                ),
            }

        logger.info(
            "Prompt validated successfully",
            stage="validation",
            metadata={"prompt_length": len(prompt)},
        )

        # Override base branch if provided
        base_branch = payload.get("base_branch", settings.default_base_branch)

        # Execute the agent workflow
        result = execute_agent_sync(settings, prompt, base_branch)

        # Build response based on result
        if result["success"]:
            logger.info(
                "Agent execution completed successfully",
                stage="lambda_complete",
                metadata={"pr_url": result.get("pr_url")},
            )

            response_body = {
                "success": True,
                "message": "Pull request created successfully",
                "output": result.get("output", ""),
                "pr_url": result.get("pr_url"),
                "correlation_id": correlation_id,
            }

            return {
                "statusCode": 200,
                "headers": response_headers,
                "body": json.dumps(response_body),
            }
        else:
            logger.error(
                "Agent execution failed",
                stage="lambda_complete",
                metadata={"error": result.get("error")},
            )

            response_body = {
                "success": False,
                "error": "Agent execution failed",
                "message": result.get("error", "Unknown error"),
                "output": result.get("output", ""),
                "correlation_id": correlation_id,
            }

            return {
                "statusCode": 500,
                "headers": response_headers,
                "body": json.dumps(response_body),
            }

    except Exception as e:
        logger.critical(
            f"Unexpected error in Lambda handler: {e}",
            stage="lambda_error",
            exc_info=True,
        )

        return {
            "statusCode": 500,
            "headers": response_headers,
            "body": json.dumps(
                {
                    "success": False,
                    "error": "Internal server error",
                    "message": str(e),
                    "correlation_id": correlation_id,
                }
            ),
        }


def execute_agent_sync(
    settings: Any,
    prompt: str,
    base_branch: str,
) -> dict[str, Any]:
    """Execute the agent synchronously (wrapping async execution).

    Args:
        settings: Application settings
        prompt: User prompt
        base_branch: Base branch for PR

    Returns:
        Execution result dictionary
    """
    import asyncio

    logger.info(
        "Initializing MCP client and agent",
        stage="agent_init",
        metadata={"base_branch": base_branch},
    )

    async def run_agent() -> dict[str, Any]:
        """Async function to run the agent."""
        # Initialize MCP client
        mcp_client = GitHubMCPClient(
            REPO_TOKEN=settings.REPO_TOKEN,
            REPO_OWNER=settings.REPO_OWNER,
            REPO_NAME=settings.REPO_NAME,
        )

        try:
            # Start MCP client
            await mcp_client.start()

            # Execute agent
            result = await create_and_execute_agent(
                mcp_client=mcp_client,
                settings=settings,
                prompt=prompt,
            )

            return result

        finally:
            # Always clean up MCP client
            await mcp_client.stop()

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(run_agent())


# For local testing
if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Test event
    test_event = {
        "prompt": "Add a hello world function to the main file",
    }

    # Mock context
    class MockContext:
        aws_request_id = "local-test"
        function_name = "genpr-lambda-test"
        memory_limit_in_mb = 2048
        invoked_function_arn = "arn:aws:lambda:local:000000000000:function:test"

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result["body"]), indent=2))
