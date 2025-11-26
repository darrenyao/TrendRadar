/**
 * Chat API - 聊天接口
 *
 * 提供 REST API 和 SSE 流式接口
 */

import { Router, Request, Response } from "express";
import { TwitterAgent, getAgent } from "../agent.js";
import { CoreMessage } from "ai";

const router = Router();

// 会话存储（生产环境应使用 Redis 等）
const sessions = new Map<
  string,
  {
    agent: TwitterAgent;
    createdAt: Date;
    lastActivity: Date;
  }
>();

// 清理过期会话（1小时）
setInterval(() => {
  const now = new Date();
  for (const [sessionId, session] of sessions.entries()) {
    if (now.getTime() - session.lastActivity.getTime() > 3600000) {
      sessions.delete(sessionId);
    }
  }
}, 300000); // 每5分钟检查一次

/**
 * 获取或创建会话
 */
function getSession(sessionId: string): TwitterAgent {
  let session = sessions.get(sessionId);

  if (!session) {
    session = {
      agent: new TwitterAgent(),
      createdAt: new Date(),
      lastActivity: new Date(),
    };
    sessions.set(sessionId, session);
  } else {
    session.lastActivity = new Date();
  }

  return session.agent;
}

/**
 * POST /api/chat
 * 发送消息并获取回复
 */
router.post("/", async (req: Request, res: Response) => {
  try {
    const { message, sessionId = "default" } = req.body;

    if (!message || typeof message !== "string") {
      return res.status(400).json({
        error: "消息内容不能为空",
      });
    }

    const agent = getSession(sessionId);
    const response = await agent.chat(message);

    res.json({
      success: true,
      response: response.content,
      toolCalls: response.toolCalls,
      sessionId,
    });
  } catch (error) {
    console.error("Chat error:", error);
    res.status(500).json({
      error: "处理消息失败",
      details: error instanceof Error ? error.message : "未知错误",
    });
  }
});

/**
 * POST /api/chat/stream
 * 流式对话（SSE）
 */
router.post("/stream", async (req: Request, res: Response) => {
  try {
    const { message, sessionId = "default" } = req.body;

    if (!message || typeof message !== "string") {
      return res.status(400).json({
        error: "消息内容不能为空",
      });
    }

    // 设置 SSE 头
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();

    const agent = getSession(sessionId);

    await agent.chatStream(message, (chunk) => {
      res.write(`data: ${JSON.stringify({ type: "chunk", content: chunk })}\n\n`);
    });

    res.write(`data: ${JSON.stringify({ type: "done" })}\n\n`);
    res.end();
  } catch (error) {
    console.error("Stream error:", error);
    res.write(
      `data: ${JSON.stringify({
        type: "error",
        error: error instanceof Error ? error.message : "未知错误",
      })}\n\n`
    );
    res.end();
  }
});

/**
 * GET /api/chat/history
 * 获取会话历史
 */
router.get("/history", (req: Request, res: Response) => {
  const sessionId = (req.query.sessionId as string) || "default";
  const session = sessions.get(sessionId);

  if (!session) {
    return res.json({
      success: true,
      history: [],
      sessionId,
    });
  }

  res.json({
    success: true,
    history: session.agent.getHistory(),
    sessionId,
    createdAt: session.createdAt,
    lastActivity: session.lastActivity,
  });
});

/**
 * DELETE /api/chat/history
 * 清除会话历史
 */
router.delete("/history", (req: Request, res: Response) => {
  const sessionId = (req.query.sessionId as string) || "default";
  const session = sessions.get(sessionId);

  if (session) {
    session.agent.clearHistory();
  }

  res.json({
    success: true,
    message: "会话历史已清除",
    sessionId,
  });
});

/**
 * POST /api/chat/summarize
 * 总结内容
 */
router.post("/summarize", async (req: Request, res: Response) => {
  try {
    const { content, maxLength, style } = req.body;

    if (!content || typeof content !== "string") {
      return res.status(400).json({
        error: "内容不能为空",
      });
    }

    const agent = getAgent();
    const summary = await agent.summarize(content, { maxLength, style });

    res.json({
      success: true,
      summary,
    });
  } catch (error) {
    console.error("Summarize error:", error);
    res.status(500).json({
      error: "总结失败",
      details: error instanceof Error ? error.message : "未知错误",
    });
  }
});

/**
 * POST /api/chat/analyze-trends
 * 分析趋势
 */
router.post("/analyze-trends", async (req: Request, res: Response) => {
  try {
    const { posts } = req.body;

    if (!Array.isArray(posts) || posts.length === 0) {
      return res.status(400).json({
        error: "帖子列表不能为空",
      });
    }

    const agent = getAgent();
    const analysis = await agent.analyzeTrends(posts);

    res.json({
      success: true,
      analysis,
    });
  } catch (error) {
    console.error("Analyze trends error:", error);
    res.status(500).json({
      error: "分析失败",
      details: error instanceof Error ? error.message : "未知错误",
    });
  }
});

export default router;
