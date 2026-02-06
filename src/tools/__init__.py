"""
Tools package for Alachua Civic Intelligence System.

Provides specialized tools for:
- Web scraping (Firecrawl)
- Document processing (Docling)
- LangChain tools (monitor_url, deep_research, scrape_pdf)
- Gemini Deep Research (gemini_deep_research)
"""

from src.tools.firecrawl_client import FirecrawlClient
from src.tools.resource_cache import ResourceCache, get_resource_cache

# Docling has heavy dependencies (PyTorch, transformers) - import lazily
# Catch both ImportError and OSError (PyTorch DLL loading issues on Windows)
try:
    from src.tools.docling_processor import DoclingProcessor
except (ImportError, OSError):
    DoclingProcessor = None  # type: ignore

# LangChain tools (Firecrawl scraping, Tavily research)
from src.tools.langchain_tools import (
    monitor_url,
    deep_research,
    scrape_pdf,
    get_tavily_client,
    get_firecrawl_client,
)

# Import Gemini Deep Research tools
try:
    from src.tools.gemini_research import (
        GeminiResearchClient,
        get_gemini_research_client,
        gemini_deep_research,
        ResearchStatus,
        ResearchResult
    )
except (ImportError, ValueError) as e:
    # May fail if google-genai not installed or API key missing
    GeminiResearchClient = None
    get_gemini_research_client = None
    gemini_deep_research = None
    ResearchStatus = None
    ResearchResult = None

__all__ = [
    "FirecrawlClient",
    "DoclingProcessor",
    "ResourceCache",
    "get_resource_cache",
    "monitor_url",
    "deep_research",
    "scrape_pdf",
    "get_tavily_client",
    "get_firecrawl_client",
    "GeminiResearchClient",
    "get_gemini_research_client",
    "gemini_deep_research",
    "ResearchStatus",
    "ResearchResult"
]
