"""
RAG (Retrieval-Augmented Generation) pipeline for Alachua Civic Intelligence System.

Provides a unified interface for:
- Ingesting documents (chunk → embed → store)
- Retrieving relevant context for queries
"""

from typing import Optional

from src.tools.embeddings import get_embedding_service, EmbeddingService
from src.tools.chunking import get_chunking_pipeline, ChunkingPipeline, DocumentChunk
from src.tools.vector_store import get_vector_store, VectorStore


class RAGPipeline:
    """
    Unified RAG pipeline for document ingestion and retrieval.
    
    Combines chunking, embedding, and vector storage into a
    simple interface for agents to use.
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        chunking_pipeline: Optional[ChunkingPipeline] = None,
        vector_store: Optional[VectorStore] = None
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            embedding_service: Optional custom embedding service.
            chunking_pipeline: Optional custom chunking pipeline.
            vector_store: Optional custom vector store.
        """
        self.embeddings = embedding_service or get_embedding_service()
        self.chunker = chunking_pipeline or get_chunking_pipeline()
        self.store = vector_store or get_vector_store()
    
    def ingest_document(
        self,
        text: str,
        document_id: str,
        metadata: Optional[dict] = None,
        title: Optional[str] = None
    ) -> int:
        """
        Ingest a document into the vector store.
        
        Chunks the document, generates embeddings, and stores them.
        
        Args:
            text: The document text to ingest.
            document_id: Unique identifier for the document.
            metadata: Optional metadata to attach to chunks.
            title: Optional document title (improves embedding quality).
        
        Returns:
            Number of chunks stored.
        """
        # Step 1: Chunk the document
        chunks = self.chunker.chunk_text(
            text=text,
            document_id=document_id,
            metadata=metadata
        )
        
        if not chunks:
            return 0
        
        # Step 2: Generate embeddings for all chunks
        embeddings = self.embeddings.embed_batch(
            texts=[chunk.content for chunk in chunks],
            task_type="RETRIEVAL_DOCUMENT",
            titles=[title] * len(chunks) if title else None
        )
        
        # Step 3: Store chunks with embeddings
        self.store.upsert_chunks(chunks, embeddings)
        
        return len(chunks)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: The search query.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filters.
        
        Returns:
            List of relevant chunks with similarity scores.
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Search vector store
        results = self.store.similarity_search(
            query_embedding=query_embedding,
            match_count=top_k,
            match_threshold=0.0,  # Return all, sorted by similarity
            filter_metadata=filter_metadata
        )
        
        return results
    
    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 4000
    ) -> str:
        """
        Retrieve and format context for LLM prompts.
        
        Args:
            query: The search query.
            top_k: Maximum number of chunks to retrieve.
            max_tokens: Approximate max characters for context.
        
        Returns:
            Formatted context string for LLM prompts.
        """
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return "No relevant context found."
        
        # Format results into context string
        context_parts = []
        total_chars = 0
        
        for i, result in enumerate(results):
            chunk_text = f"[Source {i+1}] (similarity: {result.get('similarity', 0):.2f})\n{result['content']}\n"
            
            if total_chars + len(chunk_text) > max_tokens:
                break
            
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n---\n".join(context_parts)
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete a document and all its chunks from the store.
        
        Args:
            document_id: The document ID to delete.
        
        Returns:
            Number of chunks deleted.
        """
        return self.store.delete_document(document_id)
    
    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dict with chunk count and other stats.
        """
        return {
            "total_chunks": self.store.count_chunks(),
            "embedding_dimension": self.embeddings.dimension,
            "chunk_size": self.chunker.chunk_size
        }


# Singleton instance
_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """
    Get or create the RAG pipeline singleton.
    
    Returns:
        RAGPipeline instance.
    """
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
