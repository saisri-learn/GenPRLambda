# GenPRLambda - AI-Powered GitHub PR Automation

AWS Lambda function that uses AI agents to automatically create Pull Requests in GitHub repositories based on natural language prompts. Built with LangChain, GitHub MCP server, and supports both Claude and OpenAI models.

## Features

- **Natural Language Interface**: Describe code changes in plain English
- **Intelligent Code Modification**: AI agent explores repository, understands context, and makes appropriate changes
- **Automated PR Creation**: Creates branches, commits changes, and opens pull requests automatically
- **Multi-LLM Support**: Works with Claude (Anthropic) or GPT (OpenAI) models
- **GitHub MCP Integration**: Uses Model Context Protocol for reliable GitHub operations
- **Production-Ready**: Container-based deployment with comprehensive error handling and logging
- **API Gateway Support**: Optional REST API endpoint for HTTP invocations

## Architecture

```
API Gateway / Direct Invocation
        ↓
    Lambda Function (Python 3.11, Container Image)
        ↓
    LangChain ReAct Agent
        ↓
    GitHub MCP Server (Node.js, stdio transport)
        ↓
    GitHub API
```

**Key Components:**
- **Lambda Handler**: Orchestrates the workflow and handles requests
- **LangChain Agent**: ReAct pattern agent for reasoning and action
- **MCP Client**: Manages GitHub MCP server subprocess
- **LangChain Tools**: Wraps GitHub operations (list files, read, write, create PR)

## Prerequisites

- **AWS Account** with permissions to create Lambda, API Gateway, CloudWatch resources
- **GitHub Account** with a Personal Access Token (PAT) with `repo` scope
- **LLM API Key**: Either Anthropic API key or OpenAI API key
- **Python 3.11+** for local development
- **Node.js 20+** for MCP server
- **Docker** for building container images
- **AWS CDK** for infrastructure deployment

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd GenPRLambda
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# GitHub Configuration
REPO_TOKEN=ghp_your_token_here
REPO_OWNER=your-github-username
REPO_NAME=your-repository-name
DEFAULT_BASE_BRANCH=main

# LLM Configuration (Anthropic)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-your-key-here

# OR use OpenAI
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4
# LLM_API_KEY=sk-your-openai-key-here

# Lambda Configuration
LOG_LEVEL=INFO
```

### 3. Install Dependencies

**Python:**
```bash
pip install -r requirements.txt
```

**Node.js:**
```bash
npm install
```

**CDK:**
```bash
cd infrastructure/cdk
pip install -r requirements.txt
npm install -g aws-cdk
```

### 4. Local Testing (Optional)

Test the Lambda function locally:

```bash
python src/lambda_function.py
```

Or invoke with custom event:

```python
python -c "
from src.lambda_function import lambda_handler
import json

event = {'prompt': 'Add a hello world function to main.py'}
result = lambda_handler(event, None)
print(json.dumps(json.loads(result['body']), indent=2))
"
```

### 5. Deploy to AWS

**Bootstrap CDK (first time only):**
```bash
cd infrastructure/cdk
cdk bootstrap
```

**Deploy the stack:**
```bash
export AWS_ACCOUNT_ID=your-account-id
export AWS_REGION=us-east-1

# Set environment variables for deployment
export REPO_TOKEN=ghp_xxx
export REPO_OWNER=your-username
export REPO_NAME=your-repo
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-5-sonnet-20241022
export LLM_API_KEY=sk-ant-xxx

cdk deploy
```

**Note the outputs:**
- Lambda Function Name
- Lambda Function ARN
- API Gateway Endpoint URL

### 6. Invoke the Lambda

**Via AWS CLI:**
```bash
aws lambda invoke \
  --function-name genpr-lambda-function \
  --payload '{"prompt": "Add error handling to the login function"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

**Via API Gateway:**
```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/generate-pr \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add a README section about testing"}'
```

## Usage Examples

### Example 1: Add a New Function

