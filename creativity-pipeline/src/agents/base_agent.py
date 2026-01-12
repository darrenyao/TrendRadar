"""Base agent class for creativity pipeline.

Provides abstract base class for all pipeline agents with Claude Agent SDK integration.
"""
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server

from .tools.obsidian_tools import get_all_tools


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents.

    Provides common functionality:
    - MCP server setup with Obsidian tools
    - ClaudeSDKClient integration
    - Message processing via run() method
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize base agent.

        Args:
            model: Claude model to use. Defaults to claude-sonnet-4-20250514.
        """
        self.model = model
        self._mcp_server = None

    def _get_mcp_server(self):
        """Get or create MCP server with Obsidian tools.

        Returns:
            MCP server instance configured with Obsidian tools.
        """
        if self._mcp_server is None:
            self._mcp_server = create_sdk_mcp_server(
                name="obsidian",
                tools=get_all_tools()
            )
        return self._mcp_server

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent-specific system prompt.

        Subclasses must implement this to provide domain-specific instructions.

        Returns:
            System prompt string for the agent.
        """
        pass

    async def run(self, user_message: str) -> str:
        """Execute agent with user message.

        Sets up ClaudeSDKClient with MCP tools and processes the message.

        Args:
            user_message: The message to process.

        Returns:
            Agent response text.
        """
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.get_system_prompt(),
            mcp_servers={"obsidian": self._get_mcp_server()},
            allowed_tools=["mcp__obsidian__*"]
        )

        async with ClaudeSDKClient(options) as client:
            await client.query(user_message)
            response_text = ""
            async for message in client.receive_response():
                if hasattr(message, 'text'):
                    response_text += message.text
            return response_text

    async def run_with_data(self, user_message: str, data: Dict[str, Any]) -> str:
        """Execute agent with user message and additional data context.

        Formats data as JSON and appends to the user message for context.

        Args:
            user_message: The message to process.
            data: Additional structured data to include in context.

        Returns:
            Agent response text.
        """
        context = f"{user_message}\n\n数据:\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"
        return await self.run(context)
