"""Tests for MCP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp.client import GitHubMCPClient, MCPClientError


@pytest.fixture
def mcp_client():
    """Create a test MCP client."""
    return GitHubMCPClient(
        github_token="test_token",
        github_owner="test_owner",
        github_repo="test_repo",
    )


@pytest.mark.asyncio
async def test_start_mcp_server(mcp_client):
    """Test starting the MCP server."""
    with patch("src.mcp.client.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        await mcp_client.start()

        assert mcp_client._started is True
        assert mcp_client.process == mock_process
        mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_stop_mcp_server(mcp_client):
    """Test stopping the MCP server."""
    mock_process = MagicMock()
    mcp_client.process = mock_process
    mcp_client._started = True

    await mcp_client.stop()

    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    assert mcp_client._started is False


@pytest.mark.asyncio
async def test_send_request_success(mcp_client):
    """Test sending a successful MCP request."""
    mock_process = MagicMock()
    mock_stdin = MagicMock()
    mock_stdout = MagicMock()

    mock_stdout.readline.return_value = b'{"jsonrpc":"2.0","id":1,"result":{"files":[]}}\n'
    mock_process.stdin = mock_stdin
    mock_process.stdout = mock_stdout

    mcp_client.process = mock_process

    result = await mcp_client._send_request("tools/call", {"name": "test"})

    assert isinstance(result, dict)
    mock_stdin.write.assert_called_once()
    mock_stdin.flush.assert_called_once()


@pytest.mark.asyncio
async def test_send_request_error(mcp_client):
    """Test sending a request that returns an error."""
    mock_process = MagicMock()
    mock_stdin = MagicMock()
    mock_stdout = MagicMock()

    mock_stdout.readline.return_value = b'{"jsonrpc":"2.0","id":1,"error":{"message":"Test error"}}\n'
    mock_process.stdin = mock_stdin
    mock_process.stdout = mock_stdout

    mcp_client.process = mock_process

    with pytest.raises(MCPClientError, match="Test error"):
        await mcp_client._send_request("tools/call", {"name": "test"})


@pytest.mark.asyncio
async def test_list_files(mcp_client):
    """Test listing files."""
    with patch.object(mcp_client, "_send_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"files": [{"name": "test.py", "type": "file"}]}

        result = await mcp_client.list_files()

        assert len(result) == 1
        assert result[0]["name"] == "test.py"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_read_file(mcp_client):
    """Test reading a file."""
    with patch.object(mcp_client, "_send_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"content": "print('hello')"}

        result = await mcp_client.read_file("test.py")

        assert result == "print('hello')"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_create_branch(mcp_client):
    """Test creating a branch."""
    with patch.object(mcp_client, "_send_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"ref": "refs/heads/test-branch"}

        result = await mcp_client.create_branch("test-branch", "main")

        assert "ref" in result
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_context_manager(mcp_client):
    """Test using MCP client as async context manager."""
    with patch.object(mcp_client, "start", new_callable=AsyncMock) as mock_start, \
         patch.object(mcp_client, "stop", new_callable=AsyncMock) as mock_stop:

        async with mcp_client:
            pass

        mock_start.assert_called_once()
        mock_stop.assert_called_once()
