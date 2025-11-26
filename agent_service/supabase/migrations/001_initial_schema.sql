-- TrendRadar Supabase 数据库初始化脚本
-- 创建表结构和 pgvector 扩展

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- Twitter 帖子表
CREATE TABLE IF NOT EXISTS twitter_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    post_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(255) NOT NULL,
    author_handle VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    url TEXT,
    media_urls JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_twitter_posts_author ON twitter_posts(author);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_timestamp ON twitter_posts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_created_at ON twitter_posts(created_at DESC);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_twitter_posts_content_fts
ON twitter_posts USING gin(to_tsvector('chinese', content));

-- 分析结果表
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    period VARCHAR(50) NOT NULL,
    summary TEXT,
    clusters JSONB DEFAULT '[]'::jsonb,
    total_posts INTEGER DEFAULT 0,
    analyzed_users JSONB DEFAULT '[]'::jsonb,
    analyzed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_analysis_results_period ON analysis_results(period);
CREATE INDEX IF NOT EXISTS idx_analysis_results_analyzed_at ON analysis_results(analyzed_at DESC);

-- Embedding 向量表
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- 'post', 'summary', 'cluster'
    reference_id VARCHAR(255) NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI text-embedding-3-small 默认维度
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 向量索引 (使用 IVFFlat 或 HNSW)
CREATE INDEX IF NOT EXISTS idx_embeddings_embedding
ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_content_type ON embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_reference_id ON embeddings(reference_id);

-- 语义搜索函数
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    content_type VARCHAR(50),
    reference_id VARCHAR(255),
    similarity float,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content,
        e.content_type,
        e.reference_id,
        1 - (e.embedding <=> query_embedding) AS similarity,
        e.metadata
    FROM embeddings e
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_twitter_posts_updated_at
    BEFORE UPDATE ON twitter_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 行级安全策略 (RLS)
ALTER TABLE twitter_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- 允许匿名读取
CREATE POLICY "Allow anonymous read" ON twitter_posts
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read" ON analysis_results
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read" ON embeddings
    FOR SELECT USING (true);

-- 允许服务角色写入
CREATE POLICY "Allow service write" ON twitter_posts
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service write" ON analysis_results
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service write" ON embeddings
    FOR ALL USING (auth.role() = 'service_role');

-- 统计视图
CREATE OR REPLACE VIEW statistics AS
SELECT
    (SELECT COUNT(*) FROM twitter_posts) AS total_posts,
    (SELECT COUNT(*) FROM analysis_results) AS total_analyses,
    (SELECT COUNT(*) FROM embeddings) AS total_embeddings,
    (SELECT COUNT(DISTINCT author) FROM twitter_posts) AS unique_users,
    (SELECT MAX(created_at) FROM twitter_posts) AS last_post_at,
    (SELECT MAX(analyzed_at) FROM analysis_results) AS last_analysis_at;
