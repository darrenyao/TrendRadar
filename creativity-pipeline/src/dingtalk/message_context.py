"""
消息上下文模块（精简版）
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MessageContext:
    user_id: str
    uid: int
    org_id: int
    content: str
    user_name: Optional[str] = None
    sender_union_id: Optional[str] = None
    is_group_chat: bool = False
    group_name: Optional[str] = None
    conversation_id: Optional[str] = None
    conversation_token: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_dingtalk_message(cls, message: Dict[str, Any]) -> 'MessageContext':
        user_id = message.get("senderId", "")
        uid = int(message.get("uid", 0))
        org_id = int(message.get("orgId", 0))
        text_obj = message.get("text", {})
        content = text_obj.get("content", "") if isinstance(text_obj, dict) else ""
        return cls(
            user_id=user_id,
            uid=uid,
            org_id=org_id,
            content=content,
            user_name=message.get("senderNick", "Unknown"),
            sender_union_id=message.get("senderUnionId"),
            is_group_chat=message.get("conversationType") == "2",
            group_name=message.get("conversationTitle"),
            conversation_id=message.get("conversationId"),
            conversation_token=message.get("conversationToken"),
            timestamp=message.get("createAt"),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "user_id": self.user_id,
            "uid": self.uid,
            "org_id": self.org_id,
            "content": self.content,
            "user_name": self.user_name,
            "is_group_chat": self.is_group_chat,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
        }
        if self.is_group_chat and self.group_name:
            data["group_name"] = self.group_name
        if self.conversation_token:
            data["conversation_token"] = self.conversation_token
        return data