```json
{
  "prompt": "Add a function called calculate_average that takes a list of numbers and returns their average. Add it to utils.py file."
}
```

### Example 2: Fix a Bug

```json
{
  "prompt": "Fix the bug in the login function where passwords are not being validated properly. Add proper validation checks."
}
```

### Example 3: Add Error Handling

```json
{
  "prompt": "Add try-except error handling to all database operations in the models.py file. Log errors appropriately."
}
```

### Example 4: Refactor Code

```json
{
  "prompt": "Refactor the UserService class to use dependency injection for the database connection instead of creating it internally."
}
```

### Example 5: Custom Base Branch

```json
{
  "prompt": "Add unit tests for the authentication module",
  "base_branch": "develop"
}
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REPO_TOKEN` | Yes | - | GitHub Personal Access Token with `repo` scope |
| `REPO_OWNER` | Yes | - | GitHub repository owner (username or organization) |
| `REPO_NAME` | Yes | - | GitHub repository name |
| `DEFAULT_BASE_BRANCH` | No | `main` | Default base branch for PRs |
| `LLM_PROVIDER` | Yes | `anthropic` | LLM provider: `anthropic` or `openai` |
| `LLM_MODEL` | Yes | `claude-3-5-sonnet-20241022` | LLM model identifier |
| `LLM_API_KEY` | Yes | - | API key for LLM provider |
| `LLM_TEMPERATURE` | No | `0.0` | Temperature for LLM generation |
| `LLM_MAX_TOKENS` | No | `4000` | Maximum tokens for LLM response |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### Lambda Configuration

- **Memory**: 2048 MB
- **Timeout**: 900 seconds (15 minutes)
- **Ephemeral Storage**: 2048 MB
- **Architecture**: x86_64
- **Runtime**: Container image (Python 3.11 + Node.js 20)

## Agent Workflow

The AI agent follows this systematic workflow:

1. **Understand Request**: Parses the user's natural language prompt
2. **Explore Repository**: Lists files and searches code to find relevant files
3. **Read Context**: Reads current file contents to understand existing code
4. **Plan Changes**: Reasons about what modifications are needed
5. **Create Branch**: Creates a new feature branch
6. **Make Changes**: Updates files with new content (can update multiple files)
7. **Create PR**: Opens a pull request with description of changes

## GitHub Actions CI/CD

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. **Test Job**: Runs on every push and PR
   - Linting (ruff)
   - Formatting check (black)
   - Type checking (mypy)
   - Unit tests (pytest)
   - Code coverage

2. **Deploy Job**: Runs on pushes to `main` branch
   - Builds container image
   - Deploys CDK stack to AWS
   - Runs smoke tests

### Required GitHub Secrets

Add these secrets to your GitHub repository:

- `AWS_ROLE_ARN`: IAM role ARN for OIDC authentication
- `AWS_ACCOUNT_ID`: AWS account ID
- `AWS_REGION`: AWS region (e.g., `us-east-1`)
- `REPO_TOKEN`: GitHub token (automatically provided)
- `REPO_OWNER`: Repository owner
- `REPO_NAME`: Repository name
- `LLM_PROVIDER`: `anthropic` or `openai`
- `LLM_MODEL`: Model identifier
- `LLM_API_KEY`: LLM API key
- `TEST_REPO_TOKEN`: Token for test repository (optional)
- `TEST_REPO_OWNER`: Test repository owner (optional)
- `TEST_REPO_NAME`: Test repository name (optional)

## Development

### Project Structure

```
GenPRLambda/
├── src/
│   ├── lambda_function.py          # Lambda handler
│   ├── agent/                      # LangChain agent logic
│   ├── mcp/                        # MCP client and tools
│   ├── config/                     # Configuration management
│   └── utils/                      # Utilities (logging, validation)
├── tests/                          # Unit tests
├── infrastructure/cdk/             # CDK infrastructure code
├── .github/workflows/              # GitHub Actions workflows
├── Dockerfile                      # Container image definition
├── requirements.txt                # Python dependencies
└── package.json                    # Node.js dependencies
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov pytest-asyncio ruff black mypy

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agent.py -v
```

