"""
Tools package for Alachua Civic Intelligence System.

Provides specialized tools for:
- Web scraping (Firecrawl)
- Document processing (Docling)
"""

from src.tools.firecrawl_client import FirecrawlClient

# Docling has heavy dependencies (TensorFlow, NumPy) - import lazily
try:
    from src.tools.docling_processor import DoclingProcessor
except ImportError:
    DoclingProcessor = None  # type: ignore

__all__ = ["FirecrawlClient", "DoclingProcessor"]
