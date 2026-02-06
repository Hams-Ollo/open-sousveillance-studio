"""
LangChain tools for Open Sousveillance Studio System.

Provides LangChain-compatible tools for:
- Web scraping via Firecrawl
- Deep research via Tavily
"""

import os
from typing import Optional
from langchain_core.tools import tool
from tavily import TavilyClient
from firecrawl import FirecrawlApp

import threading

# Initialize clients lazily to avoid import-time crashes
_tavily_client: Optional[TavilyClient] = None
_firecrawl_client: Optional[FirecrawlApp] = None
_tavily_lock = threading.Lock()
_firecrawl_lock = threading.Lock()


def get_tavily_client() -> Optional[TavilyClient]:
    """Get or create Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        with _tavily_lock:
            if _tavily_client is None:
                api_key = os.getenv("TAVILY_API_KEY")
                if api_key:
                    _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def get_firecrawl_client() -> Optional[FirecrawlApp]:
    """Get or create Firecrawl client."""
    global _firecrawl_client
    if _firecrawl_client is None:
        with _firecrawl_lock:
            if _firecrawl_client is None:
                api_key = os.getenv("FIRECRAWL_API_KEY")
                if api_key:
                    _firecrawl_client = FirecrawlApp(api_key=api_key)
    return _firecrawl_client


@tool
def deep_research(query: str, max_results: int = 5) -> str:
    """
    Performs a deep web search using Tavily to find recent news, documents, and connections.
    Use this for broad "Analyst" questions like "What is the connection between Tara Forest and Mill Creek?".
    """
    client = get_tavily_client()
    if not client:
        return "Error: Tavily API Key not configured. Set TAVILY_API_KEY environment variable."

    try:
        response = client.search(query, search_depth="advanced", max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append(f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n---")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


@tool
def monitor_url(url: str, wait_time: int = 2000) -> str:
    """
    Fetches the content of a URL using Firecrawl.
    Handles JavaScript-rendered pages (React SPAs like CivicClerk).
    Use this for "Scout" tasks to read specific agendas or pages.

    Args:
        url: The URL to scrape
        wait_time: Milliseconds to wait for JS rendering (default 2000ms)
    """
    client = get_firecrawl_client()
    if not client:
        return "Error: Firecrawl API Key not configured. Set FIRECRAWL_API_KEY environment variable."

    try:
        # Use Firecrawl with actions for JS-rendered content
        result = client.scrape(
            url,
            formats=["markdown"],
            actions=[
                {"type": "wait", "milliseconds": wait_time},
                {"type": "scroll", "direction": "down"}
            ]
        )

        # Extract markdown content
        if hasattr(result, 'markdown'):
            content = result.markdown
        elif isinstance(result, dict):
            content = result.get('markdown', result.get('content', str(result)))
        else:
            content = str(result)

        # Truncate if needed for LLM context
        return content[:50000] if content else "No content extracted."

    except Exception as e:
        return f"Failed to fetch {url}: {e}"


@tool
def scrape_pdf(url: str) -> str:
    """
    Fetches and extracts text from a PDF URL using Firecrawl.
    Use this for agenda packets, staff reports, and other PDF documents.

    Args:
        url: Direct URL to a PDF file
    """
    client = get_firecrawl_client()
    if not client:
        return "Error: Firecrawl API Key not configured. Set FIRECRAWL_API_KEY environment variable."

    try:
        result = client.scrape(
            url,
            formats=["markdown"]
        )

        if hasattr(result, 'markdown'):
            content = result.markdown
        elif isinstance(result, dict):
            content = result.get('markdown', result.get('content', str(result)))
        else:
            content = str(result)

        return content[:50000] if content else "No content extracted from PDF."

    except Exception as e:
        return f"Failed to extract PDF from {url}: {e}"
