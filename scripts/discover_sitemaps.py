#!/usr/bin/env python3
"""
Sitemap Discovery Script for Open Sousveillance Studio
=======================================================

Uses Firecrawl's map_site API to perform comprehensive sitemap discovery
on all target data sources. Outputs a structured SOURCE_DIRECTORY that
Scout agents can reference to find:

- Meeting detail pages
- Document download URLs
- PDF repositories
- API endpoints
- Archive sections
- Drill-down pages with additional context

Usage:
    python scripts/discover_sitemaps.py [--source SOURCE_ID] [--limit LIMIT] [--output FORMAT]

Examples:
    # Discover all sources (default limit 100 URLs per source)
    python scripts/discover_sitemaps.py

    # Discover specific source with higher limit
    python scripts/discover_sitemaps.py --source alachua-civicclerk --limit 500

    # Output as YAML instead of Markdown
    python scripts/discover_sitemaps.py --output yaml
"""

import os
import sys
import json
import yaml
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse, urljoin
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.tools.firecrawl_client import FirecrawlClient, ALLOWED_DOMAINS
from src.logging_config import get_logger

logger = get_logger("scripts.discover_sitemaps")


# =============================================================================
# URL Classification
# =============================================================================

@dataclass
class URLCategory:
    """Categorization of a discovered URL."""
    url: str
    category: str  # meeting_list, meeting_detail, document, pdf, api, archive, other
    subcategory: Optional[str] = None
    description: Optional[str] = None
    priority: str = "medium"  # critical, high, medium, low
    file_type: Optional[str] = None  # pdf, html, json, xml
    keywords: List[str] = field(default_factory=list)


class URLClassifier:
    """Classifies URLs by type and relevance."""

    # Patterns for classification
    PATTERNS = {
        # Document types
        "pdf": [r"\.pdf$", r"/pdf/", r"download.*pdf", r"document.*\.pdf"],
        "document": [r"/documents?/", r"/files?/", r"/attachments?/", r"/downloads?/"],

        # Meeting-related
        "meeting_list": [r"/meetings?/?$", r"/calendar", r"/events?/?$", r"/agendas?/?$", r"portal\.civicclerk\.com/?$"],
        "meeting_detail": [r"/meeting/\d+", r"/event/\d+", r"/agenda/\d+", r"eventid=", r"meetingid="],
        "minutes": [r"/minutes", r"minutes\.pdf"],
        "agenda": [r"/agenda", r"agenda\.pdf", r"agenda-packet"],

        # Permit-related
        "permit_list": [r"/permits?/?$", r"/applications?/?$", r"/notice.*permit", r"/1616", r"/1617"],
        "permit_detail": [r"/permit/\d+", r"/application/\d+", r"#/ep/permit/", r"permitid="],

        # Archive/History
        "archive": [r"/archive", r"/history", r"/past-", r"/previous", r"/\d{4}/"],

        # API endpoints
        "api": [r"/api/", r"\.json$", r"\.xml$", r"/rest/", r"/graphql", r"/v\d+/"],

        # Search/Filter
        "search": [r"/search", r"\?q=", r"\?query=", r"/filter"],

        # Board/Committee specific
        "board": [r"/board", r"/commission", r"/committee", r"/council"],

        # Video/Media
        "video": [r"/video", r"youtube", r"vimeo", r"/media/", r"\.mp4"],

        # Maps/GIS
        "gis": [r"/map", r"/gis", r"arcgis", r"mapgenius"],
    }

    # Priority keywords
    PRIORITY_KEYWORDS = {
        "critical": ["permit", "application", "hearing", "agenda", "commission", "zoning", "development"],
        "high": ["meeting", "minutes", "board", "notice", "document", "pdf"],
        "medium": ["archive", "calendar", "event", "search"],
        "low": ["video", "media", "about", "contact", "faq"],
    }

    @classmethod
    def classify(cls, url: str) -> URLCategory:
        """Classify a URL by its pattern and content."""
        url_lower = url.lower()
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Determine file type
        file_type = None
        if ".pdf" in url_lower:
            file_type = "pdf"
        elif ".json" in url_lower:
            file_type = "json"
        elif ".xml" in url_lower:
            file_type = "xml"

        # Find matching category
        category = "other"
        subcategory = None

        for cat, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    # Map to broader categories
                    if cat in ["pdf", "document"]:
                        category = "document"
                        subcategory = cat
                    elif cat in ["meeting_list", "meeting_detail", "minutes", "agenda"]:
                        category = "meeting"
                        subcategory = cat
                    elif cat in ["permit_list", "permit_detail"]:
                        category = "permit"
                        subcategory = cat
                    elif cat in ["archive"]:
                        category = "archive"
                    elif cat in ["api"]:
                        category = "api"
                    elif cat in ["search"]:
                        category = "search"
                    elif cat in ["board"]:
                        category = "board"
                    elif cat in ["video"]:
                        category = "media"
                    elif cat in ["gis"]:
                        category = "gis"
                    else:
                        category = cat
                    break
            if category != "other":
                break

        # Determine priority
        priority = "medium"
        keywords_found = []
        for prio, keywords in cls.PRIORITY_KEYWORDS.items():
            for kw in keywords:
                if kw in url_lower:
                    keywords_found.append(kw)
                    if prio == "critical" or (prio == "high" and priority not in ["critical"]):
                        priority = prio
                    elif prio == "low" and priority == "medium":
                        priority = prio

        return URLCategory(
            url=url,
            category=category,
            subcategory=subcategory,
            priority=priority,
            file_type=file_type,
            keywords=keywords_found
        )


