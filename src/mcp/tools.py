"""LangChain tools wrapping REPO MCP client operations."""

import asyncio
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.mcp.client import REPOMCPClient


# Pydantic models for tool inputs


class ListFilesInput(BaseModel):
    """Input for list_repository_files tool."""

    path: str = Field(
        default="",
        description="Repository path to list files from. Use empty string for root directory.",
    )


class ReadFileInput(BaseModel):
    """Input for read_file_contents tool."""

    path: str = Field(description="File path in the repository to read")


class SearchCodeInput(BaseModel):
    """Input for search_code tool."""

    query: str = Field(description="Search query to find code in the repository")


class CreateBranchInput(BaseModel):
    """Input for create_branch tool."""

    branch_name: str = Field(description="Name for the new branch (e.g., 'feature/add-logging')")
    base_branch: str = Field(
        default="main",
        description="Base branch to create from (default: main)",
    )


class UpdateFileInput(BaseModel):
    """Input for update_file tool."""

    path: str = Field(description="File path in the repository")
    content: str = Field(description="New content for the file")
    branch: str = Field(description="Branch to commit the change to")
    message: str = Field(description="Commit message describing the change")


class CreatePullRequestInput(BaseModel):
    """Input for create_pull_request tool."""

    title: str = Field(description="Title for the pull request")
    body: str = Field(description="Description of changes in the pull request")
    head_branch: str = Field(description="Source branch containing the changes")
    base_branch: str = Field(
        default="main",
        description="Target branch to merge into (default: main)",
    )


def create_langchain_tools(mcp_client: REPOMCPClient) -> list[StructuredTool]:
    """Create LangChain tools from MCP client.

    Args:
        mcp_client: Initialized REPO MCP client

    Returns:
        List of LangChain StructuredTool instances
    """

    def run_async(coro: Callable[..., Any]) -> Callable[..., Any]:
        """Helper to run async functions in sync context."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new one
                return asyncio.run(coro(*args, **kwargs))
            else:
                return loop.run_until_complete(coro(*args, **kwargs))

        return wrapper

    # Tool 1: List repository files
    async def list_files_async(path: str = "") -> str:
        """List files in the repository at the specified path."""
        try:
            files = await mcp_client.list_files(path)
            if not files:
                return f"No files found at path: {path or '/'}"

            file_list = "\n".join(
                [
                    f"- {f.get('name', 'unknown')} ({'dir' if f.get('type') == 'dir' else 'file'})"
                    for f in files
                ]
            )
            return f"Files at {path or '/'}:\n{file_list}"
        except Exception as e:
            return f"Error listing files: {str(e)}"

    list_files_tool = StructuredTool(
        name="list_repository_files",
        description=(
            "List files and directories in the REPO repository. "
            "Use this to explore the repository structure and find relevant files. "
            "Provide a path to list contents of a specific directory, or leave empty for root."
        ),
        func=run_async(list_files_async),
        args_schema=ListFilesInput,
    )

    # Tool 2: Read file contents
    async def read_file_async(path: str) -> str:
        """Read the contents of a file from the repository."""
        try:
            content = await mcp_client.read_file(path)
            if not content:
                return f"File is empty or not found: {path}"
            return f"Contents of {path}:\n\n{content}"
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

    read_file_tool = StructuredTool(
        name="read_file_contents",
        description=(
            "Read the contents of a specific file from the REPO repository. "
            "Use this to understand the current code before making changes. "
            "Provide the full file path relative to the repository root."
        ),
        func=run_async(read_file_async),
        args_schema=ReadFileInput,
    )

    # Tool 3: Search code
    async def search_code_async(query: str) -> str:
        """Search for code in the repository."""
        try:
            results = await mcp_client.search_code(query)
            if not results:
                return f"No results found for query: {query}"

            search_results = "\n".join(
                [
                    f"- {r.get('path', 'unknown')}: {r.get('text_matches', [''])[0][:100]}"
                    for r in results[:10]  # Limit to top 10 results
                ]
            )
            return f"Search results for '{query}':\n{search_results}"
        except Exception as e:
            return f"Error searching code: {str(e)}"

    search_code_tool = StructuredTool(
        name="search_code",
        description=(
            "Search for code patterns or keywords in the REPO repository. "
            "Use this to find relevant files when you're unsure of their exact location. "
            "Returns file paths and matching code snippets."
        ),
        func=run_async(search_code_async),
        args_schema=SearchCodeInput,
    )

    # Tool 4: Create branch
    async def create_branch_async(branch_name: str, base_branch: str = "main") -> str:
        """Create a new branch in the repository."""
        try:
            result = await mcp_client.create_branch(branch_name, base_branch)
            return f"Successfully created branch '{branch_name}' from '{base_branch}'. Details: {result}"
        except Exception as e:
            return f"Error creating branch '{branch_name}': {str(e)}"

    create_branch_tool = StructuredTool(
        name="create_branch",
        description=(
            "Create a new branch in the REPO repository. "
            "Use this before making any file changes to work in an isolated branch. "
            "Choose a descriptive branch name like 'feature/add-logging' or 'fix/auth-bug'."
        ),
        func=run_async(create_branch_async),
        args_schema=CreateBranchInput,
    )

    # Tool 5: Update file
    async def update_file_async(
        path: str,
        content: str,
        branch: str,
        message: str,
    ) -> str:
        """Update or create a file in the repository."""
        try:
            result = await mcp_client.update_file(path, content, branch, message)
            return f"Successfully updated file '{path}' in branch '{branch}'. Commit: {message}"
        except Exception as e:
            return f"Error updating file '{path}': {str(e)}"

    update_file_tool = StructuredTool(
        name="update_file",
        description=(
            "Update or create a file in the REPO repository. "
            "Use this to make code changes after creating a branch. "
            "Provide the complete new file content (not a diff). "
            "Can be called multiple times to update different files."
        ),
        func=run_async(update_file_async),
        args_schema=UpdateFileInput,
    )

    # Tool 6: Create pull request
    async def create_pr_async(
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> str:
        """Create a pull request in the repository."""
        try:
            result = await mcp_client.create_pull_request(title, body, head_branch, base_branch)
            pr_url = result.get("html_url", "")
            pr_number = result.get("number", "")
            return (
                f"Successfully created pull request #{pr_number}: {title}\n"
                f"URL: {pr_url}\n"
                f"Branch: {head_branch} -> {base_branch}"
            )
        except Exception as e:
            return f"Error creating pull request: {str(e)}"

    create_pr_tool = StructuredTool(
        name="create_pull_request",
        description=(
            "Create a pull request in the REPO repository. "
            "Use this as the final step after making all file changes. "
            "Provide a clear title and detailed description of the changes made."
        ),
        func=run_async(create_pr_async),
        args_schema=CreatePullRequestInput,
    )

    return [
        list_files_tool,
        read_file_tool,
        search_code_tool,
        create_branch_tool,
        update_file_tool,
        create_pr_tool,
    ]
