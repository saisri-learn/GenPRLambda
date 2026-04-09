"""LangChain agent implementation for code modification."""

from typing import Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.agent.prompts import REACT_PROMPT_TEMPLATE, SYSTEM_PROMPT
from src.config.settings import Settings
from src.mcp.client import REPOMCPClient
from src.mcp.tools import create_langchain_tools
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeModificationAgent:
    """Agent for modifying code based on natural language prompts."""

    def __init__(
        self,
        mcp_client: REPOMCPClient,
        settings: Settings,
    ) -> None:
        """Initialize the code modification agent.

        Args:
            mcp_client: Initialized REPO MCP client
            settings: Application settings
        """
        self.mcp_client = mcp_client
        self.settings = settings
        self.tools = create_langchain_tools(mcp_client)
        self.llm = self._create_llm()
        self.agent_executor = self._create_agent_executor()

    def _create_llm(self) -> ChatAnthropic | ChatOpenAI:
        """Create the LLM instance based on configuration.

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If provider is not supported
        """
        logger.info(
            f"Initializing LLM: {self.settings.llm_provider}/{self.settings.llm_model}",
            stage="agent_init",
        )

        if self.settings.llm_provider == "anthropic":
            return ChatAnthropic(
                model=self.settings.llm_model,
                anthropic_api_key=self.settings.llm_api_key,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
        elif self.settings.llm_provider == "openai":
            return ChatOpenAI(
                model=self.settings.llm_model,
                openai_api_key=self.settings.llm_api_key,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    def _create_agent_executor(self) -> AgentExecutor:
        """Create the agent executor with ReAct pattern.

        Returns:
            Configured AgentExecutor instance
        """
        logger.info("Creating ReAct agent executor", stage="agent_init")

        # Create prompt template
        prompt = PromptTemplate.from_template(
            template=f"{SYSTEM_PROMPT}\n\n{REACT_PROMPT_TEMPLATE}"
        )

        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=30,  # Limit iterations to prevent infinite loops
            max_execution_time=800,  # 13+ minutes (leave buffer for Lambda timeout)
        )

        return agent_executor

    async def execute(self, prompt: str) -> dict[str, Any]:
        """Execute the agent with a user prompt.

        Args:
            prompt: User's natural language instruction

        Returns:
            Dictionary with execution results including:
                - success: bool
                - output: str (agent's final answer)
                - pr_url: str (if PR was created)
                - error: str (if execution failed)
        """
        logger.info(
            "Starting agent execution",
            stage="agent_execute",
            metadata={"prompt_length": len(prompt)},
        )

        try:
            # Execute the agent
            result = await self.agent_executor.ainvoke(
                {"input": prompt},
            )

            output = result.get("output", "")

            # Try to extract PR URL from output
            pr_url = self._extract_pr_url(output)

            logger.info(
                "Agent execution completed successfully",
                stage="agent_execute",
                metadata={"pr_url": pr_url, "output_length": len(output)},
            )

            return {
                "success": True,
                "output": output,
                "pr_url": pr_url,
            }

        except Exception as e:
            logger.error(
                f"Agent execution failed: {e}",
                stage="agent_execute",
                exc_info=True,
            )

            return {
                "success": False,
                "error": str(e),
                "output": f"Failed to execute agent: {e}",
            }

    def _extract_pr_url(self, output: str) -> str | None:
        """Extract PR URL from agent output.

        Args:
            output: Agent's output text

        Returns:
            PR URL if found, None otherwise
        """
        import re

        # Look for REPO PR URLs
        pr_url_pattern = r"https://REPO\.com/[\w-]+/[\w-]+/pull/\d+"
        match = re.search(pr_url_pattern, output)

        if match:
            return match.group(0)

        return None


async def create_and_execute_agent(
    mcp_client: REPOMCPClient,
    settings: Settings,
    prompt: str,
) -> dict[str, Any]:
    """Create and execute an agent with a single prompt.

    This is a convenience function for one-shot agent execution.

    Args:
        mcp_client: Initialized REPO MCP client
        settings: Application settings
        prompt: User's natural language instruction

    Returns:
        Dictionary with execution results
    """
    agent = CodeModificationAgent(mcp_client, settings)
    return await agent.execute(prompt)
