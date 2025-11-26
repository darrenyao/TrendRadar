/**
 * AI Agent - 基于 Vercel AI SDK 的智能问答助理
 *
 * 功能：
 * - 针对抓取的 Twitter 内容进行问答
 * - 语义检索相关帖子
 * - 生成内容总结
 * - 多轮对话支持
 */

import { openai } from "@ai-sdk/openai";
import { generateText, streamText, tool, CoreMessage } from "ai";
import { z } from "zod";
import { SupabaseService, getSupabaseService } from "./supabase.js";
import { EmbeddingService, getEmbeddingService } from "./embedding.js";

// Agent 配置
export interface AgentConfig {
  model?: string;
  systemPrompt?: string;
  maxTokens?: number;
  temperature?: number;
}

// 对话消息
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

// Agent 响应
export interface AgentResponse {
  content: string;
  toolCalls?: Array<{
    name: string;
    args: Record<string, unknown>;
    result: unknown;
  }>;
}

// 默认系统提示词
const DEFAULT_SYSTEM_PROMPT = `你是 TrendRadar 的智能助理，专门帮助用户了解和分析 Twitter 上的热点内容。

你的能力包括：
1. 搜索和检索已抓取的 Twitter 帖子
2. 根据语义相似度查找相关内容
3. 总结和分析帖子内容
4. 回答关于特定用户或话题的问题

请用简洁、专业的中文回答用户问题。当需要引用具体帖子时，请说明来源。

注意：
- 只基于已抓取的数据回答，如果没有相关数据请如实告知
- 保持客观，不添加主观评价
- 对于敏感话题，保持中立`;

export class TwitterAgent {
  private config: AgentConfig;
  private supabase: SupabaseService;
  private embedding: EmbeddingService;
  private conversationHistory: CoreMessage[] = [];

  constructor(config: Partial<AgentConfig> = {}) {
    this.config = {
      model: config.model || process.env.AGENT_MODEL || "gpt-4o",
      systemPrompt: config.systemPrompt || DEFAULT_SYSTEM_PROMPT,
      maxTokens: config.maxTokens || 2048,
      temperature: config.temperature || 0.7,
    };

    this.supabase = getSupabaseService();
    this.embedding = getEmbeddingService();
  }

  /**
   * 定义 Agent 工具
   */
  private getTools() {
    return {
      // 搜索帖子工具
      searchPosts: tool({
        description: "搜索 Twitter 帖子内容，支持关键词搜索",
        parameters: z.object({
          query: z.string().describe("搜索关键词"),
          limit: z.number().optional().describe("返回数量限制，默认 10"),
        }),
        execute: async ({ query, limit = 10 }) => {
          const posts = await this.supabase.searchPosts(query, limit);
          return posts.map((p) => ({
            author: p.author_handle,
            content: p.content,
            timestamp: p.timestamp,
            likes: p.likes,
            url: p.url,
          }));
        },
      }),

      // 语义搜索工具
      semanticSearch: tool({
        description: "基于语义相似度搜索相关内容，适合查找相似话题或观点",
        parameters: z.object({
          query: z.string().describe("搜索内容描述"),
          contentType: z
            .enum(["post", "summary", "cluster"])
            .optional()
            .describe("内容类型"),
          limit: z.number().optional().describe("返回数量限制，默认 5"),
        }),
        execute: async ({ query, contentType, limit = 5 }) => {
          // 生成查询的 embedding
          const queryEmbedding = await this.embedding.generateEmbedding(query);

          // 语义搜索
          const results = await this.supabase.semanticSearch(queryEmbedding, {
            matchCount: limit,
            contentType: contentType as "post" | "summary" | "cluster",
          });

          return results.map((r) => ({
            content: r.content,
            type: r.content_type,
            similarity: Math.round(r.similarity * 100) / 100,
          }));
        },
      }),

      // 获取用户帖子工具
      getUserPosts: tool({
        description: "获取指定 Twitter 用户的最新帖子",
        parameters: z.object({
          username: z.string().describe("Twitter 用户名（不含@）"),
          limit: z.number().optional().describe("返回数量限制，默认 20"),
        }),
        execute: async ({ username, limit = 20 }) => {
          const posts = await this.supabase.getPostsByUser(username, limit);
          return posts.map((p) => ({
            content: p.content,
            timestamp: p.timestamp,
            likes: p.likes,
            retweets: p.retweets,
            url: p.url,
          }));
        },
      }),

      // 获取最新分析结果工具
      getRecentAnalysis: tool({
        description: "获取最近的 Twitter 内容分析结果和话题聚类",
        parameters: z.object({
          limit: z.number().optional().describe("返回数量限制，默认 5"),
        }),
        execute: async ({ limit = 5 }) => {
          const analyses = await this.supabase.getRecentAnalysis(limit);
          return analyses.map((a) => ({
            period: a.period,
            summary: a.summary,
            clusters: a.clusters.map((c) => ({
              name: c.topic_name,
              summary: c.topic_summary,
              keywords: c.keywords,
            })),
            analyzedAt: a.analyzed_at,
          }));
        },
      }),

      // 获取统计信息工具
      getStatistics: tool({
        description: "获取数据库统计信息",
        parameters: z.object({}),
        execute: async () => {
          return await this.supabase.getStatistics();
        },
      }),
    };
  }

