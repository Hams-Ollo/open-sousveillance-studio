"""
CivicClerk Portal Scraper for Open Sousveillance Studio.

Specialized scraper for CivicClerk meeting portals (React SPA).
Handles:
- Meeting list extraction with scroll loading
- PDF agenda/packet downloads
- Board/category filtering

CivicClerk Portal Structure:
- Base URL: https://{site_id}.portal.civicclerk.com/
- Events load dynamically via React
- Download dropdown offers: Agenda (PDF), Agenda Packet (PDF), Plain Text versions
"""

import re
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from src.logging_config import get_logger
from src.tools.firecrawl_client import FirecrawlClient, ScrapeResult

logger = get_logger("tools.civicclerk")


@dataclass
class CivicClerkMeeting:
    """Represents a meeting extracted from CivicClerk portal."""

    # Core identifiers
    meeting_id: str  # Generated from title + date hash
    title: str
    date: datetime
    time: Optional[str] = None

    # Location and board
    location: Optional[str] = None
    board: Optional[str] = None
    board_tag: Optional[str] = None  # e.g., "City Commission", "Planning and Zoning Board"

    # Document availability
    agenda_posted_date: Optional[datetime] = None
    has_agenda: bool = False
    has_agenda_packet: bool = False
    has_minutes: bool = False

    # URLs for downloads
    agenda_pdf_url: Optional[str] = None
    agenda_packet_pdf_url: Optional[str] = None
    agenda_text_url: Optional[str] = None
    minutes_url: Optional[str] = None

    # Processing status
    scraped_at: datetime = field(default_factory=datetime.now)
    content_hash: Optional[str] = None

    def generate_id(self) -> str:
        """Generate a unique ID from title and date."""
        key = f"{self.title}-{self.date.isoformat()}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


@dataclass
class CivicClerkScrapeResult:
    """Result from scraping a CivicClerk portal."""

    site_id: str
    url: str
    meetings: List[CivicClerkMeeting] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    raw_markdown: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)

    @property
    def meeting_count(self) -> int:
        return len(self.meetings)

    @property
    def past_meetings(self) -> List[CivicClerkMeeting]:
        now = datetime.now()
        return [m for m in self.meetings if m.date < now]

    @property
    def upcoming_meetings(self) -> List[CivicClerkMeeting]:
        now = datetime.now()
        return [m for m in self.meetings if m.date >= now]


