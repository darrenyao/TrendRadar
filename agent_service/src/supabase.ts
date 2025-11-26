/**
 * Supabase 客户端 - 数据存储与向量检索
 *
 * 功能：
 * - 存储 Twitter 帖子数据
 * - 存储分析结果
 * - 向量存储与语义检索 (pgvector)
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// 数据库类型定义
export interface TwitterPost {
  id?: string;
  post_id: string;
  author: string;
  author_handle: string;
  content: string;
  timestamp: string;
  likes: number;
  retweets: number;
  replies: number;
  url: string;
  media_urls?: string[];
  embedding?: number[];
  created_at?: string;
}

export interface AnalysisResult {
  id?: string;
  period: string;
  summary: string;
  clusters: TopicCluster[];
  total_posts: number;
  analyzed_users: string[];
  analyzed_at: string;
  created_at?: string;
}

export interface TopicCluster {
  topic_id: string;
  topic_name: string;
  topic_summary: string;
  keywords: string[];
  post_ids: string[];
  importance_score: number;
}

export interface EmbeddingRecord {
  id?: string;
  content: string;
  content_type: "post" | "summary" | "cluster";
  reference_id: string;
  embedding: number[];
  metadata?: Record<string, unknown>;
  created_at?: string;
}

// Supabase 服务类
export class SupabaseService {
  private client: SupabaseClient;

  constructor(supabaseUrl?: string, supabaseKey?: string) {
    const url = supabaseUrl || process.env.SUPABASE_URL;
    const key = supabaseKey || process.env.SUPABASE_ANON_KEY;

    if (!url || !key) {
      throw new Error(
        "Supabase URL 和 Key 必须提供。请设置 SUPABASE_URL 和 SUPABASE_ANON_KEY 环境变量。"
      );
    }

    this.client = createClient(url, key);
  }

  // ========== Twitter 帖子操作 ==========

  /**
   * 保存 Twitter 帖子
   */
  async savePosts(posts: TwitterPost[]): Promise<void> {
    if (posts.length === 0) return;

    const { error } = await this.client.from("twitter_posts").upsert(
      posts.map((post) => ({
        post_id: post.post_id,
        author: post.author,
        author_handle: post.author_handle,
        content: post.content,
        timestamp: post.timestamp,
        likes: post.likes,
        retweets: post.retweets,
        replies: post.replies,
        url: post.url,
        media_urls: post.media_urls || [],
      })),
      { onConflict: "post_id" }
    );

    if (error) {
      console.error("保存帖子失败:", error);
      throw error;
    }
  }

  /**
   * 获取指定用户的帖子
   */
  async getPostsByUser(
    username: string,
    limit: number = 50
  ): Promise<TwitterPost[]> {
    const { data, error } = await this.client
      .from("twitter_posts")
      .select("*")
      .eq("author", username)
      .order("timestamp", { ascending: false })
      .limit(limit);

    if (error) {
      console.error("获取帖子失败:", error);
      throw error;
    }

    return data || [];
  }

  /**
   * 获取指定日期范围的帖子
   */
  async getPostsByDateRange(
    startDate: string,
    endDate: string,
    usernames?: string[]
  ): Promise<TwitterPost[]> {
    let query = this.client
      .from("twitter_posts")
      .select("*")
      .gte("timestamp", startDate)
      .lte("timestamp", endDate)
      .order("timestamp", { ascending: false });

    if (usernames && usernames.length > 0) {
      query = query.in("author", usernames);
    }

    const { data, error } = await query;

    if (error) {
      console.error("获取帖子失败:", error);
      throw error;
    }

    return data || [];
  }

  /**
   * 搜索帖子内容
   */
  async searchPosts(
    query: string,
    limit: number = 20
  ): Promise<TwitterPost[]> {
    const { data, error } = await this.client
      .from("twitter_posts")
      .select("*")
      .textSearch("content", query)
      .limit(limit);

    if (error) {
      console.error("搜索帖子失败:", error);
      throw error;
    }

    return data || [];
  }

  // ========== 分析结果操作 ==========

  /**
   * 保存分析结果
   */
  async saveAnalysis(analysis: AnalysisResult): Promise<void> {
    const { error } = await this.client.from("analysis_results").insert({
      period: analysis.period,
      summary: analysis.summary,
      clusters: analysis.clusters,
      total_posts: analysis.total_posts,
      analyzed_users: analysis.analyzed_users,
      analyzed_at: analysis.analyzed_at,
    });

    if (error) {
      console.error("保存分析结果失败:", error);
      throw error;
    }
  }

  /**
   * 获取最近的分析结果
   */
  async getRecentAnalysis(limit: number = 10): Promise<AnalysisResult[]> {
    const { data, error } = await this.client
      .from("analysis_results")
      .select("*")
      .order("analyzed_at", { ascending: false })
      .limit(limit);

    if (error) {
      console.error("获取分析结果失败:", error);
      throw error;
    }

    return data || [];
  }

  // ========== 向量存储操作 (pgvector) ==========

  /**
   * 保存 embedding
   */
  async saveEmbedding(record: EmbeddingRecord): Promise<void> {
    const { error } = await this.client.from("embeddings").insert({
      content: record.content,
      content_type: record.content_type,
      reference_id: record.reference_id,
      embedding: record.embedding,
      metadata: record.metadata || {},
    });

    if (error) {
      console.error("保存 embedding 失败:", error);
      throw error;
    }
  }

  /**
   * 批量保存 embeddings
   */
  async saveEmbeddings(records: EmbeddingRecord[]): Promise<void> {
    if (records.length === 0) return;

    const { error } = await this.client.from("embeddings").insert(
      records.map((r) => ({
        content: r.content,
        content_type: r.content_type,
        reference_id: r.reference_id,
        embedding: r.embedding,
        metadata: r.metadata || {},
      }))
    );

    if (error) {
      console.error("批量保存 embedding 失败:", error);
      throw error;
    }
  }

  /**
   * 语义搜索 - 基于向量相似度
   *
   * 需要在 Supabase 中创建函数:
   * CREATE OR REPLACE FUNCTION match_embeddings(
   *   query_embedding vector(1536),
   *   match_threshold float,
   *   match_count int
   * )
   */
  async semanticSearch(
    queryEmbedding: number[],
    options: {
      matchThreshold?: number;
      matchCount?: number;
      contentType?: "post" | "summary" | "cluster";
    } = {}
  ): Promise<
    Array<{
      id: string;
      content: string;
      content_type: string;
      reference_id: string;
      similarity: number;
      metadata: Record<string, unknown>;
    }>
  > {
    const { matchThreshold = 0.7, matchCount = 10, contentType } = options;

    let query = this.client.rpc("match_embeddings", {
      query_embedding: queryEmbedding,
      match_threshold: matchThreshold,
      match_count: matchCount,
    });

    if (contentType) {
      query = query.eq("content_type", contentType);
    }

    const { data, error } = await query;

    if (error) {
      console.error("语义搜索失败:", error);
      throw error;
    }

    return data || [];
  }

  /**
   * 获取帖子及其 embedding
   */
  async getPostsWithEmbeddings(
    postIds: string[]
  ): Promise<Array<TwitterPost & { embedding?: number[] }>> {
    const { data: posts, error: postsError } = await this.client
      .from("twitter_posts")
      .select("*")
      .in("post_id", postIds);

    if (postsError) {
      console.error("获取帖子失败:", postsError);
      throw postsError;
    }

    const { data: embeddings, error: embError } = await this.client
      .from("embeddings")
      .select("reference_id, embedding")
      .eq("content_type", "post")
      .in("reference_id", postIds);

    if (embError) {
      console.error("获取 embedding 失败:", embError);
      throw embError;
    }

    const embeddingMap = new Map(
      (embeddings || []).map((e) => [e.reference_id, e.embedding])
    );

    return (posts || []).map((post) => ({
      ...post,
      embedding: embeddingMap.get(post.post_id),
    }));
  }

  // ========== 统计与管理 ==========

  /**
   * 获取统计信息
   */
  async getStatistics(): Promise<{
    totalPosts: number;
    totalAnalysis: number;
    totalEmbeddings: number;
    userCount: number;
  }> {
    const [postsCount, analysisCount, embeddingsCount, usersCount] =
      await Promise.all([
        this.client
          .from("twitter_posts")
          .select("*", { count: "exact", head: true }),
        this.client
          .from("analysis_results")
          .select("*", { count: "exact", head: true }),
        this.client
          .from("embeddings")
          .select("*", { count: "exact", head: true }),
        this.client
          .from("twitter_posts")
          .select("author", { count: "exact", head: true }),
      ]);

    return {
      totalPosts: postsCount.count || 0,
      totalAnalysis: analysisCount.count || 0,
      totalEmbeddings: embeddingsCount.count || 0,
      userCount: usersCount.count || 0,
    };
  }

  /**
   * 清理旧数据
   */
  async cleanupOldData(retentionDays: number = 30): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    const { count, error } = await this.client
      .from("twitter_posts")
      .delete()
      .lt("created_at", cutoffDate.toISOString())
      .select("*", { count: "exact", head: true });

    if (error) {
      console.error("清理数据失败:", error);
      throw error;
    }

    return count || 0;
  }
}

// 导出单例
let supabaseInstance: SupabaseService | null = null;

export function getSupabaseService(): SupabaseService {
  if (!supabaseInstance) {
    supabaseInstance = new SupabaseService();
  }
  return supabaseInstance;
}

export default SupabaseService;
