"""Agent layer for creativity pipeline.

Provides AI-powered agents for the creativity pipeline:
- InputFeederAgent: Transform news into cards
- IdeaFactoryAgent: Generate ideas from cards
- MVPRunnerAgent: Design experiments from ideas

Preprocessing utilities (no SDK dependency):
- NewsPreprocessor: Deduplicate and cluster news
- NewsCluster: Cluster data structure
"""

# Preprocessing utilities (no SDK dependency)
from .news_preprocessor import NewsPreprocessor, NewsCluster

# Check if Claude Agent SDK is available
try:
    from claude_agent_sdk import ClaudeSDKClient
    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False

# Core classes (with SDK dependency protection)
if HAS_CLAUDE_SDK:
    from .base_agent import BaseAgent
    from .input_feeder import InputFeederAgent
    from .idea_factory import IdeaFactoryAgent
    from .mvp_runner import MVPRunnerAgent
else:
    BaseAgent = None
    InputFeederAgent = None
    IdeaFactoryAgent = None
    MVPRunnerAgent = None

# Tools can be imported separately (they have their own SDK guard)
try:
    from .tools.obsidian_tools import get_all_tools
except ImportError:
    get_all_tools = None

__all__ = [
    # SDK availability flag
    "HAS_CLAUDE_SDK",
    # Preprocessing (no SDK dependency)
    "NewsPreprocessor",
    "NewsCluster",
    # Base
    "BaseAgent",
    # Agents
    "InputFeederAgent",
    "IdeaFactoryAgent",
    "MVPRunnerAgent",
    # Tools
    "get_all_tools",
]
