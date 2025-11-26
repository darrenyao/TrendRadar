# Twitter Monitor - Twitter 帖子抓取与聚类分析模块

## 功能概述

Twitter Monitor 是 TrendRadar 的扩展模块，提供以下功能：

1. **帖子抓取** - 使用 browser-use 浏览器自动化技术抓取指定 Twitter 用户的帖子
2. **聚类分析** - 使用 LLM（大语言模型）对帖子内容进行主题聚类和分析
3. **定时推送** - 每天早中晚三次自动推送聚类总结到配置的通知渠道

## 架构设计

```
twitter_monitor/
├── __init__.py      # 模块初始化
├── scraper.py       # Twitter 抓取器（browser-use）
├── analyzer.py      # LLM 聚类分析器
├── storage.py       # 数据存储管理
├── scheduler.py     # 早中晚定时调度
├── main.py          # 主入口
└── README.md        # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install browser-use langchain-openai openai playwright

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```bash
# 启用 Twitter 监控
TWITTER_MONITOR_ENABLED=true

# 要监控的用户（逗号分隔，不含@符号）
TWITTER_MONITOR_USERS=elonmusk,OpenAI,sama

# LLM API 配置（必需）
TWITTER_LLM_BASE_URL=https://api.openai.com/v1
TWITTER_LLM_API_KEY=your-api-key
TWITTER_LLM_MODEL=gpt-4o

# 推送时间配置（可选）
TWITTER_PUSH_MORNING=08:00
TWITTER_PUSH_NOON=12:00
TWITTER_PUSH_EVENING=20:00
```

### 3. 运行

```bash
# 与主程序一起运行
python main.py

# 或单独运行 Twitter 监控
python -m twitter_monitor.main
```

## 配置详解

### 环境变量配置

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `TWITTER_MONITOR_ENABLED` | 是否启用监控 | `false` | 是 |
| `TWITTER_MONITOR_USERS` | 监控的用户列表 | - | 是 |
| `TWITTER_LLM_BASE_URL` | LLM API 地址 | `https://api.openai.com/v1` | 否 |
| `TWITTER_LLM_API_KEY` | LLM API 密钥 | - | 是 |
| `TWITTER_LLM_MODEL` | LLM 模型名称 | `gpt-4o` | 否 |
| `TWITTER_PUSH_MORNING` | 早间推送时间 | `08:00` | 否 |
| `TWITTER_PUSH_NOON` | 午间推送时间 | `12:00` | 否 |
| `TWITTER_PUSH_EVENING` | 晚间推送时间 | `20:00` | 否 |
| `TWITTER_PUSH_TOLERANCE` | 推送时间容差(分钟) | `30` | 否 |

### 配置文件配置

也可以在 `config/config.yaml` 中配置：

```yaml
twitter_monitor:
  enabled: true
  users:
    - elonmusk
    - OpenAI
    - sama
  max_posts_per_user: 20
  retention_days: 30
  push_schedule:
    morning: "08:00"
    noon: "12:00"
    evening: "20:00"
  llm:
    base_url: ""  # 留空使用环境变量
    api_key: ""   # 留空使用环境变量
    model: ""     # 留空使用环境变量
```

## LLM 服务配置

本模块支持任何 OpenAI 兼容的 API 服务：

### OpenAI

```bash
TWITTER_LLM_BASE_URL=https://api.openai.com/v1
TWITTER_LLM_API_KEY=sk-xxxx
TWITTER_LLM_MODEL=gpt-4o
```

### Azure OpenAI

```bash
TWITTER_LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
TWITTER_LLM_API_KEY=your-azure-key
TWITTER_LLM_MODEL=gpt-4
```

### DeepSeek

```bash
TWITTER_LLM_BASE_URL=https://api.deepseek.com/v1
TWITTER_LLM_API_KEY=sk-xxxx
TWITTER_LLM_MODEL=deepseek-chat
```

### Anthropic (通过兼容代理)

```bash
TWITTER_LLM_BASE_URL=https://your-anthropic-proxy/v1
TWITTER_LLM_API_KEY=sk-xxxx
TWITTER_LLM_MODEL=claude-3-opus
```

## 数据存储

数据存储在 `output/twitter/` 目录下：

```
output/twitter/
├── posts/                    # 原始帖子数据
│   └── 2025-11-26/
│       ├── elonmusk.json
│       └── OpenAI.json
├── analysis/                 # 分析结果
│   └── 2025-11-26/
│       ├── morning.json      # 早间分析
│       ├── noon.json         # 午间分析
│       └── evening.json      # 晚间分析
└── push_records/             # 推送记录
    └── 2025-11-26.json
```

