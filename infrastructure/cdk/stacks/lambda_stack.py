"""CDK stack for GenPRLambda function and infrastructure."""

import os
from typing import Any

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
)
from constructs import Construct


class GenPRLambdaStack(Stack):
    """CDK Stack for GenPRLambda infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        """Initialize the stack.

        Args:
            scope: CDK app scope
            construct_id: Unique identifier for this stack
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        # Get configuration from environment variables or use defaults
        REPO_token = os.environ.get("REPO_TOKEN", "")
        REPO_owner = os.environ.get("REPO_OWNER", "")
        REPO_NAME = os.environ.get("REPO_NAME", "")
        llm_provider = os.environ.get("LLM_PROVIDER", "anthropic")
        llm_model = os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")
        llm_api_key = os.environ.get("LLM_API_KEY", "")
        log_level = os.environ.get("LOG_LEVEL", "INFO")

        # Create Lambda function from Docker image
        lambda_function = lambda_.DockerImageFunction(
            self,
            "GenPRLambdaFunction",
            function_name="genpr-lambda-function",
            description="AI agent for automated REPO PR creation",
            code=lambda_.DockerImageCode.from_image_asset(
                directory="../../",  # Root directory containing Dockerfile
                file="Dockerfile",
            ),
            timeout=Duration.seconds(900),  # 15 minutes (maximum for Lambda)
            memory_size=2048,  # 2GB memory
            ephemeral_storage_size=lambda_.Size.mebibytes(2048),  # 2GB ephemeral storage
            architecture=lambda_.Architecture.X86_64,  # Use x86_64 for compatibility
            environment={
                "REPO_TOKEN": REPO_token,
                "REPO_OWNER": REPO_owner,
                "REPO_NAME": REPO_NAME,
                "DEFAULT_BASE_BRANCH": "main",
                "LLM_PROVIDER": llm_provider,
                "LLM_MODEL": llm_model,
                "LLM_API_KEY": llm_api_key,
                "LLM_TEMPERATURE": "0.0",
                "LLM_MAX_TOKENS": "4000",
                "LOG_LEVEL": log_level,
                "TIMEOUT_BUFFER": "30",
            },
            retry_attempts=0,  # Don't retry on failure (agent state may be inconsistent)
        )

        # Grant CloudWatch Logs permissions (automatically added by CDK)
        # Lambda execution role gets these by default

        # Create CloudWatch Log Group with retention
        log_group = logs.LogGroup(
            self,
            "GenPRLambdaLogGroup",
            log_group_name=f"/aws/lambda/{lambda_function.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Optional: Create API Gateway REST API
        # Uncomment this section if you want to expose the Lambda via HTTP endpoint

        api = apigw.RestApi(
            self,
            "GenPRLambdaApi",
            rest_api_name="GenPR Lambda API",
            description="API for triggering REPO PR automation",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=10,  # requests per second
                throttling_burst_limit=20,  # concurrent requests
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
            ),
        )

        # Add /generate-pr endpoint
        generate_pr = api.root.add_resource("generate-pr")
        generate_pr.add_method(
            "POST",
            apigw.LambdaIntegration(
                lambda_function,
                proxy=True,
            ),
        )

        # Add CORS support
        generate_pr.add_cors_preflight(
            allow_origins=apigw.Cors.ALL_ORIGINS,
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

        # Outputs
        CfnOutput(
            self,
            "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the Lambda function",
        )

        CfnOutput(
            self,
            "LambdaFunctionArn",
            value=lambda_function.function_arn,
            description="ARN of the Lambda function",
        )

        CfnOutput(
            self,
            "ApiEndpoint",
            value=f"{api.url}generate-pr",
            description="API Gateway endpoint URL",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="CloudWatch Log Group name",
        )
