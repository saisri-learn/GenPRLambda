"""Tests for LangChain agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.langchain_agent import CodeModificationAgent, create_and_execute_agent
from src.config.settings import Settings
from src.mcp.client import REPOMCPClient


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.REPO_token = "test_token"
    settings.REPO_owner = "test_owner"
    settings.REPO_NAME = "test_repo"
    settings.llm_provider = "anthropic"
    settings.llm_model = "claude-3-5-sonnet-20241022"
    settings.llm_api_key = "test_api_key"
    settings.llm_temperature = 0.0
    settings.llm_max_tokens = 4000
    return settings


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    client = MagicMock(spec=REPOMCPClient)
    client.list_files = AsyncMock(return_value=[{"name": "test.py", "type": "file"}])
    client.read_file = AsyncMock(return_value="print('hello')")
    client.create_branch = AsyncMock(return_value={"ref": "refs/heads/test"})
    client.update_file = AsyncMock(return_value={"commit": "abc123"})
    client.create_pull_request = AsyncMock(
        return_value={"number": 1, "html_url": "https://REPO.com/test/test/pull/1"}
    )
    return client


def test_agent_initialization(mock_mcp_client, mock_settings):
    """Test agent initialization."""
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    assert agent.mcp_client == mock_mcp_client
    assert agent.settings == mock_settings
    assert len(agent.tools) > 0
    assert agent.llm is not None
    assert agent.agent_executor is not None


def test_create_llm_anthropic(mock_mcp_client, mock_settings):
    """Test creating Anthropic LLM."""
    mock_settings.llm_provider = "anthropic"
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    from langchain_anthropic import ChatAnthropic
    assert isinstance(agent.llm, ChatAnthropic)


def test_create_llm_openai(mock_mcp_client, mock_settings):
    """Test creating OpenAI LLM."""
    mock_settings.llm_provider = "openai"
    mock_settings.llm_model = "gpt-4"
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    from langchain_openai import ChatOpenAI
    assert isinstance(agent.llm, ChatOpenAI)


def test_create_llm_invalid_provider(mock_mcp_client, mock_settings):
    """Test creating LLM with invalid provider."""
    mock_settings.llm_provider = "invalid"

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        CodeModificationAgent(mock_mcp_client, mock_settings)


@pytest.mark.asyncio
async def test_agent_execute_success(mock_mcp_client, mock_settings):
    """Test successful agent execution."""
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    # Mock the agent executor
    mock_result = {
        "output": "Successfully created PR #1\nURL: https://REPO.com/test/test/pull/1"
    }

    with patch.object(agent.agent_executor, "ainvoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_result

        result = await agent.execute("Add a hello world function")

        assert result["success"] is True
        assert "output" in result
        assert result["pr_url"] == "https://REPO.com/test/test/pull/1"


@pytest.mark.asyncio
async def test_agent_execute_failure(mock_mcp_client, mock_settings):
    """Test agent execution failure."""
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    with patch.object(agent.agent_executor, "ainvoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = Exception("Test error")

        result = await agent.execute("Add a hello world function")

        assert result["success"] is False
        assert "error" in result


def test_extract_pr_url(mock_mcp_client, mock_settings):
    """Test extracting PR URL from output."""
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    output = "Created PR at https://REPO.com/owner/repo/pull/123"
    pr_url = agent._extract_pr_url(output)

    assert pr_url == "https://REPO.com/owner/repo/pull/123"


def test_extract_pr_url_no_match(mock_mcp_client, mock_settings):
    """Test extracting PR URL when none exists."""
    agent = CodeModificationAgent(mock_mcp_client, mock_settings)

    output = "No PR created"
    pr_url = agent._extract_pr_url(output)

    assert pr_url is None


@pytest.mark.asyncio
async def test_create_and_execute_agent(mock_settings):
    """Test convenience function for agent execution."""
    mock_client = MagicMock(spec=REPOMCPClient)

    with patch("src.agent.langchain_agent.CodeModificationAgent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value={"success": True})
        mock_agent_class.return_value = mock_agent

        result = await create_and_execute_agent(
            mock_client,
            mock_settings,
            "Test prompt"
        )

        assert result["success"] is True
        mock_agent.execute.assert_called_once_with("Test prompt")
