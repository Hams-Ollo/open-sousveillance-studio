"""
Tests for tools modules.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestLoggingConfig:
    """Tests for logging configuration."""
    
    def test_get_logger_returns_bound_logger(self):
        """Test get_logger returns a structlog logger."""
        from src.logging_config import get_logger
        
        logger = get_logger("test.module")
        
        assert logger is not None
    
    def test_get_logger_with_context(self):
        """Test get_logger with initial context."""
        from src.logging_config import get_logger
        
        logger = get_logger("test.module", agent_id="A1", source="test")
        
        assert logger is not None
    
    def test_configure_logging_idempotent(self):
        """Test configure_logging can be called multiple times."""
        from src.logging_config import configure_logging
        
        # Should not raise
        configure_logging()
        configure_logging()
    
    def test_bind_and_clear_context(self):
        """Test context binding and clearing."""
        from src.logging_config import bind_context, clear_context
        
        # Should not raise
        bind_context(request_id="test-123")
        clear_context()


class TestEmbeddings:
    """Tests for embedding service."""
    
    @patch('src.tools.embeddings.genai')
    def test_embedding_service_initialization(self, mock_genai):
        """Test EmbeddingService initialization."""
        from src.tools.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        # Actual implementation uses 'model' and 'dimension'
        assert service.model == "models/gemini-embedding-001"
        assert service.dimension == 1536
    
    @patch('src.tools.embeddings.genai')
    def test_embedding_service_custom_dimensions(self, mock_genai):
        """Test EmbeddingService with custom dimensions."""
        from src.tools.embeddings import EmbeddingService
        
        # Actual implementation uses 'dimension' parameter
        service = EmbeddingService(dimension=768)
        
        assert service.dimension == 768


class TestChunking:
    """Tests for document chunking."""
    
    def test_chunking_pipeline_initialization(self):
        """Test ChunkingPipeline initialization."""
        from src.tools.chunking import ChunkingPipeline
        
        chunker = ChunkingPipeline(chunk_size=512, chunk_overlap=50)
        
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
    
    def test_chunking_pipeline_chunk_text(self):
        """Test chunking text content."""
        from src.tools.chunking import ChunkingPipeline
        
        chunker = ChunkingPipeline(chunk_size=100, chunk_overlap=10)
        
        # Create text longer than chunk size
        long_text = "This is a test sentence. " * 20
        
        chunks = chunker.chunk_text(long_text, document_id="test-doc")
        
        assert len(chunks) > 1
        assert all(chunk.document_id == "test-doc" for chunk in chunks)
    
    def test_document_chunk_dataclass(self):
        """Test DocumentChunk dataclass."""
        from src.tools.chunking import DocumentChunk
        
        chunk = DocumentChunk(
            document_id="doc-123",
            chunk_index=0,
            content="Test content",
            metadata={"source": "test"}
        )
        
        assert chunk.document_id == "doc-123"
        assert chunk.chunk_index == 0


class TestVectorStore:
    """Tests for vector store operations."""
    
    def test_vector_store_with_mock_client(self):
        """Test VectorStore initialization with mock client."""
        from src.tools.vector_store import VectorStore
        
        mock_client = MagicMock()
        store = VectorStore(supabase_client=mock_client)
        
        assert store.client is mock_client


class TestRAGPipeline:
    """Tests for RAG pipeline."""
    
    @patch('src.tools.rag_pipeline.get_vector_store')
    @patch('src.tools.rag_pipeline.get_embedding_service')
    @patch('src.tools.rag_pipeline.get_chunking_pipeline')
    def test_rag_pipeline_initialization(self, mock_chunker, mock_embeddings, mock_store):
        """Test RAGPipeline initialization."""
        from src.tools.rag_pipeline import RAGPipeline
        
        pipeline = RAGPipeline()
        
        assert pipeline.chunker is not None
        assert pipeline.embeddings is not None
        assert pipeline.store is not None  # Actual attribute name is 'store'
