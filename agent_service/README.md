# TrendRadar Agent Service

基于 Vercel AI SDK 的智能问答服务，支持 Supabase 云端存储和 pgvector 向量检索。

## 功能特性

- **AI 问答助理** - 基于 Vercel AI SDK 实现，支持针对抓取的 Twitter 内容进行问答
- **Supabase 存储** - 云端数据存储，支持跨设备访问
- **语义检索** - 基于 pgvector 的向量相似度搜索
- **流式响应** - 支持 SSE 流式输出，提供更好的用户体验
- **多轮对话** - 支持上下文连续对话

## 架构

```
agent_service/
├── src/
│   ├── index.ts          # Express 服务主入口
│   ├── agent.ts          # Vercel AI SDK Agent 实现
│   ├── supabase.ts       # Supabase 客户端
│   ├── embedding.ts      # Embedding 服务
│   └── api/
│       └── chat.ts       # 聊天 API 路由
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql  # 数据库初始化脚本
├── package.json
├── tsconfig.json
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd agent_service
npm install
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# OpenAI API 配置
OPENAI_API_KEY=your-openai-api-key

# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# 服务配置
PORT=3001
AGENT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. 初始化 Supabase 数据库

在 Supabase SQL 编辑器中执行 `supabase/migrations/001_initial_schema.sql`

### 4. 运行服务

```bash
# 开发模式
npm run dev

# 生产模式
npm run build
npm start
```

## API 文档

### 聊天接口

#### POST /api/chat

发送消息并获取 AI 回复。

**请求体：**
```json
{
  "message": "最近有什么关于 AI 的热门话题？",
  "sessionId": "optional-session-id"
}
```

**响应：**
```json
{
  "success": true,
  "response": "根据最近抓取的数据，AI 领域的热门话题包括...",
  "toolCalls": [...],
  "sessionId": "default"
}
```

#### POST /api/chat/stream

流式聊天（SSE）。

**请求体：** 同上

**响应：** Server-Sent Events
```
data: {"type": "chunk", "content": "根据"}
data: {"type": "chunk", "content": "最近"}
...
data: {"type": "done"}
```

#### GET /api/chat/history

获取会话历史。

**查询参数：**
- `sessionId` - 会话 ID（可选，默认 "default"）

#### DELETE /api/chat/history

清除会话历史。

### 搜索接口

#### POST /api/search/semantic

语义搜索。

**请求体：**
```json
{
  "query": "人工智能发展趋势",
  "contentType": "post",
  "limit": 10
}
```

### 数据接口

#### GET /api/posts

获取帖子列表。

**查询参数：**
- `username` - Twitter 用户名（可选）
- `limit` - 返回数量限制（默认 20）

#### GET /api/analysis

获取分析结果。

**查询参数：**
- `limit` - 返回数量限制（默认 10）

#### GET /api/status

获取服务状态和统计信息。

## Agent 工具

Agent 内置以下工具，可在对话中自动调用：

| 工具名 | 描述 |
|--------|------|
| `searchPosts` | 关键词搜索帖子 |
| `semanticSearch` | 语义相似度搜索 |
| `getUserPosts` | 获取指定用户帖子 |
| `getRecentAnalysis` | 获取最近分析结果 |
| `getStatistics` | 获取数据统计 |

## 前端集成示例

### React 示例

```tsx
import { useState } from 'react';

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input }),
    });

    const data = await response.json();
    setMessages([...messages,
      { role: 'user', content: input },
      { role: 'assistant', content: data.response }
    ]);
    setInput('');
  };

  return (
    <div>
      {messages.map((msg, i) => (
        <div key={i} className={msg.role}>
          {msg.content}
        </div>
      ))}
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyPress={e => e.key === 'Enter' && sendMessage()}
      />
      <button onClick={sendMessage}>发送</button>
    </div>
  );
}
```

### 流式响应示例

```typescript
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello' }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.type === 'chunk') {
        console.log(data.content);
      }
    }
  }
}
```

## Supabase 数据库

### 表结构

**twitter_posts** - Twitter 帖子
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| post_id | VARCHAR | 帖子 ID |
| author | VARCHAR | 作者用户名 |
| content | TEXT | 帖子内容 |
| timestamp | TIMESTAMPTZ | 发布时间 |
| likes | INTEGER | 点赞数 |
| retweets | INTEGER | 转发数 |

**analysis_results** - 分析结果
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| period | VARCHAR | 时段标识 |
| summary | TEXT | 总结 |
| clusters | JSONB | 话题聚类 |

**embeddings** - 向量存储
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| content | TEXT | 原始内容 |
| content_type | VARCHAR | 内容类型 |
| embedding | vector(1536) | 向量 |

### 语义搜索函数

数据库提供 `match_embeddings` 函数用于向量相似度搜索：

```sql
SELECT * FROM match_embeddings(
  query_embedding := '[...]'::vector,
  match_threshold := 0.7,
  match_count := 10
);
```

## Docker 部署

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY dist ./dist

ENV NODE_ENV=production
EXPOSE 3001

CMD ["node", "dist/index.js"]
```

```yaml
# docker-compose.yml
services:
  agent-service:
    build: ./agent_service
    ports:
      - "3001:3001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
```

## 常见问题

### Q: 语义搜索不返回结果？

确保：
1. Supabase 数据库已启用 pgvector 扩展
2. 数据已生成 embedding
3. 相似度阈值设置合理（默认 0.7）

### Q: Agent 响应慢？

- 使用更快的模型（如 gpt-4o-mini）
- 减少最大步骤数（maxSteps）
- 使用流式响应

### Q: 如何自定义 Agent 行为？

修改 `src/agent.ts` 中的系统提示词：

```typescript
const DEFAULT_SYSTEM_PROMPT = `你是...`;
```

## 技术栈

- **Vercel AI SDK** - AI 应用开发框架
- **Express** - Node.js Web 框架
- **Supabase** - 云端数据库（PostgreSQL）
- **pgvector** - PostgreSQL 向量扩展
- **TypeScript** - 类型安全
