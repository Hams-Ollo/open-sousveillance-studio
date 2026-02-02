"""
Firecrawl client wrapper for Open Sousveillance Studio System.

Provides a high-level interface for web scraping with:
- Retry logic with exponential backoff
- Actions support for React SPAs
- Batch scraping
- PDF extraction
- URL validation for security
"""

import os
import time
import re
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse

from firecrawl import FirecrawlApp


# Allowed domains for scraping (security measure against SSRF)
ALLOWED_DOMAINS = [
    "portal.civicclerk.com",
    "floridapublicnotices.com",
    "mysuwanneeriver.com",
    "permitting.sjrwmd.com",
    "alachuacounty.us",
    "cityofalachua.com",
    "alachuafl.gov",
    "floridadep.gov",
    "clerk.alachuacounty.us",
]


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

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        validate_urls: bool = True,
        allowed_domains: Optional[List[str]] = None
    ):
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key (defaults to FIRECRAWL_API_KEY env var)
            max_retries: Maximum retry attempts for failed requests
            validate_urls: Whether to validate URLs against allowed domains
            allowed_domains: Custom list of allowed domains (uses default if None)
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not found. Set environment variable or pass api_key.")

        self.client = FirecrawlApp(api_key=self.api_key)
        self.max_retries = max_retries
        self.validate_urls = validate_urls
        self.allowed_domains = allowed_domains or ALLOWED_DOMAINS

    def _validate_url(self, url: str) -> bool:
        """
        Validate URL against allowed domains list.

        Args:
            url: URL to validate

        Returns:
            True if URL is allowed, False otherwise

        Raises:
            ValueError: If URL is not in allowed domains and validation is enabled
        """
        if not self.validate_urls:
            return True

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if domain matches any allowed domain (including subdomains)
            for allowed in self.allowed_domains:
                if domain == allowed or domain.endswith('.' + allowed):
                    return True

            raise ValueError(
                f"URL domain '{domain}' not in allowed list. "
                f"Allowed domains: {', '.join(self.allowed_domains)}"
            )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid URL format: {url}") from e

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
        # Validate URL against allowed domains
        self._validate_url(url)

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
        # Validate URL against allowed domains
        self._validate_url(url)

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
        # Validate URL against allowed domains
        self._validate_url(url)

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

    def scrape_with_actions(
        self,
        url: str,
        actions: list[dict],
        formats: list[str] = None
    ) -> ScrapeResult:
        """
        Scrape a page with custom browser actions.

        Args:
            url: URL to scrape
            actions: List of action dicts (click, wait, scroll, etc.)
            formats: Output formats (default: ["markdown"])

        Returns:
            ScrapeResult with content after actions executed

        Example actions:
            [
                {"type": "wait", "milliseconds": 2000},
                {"type": "click", "selector": "#download-btn"},
                {"type": "wait", "milliseconds": 500},
                {"type": "click", "selector": "[data-option='agenda-packet']"},
            ]
        """
        formats = formats or ["markdown"]

        try:
            result = self._retry_with_backoff(
                self.client.scrape,
                url,
                formats=formats,
                actions=actions
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

    def scrape_civicclerk_with_scroll(
        self,
        url: str,
        scroll_count: int = 3
    ) -> ScrapeResult:
        """
        Scrape CivicClerk portal with scrolling to load more events.

        Args:
            url: CivicClerk portal URL
            scroll_count: Number of scroll iterations (up for past, down for future)

        Returns:
            ScrapeResult with all loaded meeting content
        """
        actions = [
            {"type": "wait", "milliseconds": 3000},  # Wait for React to load
        ]

        # Scroll up to load past events
        for _ in range(scroll_count):
            actions.append({"type": "scroll", "direction": "up"})
            actions.append({"type": "wait", "milliseconds": 1000})

        # Scroll back down to load future events
        for _ in range(scroll_count):
            actions.append({"type": "scroll", "direction": "down"})
            actions.append({"type": "wait", "milliseconds": 1000})

        return self.scrape_with_actions(
            url,
            actions=actions,
            formats=["markdown", "links"]
        )

    def civicclerk_click_download(
        self,
        url: str,
        download_button_selector: str = "[aria-label='Download Files from this Event']",
        agenda_packet_selector: str = "text=Agenda Packet (PDF)"
    ) -> ScrapeResult:
        """
        Click download button and select Agenda Packet on CivicClerk.

        This attempts to trigger the download dropdown and click the
        Agenda Packet (PDF) option. Note: Firecrawl may not capture
        the actual file download, but will return the page state after clicks.

        Args:
            url: CivicClerk meeting page URL
            download_button_selector: CSS selector for download button
            agenda_packet_selector: Selector for Agenda Packet option

        Returns:
            ScrapeResult with page content after clicking
        """
        actions = [
            {"type": "wait", "milliseconds": 3000},
            {"type": "click", "selector": download_button_selector},
            {"type": "wait", "milliseconds": 500},
            {"type": "click", "selector": agenda_packet_selector},
            {"type": "wait", "milliseconds": 1000},
        ]

        return self.scrape_with_actions(
            url,
            actions=actions,
            formats=["markdown", "links"]
        )
