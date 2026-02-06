"""
Florida Public Notices Scraper for Open Sousveillance Studio.

Scrapes legal notices from https://floridapublicnotices.com/

Workflow:
1. Apply filters (newspaper, county) via Firecrawl Actions
2. Scrape notice cards from filtered results
3. Click each card to get detail modal with PDF link
4. Extract and scrape PDF content

Key observations:
- PDFs hosted on CloudFront (direct URLs available)
- "Next Notice" button allows iteration through results
- Categories include: Government Publications, Notices of Hearings, etc.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from src.logging_config import get_logger
from src.tools.firecrawl_client import FirecrawlClient, ScrapeResult
from src.tools.resource_cache import get_resource_cache, ResourceCache
from src.intelligence.health import get_health_service, HealthService

logger = get_logger("tools.florida_notices")


@dataclass
class PublicNotice:
    """Represents a public notice from Florida Public Notices."""

    notice_id: str
    title: str
    publication_date: datetime

    # Source info
    newspaper: str  # e.g., "Alachua County Today"
    county: str  # e.g., "Alachua"

    # Content
    keywords: Optional[str] = None
    subcategory: Optional[str] = None  # e.g., "Government Publications - Notices of Hearings"
    description: Optional[str] = None

    # PDF
    pdf_url: Optional[str] = None
    has_pdf: bool = False

    # Processing
    scraped_at: datetime = field(default_factory=datetime.now)


@dataclass
class FloridaNoticesScrapeResult:
    """Result from scraping Florida Public Notices."""

    newspaper: str
    county: str
    notices: List[PublicNotice] = field(default_factory=list)
    total_results: int = 0
    success: bool = True
    error: Optional[str] = None
    raw_markdown: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)

    @property
    def notice_count(self) -> int:
        return len(self.notices)

    @property
    def notices_with_pdf(self) -> List[PublicNotice]:
        return [n for n in self.notices if n.has_pdf]


class FloridaNoticesScraper:
    """
    Scraper for Florida Public Notices website.

    Usage:
        scraper = FloridaNoticesScraper()
        result = scraper.scrape_notices(
            newspaper="Alachua County Today",
            county="Alachua"
        )

        for notice in result.notices:
            if notice.has_pdf:
                pdf_content = scraper.scrape_pdf(notice.pdf_url)
    """

    BASE_URL = "https://floridapublicnotices.com/"

    def __init__(
        self,
        firecrawl_client: Optional[FirecrawlClient] = None,
        resource_cache: Optional[ResourceCache] = None
    ):
        """
        Initialize Florida Public Notices scraper.

        Args:
            firecrawl_client: Optional pre-configured Firecrawl client
            resource_cache: Optional ResourceCache for discovered resources
        """
        self.client = firecrawl_client or FirecrawlClient()

        # Load discovered resources cache
        self.resource_cache = resource_cache or get_resource_cache()
        self.source_id = "florida-public-notices"

        # Health tracking
        self.health_service = get_health_service()
        self.scraper_id = "florida-notices"

        # Load known notice IDs from cache
        self._known_notice_ids = set(self.resource_cache.get_ids(self.source_id, "notice_ids"))
        self._known_pdf_urls = set(self.resource_cache.get_ids(self.source_id, "pdf_urls"))

        logger.info(
            "FloridaNoticesScraper initialized",
            cached_notices=len(self._known_notice_ids),
            cached_pdfs=len(self._known_pdf_urls)
        )

    def scrape_notices(
        self,
        newspaper: str = "Alachua County Today",
        county: str = "Alachua",
        max_pages: int = 5
    ) -> FloridaNoticesScrapeResult:
        """
        Scrape public notices with filters applied.

        Uses Firecrawl Actions to:
        1. Select newspaper from dropdown
        2. Select county from multi-select
        3. Click Update button
        4. Scrape resulting notice cards

        Args:
            newspaper: Newspaper name to filter by
            county: County name to filter by
            max_pages: Maximum pages to scrape (12 results per page)

        Returns:
            FloridaNoticesScrapeResult with extracted notices
        """
        import time
        start_time = time.perf_counter()

        logger.info(
            "Scraping Florida Public Notices",
            newspaper=newspaper,
            county=county
        )

        # Build actions to apply filters
        actions = [
            # Wait for page to load
            {"type": "wait", "milliseconds": 2000},

            # Click newspaper dropdown and select option
            {"type": "click", "selector": "select[name='newspaper'], .newspaper-select, #newspaper"},
            {"type": "wait", "milliseconds": 300},

            # Try to select the newspaper option
            # Note: Selector may need adjustment based on actual HTML
            {"type": "click", "selector": f"option:contains('{newspaper}')"},
            {"type": "wait", "milliseconds": 300},

            # Click county multi-select
            {"type": "click", "selector": f"option:contains('{county}')"},
            {"type": "wait", "milliseconds": 300},

            # Click Update button
            {"type": "click", "selector": "button:contains('Update'), .update-btn, #update-button"},
            {"type": "wait", "milliseconds": 2000},

            # Scroll to load more results if needed
            {"type": "scroll", "direction": "down"},
            {"type": "wait", "milliseconds": 1000},
        ]

        try:
            result = self.client.scrape_with_actions(
                self.BASE_URL,
                actions=actions,
                formats=["markdown", "links"]
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            if not result.success:
                self.health_service.record_scrape(
                    scraper_id=self.scraper_id,
                    success=False,
                    duration_ms=duration_ms,
                    error_type="ScrapeError",
                    error_message=result.error,
                )
                return FloridaNoticesScrapeResult(
                    newspaper=newspaper,
                    county=county,
                    success=False,
                    error=result.error
                )

            # Parse notices from markdown
            notices = self._parse_notices_from_markdown(
                result.markdown,
                newspaper=newspaper,
                county=county
            )

            # Update resource cache with discovered IDs
            self.update_resource_cache(notices, result.markdown)

            # Extract total results count
            total_match = re.search(r'Showing \d+-\d+ of (\d+) results', result.markdown)
            total_results = int(total_match.group(1)) if total_match else len(notices)

            # Record successful scrape
            self.health_service.record_scrape(
                scraper_id=self.scraper_id,
                success=True,
                items_found=len(notices),
                duration_ms=duration_ms,
            )

            logger.info(
                "Scraped Florida Public Notices",
                notice_count=len(notices),
                total_results=total_results
            )

            return FloridaNoticesScrapeResult(
                newspaper=newspaper,
                county=county,
                notices=notices,
                total_results=total_results,
                success=True,
                raw_markdown=result.markdown
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.health_service.record_scrape(
                scraper_id=self.scraper_id,
                success=False,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e)[:500],
            )
            logger.error("Failed to scrape Florida Public Notices", error=str(e))
            return FloridaNoticesScrapeResult(
                newspaper=newspaper,
                county=county,
                success=False,
                error=str(e)
            )

    def _parse_notices_from_markdown(
        self,
        markdown: str,
        newspaper: str,
        county: str
    ) -> List[PublicNotice]:
        """
        Parse notice information from scraped markdown.

        Notice cards typically contain:
        - Newspaper name
        - Location
        - Date
        - Keywords/description
        - Category tag
        """
        notices = []

        # Look for date patterns in the format "January 29, 2026"
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'

        # Split by newspaper name occurrences (each card starts with newspaper)
        cards = re.split(rf'({re.escape(newspaper)})', markdown)

        notice_id = 0
        for i in range(1, len(cards), 2):
            if i + 1 >= len(cards):
                break

            card_text = cards[i] + cards[i + 1] if i + 1 < len(cards) else cards[i]

            try:
                # Extract date
                date_match = re.search(date_pattern, card_text)
                if date_match:
                    month_str = date_match.group(1)
                    day = int(date_match.group(2))
                    year = int(date_match.group(3))

                    month_map = {
                        'January': 1, 'February': 2, 'March': 3, 'April': 4,
                        'May': 5, 'June': 6, 'July': 7, 'August': 8,
                        'September': 9, 'October': 10, 'November': 11, 'December': 12
                    }
                    month = month_map.get(month_str, 1)
                    pub_date = datetime(year, month, day)
                else:
                    pub_date = datetime.now()

                # Extract keywords section
                keywords_match = re.search(r'Keywords?:?\s*(.+?)(?:\n|$)', card_text, re.IGNORECASE)
                keywords = keywords_match.group(1).strip() if keywords_match else None

                # Extract category (in brackets or specific patterns)
                category_match = re.search(
                    r'(Government Publications[^,\n]*|Miscellaneous[^,\n]*|Notices of Hearings[^,\n]*)',
                    card_text,
                    re.IGNORECASE
                )
                subcategory = category_match.group(1).strip() if category_match else None

                # Extract description (first substantial text block)
                desc_match = re.search(r'(?:Keywords?:?\s*.+?\n)?(.{50,300})', card_text, re.DOTALL)
                description = desc_match.group(1).strip() if desc_match else None

                # Create notice
                notice_id += 1
                notice = PublicNotice(
                    notice_id=f"fpn-{notice_id:04d}",
                    title=f"{newspaper} - {pub_date.strftime('%Y-%m-%d')}",
                    publication_date=pub_date,
                    newspaper=newspaper,
                    county=county,
                    keywords=keywords,
                    subcategory=subcategory,
                    description=description,
                    has_pdf=True  # Most notices have PDFs
                )

                notices.append(notice)

            except Exception as e:
                logger.warning("Failed to parse notice card", error=str(e))
                continue

        return notices

    def scrape_notice_detail(self, notice_index: int = 0) -> Optional[ScrapeResult]:
        """
        Click a notice card to open detail modal and extract PDF URL.

        Args:
            notice_index: Index of the notice card to click (0-based)

        Returns:
            ScrapeResult with modal content including PDF URL
        """
        # Click the nth notice card
        card_selector = f".notice-card:nth-child({notice_index + 1}), .card:nth-child({notice_index + 1})"

        actions = [
            {"type": "wait", "milliseconds": 2000},
            {"type": "click", "selector": card_selector},
            {"type": "wait", "milliseconds": 1500},
        ]

        try:
            result = self.client.scrape_with_actions(
                self.BASE_URL,
                actions=actions,
                formats=["markdown", "links"]
            )

            if result.success:
                # Extract PDF URL from the result
                pdf_urls = self.extract_pdf_urls(result.markdown)
                if pdf_urls:
                    logger.info("Found PDF URL in notice detail", url=pdf_urls[0])

            return result

        except Exception as e:
            logger.error("Failed to scrape notice detail", error=str(e))
            return None

    def extract_pdf_urls(self, content: str) -> List[str]:
        """
        Extract PDF URLs from content.

        Florida Public Notices uses CloudFront for PDF hosting.
        Pattern: https://d3pf...cloudfront.net/XX/XXXXXXXX.pdf

        Args:
            content: Markdown or HTML content

        Returns:
            List of PDF URLs found
        """
        # CloudFront PDF pattern
        cloudfront_pattern = r'https?://[a-z0-9]+\.cloudfront\.net/\d+/\d+\.pdf'
        cloudfront_urls = re.findall(cloudfront_pattern, content, re.IGNORECASE)

        # Generic PDF pattern as fallback
        generic_pattern = r'https?://[^\s\)\"\']+\.pdf'
        generic_urls = re.findall(generic_pattern, content, re.IGNORECASE)

        # Combine and deduplicate
        all_urls = list(set(cloudfront_urls + generic_urls))
        return all_urls

    def scrape_pdf(self, pdf_url: str) -> Optional[ScrapeResult]:
        """
        Scrape PDF content from URL.

        Args:
            pdf_url: Direct URL to PDF file

        Returns:
            ScrapeResult with PDF content as markdown
        """
        logger.info("Scraping PDF", url=pdf_url)
        return self.client.scrape_pdf(pdf_url)

    # =========================================================================
    # RESOURCE CACHE METHODS
    # =========================================================================

    def extract_notice_ids_from_notices(self, notices: List[PublicNotice]) -> List[str]:
        """
        Extract notice IDs from parsed notices.

        Args:
            notices: List of PublicNotice objects

        Returns:
            List of notice ID strings
        """
        return [n.notice_id for n in notices if n.notice_id]

    def update_resource_cache(self, notices: List[PublicNotice], markdown: str = None):
        """
        Extract and cache newly discovered notice IDs and PDF URLs.

        Args:
            notices: List of parsed public notices
            markdown: Optional raw markdown for PDF URL extraction
        """
        # Update notice IDs
        new_notice_ids = self.extract_notice_ids_from_notices(notices)
        if new_notice_ids:
            before_count = len(self._known_notice_ids)
            self._known_notice_ids.update(new_notice_ids)
            after_count = len(self._known_notice_ids)

            self.resource_cache.add_ids(self.source_id, "notice_ids", new_notice_ids)

            if after_count > before_count:
                logger.info(
                    "Discovered new notice IDs",
                    new_count=after_count - before_count,
                    total=after_count
                )

        # Update PDF URLs from notices
        new_pdf_urls = [n.pdf_url for n in notices if n.pdf_url]

        # Also extract from markdown if provided
        if markdown:
            new_pdf_urls.extend(self.extract_pdf_urls(markdown))

        if new_pdf_urls:
            before_count = len(self._known_pdf_urls)
            self._known_pdf_urls.update(new_pdf_urls)
            after_count = len(self._known_pdf_urls)

            self.resource_cache.add_ids(self.source_id, "pdf_urls", list(set(new_pdf_urls)))

            if after_count > before_count:
                logger.info(
                    "Discovered new PDF URLs",
                    new_count=after_count - before_count,
                    total=after_count
                )

        self.resource_cache.save()

    def get_known_notice_ids(self) -> List[str]:
        """
        Get known notice IDs from cache.

        Returns:
            List of notice ID strings
        """
        return list(self._known_notice_ids)

    def get_known_pdf_urls(self) -> List[str]:
        """
        Get known PDF URLs from cache.

        Returns:
            List of PDF URL strings
        """
        return list(self._known_pdf_urls)

    def iterate_notices_via_modal(
        self,
        max_notices: int = 20
    ) -> List[PublicNotice]:
        """
        Iterate through notices using the "Next Notice" button in modal.

        This approach:
        1. Opens first notice card
        2. Extracts content and PDF URL
        3. Clicks "Next Notice" to advance
        4. Repeats until max_notices reached

        Args:
            max_notices: Maximum notices to iterate through

        Returns:
            List of PublicNotice objects with PDF URLs
        """
        notices = []

        # First, open the first notice
        actions = [
            {"type": "wait", "milliseconds": 2000},
            {"type": "click", "selector": ".notice-card:first-child, .card:first-child"},
            {"type": "wait", "milliseconds": 1500},
        ]

        try:
            result = self.client.scrape_with_actions(
                self.BASE_URL,
                actions=actions,
                formats=["markdown", "links"]
            )

            if not result.success:
                logger.error("Failed to open first notice")
                return notices

            # Extract first notice
            pdf_urls = self.extract_pdf_urls(result.markdown)
            notice = self._parse_notice_from_modal(result.markdown, pdf_urls)
            if notice:
                notices.append(notice)

            # Iterate using "Next Notice" button
            for i in range(1, max_notices):
                next_actions = [
                    {"type": "click", "selector": "text=Next Notice, .next-notice-btn"},
                    {"type": "wait", "milliseconds": 1500},
                ]

                result = self.client.scrape_with_actions(
                    self.BASE_URL,
                    actions=next_actions,
                    formats=["markdown", "links"]
                )

                if not result.success:
                    logger.warning("Failed to advance to next notice", index=i)
                    break

                pdf_urls = self.extract_pdf_urls(result.markdown)
                notice = self._parse_notice_from_modal(result.markdown, pdf_urls)
                if notice:
                    notices.append(notice)
                else:
                    # Might have reached the end
                    break

            logger.info("Iterated through notices", count=len(notices))
            return notices

        except Exception as e:
            logger.error("Failed to iterate notices", error=str(e))
            return notices

    def _parse_notice_from_modal(
        self,
        markdown: str,
        pdf_urls: List[str]
    ) -> Optional[PublicNotice]:
        """
        Parse notice details from modal content.

        Modal contains:
        - Publication Date
        - Subcategory
        - Keywords
        - View original file link
        """
        try:
            # Extract publication date
            date_match = re.search(r'Publication Date\s*[\n:]+\s*(\d{4}-\d{2}-\d{2})', markdown)
            if date_match:
                pub_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
            else:
                pub_date = datetime.now()

            # Extract subcategory
            subcat_match = re.search(r'Subcategory\s*[\n:]+\s*(.+?)(?:\n|$)', markdown)
            subcategory = subcat_match.group(1).strip() if subcat_match else None

            # Extract keywords
            keywords_match = re.search(r'Keywords?:?\s*(.+?)(?:\n\n|View original)', markdown, re.DOTALL)
            keywords = keywords_match.group(1).strip() if keywords_match else None

            # Extract newspaper from header
            newspaper_match = re.search(r'^([A-Za-z\s]+(?:Today|Times|News|Herald))', markdown)
            newspaper = newspaper_match.group(1).strip() if newspaper_match else "Unknown"

            notice = PublicNotice(
                notice_id=f"fpn-modal-{datetime.now().strftime('%H%M%S')}",
                title=keywords[:100] if keywords else f"Notice {pub_date.strftime('%Y-%m-%d')}",
                publication_date=pub_date,
                newspaper=newspaper,
                county="Alachua",  # Default for our use case
                keywords=keywords,
                subcategory=subcategory,
                pdf_url=pdf_urls[0] if pdf_urls else None,
                has_pdf=len(pdf_urls) > 0
            )

            return notice

        except Exception as e:
            logger.warning("Failed to parse notice from modal", error=str(e))
            return None


    # =========================================================================
    # HYBRID PIPELINE METHODS
    # =========================================================================

    def discover_notices(
        self,
        newspaper: str = "Alachua County Today",
        county: str = "Alachua",
        days_back: int = 35
    ) -> List[PublicNotice]:
        """
        Phase 1: DISCOVERY - Light scrape to get notice list only.

        Args:
            newspaper: Newspaper to filter by
            county: County to filter by
            days_back: How many days of notices to include

        Returns:
            List of PublicNotice objects
        """
        from datetime import timedelta

        logger.info(
            "Discovery phase: scraping notice list",
            newspaper=newspaper,
            county=county,
            days_back=days_back
        )

        result = self.scrape_notices(newspaper=newspaper, county=county)

        if not result.success:
            logger.error("Discovery phase failed", error=result.error)
            return []

        # Filter by date
        cutoff = datetime.now() - timedelta(days=days_back)
        filtered = [n for n in result.notices if n.publication_date >= cutoff]

        logger.info(
            "Discovery phase complete",
            total_scraped=len(result.notices),
            in_date_range=len(filtered)
        )

        return filtered

    def sync_notices_to_database(
        self,
        notices: List[PublicNotice],
        db: "Database"
    ) -> dict:
        """
        Sync discovered notices to database.

        Args:
            notices: List of discovered notices
            db: Database instance

        Returns:
            Dict with 'new', 'updated', 'unchanged' counts
        """
        source_id = "florida-public-notices"

        result = {'new': [], 'updated': [], 'unchanged': []}

        for notice in notices:
            existing = db.get_meeting(notice.notice_id, source_id)

            notice_data = {
                'meeting_id': notice.notice_id,
                'source_id': source_id,
                'title': notice.title[:200] if notice.title else "Notice",
                'meeting_date': notice.publication_date,
                'board': notice.subcategory,
                'has_agenda': notice.has_pdf,
                'agenda_packet_url': notice.pdf_url,
                'metadata': {
                    'newspaper': notice.newspaper,
                    'county': notice.county,
                    'keywords': notice.keywords,
                    'subcategory': notice.subcategory
                }
            }

            if not existing:
                result['new'].append(notice.notice_id)
                db.upsert_meeting(notice_data)
            else:
                result['unchanged'].append(notice.notice_id)

        logger.info(
            "Synced notices to database",
            new=len(result['new']),
            unchanged=len(result['unchanged'])
        )

        return result

    def run_hybrid_pipeline(
        self,
        db: "Database",
        newspaper: str = "Alachua County Today",
        county: str = "Alachua",
        days_back: int = 35,
        download_pdfs: bool = True,
        max_pdf_downloads: int = 10
    ) -> dict:
        """
        Run the full hybrid scraping pipeline for Florida Public Notices.

        Args:
            db: Database instance
            newspaper: Newspaper to filter by
            county: County to filter by
            days_back: Days of notices to include
            download_pdfs: Whether to download PDFs
            max_pdf_downloads: Limit PDF downloads per run

        Returns:
            Dict with pipeline results
        """
        source_id = "florida-public-notices"

        logger.info(
            "Starting hybrid pipeline",
            source_id=source_id,
            newspaper=newspaper,
            county=county
        )

        results = {
            'source_id': source_id,
            'phase1_discovery': {},
            'phase2_detail': {},
            'notices_ready_for_analysis': [],
            'raw_notices': []
        }

        # Phase 1: Discovery
        notices = self.discover_notices(
            newspaper=newspaper,
            county=county,
            days_back=days_back
        )

        if not notices:
            results['phase1_discovery'] = {'error': 'No notices found'}
            return results

        # Sync to database
        sync_result = self.sync_notices_to_database(notices, db)
        results['phase1_discovery'] = {
            'total_discovered': len(notices),
            'new': len(sync_result['new']),
            'unchanged': len(sync_result['unchanged'])
        }
        results['raw_notices'] = notices

        # Phase 2: PDF downloads for new notices
        if download_pdfs:
            notices_to_download = [
                n for n in notices
                if n.notice_id in sync_result['new'] and n.has_pdf
            ][:max_pdf_downloads]

            pdf_results = {'attempted': len(notices_to_download), 'success': 0, 'failed': 0}

            for notice in notices_to_download:
                if notice.pdf_url:
                    pdf_result = self.scrape_pdf(notice.pdf_url)
                    if pdf_result and pdf_result.success:
                        content_hash = db.compute_content_hash(pdf_result.markdown)
                        db.upsert_meeting({
                            'meeting_id': notice.notice_id,
                            'source_id': source_id,
                            'title': notice.title,
                            'meeting_date': notice.publication_date,
                            'pdf_content': pdf_result.markdown,
                            'content_hash': content_hash
                        })
                        pdf_results['success'] += 1
                        results['notices_ready_for_analysis'].append(notice.notice_id)
                    else:
                        pdf_results['failed'] += 1

            results['phase2_detail'] = pdf_results

        logger.info("Hybrid pipeline complete", results=results)
        return results


def scrape_alachua_public_notices() -> FloridaNoticesScrapeResult:
    """
    Convenience function to scrape Alachua County public notices.

    Returns:
        FloridaNoticesScrapeResult with all notices
    """
    scraper = FloridaNoticesScraper()
    return scraper.scrape_notices(
        newspaper="Alachua County Today",
        county="Alachua"
    )


if __name__ == "__main__":
    # Test the scraper
    result = scrape_alachua_public_notices()

    print(f"\n{'='*60}")
    print(f"Florida Public Notices Scrape Results")
    print(f"{'='*60}")
    print(f"Success: {result.success}")
    print(f"Newspaper: {result.newspaper}")
    print(f"County: {result.county}")
    print(f"Total Results: {result.total_results}")
    print(f"Notices Scraped: {result.notice_count}")
    print(f"Notices with PDF: {len(result.notices_with_pdf)}")

    if result.notices:
        print(f"\n--- Sample Notices ---")
        for notice in result.notices[:5]:
            print(f"\n  {notice.publication_date.strftime('%Y-%m-%d')} | {notice.subcategory}")
            print(f"    Keywords: {notice.keywords[:80] if notice.keywords else 'N/A'}...")
            print(f"    Has PDF: {notice.has_pdf}")
