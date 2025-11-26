# TrendRadar Twitter 监控与 AI 问答系统 - 启动配置指南

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [启动方式](#启动方式)
- [验证部署](#验证部署)
- [常见问题](#常见问题)

---

## 系统要求

### 基础环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.10 | Twitter 监控主程序 |
| Node.js | ≥ 18.0 | Agent Service（可选） |
| Chrome/Chromium | 最新版 | browser-use 浏览器抓取 |

### 必需服务

| 服务 | 用途 | 获取方式 |
|------|------|---------|
| OpenAI API | LLM 聚类分析 | https://platform.openai.com |

### 可选服务

| 服务 | 用途 | 获取方式 |
|------|------|---------|
| Supabase | 云端存储 + 向量检索 | https://supabase.com |
| 通知渠道 | 消息推送 | 钉钉/飞书/企业微信/Telegram |

---

## 快速开始

### 方式一：最简配置（本地运行）

```bash
# 1. 克隆项目
git clone https://github.com/darrenyao/TrendRadar.git
cd TrendRadar

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装浏览器
playwright install chromium

# 4. 配置环境变量
cp .env.example .env

# 5. 编辑 .env 文件（最小配置）
cat >> .env << 'EOF'
TWITTER_MONITOR_ENABLED=true
TWITTER_MONITOR_USERS=elonmusk,OpenAI
TWITTER_LLM_API_KEY=your-openai-api-key
EOF

# 6. 运行
python main.py
```

### 方式二：完整配置（含云端存储 + AI 问答）

```bash
# 1-4 步同上

# 5. 完整配置
cat >> .env << 'EOF'
# Twitter 监控
TWITTER_MONITOR_ENABLED=true
TWITTER_MONITOR_USERS=elonmusk,OpenAI,sama
TWITTER_LLM_API_KEY=your-openai-api-key

# Supabase 云端存储
SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# 通知渠道（至少配置一个）
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
EOF

# 6. 初始化 Supabase 数据库
# 在 Supabase SQL 编辑器中执行:
# agent_service/supabase/migrations/001_initial_schema.sql

# 7. 启动 Agent Service（可选）
cd agent_service
npm install
npm run dev &

# 8. 运行主程序
cd ..
python main.py
```

---

## 详细配置

### 1. 环境变量配置 (.env)

创建 `.env` 文件，参考 `.env.example`：

```bash
# ============================================
# 核心配置（必需）
# ============================================

# 启用 Twitter 监控
TWITTER_MONITOR_ENABLED=true

# 监控的 Twitter 用户（逗号分隔，不含@）
TWITTER_MONITOR_USERS=elonmusk,OpenAI,sama,AndrewYNg

# LLM API 配置
TWITTER_LLM_BASE_URL=https://api.openai.com/v1
TWITTER_LLM_API_KEY=sk-xxxxxxxx
TWITTER_LLM_MODEL=gpt-4o

# ============================================
# 推送时间配置（可选）
# ============================================

# 早中晚推送时间（北京时间）
TWITTER_PUSH_MORNING=08:00
TWITTER_PUSH_NOON=12:00
TWITTER_PUSH_EVENING=20:00

# 推送时间容差（分钟）
TWITTER_PUSH_TOLERANCE=30

# ============================================
# Supabase 云端存储（可选）
# ============================================

SUPABASE_ENABLED=false
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ============================================
# 通知渠道（至少配置一个）
# ============================================

# 钉钉机器人
DINGTALK_WEBHOOK_URL=

# 飞书机器人
FEISHU_WEBHOOK_URL=

# 企业微信机器人
WEWORK_WEBHOOK_URL=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# 邮件
EMAIL_FROM=
EMAIL_PASSWORD=
EMAIL_TO=

# ntfy
NTFY_SERVER_URL=https://ntfy.sh
NTFY_TOPIC=
```

### 2. 配置文件 (config/config.yaml)

```yaml
# Twitter 监控配置
twitter_monitor:
  enabled: true

  # 监控用户列表
  users:
    - elonmusk
    - OpenAI
    - sama
    - AndrewYNg

  # 每用户最大抓取帖子数
  max_posts_per_user: 20

  # 数据保留天数
  retention_days: 30

  # 推送时间
  push_schedule:
    morning: "08:00"
    noon: "12:00"
    evening: "20:00"

  # Supabase 云端存储
  supabase_enabled: false

# Agent Service 配置
agent_service:
  enabled: false
  port: 3001
  model: "gpt-4o"
```

### 3. LLM 服务配置

支持 OpenAI 兼容的 API 服务：

**OpenAI**
```bash
TWITTER_LLM_BASE_URL=https://api.openai.com/v1
TWITTER_LLM_API_KEY=sk-xxxxxxxx
TWITTER_LLM_MODEL=gpt-4o
```

**Azure OpenAI**
```bash
TWITTER_LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
TWITTER_LLM_API_KEY=your-azure-key
TWITTER_LLM_MODEL=gpt-4
```

**DeepSeek**
```bash
TWITTER_LLM_BASE_URL=https://api.deepseek.com/v1
TWITTER_LLM_API_KEY=sk-xxxxxxxx
TWITTER_LLM_MODEL=deepseek-chat
```

**本地 Ollama**
```bash
TWITTER_LLM_BASE_URL=http://localhost:11434/v1
TWITTER_LLM_API_KEY=ollama
TWITTER_LLM_MODEL=llama3.1
```

### 4. Supabase 配置

#### 创建项目

1. 访问 https://supabase.com 创建账号
2. 创建新项目
3. 在 Settings → API 获取：
   - Project URL → `SUPABASE_URL`
   - anon public key → `SUPABASE_ANON_KEY`

#### 初始化数据库

在 Supabase SQL 编辑器中执行：

```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建表（完整脚本见 agent_service/supabase/migrations/001_initial_schema.sql）
```

### 5. 通知渠道配置

#### 钉钉机器人

1. 打开钉钉群 → 群设置 → 智能群助手
2. 添加机器人 → 自定义机器人
3. 复制 Webhook URL

```bash
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxxxx
```

#### 飞书机器人

1. 打开飞书群 → 群设置 → 群机器人
2. 添加机器人 → 自定义机器人
3. 复制 Webhook URL

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx
```

#### Telegram

1. 与 @BotFather 对话创建机器人，获取 Token
2. 与 @userinfobot 对话获取 Chat ID

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-xxxxx
TELEGRAM_CHAT_ID=123456789
```

---

## 启动方式

### 方式一：手动运行

```bash
# 运行一次
python main.py

# 后台运行
nohup python main.py > output.log 2>&1 &
```

### 方式二：定时任务 (Cron)

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每小时执行）
0 * * * * cd /path/to/TrendRadar && /usr/bin/python main.py >> /var/log/trendradar.log 2>&1

# 或者使用项目配置的时间点（早中晚）
0 8,12,20 * * * cd /path/to/TrendRadar && /usr/bin/python main.py >> /var/log/trendradar.log 2>&1
```

### 方式三：Docker 部署

```bash
# 使用 docker-compose
cd docker
cp ../.env .env
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 方式四：GitHub Actions

已配置 `.github/workflows/crawler.yml`，Fork 后设置 Secrets 即可自动运行。

---

## 启动 Agent Service

Agent Service 是可选组件，提供 AI 问答功能。

```bash
# 进入目录
cd agent_service

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 开发模式运行
npm run dev

# 生产模式
npm run build
npm start
```

**验证服务：**

```bash
# 健康检查
curl http://localhost:3001/health

# 测试聊天
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "有什么热门话题？"}'
```

---

## 验证部署

### 1. 检查 Twitter 抓取

```bash
# 查看输出目录
ls -la output/twitter/posts/

# 查看帖子数据
cat output/twitter/posts/$(date +%Y-%m-%d)/elonmusk.json
```

### 2. 检查分析结果

```bash
ls -la output/twitter/analysis/
```

### 3. 检查推送记录

```bash
cat output/twitter/push_records/$(date +%Y-%m-%d).json
```

### 4. 检查 Supabase 数据

```sql
-- 在 Supabase SQL 编辑器中执行
SELECT COUNT(*) FROM twitter_posts;
SELECT COUNT(*) FROM analysis_results;
SELECT COUNT(*) FROM embeddings;
```

### 5. 测试 Agent Service

```bash
# 语义搜索
curl -X POST http://localhost:3001/api/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "AI 人工智能", "limit": 5}'

# 获取统计
curl http://localhost:3001/api/status
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        TrendRadar 系统架构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │  Twitter/X 网站   │ ──► │  browser-use     │                  │
│  └──────────────────┘     │  (浏览器自动化)   │                  │
│                           └────────┬─────────┘                  │
│                                    │                             │
│                                    ▼                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Twitter Monitor (Python)               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │   Scraper   │  │  Analyzer   │  │  Scheduler  │       │   │
│  │  │  (抓取帖子)  │  │ (LLM聚类)   │  │ (早中晚调度) │       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  本地存储      │  │   Supabase    │  │   通知推送    │       │
│  │  (JSON/TXT)   │  │  (PostgreSQL  │  │  钉钉/飞书/   │       │
│  │               │  │  + pgvector)  │  │  Telegram...  │       │
│  └───────────────┘  └───────┬───────┘  └───────────────┘       │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Agent Service (TypeScript/Node.js)           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │ Vercel AI   │  │  Embedding  │  │  REST API   │       │   │
│  │  │    SDK      │  │   Service   │  │  + SSE      │       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                    ┌───────────────┐                            │
│                    │   用户/客户端  │                            │
│                    │  (问答交互)    │                            │
│                    └───────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 常见问题

### Q1: browser-use 抓取失败

**可能原因：**
- 网络无法访问 Twitter
- 浏览器未安装

**解决方案：**
```bash
# 安装浏览器
playwright install chromium

# 检查网络
curl -I https://x.com
```

### Q2: LLM API 调用失败

**可能原因：**
- API Key 无效
- 余额不足
- 网络问题

**解决方案：**
```bash
# 测试 API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $TWITTER_LLM_API_KEY"
```

### Q3: Supabase 连接失败

**可能原因：**
- URL 或 Key 错误
- 数据库未初始化

**解决方案：**
1. 检查 SUPABASE_URL 和 SUPABASE_ANON_KEY
2. 执行数据库迁移脚本

### Q4: 推送通知失败

**可能原因：**
- Webhook URL 错误
- 机器人被禁用

**解决方案：**
```bash
# 测试钉钉
curl -X POST "$DINGTALK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"测试消息"}}'
```

### Q5: Agent Service 启动失败

**可能原因：**
- Node.js 版本过低
- 依赖未安装

**解决方案：**
```bash
# 检查 Node 版本
node --version  # 需要 >= 18

# 重新安装依赖
cd agent_service
rm -rf node_modules
npm install
```

### Q6: 语义搜索无结果

**可能原因：**
- 数据未生成 embedding
- 相似度阈值过高

**解决方案：**
```sql
-- 检查 embedding 数量
SELECT COUNT(*) FROM embeddings;

-- 降低阈值重试
SELECT * FROM match_embeddings(
  query_embedding := '[...]',
  match_threshold := 0.5,  -- 降低阈值
  match_count := 20
);
```

---

## 日志查看

```bash
# 主程序日志
tail -f output.log

# Docker 日志
docker-compose logs -f

# Agent Service 日志
cd agent_service && npm run dev
```

---

## 更新升级

```bash
# 拉取最新代码
git pull origin main

# 更新 Python 依赖
pip install -r requirements.txt --upgrade

# 更新 Node 依赖
cd agent_service && npm update
```

---

## 支持

- 问题反馈：https://github.com/darrenyao/TrendRadar/issues
- 文档：`twitter_monitor/README.md`, `agent_service/README.md`
