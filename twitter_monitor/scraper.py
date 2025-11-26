"""
Twitter Scraper - 使用browser-use抓取Twitter帖子

使用浏览器自动化技术抓取指定用户的Twitter/X帖子内容
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Optional

import pytz

# browser-use 相关导入
try:
    from browser_use import Agent, Browser, BrowserConfig
    from langchain_openai import ChatOpenAI

    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("[警告] browser-use 未安装，请运行: pip install browser-use langchain-openai")


class TwitterPost:
    """Twitter帖子数据类"""

    def __init__(
        self,
        post_id: str,
        author: str,
        author_handle: str,
        content: str,
        timestamp: datetime,
        likes: int = 0,
        retweets: int = 0,
        replies: int = 0,
        url: str = "",
        media_urls: list = None,
    ):
        self.post_id = post_id
        self.author = author
        self.author_handle = author_handle
        self.content = content
        self.timestamp = timestamp
        self.likes = likes
        self.retweets = retweets
        self.replies = replies
        self.url = url
        self.media_urls = media_urls or []

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "author": self.author,
            "author_handle": self.author_handle,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "likes": self.likes,
            "retweets": self.retweets,
            "replies": self.replies,
            "url": self.url,
            "media_urls": self.media_urls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TwitterPost":
        data = data.copy()
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class TwitterScraper:
    """
    Twitter抓取器 - 使用browser-use进行浏览器自动化抓取

    使用方法:
        scraper = TwitterScraper(
            llm_base_url="https://api.openai.com/v1",
            llm_api_key="your-api-key",
            llm_model="gpt-4o"
        )
        posts = await scraper.scrape_user_posts("elonmusk", max_posts=20)
    """

    def __init__(
        self,
        llm_base_url: str = None,
        llm_api_key: str = None,
        llm_model: str = "gpt-4o",
        headless: bool = True,
        browser_path: str = None,
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化Twitter抓取器

        Args:
            llm_base_url: LLM API base URL (OpenAI兼容)
            llm_api_key: LLM API密钥
            llm_model: LLM模型名称
            headless: 是否使用无头模式
            browser_path: 浏览器可执行文件路径
            timezone: 时区设置
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "browser-use 未安装，请运行: pip install browser-use langchain-openai"
            )

        self.llm_base_url = llm_base_url or os.getenv(
            "TWITTER_LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.llm_api_key = llm_api_key or os.getenv("TWITTER_LLM_API_KEY", "")
        self.llm_model = llm_model or os.getenv("TWITTER_LLM_MODEL", "gpt-4o")
        self.headless = headless
        self.browser_path = browser_path
        self.timezone = pytz.timezone(timezone)

        # 初始化LLM
        self.llm = ChatOpenAI(
            model=self.llm_model,
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            temperature=0,
        )

    async def _create_browser(self) -> Browser:
        """创建浏览器实例"""
        config = BrowserConfig(
            headless=self.headless,
            chrome_instance_path=self.browser_path,
        )
        return Browser(config=config)

    async def scrape_user_posts(
        self, username: str, max_posts: int = 20, include_replies: bool = False
    ) -> list[TwitterPost]:
        """
        抓取指定用户的Twitter帖子

        Args:
            username: Twitter用户名（不含@符号）
            max_posts: 最大抓取帖子数
            include_replies: 是否包含回复

        Returns:
            帖子列表
        """
        browser = await self._create_browser()

        try:
            # 构建抓取任务描述
            task = f"""
            请访问 Twitter/X 用户 @{username} 的个人主页：https://x.com/{username}

            任务目标：获取该用户最近的 {max_posts} 条帖子信息

            请执行以下步骤：
            1. 访问用户主页 https://x.com/{username}
            2. 等待页面加载完成
            3. 向下滚动页面以加载更多帖子（如果需要）
            4. 收集每条帖子的以下信息：
               - 帖子内容（完整文本）
               - 发布时间
               - 点赞数
               - 转发数
               - 评论数
               - 帖子链接

            {"包含用户的回复帖子。" if include_replies else "只收集原创帖子，跳过回复。"}

            请将收集到的帖子信息以JSON格式返回，格式如下：
            {{
                "posts": [
                    {{
                        "content": "帖子内容",
                        "timestamp": "发布时间",
                        "likes": 点赞数,
                        "retweets": 转发数,
                        "replies": 评论数,
                        "url": "帖子链接"
                    }}
                ]
            }}
            """

            agent = Agent(task=task, llm=self.llm, browser=browser)

            result = await agent.run()

            # 解析结果
            posts = self._parse_agent_result(result, username)
            return posts[:max_posts]

        except Exception as e:
            print(f"[错误] 抓取 @{username} 的帖子失败: {e}")
            return []
        finally:
            await browser.close()

    async def scrape_multiple_users(
        self, usernames: list[str], max_posts_per_user: int = 10
    ) -> dict[str, list[TwitterPost]]:
        """
        抓取多个用户的帖子

        Args:
            usernames: 用户名列表
            max_posts_per_user: 每个用户最大抓取数

        Returns:
            用户名到帖子列表的映射
        """
        results = {}
        for username in usernames:
            print(f"[抓取] 正在抓取 @{username} 的帖子...")
            posts = await self.scrape_user_posts(username, max_posts_per_user)
            results[username] = posts
            print(f"[完成] @{username}: 获取到 {len(posts)} 条帖子")
            # 间隔一段时间避免请求过快
            await asyncio.sleep(2)
        return results

    def _parse_agent_result(
        self, result: str, username: str
    ) -> list[TwitterPost]:
        """解析Agent返回的结果"""
        posts = []

        try:
            # 尝试从结果中提取JSON
            json_match = re.search(r"\{[\s\S]*\}", str(result))
            if json_match:
                data = json.loads(json_match.group())
                raw_posts = data.get("posts", [])

                for idx, post_data in enumerate(raw_posts):
                    try:
                        # 解析时间戳
                        timestamp = self._parse_timestamp(
                            post_data.get("timestamp", "")
                        )

                        post = TwitterPost(
                            post_id=f"{username}_{idx}_{int(timestamp.timestamp())}",
                            author=username,
                            author_handle=f"@{username}",
                            content=post_data.get("content", ""),
                            timestamp=timestamp,
                            likes=self._parse_number(post_data.get("likes", 0)),
                            retweets=self._parse_number(post_data.get("retweets", 0)),
                            replies=self._parse_number(post_data.get("replies", 0)),
                            url=post_data.get("url", f"https://x.com/{username}"),
                        )
                        posts.append(post)
                    except Exception as e:
                        print(f"[警告] 解析帖子失败: {e}")
                        continue

        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {e}")
        except Exception as e:
            print(f"[错误] 解析结果失败: {e}")

        return posts

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """解析时间戳字符串"""
        if not timestamp_str:
            return datetime.now(self.timezone)

        # 尝试多种时间格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return self.timezone.localize(dt)
            except ValueError:
                continue

        # 处理相对时间（如"2h", "3d"等）
        relative_patterns = [
            (r"(\d+)\s*[秒s]", lambda x: datetime.now(self.timezone)),
            (r"(\d+)\s*[分m]", lambda x: datetime.now(self.timezone)),
            (r"(\d+)\s*[时h]", lambda x: datetime.now(self.timezone)),
            (r"(\d+)\s*[天d]", lambda x: datetime.now(self.timezone)),
        ]

        for pattern, _ in relative_patterns:
            if re.search(pattern, timestamp_str, re.IGNORECASE):
                return datetime.now(self.timezone)

        return datetime.now(self.timezone)

    def _parse_number(self, value) -> int:
        """解析数字（支持K、M等缩写）"""
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if not isinstance(value, str):
            return 0

        value = value.strip().upper()
        if not value:
            return 0

        try:
            if "K" in value:
                return int(float(value.replace("K", "")) * 1000)
            elif "M" in value:
                return int(float(value.replace("M", "")) * 1000000)
            else:
                return int(float(re.sub(r"[^\d.]", "", value) or 0))
        except (ValueError, TypeError):
            return 0


# 简单的测试函数
async def _test_scraper():
    """测试抓取功能"""
    scraper = TwitterScraper()
    posts = await scraper.scrape_user_posts("elonmusk", max_posts=5)
    for post in posts:
        print(f"\n{'='*50}")
        print(f"作者: {post.author_handle}")
        print(f"内容: {post.content[:100]}...")
        print(f"时间: {post.timestamp}")
        print(f"互动: {post.likes} 赞 | {post.retweets} 转 | {post.replies} 评")


if __name__ == "__main__":
    asyncio.run(_test_scraper())
