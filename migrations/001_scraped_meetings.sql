-- Migration: Create scraped_meetings and documents tables for Hybrid Scraping Pipeline
-- Run this in your Supabase SQL Editor

-- ============================================================================
-- Table: scraped_meetings
-- Tracks meeting state for incremental scraping
-- ============================================================================

CREATE TABLE IF NOT EXISTS scraped_meetings (
    -- Primary key (composite)
    meeting_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    
    -- Meeting metadata
    title TEXT NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    board TEXT,
    
    -- Agenda tracking
    agenda_posted_date TIMESTAMPTZ,
    agenda_packet_url TEXT,
    has_agenda_packet BOOLEAN DEFAULT FALSE,
    has_agenda BOOLEAN DEFAULT FALSE,
    
    -- Content tracking
    content_hash TEXT,
    pdf_content TEXT,
    
    -- Processing state
    last_scraped_at TIMESTAMPTZ DEFAULT NOW(),
    last_analyzed_at TIMESTAMPTZ,
    report_id TEXT,
    
    -- Additional metadata (JSON)
    metadata JSONB DEFAULT '{}',
    
    -- Composite primary key
    PRIMARY KEY (meeting_id, source_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_scraped_meetings_source ON scraped_meetings(source_id);
CREATE INDEX IF NOT EXISTS idx_scraped_meetings_date ON scraped_meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_scraped_meetings_unanalyzed ON scraped_meetings(source_id) 
    WHERE last_analyzed_at IS NULL;

-- ============================================================================
-- Table: documents
-- Stores extracted PDF content
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    -- Primary key
    document_id TEXT PRIMARY KEY,
    
    -- Links
    source_id TEXT NOT NULL,
    meeting_id TEXT,
    
    -- Content
    title TEXT,
    document_type TEXT,  -- agenda, agenda_packet, minutes, notice, etc.
    url TEXT,
    content TEXT,
    content_hash TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Additional metadata (JSON)
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_meeting ON documents(meeting_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);

-- ============================================================================
-- Table: reports (if not exists)
-- Stores ScoutReports and AnalystReports
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- scout, analyst, synthesizer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(type);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE scraped_meetings IS 'Tracks meeting state for hybrid scraping pipeline. Enables incremental processing.';
COMMENT ON TABLE documents IS 'Stores extracted PDF content from agenda packets and other documents.';
COMMENT ON TABLE reports IS 'Stores ScoutReports, AnalystReports, and SynthesizerReports as JSON.';
