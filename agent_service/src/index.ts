/**
 * TrendRadar Agent Service - 主入口
 *
 * 基于 Vercel AI SDK 的智能问答服务
 * 集成 Supabase 存储和 pgvector 向量检索
 */

import "dotenv/config";
import express from "express";
import cors from "cors";
import chatRouter from "./api/chat.js";
import { getSupabaseService } from "./supabase.js";
import { getEmbeddingService } from "./embedding.js";

const app = express();
const PORT = process.env.PORT || 3001;

// 中间件
app.use(cors());
app.use(express.json({ limit: "10mb" }));

// API 路由
app.use("/api/chat", chatRouter);

// 健康检查
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "TrendRadar Agent Service",
    timestamp: new Date().toISOString(),
  });
});

// 数据库状态
app.get("/api/status", async (req, res) => {
  try {
    const supabase = getSupabaseService();
    const stats = await supabase.getStatistics();

    res.json({
      success: true,
      database: "connected",
      statistics: stats,
    });
  } catch (error) {
    res.json({
      success: false,
      database: "disconnected",
      error: error instanceof Error ? error.message : "未知错误",
    });
  }
});

// Embedding 测试
app.post("/api/embedding/test", async (req, res) => {
  try {
    const { text } = req.body;

    if (!text) {
      return res.status(400).json({ error: "文本不能为空" });
    }

    const embeddingService = getEmbeddingService();
    const embedding = await embeddingService.generateEmbedding(text);

    res.json({
      success: true,
      dimensions: embedding.length,
      preview: embedding.slice(0, 5),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "未知错误",
    });
  }
});

// Supabase 帖子 API
app.get("/api/posts", async (req, res) => {
  try {
    const { username, limit = "20" } = req.query;
    const supabase = getSupabaseService();

    if (username && typeof username === "string") {
      const posts = await supabase.getPostsByUser(username, parseInt(limit as string));
      res.json({ success: true, posts });
    } else {
      // 获取最近帖子
      const posts = await supabase.getPostsByDateRange(
        new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        new Date().toISOString()
      );
      res.json({ success: true, posts: posts.slice(0, parseInt(limit as string)) });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "未知错误",
    });
  }
});

// 语义搜索 API
app.post("/api/search/semantic", async (req, res) => {
  try {
    const { query, contentType, limit = 10 } = req.body;

    if (!query) {
      return res.status(400).json({ error: "搜索内容不能为空" });
    }

    const embeddingService = getEmbeddingService();
    const supabase = getSupabaseService();

    // 生成查询 embedding
    const queryEmbedding = await embeddingService.generateEmbedding(query);

    // 语义搜索
    const results = await supabase.semanticSearch(queryEmbedding, {
      matchCount: limit,
      contentType,
    });

    res.json({
      success: true,
      results,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "未知错误",
    });
  }
});

// 分析结果 API
app.get("/api/analysis", async (req, res) => {
  try {
    const { limit = "10" } = req.query;
    const supabase = getSupabaseService();

    const analyses = await supabase.getRecentAnalysis(parseInt(limit as string));

    res.json({
      success: true,
      analyses,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "未知错误",
    });
  }
});

// 错误处理
app.use(
  (
    err: Error,
    req: express.Request,
    res: express.Response,
    next: express.NextFunction
  ) => {
    console.error("Server error:", err);
    res.status(500).json({
      error: "服务器内部错误",
      details: err.message,
    });
  }
);

// 启动服务
app.listen(PORT, () => {
  console.log("=========================================");
  console.log("TrendRadar Agent Service");
  console.log("=========================================");
  console.log(`服务地址: http://localhost:${PORT}`);
  console.log(`健康检查: http://localhost:${PORT}/health`);
  console.log(`聊天 API: http://localhost:${PORT}/api/chat`);
  console.log("=========================================");

  // 检查必要的环境变量
  const requiredEnvs = ["OPENAI_API_KEY"];
  const missingEnvs = requiredEnvs.filter((env) => !process.env[env]);

  if (missingEnvs.length > 0) {
    console.warn(`警告: 缺少环境变量: ${missingEnvs.join(", ")}`);
  }

  // 检查 Supabase 配置
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_ANON_KEY) {
    console.warn("警告: Supabase 未配置，数据存储功能将不可用");
  }
});

export default app;
