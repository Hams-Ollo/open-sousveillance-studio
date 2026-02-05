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

# Import LangChain tools from the tools module
# Note: src/tools.py coexists with src/tools/ package
# We import its contents here to make them accessible via src.tools
import sys
import importlib.util

# Load src/tools.py as a separate module
_tools_module_path = __file__.replace("__init__.py", "").rstrip("/\\").rstrip("tools") + "tools.py"
_spec = importlib.util.spec_from_file_location("_tools_module", _tools_module_path)
if _spec and _spec.loader:
    _tools_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_tools_module)

    # Export the tools
    monitor_url = _tools_module.monitor_url
    deep_research = _tools_module.deep_research
    scrape_pdf = _tools_module.scrape_pdf
    get_tavily_client = _tools_module.get_tavily_client
    get_firecrawl_client = _tools_module.get_firecrawl_client
else:
    # Fallback if module loading fails
    monitor_url = None
    deep_research = None
    scrape_pdf = None
    get_tavily_client = None
    get_firecrawl_client = None

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
