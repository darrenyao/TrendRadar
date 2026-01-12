"""
钉钉流式客户端管理器

通过 WebSocket 长连接接收钉钉消息推送，支持：
- 机器人消息回调（用户发送的文本消息）
- 卡片实例回调（用户点击卡片按钮）

Topic 说明：
- /v1.0/im/bot/messages/get      : 传统机器人消息
- /v1.0/graph/api/invoke         : AI Graph API（AI 助理模式）
- /v1.0/card/instances/callback  : 互动卡片按钮回调
"""
import os
import threading
import time
import atexit
import logging
from typing import Optional
from dataclasses import dataclass

try:
    from dingtalk_stream import DingTalkStreamClient, Credential
    HAS_DINGTALK_STREAM = True
except ImportError:
    HAS_DINGTALK_STREAM = False

logger = logging.getLogger(__name__)

# 默认 Topic 配置
# 注意：根据机器人类型选择正确的 topic
# - 普通机器人: /v1.0/im/bot/messages/get
# - AI 助理 (Graph API): /v1.0/graph/api/invoke
DEFAULT_STREAM_TOPIC = "/v1.0/graph/api/invoke"  # AI 助理模式
DEFAULT_CARD_CALLBACK_TOPIC = "/v1.0/card/instances/callback"


@dataclass
class ConnectionStats:
    """连接统计"""
    connection_attempts: int = 0
    successful_connections: int = 0
    last_connection_time: float = 0
    uptime: float = 0
    messages_received: int = 0


class DingTalkStreamManager:
    """钉钉流式客户端管理器

    通过 WebSocket 与钉钉服务器建立长连接，实时接收消息推送。
    """

    def __init__(self, handler, card_handler=None):
        """
        初始化管理器

        Args:
            handler: 消息处理器（PipelineCallbackHandler）
            card_handler: 卡片回调处理器（可选）
        """
        self.handler = handler
        self.card_handler = card_handler
        self.stream_client = None
        self.stop_event = threading.Event()
        self.stream_thread: Optional[threading.Thread] = None

        self.stats = ConnectionStats()

        # 从环境变量读取配置
        self.client_id = os.environ.get("DINGTALK_CLIENT_ID", "")
        self.client_secret = os.environ.get("DINGTALK_CLIENT_SECRET", "")

        # Topic 配置
        self.stream_topic = os.environ.get(
            "DINGTALK_STREAM_TOPIC", DEFAULT_STREAM_TOPIC
        )
        self.card_callback_topic = os.environ.get(
            "DINGTALK_CARD_CALLBACK_TOPIC", DEFAULT_CARD_CALLBACK_TOPIC
        )

        atexit.register(self.stop)

    def start_async(self) -> None:
        """在后台线程中启动客户端（非阻塞）"""
        if not HAS_DINGTALK_STREAM:
            logger.error("dingtalk_stream 库未安装，无法启动")
            return

        if self.stream_thread and self.stream_thread.is_alive():
            logger.warning("钉钉流客户端已经在运行中")
            return

        if not self.client_id or not self.client_secret:
            logger.error(
                "缺少钉钉配置，请设置 DINGTALK_CLIENT_ID 和 DINGTALK_CLIENT_SECRET"
            )
            return

        logger.info("正在后台启动钉钉流客户端...")

        self.stream_thread = threading.Thread(
            target=self._run_stream_client,
            name="DingTalkStreamThread",
            daemon=True
        )
        self.stream_thread.start()

        time.sleep(1)

        if self.stream_thread.is_alive():
            logger.info("✅ 钉钉流客户端已在后台启动")
        else:
            logger.error("❌ 钉钉流客户端启动失败")

    def _run_stream_client(self) -> None:
        """在线程中运行流客户端

        建立 WebSocket 长连接，注册消息和卡片回调处理器。
        """
        try:
            credential = Credential(self.client_id, self.client_secret)
            self.stream_client = DingTalkStreamClient(credential)

            # 注册消息回调处理器
            self.stream_client.register_callback_handler(
                self.stream_topic, self.handler
            )
            logger.info(f"📨 已注册消息回调: {self.stream_topic}")

            # 注册卡片回调处理器（如果提供）
            if self.card_handler:
                self.stream_client.register_callback_handler(
                    self.card_callback_topic, self.card_handler
                )
                logger.info(f"🃏 已注册卡片回调: {self.card_callback_topic}")

            self.stats.connection_attempts += 1
            self.stats.last_connection_time = time.time()

            logger.info("🔗 钉钉流客户端正在连接...")
            logger.info(f"   Client ID: {self.client_id[:8]}...")
            logger.info(f"   Stream Topic: {self.stream_topic}")

            # 阻塞运行，保持 WebSocket 长连接
            self.stream_client.start_forever()

        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"钉钉流客户端运行时出错: {e}", exc_info=True)
        finally:
            logger.info("钉钉流客户端已停止")

    def stop(self) -> None:
        """优雅关闭客户端"""
        if self.stop_event.is_set():
            return

        logger.info("正在关闭钉钉流客户端...")
        self.stop_event.set()

        if self.stream_client and hasattr(self.stream_client, 'close'):
            try:
                self.stream_client.close()
            except Exception as e:
                logger.warning(f"关闭流客户端时出错: {e}")

        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            if self.stream_thread.is_alive():
                logger.warning("钉钉流客户端线程未能在5秒内结束")
            else:
                logger.info("✅ 钉钉流客户端已优雅关闭")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return (
            self.stream_thread is not None
            and self.stream_thread.is_alive()
            and not self.stop_event.is_set()
        )

    def get_stats(self) -> ConnectionStats:
        """获取连接统计"""
        if self.is_running():
            self.stats.uptime = time.time() - self.stats.last_connection_time
        return self.stats