## 推送消息示例

```
【Twitter 早间动态】

共分析 45 条帖子
━━━━━━━━━━━━━━━━━━━

今日重点：AI技术持续突破，GPT-4o引发热议；特斯拉FSD最新进展备受关注。

━━━━━━━━━━━━━━━━━━━

📌 AI 技术进展
   OpenAI发布GPT-4o多项能力提升，实时语音交互成为亮点
   关键词：AI, GPT-4o, 多模态
   帖子数：12
   热门帖子：GPT-4o is here, and it's free...

📌 特斯拉动态
   Elon Musk分享FSD最新测试视频，自动驾驶表现惊艳
   关键词：Tesla, FSD, 自动驾驶
   帖子数：8
   热门帖子：FSD v12.5 is insane...

━━━━━━━━━━━━━━━━━━━
分析时间：2025-11-26 08:00
关注用户：elonmusk, OpenAI, sama
```

## API 使用示例

### 独立使用抓取器

```python
import asyncio
from twitter_monitor import TwitterScraper

async def main():
    scraper = TwitterScraper(
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="your-api-key",
        llm_model="gpt-4o"
    )

    posts = await scraper.scrape_user_posts("elonmusk", max_posts=20)

    for post in posts:
        print(f"{post.author_handle}: {post.content[:100]}...")

asyncio.run(main())
```

### 独立使用分析器

```python
from twitter_monitor import PostAnalyzer

analyzer = PostAnalyzer(
    llm_base_url="https://api.openai.com/v1",
    llm_api_key="your-api-key"
)

# posts 是 TwitterPost 列表
result = analyzer.analyze_posts(posts)

print(f"识别出 {len(result.clusters)} 个话题")
print(f"总结: {result.summary}")

# 生成推送消息
message = analyzer.generate_notification_message(result, "今日")
print(message)
```

### 完整监控流程

```python
import asyncio
from twitter_monitor import TwitterMonitor

async def main():
    monitor = TwitterMonitor()

    # 设置自定义通知发送函数
    monitor.set_notification_sender(lambda msg: print(msg))

    # 运行一次完整流程
    result = await monitor.run_once()

    # 或运行定时推送
    await monitor.run()

asyncio.run(main())
```

## 常见问题

### Q: 为什么使用 browser-use 而不是 Twitter API？

A: Twitter API 需要付费且有严格的使用限制。browser-use 通过浏览器自动化模拟用户行为，无需 API 密钥即可抓取公开帖子。

### Q: 抓取速度慢怎么办？

A:
1. 减少 `max_posts_per_user` 配置
2. 减少监控的用户数量
3. 使用更快的 LLM 模型

### Q: LLM 聚类效果不好？

A:
1. 使用更强大的模型（如 GPT-4）
2. 增加帖子数量以获得更多上下文
3. 调整聚类的最小帖子数阈值

### Q: 如何调试？

```bash
# 设置环境变量开启详细日志
export TWITTER_DEBUG=true
```

## 注意事项

1. **网络要求** - 需要能够访问 Twitter/X 网站
2. **资源消耗** - browser-use 会启动浏览器，消耗较多内存
3. **速率限制** - 建议适当设置抓取间隔，避免被 Twitter 限制
4. **LLM 成本** - 每次分析会消耗 LLM API 调用额度

## Supabase 云端存储

启用 Supabase 后，数据将同步到云端，支持：

- 跨设备数据访问
- AI 问答助理（语义检索）
- 数据持久化存储

### 配置

```bash
# .env
SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### 数据库初始化

在 Supabase SQL 编辑器中执行 `agent_service/supabase/migrations/001_initial_schema.sql`

## Agent Service（AI 问答助理）

启动 Agent Service 后，可以通过 API 与 AI 助理进行对话：

```bash
# 启动服务
cd agent_service
npm install
npm run dev

# 发送消息
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "最近有什么热门话题？"}'
```

详细文档请参考 `agent_service/README.md`

## 技术栈

- **browser-use** - 基于 LLM 的浏览器自动化框架
- **langchain-openai** - LangChain OpenAI 集成
- **openai** - OpenAI Python 客户端
- **playwright** - 底层浏览器自动化引擎
- **supabase** - 云端数据库（可选）
- **Vercel AI SDK** - AI 问答助理（可选）
