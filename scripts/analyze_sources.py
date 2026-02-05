#!/usr/bin/env python3
"""
Source Playbook Generator for Open Sousveillance Studio
========================================================

Performs deep content sampling on target data sources to generate
actionable "playbooks" that Scout agents can use to navigate each site.

Unlike sitemap discovery (which just lists URLs), this script:
1. Actually visits and renders pages (including JS)
2. Extracts page structure (elements, links, buttons)
3. Identifies navigation patterns (list → detail → document)
4. Discovers actual document/PDF URLs
5. Documents the action sequences needed to access content

Output: YAML playbooks in config/source_playbooks/

Usage:
    python scripts/analyze_sources.py [--source SOURCE_ID] [--verbose]

Examples:
    # Analyze all sources
    python scripts/analyze_sources.py

    # Analyze specific source with verbose output
    python scripts/analyze_sources.py --source alachua-civicclerk --verbose
"""

import os
import sys
import re
import json
import yaml
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse, urljoin
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.tools.firecrawl_client import FirecrawlClient, ScrapeResult
from src.logging_config import get_logger

logger = get_logger("scripts.analyze_sources")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class PageElement:
    """An element discovered on a page."""
    selector: str
    tag: str
    count: int
    description: str
    sample_text: Optional[str] = None
    sample_href: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class NavigationStep:
    """A step in a navigation sequence."""
    action: str  # click, scroll, wait, input
    selector: Optional[str] = None
    value: Optional[str] = None
    wait_ms: int = 500
    description: str = ""


@dataclass
class DocumentPattern:
    """A pattern for document URLs."""
    doc_type: str  # agenda, agenda_packet, minutes, permit, notice
    url_pattern: str
    sample_urls: List[str] = field(default_factory=list)
    requires_auth: bool = False
    file_type: str = "pdf"


@dataclass
class APIEndpoint:
    """A discovered API endpoint."""
    endpoint: str
    method: str = "GET"
    params: List[str] = field(default_factory=list)
    returns: str = ""
    sample_response: Optional[str] = None


@dataclass
class SourcePlaybook:
    """Complete playbook for a data source."""
    source_id: str
    source_name: str
    base_url: str
    analyzed_at: datetime

    # Page characteristics
    page_type: str = "static"  # static, react_spa, angular, dynamic
    requires_javascript: bool = False
    load_time_ms: int = 2000

    # Structure
    elements: List[PageElement] = field(default_factory=list)

    # Navigation
    navigation_patterns: Dict[str, List[NavigationStep]] = field(default_factory=dict)

    # Documents
    document_patterns: List[DocumentPattern] = field(default_factory=list)

    # APIs
    api_endpoints: List[APIEndpoint] = field(default_factory=list)

    # Links discovered
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    document_links: List[str] = field(default_factory=list)

    # Scout instructions (generated)
    scout_instructions: str = ""

    # Errors/warnings
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "base_url": self.base_url,
            "analyzed_at": self.analyzed_at.isoformat(),
            "page_structure": {
                "type": self.page_type,
                "requires_javascript": self.requires_javascript,
                "load_time_ms": self.load_time_ms,
                "elements_found": [
                    {
                        "selector": e.selector,
                        "tag": e.tag,
                        "count": e.count,
                        "description": e.description,
                        "sample_text": e.sample_text,
                        "sample_href": e.sample_href,
                    }
                    for e in self.elements
                ]
            },
            "navigation": {
                name: [
                    {
                        "action": step.action,
                        "selector": step.selector,
                        "value": step.value,
                        "wait_ms": step.wait_ms,
                        "description": step.description,
                    }
                    for step in steps
                ]
                for name, steps in self.navigation_patterns.items()
            },
            "documents": {
                "patterns": [
                    {
                        "type": p.doc_type,
                        "url_pattern": p.url_pattern,
                        "file_type": p.file_type,
                        "requires_auth": p.requires_auth,
                        "sample_urls": p.sample_urls[:5],  # Limit samples
                    }
                    for p in self.document_patterns
                ],
                "discovered_links": self.document_links[:20],  # Limit
            },
            "api_endpoints": [
                {
                    "endpoint": api.endpoint,
                    "method": api.method,
                    "params": api.params,
                    "returns": api.returns,
                }
                for api in self.api_endpoints
            ],
            "links": {
                "internal_count": len(self.internal_links),
                "external_count": len(self.external_links),
                "document_count": len(self.document_links),
                "sample_internal": self.internal_links[:10],
                "sample_external": self.external_links[:5],
            },
            "scout_instructions": self.scout_instructions,
            "warnings": self.warnings,
        }


