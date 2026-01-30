"""
Firecrawl client wrapper for Alachua Civic Intelligence System.

Provides a high-level interface for web scraping with:
- Retry logic with exponential backoff
- Actions support for React SPAs
- Batch scraping
- PDF extraction
"""

import os
import time
from typing import Optional
from dataclasses import dataclass

from firecrawl import FirecrawlApp


@dataclass
class ScrapeResult:
    """Result from a scrape operation."""
    url: str
    markdown: str
    success: bool
    error: Optional[str] = None
    metadata: Optional[dict] = None


class FirecrawlClient:
    """
    Wrapper around Firecrawl with retry logic and convenience methods.
    
    Usage:
        client = FirecrawlClient()
        result = client.scrape_page("https://example.com")
        print(result.markdown)
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        """
        Initialize Firecrawl client.
        
        Args:
            api_key: Firecrawl API key (defaults to FIRECRAWL_API_KEY env var)
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not found. Set environment variable or pass api_key.")
        
        self.client = FirecrawlApp(api_key=self.api_key)
        self.max_retries = max_retries
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1, 2, 4 seconds
                    time.sleep(wait_time)
        raise last_error
    
    def scrape_page(
        self,
        url: str,
        wait_ms: int = 2000,
        scroll: bool = True,
        formats: list[str] = None
    ) -> ScrapeResult:
        """
        Scrape a single page with JavaScript rendering support.
        
        Args:
            url: URL to scrape
            wait_ms: Milliseconds to wait for JS rendering
            scroll: Whether to scroll down to load lazy content
            formats: Output formats (default: ["markdown"])
        
        Returns:
            ScrapeResult with markdown content
        """
        formats = formats or ["markdown"]
        
        actions = [{"type": "wait", "milliseconds": wait_ms}]
        if scroll:
            actions.append({"type": "scroll", "direction": "down"})
        
        try:
            result = self._retry_with_backoff(
                self.client.scrape,
                url,
                formats=formats,
                actions=actions
            )
            
            # Extract markdown from result
            if hasattr(result, 'markdown'):
                markdown = result.markdown
            elif isinstance(result, dict):
                markdown = result.get('markdown', result.get('content', ''))
            else:
                markdown = str(result)
            
            return ScrapeResult(
                url=url,
                markdown=markdown or "",
                success=True,
                metadata=result.get('metadata') if isinstance(result, dict) else None
            )
            
        except Exception as e:
            return ScrapeResult(
                url=url,
                markdown="",
                success=False,
                error=str(e)
            )
    
    def scrape_pdf(self, url: str) -> ScrapeResult:
        """
        Extract text from a PDF URL.
        
        Args:
            url: Direct URL to PDF file
        
        Returns:
            ScrapeResult with extracted text as markdown
        """
        try:
            result = self._retry_with_backoff(
                self.client.scrape,
                url,
                formats=["markdown"]
            )
            
            if hasattr(result, 'markdown'):
                markdown = result.markdown
            elif isinstance(result, dict):
                markdown = result.get('markdown', result.get('content', ''))
            else:
                markdown = str(result)
            
            return ScrapeResult(
                url=url,
                markdown=markdown or "",
                success=True
            )
            
        except Exception as e:
            return ScrapeResult(
                url=url,
                markdown="",
                success=False,
                error=str(e)
            )
    
    def scrape_civicclerk(self, url: str) -> ScrapeResult:
        """
        Specialized scraper for CivicClerk portals (React SPA).
        
        Uses longer wait times and scrolling to ensure content loads.
        
        Args:
            url: CivicClerk portal URL
        
        Returns:
            ScrapeResult with meeting/agenda content
        """
        return self.scrape_page(
            url,
            wait_ms=3000,  # CivicClerk needs more time
            scroll=True,
            formats=["markdown", "links"]
        )
    
    def map_site(self, url: str, search: Optional[str] = None, limit: int = 100) -> list[str]:
        """
        Discover all URLs on a website.
        
        Args:
            url: Base URL to map
            search: Optional search term to filter URLs
            limit: Maximum URLs to return
        
        Returns:
            List of discovered URLs
        """
        try:
            kwargs = {"url": url, "limit": limit}
            if search:
                kwargs["search"] = search
            
            result = self._retry_with_backoff(self.client.map, **kwargs)
            
            if hasattr(result, 'links'):
                return [link.url if hasattr(link, 'url') else link for link in result.links]
            elif isinstance(result, dict) and 'links' in result:
                return [link.get('url', link) if isinstance(link, dict) else link 
                        for link in result['links']]
            elif isinstance(result, list):
                return result
            
            return []
            
        except Exception as e:
            print(f"Error mapping site {url}: {e}")
            return []
    
    def batch_scrape(self, urls: list[str], wait_ms: int = 2000) -> list[ScrapeResult]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            wait_ms: Wait time per page
        
        Returns:
            List of ScrapeResults
        """
        results = []
        for url in urls:
            result = self.scrape_page(url, wait_ms=wait_ms)
            results.append(result)
        return results
