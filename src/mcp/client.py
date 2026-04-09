"""MCP client for GitHub operations via subprocess communication."""

import asyncio
import json
import subprocess
import sys
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""

    pass


class GitHubMCPClient:
    """Client for communicating with GitHub MCP server via stdio."""

    def __init__(self, REPO_TOKEN: str, REPO_OWNER: str, REPO_NAME: str) -> None:
        """Initialize the MCP client.

        Args:
            REPO_TOKEN: GitHub Personal Access Token
            REPO_OWNER: GitHub repository owner
            REPO_NAME: GitHub repository name
        """
        self.REPO_TOKEN = REPO_TOKEN
        self.REPO_OWNER = REPO_OWNER
        self.REPO_NAME = REPO_NAME
        self.process: subprocess.Popen[bytes] | None = None
        self.request_id = 0
        self._started = False

    async def start(self) -> None:
        """Start the MCP server subprocess."""
        if self._started and self.process and self.process.poll() is None:
            logger.debug("MCP server already running", stage="mcp_start")
            return

        try:
            logger.info("Starting GitHub MCP server", stage="mcp_start")

            # Set environment variables for the MCP server
            env = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.REPO_TOKEN,
                "PATH": sys.path[0],  # Ensure node is in PATH
            }

            # Start the MCP server process
            # The server should be installed via npm in the container
            self.process = subprocess.Popen(
                ["npx", "-y", "@modelcontextprotocol/server-github"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
            )

            self._started = True
            logger.info(
                "GitHub MCP server started successfully",
                stage="mcp_start",
                metadata={"pid": self.process.pid},
            )

        except Exception as e:
            logger.error(
                f"Failed to start MCP server: {e}",
                stage="mcp_start",
                exc_info=True,
            )
            raise MCPClientError(f"Failed to start MCP server: {e}") from e

    async def stop(self) -> None:
        """Stop the MCP server subprocess."""
        if self.process:
            logger.info("Stopping GitHub MCP server", stage="mcp_stop")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MCP server did not terminate, killing", stage="mcp_stop")
                self.process.kill()
            self._started = False

    def _get_next_request_id(self) -> int:
        """Get the next request ID."""
        self.request_id += 1
        return self.request_id

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Response dictionary

        Raises:
            MCPClientError: If request fails
        """
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise MCPClientError("MCP server not started")

        request_id = self._get_next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            self.process.stdin.flush()

            logger.debug(
                f"Sent MCP request: {method}",
                stage="mcp_request",
                metadata={"method": method, "request_id": request_id},
            )

            # Read response
            response_line = self.process.stdout.readline().decode()
            if not response_line:
                raise MCPClientError("No response from MCP server")

            response = json.loads(response_line)

            # Check for errors
            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                raise MCPClientError(f"MCP server error: {error_msg}")

            logger.debug(
                f"Received MCP response: {method}",
                stage="mcp_response",
                metadata={"method": method, "request_id": request_id},
            )

            return response.get("result", {})

        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response from MCP server: {e}") from e
        except Exception as e:
            logger.error(
                f"MCP request failed: {e}",
                stage="mcp_request",
                metadata={"method": method},
                exc_info=True,
            )
            raise MCPClientError(f"MCP request failed: {e}") from e

    async def list_files(self, path: str = "") -> list[dict[str, Any]]:
        """List files in the repository.

        Args:
            path: Repository path (default: root)

        Returns:
            List of file information dictionaries
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "list_files",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "path": path,
                },
            },
        )
        return result.get("files", [])

    async def read_file(self, path: str) -> str:
        """Read file contents from the repository.

        Args:
            path: File path in repository

        Returns:
            File contents as string
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "get_file_contents",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "path": path,
                },
            },
        )
        return result.get("content", "")

    async def search_code(self, query: str) -> list[dict[str, Any]]:
        """Search for code in the repository.

        Args:
            query: Search query

        Returns:
            List of search result dictionaries
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "search_code",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "query": query,
                },
            },
        )
        return result.get("results", [])

    async def create_branch(self, branch_name: str, base_branch: str = "main") -> dict[str, Any]:
        """Create a new branch.

        Args:
            branch_name: Name for the new branch
            base_branch: Base branch to create from

        Returns:
            Branch creation result
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "create_branch",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "branch": branch_name,
                    "from_branch": base_branch,
                },
            },
        )
        return result

    async def update_file(
        self,
        path: str,
        content: str,
        branch: str,
        message: str,
    ) -> dict[str, Any]:
        """Update or create a file in the repository.

        Args:
            path: File path in repository
            content: New file content
            branch: Branch to commit to
            message: Commit message

        Returns:
            Commit result
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "push_files",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "branch": branch,
                    "files": [{"path": path, "content": content}],
                    "message": message,
                },
            },
        )
        return result

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch

        Returns:
            Pull request information
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": "create_pull_request",
                "arguments": {
                    "owner": self.REPO_OWNER,
                    "repo": self.REPO_NAME,
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": base_branch,
                },
            },
        )
        return result

    async def __aenter__(self) -> "GitHubMCPClient":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()
