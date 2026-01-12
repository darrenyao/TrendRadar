"""
钉钉集成模块

提供创意流水线的钉钉交互能力：
- 消息收发
- 三次推送（早间/下午/晚间）
- 用户输入解析
"""

# 核心模块（无外部依赖）
from .message_context import MessageContext
from .pipeline_handler import PipelineCallbackHandler

# 可选模块（需要 DingTalk SDK）
try:
    from .dingtalk_auth import DingtalkAuth, get_auth
    HAS_AUTH = True
except ImportError:
    DingtalkAuth = None
    get_auth = None
    HAS_AUTH = False

try:
    from .reply_service import DingTalkReplyService, ContentType, reply_service
    HAS_REPLY = True
except ImportError:
    DingTalkReplyService = None
    ContentType = None
    reply_service = None
    HAS_REPLY = False

try:
    from .stream_client import DingTalkStreamManager, ConnectionStats
    HAS_STREAM = True
except ImportError:
    DingTalkStreamManager = None
    ConnectionStats = None
    HAS_STREAM = False

# DingTalkService 依赖 reply_service，但本身无 SDK 依赖
from .dingtalk_service import DingTalkService

__all__ = [
    # 核心（始终可用）
    "MessageContext",
    "PipelineCallbackHandler",
    "DingTalkService",
    # 认证（可选）
    "DingtalkAuth",
    "get_auth",
    "HAS_AUTH",
    # 回复服务（可选）
    "DingTalkReplyService",
    "ContentType",
    "reply_service",
    "HAS_REPLY",
    # 流式客户端（可选）
    "DingTalkStreamManager",
    "ConnectionStats",
    "HAS_STREAM",
]