# =============================================================================
# Content Analyzer
# =============================================================================

class ContentAnalyzer:
    """Analyzes page content to extract structure and patterns."""

    # Patterns for identifying page types
    SPA_INDICATORS = [
        r"react", r"angular", r"vue", r"__NEXT_DATA__", r"__NUXT__",
        r"data-reactroot", r"ng-app", r"v-app"
    ]

    # Patterns for document links
    DOC_PATTERNS = {
        "pdf": r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
        "doc": r'href=["\']([^"\']*\.(doc|docx)[^"\']*)["\']',
        "xls": r'href=["\']([^"\']*\.(xls|xlsx)[^"\']*)["\']',
    }

    # Patterns for API endpoints
    API_PATTERNS = [
        r'/api/[a-zA-Z0-9/_-]+',
        r'/rest/[a-zA-Z0-9/_-]+',
        r'/v\d+/[a-zA-Z0-9/_-]+',
        r'\.json\b',
    ]

    # Common element patterns to look for
    ELEMENT_PATTERNS = {
        "meeting_cards": [
            r'class=["\'][^"\']*event[^"\']*["\']',
            r'class=["\'][^"\']*meeting[^"\']*["\']',
            r'class=["\'][^"\']*agenda[^"\']*["\']',
        ],
        "download_buttons": [
            r'download',
            r'aria-label=["\'][^"\']*download[^"\']*["\']',
            r'class=["\'][^"\']*btn[^"\']*download[^"\']*["\']',
        ],
        "tables": [
            r'<table[^>]*>',
        ],
        "forms": [
            r'<form[^>]*>',
        ],
        "pagination": [
            r'class=["\'][^"\']*pagination[^"\']*["\']',
            r'class=["\'][^"\']*pager[^"\']*["\']',
        ],
    }

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.parsed_base = urlparse(base_url)

    def analyze_content(self, markdown: str, html: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze page content from markdown and optional HTML.

        Returns dict with:
        - page_type: static, react_spa, etc.
        - links: categorized links
        - elements: discovered page elements
        - patterns: document/API patterns found
        """
        results = {
            "page_type": "static",
            "requires_javascript": False,
            "links": {
                "internal": [],
                "external": [],
                "documents": [],
                "anchors": [],
            },
            "elements": [],
            "document_patterns": [],
            "api_patterns": [],
        }

        content = markdown + (html or "")

        # Detect SPA
        for indicator in self.SPA_INDICATORS:
            if re.search(indicator, content, re.IGNORECASE):
                results["page_type"] = "react_spa" if "react" in indicator else "spa"
                results["requires_javascript"] = True
                break

        # Extract links from markdown
        # Markdown link format: [text](url)
        md_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', markdown)
        for text, url in md_links:
            self._categorize_link(url, results["links"])

        # Extract href links from any HTML content
        href_links = re.findall(r'href=["\']([^"\']+)["\']', content)
        for url in href_links:
            self._categorize_link(url, results["links"])

        # Find document patterns
        for doc_type, pattern in self.DOC_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                if url not in results["links"]["documents"]:
                    results["links"]["documents"].append(url)

        # Find API patterns
        for pattern in self.API_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if match not in results["api_patterns"]:
                    results["api_patterns"].append(match)

        # Analyze element patterns
        for element_type, patterns in self.ELEMENT_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, content, re.IGNORECASE))
            if count > 0:
                results["elements"].append({
                    "type": element_type,
                    "count": count,
                })

        return results

    def _categorize_link(self, url: str, links: Dict[str, List[str]]):
        """Categorize a link as internal, external, document, or anchor."""
        if not url or url.startswith("#"):
            if url:
                links["anchors"].append(url)
            return

        # Check for document
        if any(ext in url.lower() for ext in ['.pdf', '.doc', '.xls', '.csv']):
            if url not in links["documents"]:
                links["documents"].append(url)
            return

        # Check internal vs external
        try:
            parsed = urlparse(url)
            if not parsed.netloc or parsed.netloc == self.parsed_base.netloc:
                full_url = urljoin(self.base_url, url)
                if full_url not in links["internal"]:
                    links["internal"].append(full_url)
            else:
                if url not in links["external"]:
                    links["external"].append(url)
        except Exception:
            pass


# =============================================================================
# Source-Specific Analyzers
# =============================================================================

class CivicClerkAnalyzer:
    """Specialized analyzer for CivicClerk portals."""

    @staticmethod
    def analyze(markdown: str, base_url: str) -> Dict[str, Any]:
        """Extract CivicClerk-specific patterns."""
        results = {
            "meetings": [],
            "boards": [],
            "download_options": [],
            "navigation": {},
            "event_urls": [],
            "url_patterns": [],
        }

        # Find event/files URLs - these are the key discovery!
        # Pattern: /event/{id}/files
        event_urls = re.findall(r'https?://[^/]+/event/(\d+)/files', markdown)
        results["event_ids"] = list(set(event_urls))
        results["events_found"] = len(results["event_ids"])

        # Extract the URL pattern
        if results["event_ids"]:
            parsed = urlparse(base_url)
            results["url_patterns"].append({
                "type": "event_files",
                "pattern": f"{parsed.scheme}://{parsed.netloc}/event/{{event_id}}/files",
                "description": "Direct URL to event files page",
                "sample_ids": results["event_ids"][:5],
            })

        # Find meeting patterns in markdown
        # CivicClerk shows: Day\nMON DD,\nYYYY\nTime\nTitle
        date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*\n\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2}),?\s*\n?\s*(\d{4})'
        meetings = re.findall(date_pattern, markdown, re.IGNORECASE)
        results["meetings_found"] = len(meetings)

        # Find board/committee names
        board_patterns = [
            r'City Commission',
            r'Planning and Zoning',
            r'Community Redevelopment',
            r'CRA\b',
            r'Board of',
        ]
        for pattern in board_patterns:
            if re.search(pattern, markdown, re.IGNORECASE):
                results["boards"].append(pattern)

        # Check for agenda posted indicators
        if "Agenda Posted" in markdown:
            results["has_agendas"] = True

        # Navigation pattern for CivicClerk
        results["navigation"] = {
            "list_to_detail": [
                {"action": "click", "selector": ".event-card, .meeting-item", "description": "Click meeting card"},
            ],
            "detail_to_document": [
                {"action": "click", "selector": "[aria-label='Download Files from this Event']", "wait_ms": 500},
                {"action": "click", "selector": "text='Agenda Packet (PDF)'", "wait_ms": 1000},
            ],
            "direct_access": [
                {"action": "navigate", "url_pattern": "/event/{event_id}/files", "description": "Direct URL to event files"},
            ],
        }

        # Mark as SPA since we know CivicClerk is React
        results["is_spa"] = True
        results["page_type"] = "react_spa"

        return results


class SRWMDAnalyzer:
    """Specialized analyzer for SRWMD permit pages."""

    @staticmethod
    def analyze(markdown: str, base_url: str) -> Dict[str, Any]:
        """Extract SRWMD-specific patterns."""
        results = {
            "permits": [],
            "table_structure": None,
            "navigation": {},
        }

        # Find permit table pattern
        # Format: | RULE | RECEIVED/ISSUED | APPLICATION/PERMIT | PROJECT NAME | COUNTY |
        table_pattern = r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|'
        rows = re.findall(table_pattern, markdown)

        if rows:
            results["table_found"] = True
            results["row_count"] = len(rows) - 1  # Exclude header

            # Check for permit links
            permit_links = re.findall(r'\[([^\]]+)\]\((https?://permitting[^)]+)\)', markdown)
            results["permit_links"] = len(permit_links)
            if permit_links:
                results["sample_permit_url"] = permit_links[0][1]

        # Check which page type
        if "/1616" in base_url or "Application" in markdown:
            results["page_type"] = "applications"
        elif "/1617" in base_url or "Issuance" in markdown:
            results["page_type"] = "issuances"

        # Navigation for SRWMD
        results["navigation"] = {
            "list_to_detail": [
                {"action": "click", "selector": "a[href*='permitting.sjrwmd.com']", "description": "Click permit number link"},
            ],
            "detail_to_document": [
                {"action": "scroll", "direction": "down", "description": "Scroll to documents section"},
                {"action": "click", "selector": "a[href*='.pdf']", "description": "Click document link"},
            ],
        }

        return results


class FloridaNoticesAnalyzer:
    """Specialized analyzer for Florida Public Notices."""

    @staticmethod
    def analyze(markdown: str, base_url: str) -> Dict[str, Any]:
        """Extract Florida Notices-specific patterns."""
        results = {
            "notices": [],
            "filters": [],
            "navigation": {},
        }

        # Find notice count
        count_match = re.search(r'Showing \d+-\d+ of (\d+) results', markdown)
        if count_match:
            results["total_notices"] = int(count_match.group(1))

        # Find newspaper names
        newspapers = re.findall(r'([\w\s]+ County (?:Today|News|Times|Tribune))', markdown)
        results["newspapers"] = list(set(newspapers))

        # Find PDF links (CloudFront pattern)
        pdf_links = re.findall(r'https://[^"\']*cloudfront\.net/[^"\']*\.pdf', markdown)
        results["pdf_links"] = len(pdf_links)
        if pdf_links:
            results["sample_pdf_url"] = pdf_links[0]

        # Navigation for Florida Notices
        results["navigation"] = {
            "apply_filters": [
                {"action": "click", "selector": "select[name='newspaper']", "wait_ms": 300},
                {"action": "click", "selector": "option:contains('Alachua')", "wait_ms": 300},
                {"action": "click", "selector": "button:contains('Update')", "wait_ms": 2000},
            ],
            "list_to_detail": [
                {"action": "click", "selector": ".notice-card", "description": "Click notice card to open modal"},
            ],
            "detail_to_document": [
                {"action": "click", "selector": "a:contains('View original file')", "description": "Opens PDF"},
            ],
        }

        return results


# =============================================================================
# Main Playbook Generator
# =============================================================================

class PlaybookGenerator:
    """Generates source playbooks by analyzing target sites."""

    # Target sources to analyze
    TARGET_SOURCES = [
        {
            "id": "alachua-civicclerk",
            "name": "City of Alachua - CivicClerk Portal",
            "url": "https://alachuafl.portal.civicclerk.com/",
            "analyzer": "civicclerk",
            "scrape_config": {
                "wait_ms": 4000,
                "scroll": True,
            }
        },
        {
            "id": "florida-public-notices",
            "name": "Florida Public Notices",
            "url": "https://floridapublicnotices.com/",
            "analyzer": "florida_notices",
            "scrape_config": {
                "wait_ms": 3000,
            }
        },
        {
            "id": "srwmd-applications",
            "name": "SRWMD - Permit Applications",
            "url": "https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications",
            "analyzer": "srwmd",
            "scrape_config": {
                "wait_ms": 2000,
            }
        },
        {
            "id": "srwmd-issuances",
            "name": "SRWMD - Permit Issuances",
            "url": "https://www.mysuwanneeriver.com/1617/Notice-of-Permit-Issuance",
            "analyzer": "srwmd",
            "scrape_config": {
                "wait_ms": 2000,
            }
        },
        {
            "id": "srwmd-epermitting",
            "name": "SRWMD - E-Permitting Portal",
            "url": "https://permitting.sjrwmd.com/srep/#/ep",
            "analyzer": "srwmd",
            "scrape_config": {
                "wait_ms": 4000,
            }
        },
    ]

    ANALYZERS = {
        "civicclerk": CivicClerkAnalyzer,
        "srwmd": SRWMDAnalyzer,
        "florida_notices": FloridaNoticesAnalyzer,
    }

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize generator."""
        self.client = FirecrawlClient(validate_urls=False)
        self.output_dir = output_dir or (PROJECT_ROOT / "config" / "source_playbooks")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_source(self, source: Dict[str, Any], verbose: bool = False) -> SourcePlaybook:
        """
        Analyze a single source and generate its playbook.
        """
        source_id = source["id"]
        source_name = source["name"]
        base_url = source["url"]

        logger.info(f"Analyzing {source_name}...", url=base_url)

        playbook = SourcePlaybook(
            source_id=source_id,
            source_name=source_name,
            base_url=base_url,
            analyzed_at=datetime.now(),
        )

        try:
            # Scrape the page with Firecrawl
            scrape_config = source.get("scrape_config", {})
            result = self.client.scrape_page(
                base_url,
                wait_ms=scrape_config.get("wait_ms", 3000),
                scroll=scrape_config.get("scroll", False),
                formats=["markdown", "links", "html"]
            )

            if not result.success:
                playbook.warnings.append(f"Scrape failed: {result.error}")
                return playbook

            # General content analysis
            analyzer = ContentAnalyzer(base_url)
            general_results = analyzer.analyze_content(
                result.markdown,
                getattr(result, 'html', None)
            )

            # Update playbook with general results
            playbook.page_type = general_results["page_type"]
            playbook.requires_javascript = general_results["requires_javascript"]
            playbook.internal_links = general_results["links"]["internal"]
            playbook.external_links = general_results["links"]["external"]
            playbook.document_links = general_results["links"]["documents"]

            # Add discovered elements
            for elem in general_results["elements"]:
                playbook.elements.append(PageElement(
                    selector=f".{elem['type']}",
                    tag="div",
                    count=elem["count"],
                    description=f"Found {elem['count']} {elem['type']} elements"
                ))

            # Add API patterns
            for api_pattern in general_results["api_patterns"]:
                playbook.api_endpoints.append(APIEndpoint(
                    endpoint=api_pattern,
                    method="GET",
                    returns="Unknown"
                ))

            # Source-specific analysis
            analyzer_name = source.get("analyzer")
            if analyzer_name and analyzer_name in self.ANALYZERS:
                specific_analyzer = self.ANALYZERS[analyzer_name]
                specific_results = specific_analyzer.analyze(result.markdown, base_url)

                # Merge navigation patterns
                if "navigation" in specific_results:
                    for nav_name, steps in specific_results["navigation"].items():
                        playbook.navigation_patterns[nav_name] = [
                            NavigationStep(
                                action=s.get("action", "click"),
                                selector=s.get("selector"),
                                value=s.get("value"),
                                wait_ms=s.get("wait_ms", 500),
                                description=s.get("description", "")
                            )
                            for s in steps
                        ]

                # Add source-specific info to playbook
                if analyzer_name == "civicclerk":
                    playbook.load_time_ms = 4000
                    playbook.page_type = specific_results.get("page_type", "react_spa")
                    playbook.requires_javascript = True

                    if specific_results.get("events_found"):
                        playbook.elements.append(PageElement(
                            selector=".event-card",
                            tag="div",
                            count=specific_results["events_found"],
                            description=f"Meeting event cards ({specific_results['events_found']} events found)"
                        ))

                    # Add discovered URL patterns
                    for url_pattern in specific_results.get("url_patterns", []):
                        playbook.document_patterns.append(DocumentPattern(
                            doc_type=url_pattern["type"],
                            url_pattern=url_pattern["pattern"],
                            sample_urls=[
                                f"https://alachuafl.portal.civicclerk.com/event/{eid}/files"
                                for eid in url_pattern.get("sample_ids", [])[:3]
                            ]
                        ))

                    # Add discovered event IDs as internal links
                    for event_id in specific_results.get("event_ids", []):
                        event_url = f"https://alachuafl.portal.civicclerk.com/event/{event_id}/files"
                        if event_url not in playbook.internal_links:
                            playbook.internal_links.append(event_url)

                elif analyzer_name == "srwmd":
                    if specific_results.get("table_found"):
                        playbook.elements.append(PageElement(
                            selector="table",
                            tag="table",
                            count=1,
                            description=f"Permit table with {specific_results.get('row_count', 0)} rows"
                        ))
                    if specific_results.get("sample_permit_url"):
                        playbook.document_patterns.append(DocumentPattern(
                            doc_type="permit_detail",
                            url_pattern="https://permitting.sjrwmd.com/srep/#/ep/permit/{permit_number}",
                            sample_urls=[specific_results["sample_permit_url"]]
                        ))

                elif analyzer_name == "florida_notices":
                    if specific_results.get("sample_pdf_url"):
                        playbook.document_patterns.append(DocumentPattern(
                            doc_type="notice_pdf",
                            url_pattern="https://*.cloudfront.net/*/*.pdf",
                            sample_urls=[specific_results["sample_pdf_url"]]
                        ))

            # Generate scout instructions
            playbook.scout_instructions = self._generate_instructions(playbook, source)

            if verbose:
                logger.info(f"Analysis complete for {source_name}",
                           links=len(playbook.internal_links),
                           documents=len(playbook.document_links),
                           elements=len(playbook.elements))

        except Exception as e:
            logger.error(f"Error analyzing {source_name}: {e}")
            playbook.warnings.append(str(e))

        return playbook

    def _generate_instructions(self, playbook: SourcePlaybook, source: Dict) -> str:
        """Generate human-readable scout instructions."""
        lines = [
            f"# Scout Instructions for {playbook.source_name}",
            "",
            f"**Source ID:** `{playbook.source_id}`",
            f"**Base URL:** {playbook.base_url}",
            f"**Page Type:** {playbook.page_type}",
            f"**Requires JS:** {'Yes' if playbook.requires_javascript else 'No'}",
            "",
        ]

        # Navigation instructions
        if playbook.navigation_patterns:
            lines.append("## Navigation")
            for nav_name, steps in playbook.navigation_patterns.items():
                lines.append(f"\n### {nav_name.replace('_', ' ').title()}")
                for i, step in enumerate(steps, 1):
                    lines.append(f"{i}. **{step.action}** `{step.selector}`")
                    if step.description:
                        lines.append(f"   - {step.description}")
                    if step.wait_ms > 500:
                        lines.append(f"   - Wait {step.wait_ms}ms")

        # Document access
        if playbook.document_patterns or playbook.document_links:
            lines.append("\n## Accessing Documents")
            for pattern in playbook.document_patterns:
                lines.append(f"\n**{pattern.doc_type}:**")
                lines.append(f"- Pattern: `{pattern.url_pattern}`")
                if pattern.sample_urls:
                    lines.append(f"- Example: `{pattern.sample_urls[0]}`")

            if playbook.document_links:
                lines.append(f"\n**Direct document links found:** {len(playbook.document_links)}")

        # API endpoints
        if playbook.api_endpoints:
            lines.append("\n## API Endpoints")
            for api in playbook.api_endpoints[:5]:
                lines.append(f"- `{api.method} {api.endpoint}`")

        return "\n".join(lines)

    def generate_all(
        self,
        source_filter: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, SourcePlaybook]:
        """Generate playbooks for all sources."""
        results = {}

        sources = self.TARGET_SOURCES
        if source_filter:
            sources = [s for s in sources if s["id"] == source_filter]
            if not sources:
                logger.error(f"Source '{source_filter}' not found")
                return results

        for i, source in enumerate(sources):
            # Rate limiting - wait between requests
            if i > 0:
                logger.info("Waiting 15s for rate limit...")
                time.sleep(15)

            playbook = self.analyze_source(source, verbose=verbose)
            results[source["id"]] = playbook

            # Save individual playbook
            self._save_playbook(playbook)

        # Generate index file
        self._save_index(results)

        return results

    def _save_playbook(self, playbook: SourcePlaybook):
        """Save a playbook to YAML file."""
        filepath = self.output_dir / f"{playbook.source_id}.yaml"

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(
                playbook.to_dict(),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

        logger.info(f"Saved playbook: {filepath}")

    def _save_index(self, playbooks: Dict[str, SourcePlaybook]):
        """Save index file summarizing all playbooks."""
        index = {
            "generated_at": datetime.now().isoformat(),
            "playbook_count": len(playbooks),
            "sources": {}
        }

        for source_id, playbook in playbooks.items():
            index["sources"][source_id] = {
                "name": playbook.source_name,
                "url": playbook.base_url,
                "page_type": playbook.page_type,
                "requires_javascript": playbook.requires_javascript,
                "internal_links": len(playbook.internal_links),
                "document_links": len(playbook.document_links),
                "has_warnings": len(playbook.warnings) > 0,
            }

        filepath = self.output_dir / "_index.yaml"
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(index, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved index: {filepath}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate source playbooks by analyzing target sites"
    )
    parser.add_argument(
        "--source", "-s",
        help="Specific source ID to analyze (default: all sources)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List available source IDs and exit"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for playbooks"
    )

    args = parser.parse_args()

    # List sources mode
    if args.list_sources:
        print("Available sources:")
        for source in PlaybookGenerator.TARGET_SOURCES:
            print(f"  {source['id']:30} - {source['name']}")
        return

    # Check for API key
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("ERROR: FIRECRAWL_API_KEY environment variable not set")
        sys.exit(1)

    # Run generator
    output_dir = Path(args.output_dir) if args.output_dir else None
    generator = PlaybookGenerator(output_dir=output_dir)

    print("Starting source analysis...")
    print("(This will take a few minutes due to rate limiting)")
    print()

    playbooks = generator.generate_all(
        source_filter=args.source,
        verbose=args.verbose
    )

    if not playbooks:
        print("No playbooks generated")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 60)
    print("PLAYBOOK GENERATION SUMMARY")
    print("=" * 60)

    for source_id, playbook in playbooks.items():
        print(f"\n{playbook.source_name}:")
        print(f"  Page Type: {playbook.page_type}")
        print(f"  Internal Links: {len(playbook.internal_links)}")
        print(f"  Document Links: {len(playbook.document_links)}")
        print(f"  Elements Found: {len(playbook.elements)}")
        print(f"  Navigation Patterns: {len(playbook.navigation_patterns)}")
        if playbook.warnings:
            print(f"  ⚠️ Warnings: {len(playbook.warnings)}")

    print(f"\nPlaybooks saved to: {generator.output_dir}")


if __name__ == "__main__":
    main()
