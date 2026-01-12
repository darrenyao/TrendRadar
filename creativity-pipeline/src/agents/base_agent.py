"""Base agent class for creativity pipeline.

Provides abstract base class for all pipeline agents with Claude Agent SDK integration.
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    # Message types
    AssistantMessage,
    ResultMessage,
    # Content block types
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    # Error types
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
)

logger = logging.getLogger(__name__)

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
                version="1.0.0",
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

        Raises:
            CLINotFoundError: If Claude Code CLI is not installed.
            ProcessError: If the Claude Code process fails.
            CLIJSONDecodeError: If response parsing fails.
        """
        # Get vault path for SDK directory access
        vault_path = os.environ.get("VAULT_PATH") or os.environ.get("OBSIDIAN_VAULT_PATH", "./vault")
        vault_abs_path = str(Path(vault_path).resolve())

        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=self.get_system_prompt(),
            mcp_servers={"obsidian": self._get_mcp_server()},
            # Allow Obsidian tools + web capabilities for deep analysis
            allowed_tools=[
                "mcp__obsidian__*",  # Obsidian read/write tools
                "WebFetch",           # Fetch web page content
                "WebSearch",          # Search the web
            ],
            cwd=vault_abs_path,  # Set working directory to vault
            add_dirs=[vault_abs_path],  # Grant read/write access to vault
        )

        try:
            async with ClaudeSDKClient(options) as client:
                await client.query(user_message)
                response_text = ""
                tool_calls = []  # Track tool usage for debugging

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text
                            elif isinstance(block, ThinkingBlock):
                                logger.debug(f"Agent thinking: {block.thinking[:100]}...")
                            elif isinstance(block, ToolUseBlock):
                                tool_calls.append(block.name)
                                logger.info(f"Tool call: {block.name}")
                                # Log tool input for debugging (truncate if too long)
                                input_str = str(block.input)[:200]
                                logger.debug(f"Tool input: {input_str}...")
                    elif isinstance(message, ResultMessage):
                        if message.total_cost_usd:
                            logger.info(
                                f"Agent completed: cost=${message.total_cost_usd:.4f}, "
                                f"turns={message.num_turns}, duration={message.duration_ms}ms"
                            )
                        if message.is_error:
                            logger.error(f"Agent error: {message.result}")

                # Log summary of agent execution
                logger.info(f"Tool calls made: {tool_calls}")
                if response_text:
                    # Log first 500 chars of response for debugging
                    preview = response_text[:500].replace('\n', ' ')
                    logger.info(f"Response preview: {preview}...")
                else:
                    logger.warning("Agent returned empty response")

                return response_text
        except CLINotFoundError:
            logger.error("Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code")
            raise
        except ProcessError as e:
            logger.error(f"Process failed with exit code {e.exit_code}: {e.stderr}")
            raise
        except CLIJSONDecodeError as e:
            logger.error(f"Failed to parse response: {e.line}")
            raise

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