class CivicClerkScraper:
    """
    Scraper for CivicClerk meeting portals.

    Usage:
        scraper = CivicClerkScraper("alachuafl")
        result = scraper.scrape_meetings()

        for meeting in result.meetings:
            if meeting.has_agenda_packet:
                pdf_content = scraper.download_agenda_packet(meeting)
    """

    def __init__(
        self,
        site_id: str,
        firecrawl_client: Optional[FirecrawlClient] = None,
        download_dir: Optional[Path] = None
    ):
        """
        Initialize CivicClerk scraper.

        Args:
            site_id: CivicClerk site ID (e.g., "alachuafl")
            firecrawl_client: Optional pre-configured Firecrawl client
            download_dir: Directory to save downloaded PDFs
        """
        self.site_id = site_id
        self.base_url = f"https://{site_id}.portal.civicclerk.com/"
        self.client = firecrawl_client or FirecrawlClient()
        self.download_dir = download_dir or Path("data/downloads/civicclerk")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        logger.info("CivicClerkScraper initialized", site_id=site_id, base_url=self.base_url)

    def scrape_meetings(
        self,
        scroll_count: int = 3,
        category_id: Optional[int] = None
    ) -> CivicClerkScrapeResult:
        """
        Scrape meeting list from the portal.

        Uses Firecrawl Actions API to:
        1. Wait for React app to load
        2. Scroll up to load past events
        3. Scroll down to load future events
        4. Extract meeting list from rendered markdown

        Args:
            scroll_count: Number of times to scroll to load more events
            category_id: Optional category filter (board type)

        Returns:
            CivicClerkScrapeResult with extracted meetings
        """
        url = self.base_url
        if category_id:
            url = f"{url}?category_id={category_id}"

        logger.info("Scraping CivicClerk meetings", url=url, scroll_count=scroll_count)

        try:
            # Use Firecrawl with scroll actions to load more events
            result = self.client.scrape_civicclerk_with_scroll(
                url,
                scroll_count=scroll_count
            )

            if not result.success:
                return CivicClerkScrapeResult(
                    site_id=self.site_id,
                    url=url,
                    success=False,
                    error=result.error
                )

            # Parse meetings from markdown
            meetings = self._parse_meetings_from_markdown(result.markdown)

            logger.info(
                "Scraped CivicClerk meetings",
                meeting_count=len(meetings),
                past=len([m for m in meetings if m.date < datetime.now()]),
                upcoming=len([m for m in meetings if m.date >= datetime.now()])
            )

            return CivicClerkScrapeResult(
                site_id=self.site_id,
                url=url,
                meetings=meetings,
                success=True,
                raw_markdown=result.markdown
            )

        except Exception as e:
            logger.error("Failed to scrape CivicClerk", error=str(e))
            return CivicClerkScrapeResult(
                site_id=self.site_id,
                url=url,
                success=False,
                error=str(e)
            )

    def _parse_meetings_from_markdown(self, markdown: str) -> List[CivicClerkMeeting]:
        """
        Parse meeting information from scraped markdown.

        CivicClerk markdown typically contains:
        - Meeting titles
        - Dates and times
        - Location info
        - Board/category tags
        - "Agenda Posted on" dates
        """
        meetings = []

        # Split by common meeting separators
        # Look for date patterns like "Tuesday\nJAN 13,\n2026"
        date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*\n\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2}),?\s*\n?\s*(\d{4})'

        # Find all date matches
        date_matches = list(re.finditer(date_pattern, markdown, re.IGNORECASE))

        for i, match in enumerate(date_matches):
            try:
                # Extract date components
                day_name = match.group(1)
                month_str = match.group(2).upper()
                day = int(match.group(3))
                year = int(match.group(4))

                # Convert month
                month_map = {
                    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
                    'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
                    'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                }
                month = month_map.get(month_str, 1)

                meeting_date = datetime(year, month, day)

                # Get text after this date until next date or end
                start_pos = match.end()
                end_pos = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(markdown)
                meeting_text = markdown[start_pos:end_pos]

                # Extract meeting title (usually first line after date/time)
                title_match = re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:EST|EDT)?\s*\n?\s*(.+?)(?:\n|$)', meeting_text, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                else:
                    # Try to find any capitalized title
                    title_match = re.search(r'^([A-Z][A-Za-z\s]+(?:Meeting|Board|Commission|Committee|Event))', meeting_text, re.MULTILINE)
                    title = title_match.group(1).strip() if title_match else "Unknown Meeting"

                # Extract time
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:EST|EDT)?)', meeting_text, re.IGNORECASE)
                time_str = time_match.group(1).strip() if time_match else None

                # Extract board tag (in brackets or specific patterns)
                board_patterns = [
                    r'\[([^\]]+)\]',  # [City Commission]
                    r'(City Commission|Planning and Zoning Board|Community Redevelopment Agency|Education Task Force)',
                ]
                board = None
                for pattern in board_patterns:
                    board_match = re.search(pattern, meeting_text, re.IGNORECASE)
                    if board_match:
                        board = board_match.group(1).strip()
                        break

                # Check for agenda posted date
                agenda_posted_match = re.search(r'Agenda Posted on:?\s*(\w+\s+\d{1,2},?\s+\d{4})', meeting_text, re.IGNORECASE)
                agenda_posted = None
                has_agenda = False
                if agenda_posted_match:
                    has_agenda = True
                    try:
                        agenda_posted = datetime.strptime(
                            agenda_posted_match.group(1).replace(',', ''),
                            '%B %d %Y'
                        )
                    except ValueError:
                        pass

                # Create meeting object
                meeting = CivicClerkMeeting(
                    meeting_id="",  # Will be generated
                    title=title,
                    date=meeting_date,
                    time=time_str,
                    board=board,
                    board_tag=board,
                    agenda_posted_date=agenda_posted,
                    has_agenda=has_agenda,
                    has_agenda_packet=has_agenda,  # If agenda exists, packet likely does too
                )
                meeting.meeting_id = meeting.generate_id()

                meetings.append(meeting)

            except Exception as e:
                logger.warning("Failed to parse meeting", error=str(e))
                continue

        return meetings

    def download_agenda_packet(
        self,
        meeting: CivicClerkMeeting,
        prefer_packet: bool = True
    ) -> Optional[ScrapeResult]:
        """
        Download agenda packet PDF for a meeting.

        Uses Firecrawl Actions API to:
        1. Navigate to meeting page
        2. Click the download button
        3. Select "Agenda Packet (PDF)" from dropdown
        4. Extract PDF content

        Args:
            meeting: Meeting to download packet for
            prefer_packet: If True, prefer full packet over simple agenda

        Returns:
            ScrapeResult with PDF content as markdown, or None if unavailable
        """
        if not meeting.has_agenda_packet and not meeting.has_agenda:
            logger.warning("Meeting has no agenda available", meeting_id=meeting.meeting_id)
            return None

        logger.info(
            "Downloading agenda packet via Firecrawl actions",
            meeting_id=meeting.meeting_id,
            title=meeting.title,
            date=meeting.date.isoformat()
        )

        # If we have a direct PDF URL, use it directly
        pdf_url = meeting.agenda_packet_pdf_url or meeting.agenda_pdf_url
        if pdf_url:
            logger.info("Using direct PDF URL", url=pdf_url)
            return self.client.scrape_pdf(pdf_url)

        # Otherwise, use Firecrawl actions to click through the UI
        # Build actions to click download button and select agenda packet
        # Note: Selectors may need adjustment based on actual CivicClerk HTML

        # The download button appears to be an icon button on each meeting card
        # We need to target the specific meeting's download button
        download_selector = f"[aria-label='Download Files from this Event']"

        # Option selectors in the dropdown
        if prefer_packet:
            option_selector = "text=Agenda Packet (PDF)"
        else:
            option_selector = "text=Agenda (PDF)"

        actions = [
            {"type": "wait", "milliseconds": 3000},
            # Click the download button for this meeting
            {"type": "click", "selector": download_selector},
            {"type": "wait", "milliseconds": 500},
            # Click the agenda packet option
            {"type": "click", "selector": option_selector},
            {"type": "wait", "milliseconds": 2000},
        ]

        try:
            result = self.client.scrape_with_actions(
                self.base_url,
                actions=actions,
                formats=["markdown", "links"]
            )

            if result.success:
                # Check if we got PDF content or links to PDFs
                if result.metadata and 'links' in str(result.metadata):
                    # Look for PDF links in the result
                    logger.info("Captured page state after download click")
                return result
            else:
                logger.warning(
                    "Failed to download via actions",
                    error=result.error,
                    meeting_id=meeting.meeting_id
                )
                return None

        except Exception as e:
            logger.error(
                "Exception during agenda packet download",
                error=str(e),
                meeting_id=meeting.meeting_id
            )
            return None

    def extract_pdf_links_from_page(self, markdown: str) -> List[str]:
        """
        Extract PDF URLs from scraped markdown content.

        Args:
            markdown: Scraped markdown content

        Returns:
            List of PDF URLs found in the content
        """
        import re
        pdf_pattern = r'https?://[^\s\)]+\.pdf'
        return re.findall(pdf_pattern, markdown, re.IGNORECASE)

    def get_board_categories(self) -> dict:
        """
        Return known board categories for this portal.

        Returns:
            Dict mapping board names to category IDs (if known)
        """
        # These would need to be discovered by inspecting the portal
        # or from the category dropdown
        return {
            "City Commission": None,  # Category ID unknown
            "Planning and Zoning Board": None,
            "Community Redevelopment Agency Board": None,
            "Education Task Force": None,
        }


    # =========================================================================
    # HYBRID PIPELINE METHODS
    # =========================================================================

    def discover_meetings(
        self,
        days_back: int = 30,
        days_forward: int = 60,
        scroll_count: int = 2
    ) -> List[CivicClerkMeeting]:
        """
        Phase 1: DISCOVERY - Light scrape to get meeting list only.

        Scrapes the meeting list and filters by date range.
        Does NOT download PDFs - that's Phase 2.

        Args:
            days_back: How many days in the past to include
            days_forward: How many days in the future to include
            scroll_count: Number of scroll actions (less = faster)

        Returns:
            List of CivicClerkMeeting objects within date range
        """
        from datetime import timedelta

        logger.info(
            "Discovery phase: scraping meeting list",
            days_back=days_back,
            days_forward=days_forward
        )

        # Calculate date boundaries
        now = datetime.now()
        cutoff_past = now - timedelta(days=days_back)
        cutoff_future = now + timedelta(days=days_forward)

        # Scrape meeting list (minimal scrolling for speed)
        result = self.scrape_meetings(scroll_count=scroll_count)

        if not result.success:
            logger.error("Discovery phase failed", error=result.error)
            return []

        # Filter by date range
        filtered_meetings = [
            m for m in result.meetings
            if cutoff_past <= m.date <= cutoff_future
        ]

        logger.info(
            "Discovery phase complete",
            total_scraped=len(result.meetings),
            in_date_range=len(filtered_meetings),
            date_range=f"{cutoff_past.date()} to {cutoff_future.date()}"
        )

        return filtered_meetings

    def sync_meetings_to_database(
        self,
        meetings: List[CivicClerkMeeting],
        db: "Database"
    ) -> dict:
        """
        Sync discovered meetings to database, identifying new/updated ones.

        Args:
            meetings: List of discovered meetings
            db: Database instance

        Returns:
            Dict with 'new', 'updated', 'unchanged' lists of meeting IDs
        """
        source_id = f"civicclerk-{self.site_id}"

        result = {
            'new': [],
            'updated': [],
            'unchanged': []
        }

        for meeting in meetings:
            existing = db.get_meeting(meeting.meeting_id, source_id)

            meeting_data = {
                'meeting_id': meeting.meeting_id,
                'source_id': source_id,
                'title': meeting.title,
                'meeting_date': meeting.date,
                'board': meeting.board,
                'agenda_posted_date': meeting.agenda_posted_date,
                'has_agenda': meeting.has_agenda,
                'has_agenda_packet': meeting.has_agenda_packet,
                'metadata': {
                    'time': meeting.time,
                    'location': meeting.location,
                    'board_tag': meeting.board_tag
                }
            }

            if not existing:
                result['new'].append(meeting.meeting_id)
                db.upsert_meeting(meeting_data)
            elif existing.get('agenda_posted_date') != (meeting.agenda_posted_date.isoformat() if meeting.agenda_posted_date else None):
                # Agenda was posted or updated
                result['updated'].append(meeting.meeting_id)
                db.upsert_meeting(meeting_data)
            else:
                result['unchanged'].append(meeting.meeting_id)

        logger.info(
            "Synced meetings to database",
            new=len(result['new']),
            updated=len(result['updated']),
            unchanged=len(result['unchanged'])
        )

        return result

    def download_meeting_pdf(
        self,
        meeting: CivicClerkMeeting,
        prefer_packet: bool = True
    ) -> Optional[str]:
        """
        Phase 2: DETAIL - Download and extract PDF content for a meeting.

        Args:
            meeting: Meeting to download PDF for
            prefer_packet: If True, prefer Agenda Packet over simple Agenda

        Returns:
            Extracted text content from PDF, or None if unavailable
        """
        if not meeting.has_agenda and not meeting.has_agenda_packet:
            logger.debug("Meeting has no agenda", meeting_id=meeting.meeting_id)
            return None

        logger.info(
            "Downloading PDF for meeting",
            meeting_id=meeting.meeting_id,
            title=meeting.title,
            date=meeting.date.isoformat()
        )

        # Try to get PDF content via Firecrawl
        result = self.download_agenda_packet(meeting, prefer_packet=prefer_packet)

        if result and result.success and result.markdown:
            logger.info(
                "PDF content extracted",
                meeting_id=meeting.meeting_id,
                content_length=len(result.markdown)
            )
            return result.markdown

        logger.warning(
            "Failed to extract PDF content",
            meeting_id=meeting.meeting_id,
            error=result.error if result else "No result"
        )
        return None

    def run_hybrid_pipeline(
        self,
        db: "Database",
        days_back: int = 30,
        days_forward: int = 60,
        download_pdfs: bool = True,
        max_pdf_downloads: int = 10
    ) -> dict:
        """
        Run the full hybrid scraping pipeline.

        Phase 1: DISCOVERY - Scrape meeting list, filter by date, sync to DB
        Phase 2: DETAIL - Download PDFs for new/updated meetings with agendas

        Args:
            db: Database instance
            days_back: Days in the past to include
            days_forward: Days in the future to include
            download_pdfs: Whether to download PDFs (Phase 2)
            max_pdf_downloads: Limit PDF downloads per run (cost control)

        Returns:
            Dict with pipeline results
        """
        source_id = f"civicclerk-{self.site_id}"

        logger.info(
            "Starting hybrid pipeline",
            source_id=source_id,
            days_back=days_back,
            days_forward=days_forward
        )

        results = {
            'source_id': source_id,
            'phase1_discovery': {},
            'phase2_detail': {},
            'meetings_ready_for_analysis': []
        }

        # Phase 1: Discovery
        meetings = self.discover_meetings(
            days_back=days_back,
            days_forward=days_forward
        )

        if not meetings:
            logger.warning("No meetings discovered")
            results['phase1_discovery'] = {'error': 'No meetings found'}
            return results

        # Sync to database
        sync_result = self.sync_meetings_to_database(meetings, db)
        results['phase1_discovery'] = {
            'total_discovered': len(meetings),
            'new': len(sync_result['new']),
            'updated': len(sync_result['updated']),
            'unchanged': len(sync_result['unchanged'])
        }

        # Phase 2: Detail (PDF downloads)
        if download_pdfs:
            # Get meetings that need PDF download (new or updated, with agenda)
            meetings_to_download = [
                m for m in meetings
                if m.meeting_id in sync_result['new'] + sync_result['updated']
                and (m.has_agenda or m.has_agenda_packet)
            ][:max_pdf_downloads]

            pdf_results = {
                'attempted': len(meetings_to_download),
                'success': 0,
                'failed': 0
            }

            for meeting in meetings_to_download:
                content = self.download_meeting_pdf(meeting)

                if content:
                    # Update database with PDF content
                    content_hash = db.compute_content_hash(content)
                    db.upsert_meeting({
                        'meeting_id': meeting.meeting_id,
                        'source_id': source_id,
                        'title': meeting.title,
                        'meeting_date': meeting.date,
                        'pdf_content': content,
                        'content_hash': content_hash
                    })

                    pdf_results['success'] += 1
                    results['meetings_ready_for_analysis'].append(meeting.meeting_id)
                else:
                    pdf_results['failed'] += 1

            results['phase2_detail'] = pdf_results

        logger.info(
            "Hybrid pipeline complete",
            discovery=results['phase1_discovery'],
            detail=results['phase2_detail'],
            ready_for_analysis=len(results['meetings_ready_for_analysis'])
        )

        return results


def scrape_alachua_civicclerk() -> CivicClerkScrapeResult:
    """
    Convenience function to scrape City of Alachua CivicClerk portal.

    Returns:
        CivicClerkScrapeResult with all meetings
    """
    scraper = CivicClerkScraper("alachuafl")
    return scraper.scrape_meetings()


if __name__ == "__main__":
    # Test the scraper
    result = scrape_alachua_civicclerk()

    print(f"\n{'='*60}")
    print(f"CivicClerk Scrape Results: {result.site_id}")
    print(f"{'='*60}")
    print(f"Success: {result.success}")
    print(f"Total Meetings: {result.meeting_count}")
    print(f"Past Meetings: {len(result.past_meetings)}")
    print(f"Upcoming Meetings: {len(result.upcoming_meetings)}")

    if result.meetings:
        print(f"\n--- Sample Meetings ---")
        for meeting in result.meetings[:5]:
            print(f"\n  {meeting.date.strftime('%Y-%m-%d')} | {meeting.title}")
            print(f"    Board: {meeting.board or 'Unknown'}")
            print(f"    Has Agenda: {meeting.has_agenda}")
