"""
Document chunking pipeline for Open Sousveillance Studio System.

Splits documents into embeddable chunks using LangChain's
RecursiveCharacterTextSplitter with settings optimized for
government documents.
"""

from typing import Optional
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter


# Default chunking parameters
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    content: str
    chunk_index: int
    document_id: str
    metadata: dict

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "document_id": self.document_id,
            "metadata": self.metadata
        }


class ChunkingPipeline:
    """
    Split documents into chunks suitable for embedding.

    Uses RecursiveCharacterTextSplitter which tries to split
    on natural boundaries (paragraphs, sentences) before
    falling back to character-level splits.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """
        Initialize the chunking pipeline.

        Args:
            chunk_size: Target size for each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",      # Paragraph breaks
                "\n",        # Line breaks
                ". ",        # Sentence endings
                "? ",        # Question endings
                "! ",        # Exclamation endings
                "; ",        # Semicolons
                ", ",        # Commas
                " ",         # Spaces
                ""           # Characters (last resort)
            ]
        )

    def chunk_text(
        self,
        text: str,
        document_id: str,
        metadata: Optional[dict] = None
    ) -> list[DocumentChunk]:
        """
        Split text into chunks with metadata.

        Args:
            text: The document text to chunk.
            document_id: Unique identifier for the source document.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            List of DocumentChunk objects.
        """
        if metadata is None:
            metadata = {}

        # Split the text
        chunks = self.splitter.split_text(text)

        # Create DocumentChunk objects
        return [
            DocumentChunk(
                content=chunk,
                chunk_index=i,
                document_id=document_id,
                metadata={
                    **metadata,
                    "chunk_size": len(chunk),
                    "total_chunks": len(chunks)
                }
            )
            for i, chunk in enumerate(chunks)
        ]

    def chunk_documents(
        self,
        documents: list[dict]
    ) -> list[DocumentChunk]:
        """
        Chunk multiple documents.

        Args:
            documents: List of dicts with 'text', 'document_id', and optional 'metadata'.

        Returns:
            List of all DocumentChunk objects from all documents.
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_text(
                text=doc["text"],
                document_id=doc["document_id"],
                metadata=doc.get("metadata", {})
            )
            all_chunks.extend(chunks)
        return all_chunks


# Singleton instance
_chunking_pipeline: Optional[ChunkingPipeline] = None


import threading
_chunking_lock = threading.Lock()

def get_chunking_pipeline(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> ChunkingPipeline:
    """
    Get or create the chunking pipeline singleton.

    Args:
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.

    Returns:
        ChunkingPipeline instance.
    """
    global _chunking_pipeline
    if _chunking_pipeline is None:
        with _chunking_lock:
            if _chunking_pipeline is None:
                _chunking_pipeline = ChunkingPipeline(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
    return _chunking_pipeline
