"""
Vector store for Alachua Civic Intelligence System.

Provides pgvector operations via Supabase for storing and
retrieving document embeddings for semantic search.
"""

from typing import Optional
from datetime import datetime

from supabase import Client

from src.config import SUPABASE_URL, SUPABASE_KEY
from src.tools.chunking import DocumentChunk


# Default configuration
DEFAULT_MATCH_COUNT = 5
DEFAULT_MATCH_THRESHOLD = 0.7
EMBEDDING_DIMENSION = 1536


class VectorStore:
    """
    Supabase pgvector operations for document embeddings.
    
    Provides methods for:
    - Storing document chunks with embeddings
    - Semantic similarity search
    - Document retrieval by ID
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize the vector store.
        
        Args:
            supabase_client: Optional Supabase client. If not provided,
                            creates one from environment variables.
        """
        if supabase_client:
            self.client = supabase_client
        else:
            self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client from environment."""
        from supabase import create_client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def upsert_chunk(
        self,
        chunk: DocumentChunk,
        embedding: list[float]
    ) -> dict:
        """
        Store a single chunk with its embedding.
        
        Args:
            chunk: The DocumentChunk to store.
            embedding: The embedding vector for the chunk.
        
        Returns:
            The upserted record.
        """
        payload = {
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "embedding": embedding,
            "metadata": chunk.metadata,
            "created_at": datetime.now().isoformat()
        }
        
        response = self.client.table("document_chunks").upsert(
            payload,
            on_conflict="document_id,chunk_index"
        ).execute()
        
        return response.data[0] if response.data else {}
    
    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]]
    ) -> list[dict]:
        """
        Store multiple chunks with their embeddings.
        
        Args:
            chunks: List of DocumentChunk objects.
            embeddings: List of embedding vectors (must match chunks length).
        
        Returns:
            List of upserted records.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        
        payloads = [
            {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "embedding": embedding,
                "metadata": chunk.metadata,
                "created_at": datetime.now().isoformat()
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]
        
        response = self.client.table("document_chunks").upsert(
            payloads,
            on_conflict="document_id,chunk_index"
        ).execute()
        
        return response.data
    
    def similarity_search(
        self,
        query_embedding: list[float],
        match_count: int = DEFAULT_MATCH_COUNT,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
        filter_metadata: Optional[dict] = None
    ) -> list[dict]:
        """
        Find chunks most similar to the query embedding.
        
        Uses cosine similarity via Supabase RPC function.
        
        Args:
            query_embedding: The query embedding vector.
            match_count: Maximum number of results to return.
            match_threshold: Minimum similarity score (0-1).
            filter_metadata: Optional metadata filters.
        
        Returns:
            List of matching chunks with similarity scores.
        """
        params = {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "match_threshold": match_threshold
        }
        
        if filter_metadata:
            params["filter_metadata"] = filter_metadata
        
        response = self.client.rpc("match_documents", params).execute()
        
        return response.data
    
    def search(
        self,
        query_embedding: list[float],
        top_k: int = DEFAULT_MATCH_COUNT
    ) -> list[dict]:
        """
        Simplified search interface.
        
        Args:
            query_embedding: The query embedding vector.
            top_k: Number of results to return.
        
        Returns:
            List of matching chunks.
        """
        return self.similarity_search(
            query_embedding=query_embedding,
            match_count=top_k,
            match_threshold=0.0  # Return all, sorted by similarity
        )
    
    def get_document_chunks(self, document_id: str) -> list[dict]:
        """
        Retrieve all chunks for a specific document.
        
        Args:
            document_id: The document ID to retrieve.
        
        Returns:
            List of chunks ordered by chunk_index.
        """
        response = self.client.table("document_chunks").select("*").eq(
            "document_id", document_id
        ).order("chunk_index").execute()
        
        return response.data
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: The document ID to delete.
        
        Returns:
            Number of deleted chunks.
        """
        response = self.client.table("document_chunks").delete().eq(
            "document_id", document_id
        ).execute()
        
        return len(response.data) if response.data else 0
    
    def count_chunks(self) -> int:
        """
        Get total number of chunks in the store.
        
        Returns:
            Total chunk count.
        """
        response = self.client.table("document_chunks").select(
            "id", count="exact"
        ).execute()
        
        return response.count or 0


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the vector store singleton.
    
    Returns:
        VectorStore instance.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