### Linting and Formatting

```bash
# Run ruff linter
ruff check src/ tests/

# Run black formatter
black src/ tests/

# Run type checker
mypy src/
```

## Monitoring and Debugging

### CloudWatch Logs

View logs in CloudWatch:
```bash
aws logs tail /aws/lambda/genpr-lambda-function --follow
```

### Structured Logging

Logs are output as JSON with the following fields:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger`: Logger name
- `message`: Log message
- `correlation_id`: Unique ID for request tracking
- `stage`: Workflow stage (e.g., `agent_init`, `mcp_request`)
- `metadata`: Additional context

### Common Issues

**Issue: MCP server fails to start**
- Check that Node.js is installed in the container
- Verify GitHub token has correct permissions
- Check CloudWatch logs for subprocess errors

**Issue: Agent timeout**
- Consider breaking complex changes into smaller tasks
- Increase Lambda timeout (max 15 minutes)
- For very large changes, consider Step Functions

**Issue: GitHub API rate limits**
- Use GitHub App instead of PAT for higher rate limits
- Implement caching for repository exploration
- Add rate limit monitoring

## Cost Estimation

Approximate costs for AWS resources:

- **Lambda**: ~$0.20 per 1000 requests (15-minute execution)
- **API Gateway**: ~$3.50 per million requests
- **CloudWatch Logs**: ~$0.50 per GB ingested
- **ECR Storage**: ~$0.10 per GB per month

**Example**: 100 PR generations per month ≈ $2-3/month

**LLM API costs are separate** and depend on your provider and usage.

## Security Considerations

- **Secrets Management**: Store tokens in AWS Secrets Manager (recommended) or use environment variables
- **IAM Roles**: Use least-privilege permissions
- **Input Validation**: All prompts are validated and sanitized
- **GitHub Permissions**: Use GitHub App with fine-grained permissions instead of PAT
- **API Gateway**: Add authentication (API keys, Cognito, Lambda authorizers)
- **Rate Limiting**: Implement rate limiting on API Gateway
- **VPC**: Consider deploying Lambda in VPC for additional security

## Limitations

- **Lambda Timeout**: Maximum 15 minutes per execution
- **GitHub Rate Limits**: 5000 requests/hour with PAT
- **Container Size**: 10GB maximum image size
- **Complexity**: Very large codebases may require multiple iterations
- **Branch Conflicts**: Does not handle merge conflicts automatically

## Future Enhancements

- [ ] Async processing with SQS + Step Functions
- [ ] Multi-repository support
- [ ] PR review and iteration capabilities
- [ ] Code validation and testing before PR
- [ ] Slack/webhook notifications
- [ ] GitHub App authentication
- [ ] Streaming responses via WebSockets
- [ ] Support for other Git providers (GitLab, Bitbucket)

## Troubleshooting

### Enable Debug Logging

Set `LOG_LEVEL=DEBUG` in environment variables to see detailed logs.

### Test Locally with Docker

Build and run the container locally:

```bash
docker build -t genpr-lambda .

docker run -p 9000:8080 \
  -e REPO_TOKEN=xxx \
  -e REPO_OWNER=xxx \
  -e REPO_NAME=xxx \
  -e LLM_PROVIDER=anthropic \
  -e LLM_MODEL=claude-3-5-sonnet-20241022 \
  -e LLM_API_KEY=xxx \
  genpr-lambda

# In another terminal
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"prompt": "Add a hello world function"}'
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run linting and tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing issues and discussions
- Review CloudWatch logs for debugging

## Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain)
- Uses [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol)
- Powered by [Claude](https://www.anthropic.com/claude) or [OpenAI](https://openai.com/)
- Deployed with [AWS CDK](https://aws.amazon.com/cdk/)
