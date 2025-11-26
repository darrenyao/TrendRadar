/**
 * Embedding 服务 - 文本向量化
 *
 * 功能：
 * - 生成文本 embedding
 * - 支持多种 embedding 模型
 * - 批量处理优化
 */

import { openai } from "@ai-sdk/openai";
import { embed, embedMany } from "ai";

// Embedding 配置
export interface EmbeddingConfig {
  model?: string;
  baseUrl?: string;
  apiKey?: string;
  dimensions?: number;
}

// 默认配置
const DEFAULT_CONFIG: EmbeddingConfig = {
  model: "text-embedding-3-small",
  dimensions: 1536,
};

export class EmbeddingService {
  private config: EmbeddingConfig;

  constructor(config: Partial<EmbeddingConfig> = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      model: config.model || process.env.EMBEDDING_MODEL || DEFAULT_CONFIG.model,
      baseUrl: config.baseUrl || process.env.EMBEDDING_BASE_URL,
      apiKey: config.apiKey || process.env.OPENAI_API_KEY,
    };
  }

  /**
   * 生成单个文本的 embedding
   */
  async generateEmbedding(text: string): Promise<number[]> {
    const { embedding } = await embed({
      model: openai.embedding(this.config.model!, {
        dimensions: this.config.dimensions,
      }),
      value: text,
    });

    return embedding;
  }

  /**
   * 批量生成 embeddings
   */
  async generateEmbeddings(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) return [];

    // 分批处理，每批最多 100 条
    const batchSize = 100;
    const batches: string[][] = [];

    for (let i = 0; i < texts.length; i += batchSize) {
      batches.push(texts.slice(i, i + batchSize));
    }

    const allEmbeddings: number[][] = [];

    for (const batch of batches) {
      const { embeddings } = await embedMany({
        model: openai.embedding(this.config.model!, {
          dimensions: this.config.dimensions,
        }),
        values: batch,
      });

      allEmbeddings.push(...embeddings);
    }

    return allEmbeddings;
  }

  /**
   * 计算两个 embedding 的余弦相似度
   */
  cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error("Embedding 维度不匹配");
    }

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * 找出最相似的文本
   */
  findMostSimilar(
    queryEmbedding: number[],
    candidates: Array<{ text: string; embedding: number[] }>,
    topK: number = 5
  ): Array<{ text: string; similarity: number }> {
    const scored = candidates.map((c) => ({
      text: c.text,
      similarity: this.cosineSimilarity(queryEmbedding, c.embedding),
    }));

    scored.sort((a, b) => b.similarity - a.similarity);

    return scored.slice(0, topK);
  }

  /**
   * 获取配置信息
   */
  getConfig(): EmbeddingConfig {
    return { ...this.config };
  }
}

// 导出单例
let embeddingInstance: EmbeddingService | null = null;

export function getEmbeddingService(
  config?: Partial<EmbeddingConfig>
): EmbeddingService {
  if (!embeddingInstance || config) {
    embeddingInstance = new EmbeddingService(config);
  }
  return embeddingInstance;
}

export default EmbeddingService;
