#!/usr/bin/env python3
"""CDK app entry point for GenPRLambda."""

import os

import aws_cdk as cdk

from stacks.lambda_stack import GenPRLambdaStack

app = cdk.App()

# Get environment variables for AWS account and region
account = os.environ.get("AWS_ACCOUNT_ID", os.environ.get("CDK_DEFAULT_ACCOUNT"))
region = os.environ.get("AWS_REGION", os.environ.get("CDK_DEFAULT_REGION", "us-east-1"))

# Create the stack
GenPRLambdaStack(
    app,
    "GenPRLambdaStack",
    env=cdk.Environment(account=account, region=region),
    description="Lambda function for automated GitHub PR creation using AI agents",
)

app.synth()
