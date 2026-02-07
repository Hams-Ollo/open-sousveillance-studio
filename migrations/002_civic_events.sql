-- =============================================================================
-- Migration 002: Create civic_events table for EventStore dual-write
-- =============================================================================
-- This table mirrors the file-based EventStore, enabling SQL queries
-- on civic events across all sources.

CREATE TABLE IF NOT EXISTS civic_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    title TEXT NOT NULL,
    description TEXT,
    content_hash TEXT,
    tags TEXT[] DEFAULT '{}',
    location JSONB,
    entities JSONB DEFAULT '[]',
    documents JSONB DEFAULT '[]',
    raw_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_civic_events_source ON civic_events (source_id);
CREATE INDEX IF NOT EXISTS idx_civic_events_type ON civic_events (event_type);
CREATE INDEX IF NOT EXISTS idx_civic_events_timestamp ON civic_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_civic_events_discovered ON civic_events (discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_civic_events_tags ON civic_events USING GIN (tags);

-- Enable RLS (Row Level Security) for Supabase
ALTER TABLE civic_events ENABLE ROW LEVEL SECURITY;

-- Allow authenticated reads
CREATE POLICY "Allow authenticated read" ON civic_events
    FOR SELECT TO authenticated USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role all" ON civic_events
    FOR ALL TO service_role USING (true);
