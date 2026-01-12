"""
钉钉集成模块

提供创意流水线的钉钉交互能力：
- 消息收发
- 三次推送（早间/下午/晚间）
- 用户输入解析
"""
from .dingtalk_auth import DingtalkAuth, get_auth
from .message_context import MessageContext
from .reply_service import DingTalkReplyService, ContentType, reply_service
from .pipeline_handler import PipelineCallbackHandler
from .dingtalk_service import DingTalkService
from .stream_client import DingTalkStreamManager, ConnectionStats

__all__ = [
    # 认证
    "DingtalkAuth",
    "get_auth",
    # 消息上下文
    "MessageContext",
    # 回复服务
    "DingTalkReplyService",
    "ContentType",
    "reply_service",
    # 流水线处理器
    "PipelineCallbackHandler",
    # 钉钉服务
    "DingTalkService",
    # 流式客户端
    "DingTalkStreamManager",
    "ConnectionStats",
]