# =============================================================================
# Source Discovery
# =============================================================================

@dataclass
class SourceSitemap:
    """Discovered sitemap for a single source."""
    source_id: str
    source_name: str
    base_url: str
    discovered_at: datetime
    total_urls: int
    urls_by_category: Dict[str, List[URLCategory]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_url(self, url_cat: URLCategory):
        """Add a categorized URL to the sitemap."""
        if url_cat.category not in self.urls_by_category:
            self.urls_by_category[url_cat.category] = []
        self.urls_by_category[url_cat.category].append(url_cat)

    def get_summary(self) -> Dict[str, int]:
        """Get count by category."""
        return {cat: len(urls) for cat, urls in self.urls_by_category.items()}


class SitemapDiscoverer:
    """Discovers and catalogs URLs from target sources."""

    # Target sources for discovery (subset of sources.yaml for critical sources)
    TARGET_SOURCES = [
        {
            "id": "alachua-civicclerk",
            "name": "City of Alachua - CivicClerk Portal",
            "url": "https://alachuafl.portal.civicclerk.com/",
            "priority": "critical",
        },
        {
            "id": "florida-public-notices",
            "name": "Florida Public Notices",
            "url": "https://floridapublicnotices.com/",
            "priority": "critical",
        },
        {
            "id": "srwmd-main",
            "name": "SRWMD - Main Site",
            "url": "https://www.mysuwanneeriver.com/",
            "priority": "critical",
        },
        {
            "id": "srwmd-epermitting",
            "name": "SRWMD - E-Permitting Portal",
            "url": "https://permitting.sjrwmd.com/",
            "priority": "critical",
        },
        {
            "id": "alachua-county",
            "name": "Alachua County Government",
            "url": "https://alachuacounty.us/",
            "priority": "high",
        },
        {
            "id": "city-of-alachua",
            "name": "City of Alachua - Main Site",
            "url": "https://www.cityofalachua.com/",
            "priority": "high",
        },
        {
            "id": "alachua-clerk",
            "name": "Alachua County Clerk",
            "url": "https://clerk.alachuacounty.us/",
            "priority": "high",
        },
    ]

    def __init__(self, firecrawl_client: Optional[FirecrawlClient] = None):
        """Initialize discoverer with Firecrawl client."""
        # Disable URL validation for discovery (we're mapping, not scraping)
        self.client = firecrawl_client or FirecrawlClient(validate_urls=False)
        self.classifier = URLClassifier()

    def discover_source(
        self,
        source_id: str,
        source_name: str,
        base_url: str,
        limit: int = 100,
        search_terms: Optional[List[str]] = None
    ) -> SourceSitemap:
        """
        Discover all URLs for a single source.

        Args:
            source_id: Unique identifier for the source
            source_name: Human-readable name
            base_url: Base URL to start discovery
            limit: Maximum URLs to discover
            search_terms: Optional search terms to filter results

        Returns:
            SourceSitemap with categorized URLs
        """
        logger.info(f"Discovering sitemap for {source_name}", url=base_url, limit=limit)

        sitemap = SourceSitemap(
            source_id=source_id,
            source_name=source_name,
            base_url=base_url,
            discovered_at=datetime.now(),
            total_urls=0
        )

        try:
            # Use Firecrawl map_site API
            urls = self.client.map_site(base_url, limit=limit)

            if not urls:
                logger.warning(f"No URLs discovered for {source_name}")
                sitemap.errors.append("No URLs returned from map_site API")
                return sitemap

            logger.info(f"Discovered {len(urls)} URLs for {source_name}")
            sitemap.total_urls = len(urls)

            # Classify each URL
            for url in urls:
                if isinstance(url, str):
                    url_cat = self.classifier.classify(url)
                    sitemap.add_url(url_cat)

            # If search terms provided, do additional targeted discovery
            if search_terms:
                for term in search_terms:
                    try:
                        term_urls = self.client.map_site(base_url, search=term, limit=50)
                        for url in term_urls:
                            if isinstance(url, str) and url not in urls:
                                url_cat = self.classifier.classify(url)
                                url_cat.keywords.append(f"search:{term}")
                                sitemap.add_url(url_cat)
                                sitemap.total_urls += 1
                    except Exception as e:
                        logger.warning(f"Search term '{term}' failed: {e}")

        except Exception as e:
            logger.error(f"Failed to discover {source_name}: {e}")
            sitemap.errors.append(str(e))

        return sitemap

    def discover_all(
        self,
        limit: int = 100,
        source_filter: Optional[str] = None
    ) -> Dict[str, SourceSitemap]:
        """
        Discover sitemaps for all target sources.

        Args:
            limit: Maximum URLs per source
            source_filter: Optional source ID to filter to single source

        Returns:
            Dict mapping source_id to SourceSitemap
        """
        results = {}

        sources = self.TARGET_SOURCES
        if source_filter:
            sources = [s for s in sources if s["id"] == source_filter]
            if not sources:
                logger.error(f"Source '{source_filter}' not found")
                return results

        for source in sources:
            sitemap = self.discover_source(
                source_id=source["id"],
                source_name=source["name"],
                base_url=source["url"],
                limit=limit
            )
            results[source["id"]] = sitemap

        return results


# =============================================================================
# Output Formatters
# =============================================================================

def format_as_markdown(sitemaps: Dict[str, SourceSitemap]) -> str:
    """Format discovery results as Markdown."""
    lines = [
        "# Source Directory - Discovered Sitemaps",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "This document catalogs all discovered URLs from target data sources.",
        "Scout agents can reference this to find the best URLs for their tasks.",
        "",
        "## Summary",
        "",
        "| Source | Total URLs | Documents | Meetings | Permits | APIs |",
        "|:-------|:-----------|:----------|:---------|:--------|:-----|",
    ]

    for source_id, sitemap in sitemaps.items():
        summary = sitemap.get_summary()
        lines.append(
            f"| {sitemap.source_name} | {sitemap.total_urls} | "
            f"{summary.get('document', 0)} | {summary.get('meeting', 0)} | "
            f"{summary.get('permit', 0)} | {summary.get('api', 0)} |"
        )

    lines.extend(["", "---", ""])

    # Detailed sections per source
    for source_id, sitemap in sitemaps.items():
        lines.extend([
            f"## {sitemap.source_name}",
            "",
            f"**Base URL:** {sitemap.base_url}",
            f"**Source ID:** `{sitemap.source_id}`",
            f"**Discovered:** {sitemap.discovered_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Total URLs:** {sitemap.total_urls}",
            "",
        ])

        if sitemap.errors:
            lines.append("### ⚠️ Errors")
            for error in sitemap.errors:
                lines.append(f"- {error}")
            lines.append("")

        # Group by category
        for category in ["document", "meeting", "permit", "api", "board", "archive", "search", "gis", "media", "other"]:
            urls = sitemap.urls_by_category.get(category, [])
            if not urls:
                continue

            # Sort by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            urls.sort(key=lambda x: priority_order.get(x.priority, 2))

            lines.extend([
                f"### {category.title()} URLs ({len(urls)})",
                "",
            ])

            # Group critical/high priority separately
            critical_high = [u for u in urls if u.priority in ["critical", "high"]]
            other = [u for u in urls if u.priority not in ["critical", "high"]]

            if critical_high:
                lines.append("**🔴 High Priority:**")
                for url_cat in critical_high[:20]:  # Limit display
                    subcategory = f" ({url_cat.subcategory})" if url_cat.subcategory else ""
                    file_type = f" [{url_cat.file_type}]" if url_cat.file_type else ""
                    lines.append(f"- {url_cat.url}{subcategory}{file_type}")
                if len(critical_high) > 20:
                    lines.append(f"- *...and {len(critical_high) - 20} more*")
                lines.append("")

            if other:
                lines.append("**Other:**")
                for url_cat in other[:10]:  # Limit display
                    lines.append(f"- {url_cat.url}")
                if len(other) > 10:
                    lines.append(f"- *...and {len(other) - 10} more*")
                lines.append("")

        lines.extend(["---", ""])

    # Scout Agent Reference Section
    lines.extend([
        "## Scout Agent Quick Reference",
        "",
        "### Finding Meeting Agendas",
        "1. Check `meeting` category for `meeting_list` URLs",
        "2. Navigate to specific meeting via `meeting_detail` URLs",
        "3. Download PDFs from `document` category",
        "",
        "### Finding Permit Information",
        "1. Check `permit` category for `permit_list` URLs",
        "2. Get details from `permit_detail` URLs",
        "3. Look for attached documents in `document` category",
        "",
        "### Accessing Historical Data",
        "1. Check `archive` category for past records",
        "2. Use `search` URLs with date filters",
        "",
    ])

    return "\n".join(lines)


def format_as_yaml(sitemaps: Dict[str, SourceSitemap]) -> str:
    """Format discovery results as YAML."""
    output = {
        "generated_at": datetime.now().isoformat(),
        "sources": {}
    }

    for source_id, sitemap in sitemaps.items():
        source_data = {
            "name": sitemap.source_name,
            "base_url": sitemap.base_url,
            "discovered_at": sitemap.discovered_at.isoformat(),
            "total_urls": sitemap.total_urls,
            "errors": sitemap.errors,
            "categories": {}
        }

        for category, urls in sitemap.urls_by_category.items():
            source_data["categories"][category] = [
                {
                    "url": u.url,
                    "subcategory": u.subcategory,
                    "priority": u.priority,
                    "file_type": u.file_type,
                    "keywords": u.keywords
                }
                for u in urls
            ]

        output["sources"][source_id] = source_data

    return yaml.dump(output, default_flow_style=False, sort_keys=False)


def format_as_json(sitemaps: Dict[str, SourceSitemap]) -> str:
    """Format discovery results as JSON."""
    output = {
        "generated_at": datetime.now().isoformat(),
        "sources": {}
    }

    for source_id, sitemap in sitemaps.items():
        source_data = {
            "name": sitemap.source_name,
            "base_url": sitemap.base_url,
            "discovered_at": sitemap.discovered_at.isoformat(),
            "total_urls": sitemap.total_urls,
            "errors": sitemap.errors,
            "categories": {}
        }

        for category, urls in sitemap.urls_by_category.items():
            source_data["categories"][category] = [
                {
                    "url": u.url,
                    "subcategory": u.subcategory,
                    "priority": u.priority,
                    "file_type": u.file_type,
                    "keywords": u.keywords
                }
                for u in urls
            ]

        output["sources"][source_id] = source_data

    return json.dumps(output, indent=2)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Discover sitemaps for target data sources using Firecrawl"
    )
    parser.add_argument(
        "--source", "-s",
        help="Specific source ID to discover (default: all sources)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Maximum URLs to discover per source (default: 100)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["markdown", "yaml", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--file", "-f",
        help="Output file path (default: stdout or docs/SOURCE_DIRECTORY.md)"
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List available source IDs and exit"
    )

    args = parser.parse_args()

    # List sources mode
    if args.list_sources:
        print("Available sources:")
        for source in SitemapDiscoverer.TARGET_SOURCES:
            print(f"  {source['id']:30} - {source['name']}")
        return

    # Check for API key
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("ERROR: FIRECRAWL_API_KEY environment variable not set")
        sys.exit(1)

    # Run discovery
    print(f"Starting sitemap discovery (limit: {args.limit} URLs per source)...")
    discoverer = SitemapDiscoverer()
    sitemaps = discoverer.discover_all(
        limit=args.limit,
        source_filter=args.source
    )

    if not sitemaps:
        print("No sitemaps discovered")
        sys.exit(1)

    # Format output
    if args.output == "markdown":
        content = format_as_markdown(sitemaps)
        default_file = PROJECT_ROOT / "docs" / "SOURCE_DIRECTORY.md"
    elif args.output == "yaml":
        content = format_as_yaml(sitemaps)
        default_file = PROJECT_ROOT / "config" / "sitemaps" / "discovered.yaml"
    else:
        content = format_as_json(sitemaps)
        default_file = PROJECT_ROOT / "config" / "sitemaps" / "discovered.json"

    # Write output
    output_file = Path(args.file) if args.file else default_file

    if args.file or args.output == "markdown":
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
        print(f"\nOutput written to: {output_file}")
    else:
        print(content)

    # Print summary
    print("\n" + "=" * 60)
    print("DISCOVERY SUMMARY")
    print("=" * 60)
    for source_id, sitemap in sitemaps.items():
        summary = sitemap.get_summary()
        print(f"\n{sitemap.source_name}:")
        print(f"  Total URLs: {sitemap.total_urls}")
        for cat, count in sorted(summary.items()):
            print(f"  - {cat}: {count}")
        if sitemap.errors:
            print(f"  ⚠️ Errors: {len(sitemap.errors)}")


if __name__ == "__main__":
    main()
