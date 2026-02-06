"""
Embedding service for Open Sousveillance Studio System.

Uses Gemini embedding model (gemini-embedding-001) for generating
vector embeddings of text content for semantic search.
"""

import os
from typing import Optional

import google.generativeai as genai


# Model configuration
EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_DIMENSION = 1536  # Recommended: 768, 1536, or 3072


class EmbeddingService:
    """
    Generate embeddings using Google's Gemini embedding model.

    Supports configurable output dimensions and task types for
    optimized embedding quality.
    """

    def __init__(self, dimension: int = DEFAULT_DIMENSION):
        """
        Initialize the embedding service.

        Args:
            dimension: Output embedding dimension (128-3072).
                       Recommended: 768, 1536, or 3072.
        """
        self.dimension = dimension
        self.model = EMBEDDING_MODEL
        self._configure_client()

    def _configure_client(self):
        """Configure the Gemini API client."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        genai.configure(api_key=api_key)

    def embed_text(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT",
        title: Optional[str] = None
    ) -> list[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: The text to embed.
            task_type: The task type for optimized embeddings.
                       Options:
                       - RETRIEVAL_DOCUMENT: For documents to be searched
                       - RETRIEVAL_QUERY: For search queries
                       - SEMANTIC_SIMILARITY: For comparing text similarity
                       - CLASSIFICATION: For text classification
                       - CLUSTERING: For clustering documents
            title: Optional title for the document (improves quality).

        Returns:
            List of floats representing the embedding vector.
        """
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type=task_type,
            title=title,
            output_dimensionality=self.dimension
        )
        return result["embedding"]

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Uses RETRIEVAL_QUERY task type optimized for queries.

        Args:
            query: The search query text.

        Returns:
            List of floats representing the embedding vector.
        """
        return self.embed_text(query, task_type="RETRIEVAL_QUERY")

    def embed_document(self, text: str, title: Optional[str] = None) -> list[float]:
        """
        Generate embedding for a document chunk.

        Uses RETRIEVAL_DOCUMENT task type optimized for documents.

        Args:
            text: The document text to embed.
            title: Optional document title for improved quality.

        Returns:
            List of floats representing the embedding vector.
        """
        return self.embed_text(text, task_type="RETRIEVAL_DOCUMENT", title=title)

    def embed_batch(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        titles: Optional[list[str]] = None
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.
            task_type: The task type for all embeddings.
            titles: Optional list of titles (must match texts length).

        Returns:
            List of embedding vectors.
        """
        embeddings = []
        for i, text in enumerate(texts):
            title = titles[i] if titles and i < len(titles) else None
            embedding = self.embed_text(text, task_type=task_type, title=title)
            embeddings.append(embedding)
        return embeddings


# Singleton instance for convenience
_embedding_service: Optional[EmbeddingService] = None


import threading
_embedding_lock = threading.Lock()

def get_embedding_service(dimension: int = DEFAULT_DIMENSION) -> EmbeddingService:
    """
    Get or create the embedding service singleton.

    Args:
        dimension: Output embedding dimension.

    Returns:
        EmbeddingService instance.
    """
    global _embedding_service
    if _embedding_service is None:
        with _embedding_lock:
            if _embedding_service is None:
                _embedding_service = EmbeddingService(dimension=dimension)
    return _embedding_service