  /**
   * 发送消息并获取回复
   */
  async chat(userMessage: string): Promise<AgentResponse> {
    // 添加用户消息到历史
    this.conversationHistory.push({
      role: "user",
      content: userMessage,
    });

    try {
      const result = await generateText({
        model: openai(this.config.model!),
        system: this.config.systemPrompt,
        messages: this.conversationHistory,
        tools: this.getTools(),
        maxTokens: this.config.maxTokens,
        temperature: this.config.temperature,
        maxSteps: 5, // 允许多步工具调用
      });

      // 添加助手回复到历史
      this.conversationHistory.push({
        role: "assistant",
        content: result.text,
      });

      // 整理工具调用信息
      const toolCalls = result.steps
        .flatMap((step) => step.toolCalls || [])
        .map((tc) => ({
          name: tc.toolName,
          args: tc.args as Record<string, unknown>,
          result: result.steps.find(
            (s) => s.toolResults?.some((tr) => tr.toolCallId === tc.toolCallId)
          )?.toolResults?.[0]?.result,
        }));

      return {
        content: result.text,
        toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      };
    } catch (error) {
      console.error("Agent 处理失败:", error);
      throw error;
    }
  }

  /**
   * 流式对话
   */
  async chatStream(
    userMessage: string,
    onChunk: (chunk: string) => void
  ): Promise<AgentResponse> {
    this.conversationHistory.push({
      role: "user",
      content: userMessage,
    });

    try {
      const result = streamText({
        model: openai(this.config.model!),
        system: this.config.systemPrompt,
        messages: this.conversationHistory,
        tools: this.getTools(),
        maxTokens: this.config.maxTokens,
        temperature: this.config.temperature,
        maxSteps: 5,
      });

      let fullContent = "";

      for await (const chunk of result.textStream) {
        fullContent += chunk;
        onChunk(chunk);
      }

      // 等待完成
      const finalResult = await result;

      this.conversationHistory.push({
        role: "assistant",
        content: fullContent,
      });

      return {
        content: fullContent,
      };
    } catch (error) {
      console.error("流式处理失败:", error);
      throw error;
    }
  }

  /**
   * 清除对话历史
   */
  clearHistory(): void {
    this.conversationHistory = [];
  }

  /**
   * 获取对话历史
   */
  getHistory(): CoreMessage[] {
    return [...this.conversationHistory];
  }

  /**
   * 设置对话历史
   */
  setHistory(history: CoreMessage[]): void {
    this.conversationHistory = [...history];
  }

  /**
   * 生成内容总结
   */
  async summarize(
    content: string,
    options: { maxLength?: number; style?: "brief" | "detailed" } = {}
  ): Promise<string> {
    const { maxLength = 200, style = "brief" } = options;

    const prompt =
      style === "brief"
        ? `请用不超过${maxLength}字总结以下内容：\n\n${content}`
        : `请详细总结以下内容的要点：\n\n${content}`;

    const result = await generateText({
      model: openai(this.config.model!),
      prompt,
      maxTokens: style === "brief" ? 300 : 1000,
    });

    return result.text;
  }

  /**
   * 分析话题趋势
   */
  async analyzeTrends(
    posts: Array<{ content: string; timestamp: string; likes: number }>
  ): Promise<{
    topics: string[];
    sentiment: string;
    insights: string[];
  }> {
    const postsText = posts
      .map((p) => `[${p.timestamp}] (${p.likes}赞) ${p.content}`)
      .join("\n");

    const result = await generateText({
      model: openai(this.config.model!),
      prompt: `分析以下 Twitter 帖子的趋势：

${postsText}

请以 JSON 格式返回：
{
  "topics": ["主要话题1", "主要话题2", ...],
  "sentiment": "整体情绪（正面/负面/中性）",
  "insights": ["洞察1", "洞察2", ...]
}`,
      maxTokens: 1000,
    });

    try {
      return JSON.parse(result.text);
    } catch {
      return {
        topics: [],
        sentiment: "未知",
        insights: [result.text],
      };
    }
  }
}

// 导出单例
let agentInstance: TwitterAgent | null = null;

export function getAgent(config?: Partial<AgentConfig>): TwitterAgent {
  if (!agentInstance || config) {
    agentInstance = new TwitterAgent(config);
  }
  return agentInstance;
}

export default TwitterAgent;
