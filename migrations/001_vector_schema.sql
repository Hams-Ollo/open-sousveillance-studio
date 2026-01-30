-- ============================================================================
-- Migration: 001_vector_schema.sql
-- Description: Create pgvector extension and document_chunks table for RAG
-- Alachua Civic Intelligence Reporting Studio
-- ============================================================================

-- Enable pgvector extension (requires Supabase or PostgreSQL with pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Document Chunks Table
-- Stores chunked document content with embeddings for semantic search
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Document reference
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Content
    content TEXT NOT NULL,
    
    -- Embedding vector (1536 dimensions for gemini-embedding-001)
    embedding VECTOR(1536),
    
    -- Metadata (source URL, date, agent, document type, etc.)
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique chunks per document
    UNIQUE(document_id, chunk_index)
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Index for document lookups
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
ON document_chunks(document_id);

-- Index for metadata queries (GIN for JSONB)
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata 
ON document_chunks USING GIN(metadata);

-- Vector similarity search index (IVFFlat for cosine similarity)
-- lists = 100 is good for up to ~100k vectors
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================================================
-- RPC Function: match_documents
-- Performs similarity search using cosine distance
-- ============================================================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.7,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id TEXT,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.chunk_index,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE 
        -- Apply similarity threshold
        1 - (dc.embedding <=> query_embedding) >= match_threshold
        -- Apply metadata filter if provided
        AND (filter_metadata IS NULL OR dc.metadata @> filter_metadata)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- Trigger: Update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_document_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Row Level Security (RLS) - Optional
-- Uncomment if you want to enable RLS for multi-tenant scenarios
-- ============================================================================

-- ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Allow all operations for authenticated users"
-- ON document_chunks
-- FOR ALL
-- TO authenticated
-- USING (true)
-- WITH CHECK (true);

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE document_chunks IS 'Stores chunked document content with vector embeddings for semantic search';
COMMENT ON COLUMN document_chunks.document_id IS 'Reference to the source document (e.g., report_id, URL hash)';
COMMENT ON COLUMN document_chunks.chunk_index IS 'Position of this chunk within the document (0-indexed)';
COMMENT ON COLUMN document_chunks.content IS 'The text content of this chunk';
COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding from gemini-embedding-001 (1536 dimensions)';
COMMENT ON COLUMN document_chunks.metadata IS 'Additional metadata: source_url, agent_id, document_type, etc.';
COMMENT ON FUNCTION match_documents IS 'Semantic similarity search using cosine distance';
