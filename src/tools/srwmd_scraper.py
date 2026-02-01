"""
Suwannee River Water Management District (SRWMD) Permit Scraper.

Scrapes permit applications and issuances from:
- https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications
- https://www.mysuwanneeriver.com/1617/Notice-of-Permit-Issuance

These are CivicPlus-hosted pages with simple HTML tables.

Table Structure:
- Applications: RULE | RECEIVED | APPLICATION | PROJECT NAME | COUNTY
- Issuances: RULE | ISSUED | PERMIT | PROJECT NAME | COUNTY

Permit numbers are hyperlinks to the E-Permitting portal.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from src.logging_config import get_logger
from src.tools.firecrawl_client import FirecrawlClient, ScrapeResult

logger = get_logger("tools.srwmd")


class PermitType(Enum):
    """Types of SRWMD permits."""
    ERP_INDIVIDUAL = "ERP Individual"
    ERP_GENERAL = "ERP General"
    ERP_NOTICED_GENERAL = "ERP Noticed General"
    ERP_STANDARD_GENERAL = "ERP Standard General"
    WUP_INDIVIDUAL = "WUP Individual"
    WOD_INDIVIDUAL = "WOD Individual"
    WOD_GENERAL = "WOD General"
    WOD_NOTICED_GENERAL = "WOD Noticed General"
    EXEMPTION = "Exemption"
    SILVICULTURAL_EXEMPTION = "Silvicultural Exemption"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, value: str) -> "PermitType":
        """Parse permit type from table cell text."""
        value_lower = value.lower().strip()
        for member in cls:
            if member.value.lower() == value_lower:
                return member
        # Partial matching
        if "erp" in value_lower and "individual" in value_lower:
            return cls.ERP_INDIVIDUAL
        if "erp" in value_lower and "general" in value_lower:
            return cls.ERP_GENERAL
        if "wup" in value_lower:
            return cls.WUP_INDIVIDUAL
        if "wod" in value_lower:
            return cls.WOD_INDIVIDUAL
        if "exemption" in value_lower:
            return cls.EXEMPTION
        return cls.UNKNOWN


class NoticeType(Enum):
    """Type of permit notice."""
    APPLICATION = "application"  # New application received
    ISSUANCE = "issuance"  # Permit issued/approved


@dataclass
class PermitDocument:
    """Represents a document attached to a permit application."""

    group_name: str  # e.g., "Application"
    document_name: str  # e.g., "Plans", "Bound Reports"
    date: Optional[datetime] = None
    size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    comments: Optional[str] = None  # e.g., "Civil Plans", "Stormwater Report"


@dataclass
class PermitDetail:
    """Detailed permit information from E-Permitting portal drill-down page."""

    # Project identification
    project_number: str
    project_name: str
    permit_type: str
    county: str

    # Sequence info
    sequence_type: Optional[str] = None  # e.g., "Minor Modification"

    # Dates
    received_date: Optional[datetime] = None
    decision_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

    # Description
    description: Optional[str] = None

    # Status
    status: Optional[str] = None  # e.g., "Pending"
    recommendation: Optional[str] = None
    current_process_stage: Optional[str] = None  # e.g., "Review"

    # Parties
    applicant: Optional[str] = None
    owner: Optional[str] = None
    consultant: Optional[str] = None
    agent: Optional[str] = None
    reviewers: Optional[str] = None

    # Wetlands
    wetlands: Optional[str] = None

    # Documents
    documents: List[PermitDocument] = field(default_factory=list)

    # Raw content for Scout analysis
    raw_content: Optional[str] = None


@dataclass
class PermitNotice:
    """Represents a permit notice from SRWMD."""

    notice_id: str
    notice_type: NoticeType

    # Permit details
    permit_number: str
    rule_type: str
    project_name: str

    # Location
    county: str

    # Permit classification
    permit_type: PermitType = PermitType.UNKNOWN

    # Dates
    date: Optional[datetime] = None  # RECEIVED or ISSUED date

    # Links
    permit_url: Optional[str] = None  # Link to E-Permitting portal

    # Detail page (populated by scrape_permit_detail)
    detail: Optional[PermitDetail] = None

    # Processing
    scraped_at: datetime = field(default_factory=datetime.now)

    def is_alachua(self) -> bool:
        """Check if this permit is in Alachua County."""
        return self.county.lower().strip() == "alachua"


@dataclass
class SRWMDScrapeResult:
    """Result from scraping SRWMD permit notices."""

    notice_type: NoticeType
    url: str
    notices: List[PermitNotice] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    raw_markdown: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)

    @property
    def notice_count(self) -> int:
        return len(self.notices)

    @property
    def alachua_notices(self) -> List[PermitNotice]:
        """Filter notices for Alachua County."""
        return [n for n in self.notices if n.is_alachua()]

    @property
    def alachua_count(self) -> int:
        return len(self.alachua_notices)


class SRWMDScraper:
    """
    Scraper for Suwannee River Water Management District permit notices.

    Usage:
        scraper = SRWMDScraper()

        # Scrape permit applications
        apps = scraper.scrape_applications()

        # Scrape permit issuances
        issued = scraper.scrape_issuances()

        # Filter for Alachua County
        alachua_apps = apps.alachua_notices

        # Scrape both
        all_results = scraper.scrape_all()
    """

    APPLICATIONS_URL = "https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications"
    ISSUANCES_URL = "https://www.mysuwanneeriver.com/1617/Notice-of-Permit-Issuance"
    BASE_URL = "https://www.mysuwanneeriver.com"
    EPERMIT_BASE = "https://permitting.sjrwmd.com/srep/#/ep"

    def __init__(self, firecrawl_client: Optional[FirecrawlClient] = None):
        """
        Initialize SRWMD scraper.

        Args:
            firecrawl_client: Optional pre-configured Firecrawl client
        """
        self.client = firecrawl_client or FirecrawlClient()

    def scrape_applications(self) -> SRWMDScrapeResult:
        """
        Scrape Notice of Receipt of Applications page.

        Returns:
            SRWMDScrapeResult with application notices
        """
        logger.info("Scraping SRWMD permit applications", url=self.APPLICATIONS_URL)

        result = SRWMDScrapeResult(
            notice_type=NoticeType.APPLICATION,
            url=self.APPLICATIONS_URL
        )

        try:
            scrape_result = self.client.scrape(
                self.APPLICATIONS_URL,
                formats=["markdown", "links"]
            )

            if not scrape_result.success:
                result.success = False
                result.error = "Failed to scrape applications page"
                return result

            result.raw_markdown = scrape_result.markdown
            result.notices = self._parse_table(
                scrape_result.markdown,
                NoticeType.APPLICATION
            )

            logger.info(
                "Scraped SRWMD applications",
                total=result.notice_count,
                alachua=result.alachua_count
            )

        except Exception as e:
            logger.error("Failed to scrape SRWMD applications", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def scrape_issuances(self) -> SRWMDScrapeResult:
        """
        Scrape Notice of Permit Issuance page.

        Returns:
            SRWMDScrapeResult with issuance notices
        """
        logger.info("Scraping SRWMD permit issuances", url=self.ISSUANCES_URL)

        result = SRWMDScrapeResult(
            notice_type=NoticeType.ISSUANCE,
            url=self.ISSUANCES_URL
        )

        try:
            scrape_result = self.client.scrape(
                self.ISSUANCES_URL,
                formats=["markdown", "links"]
            )

            if not scrape_result.success:
                result.success = False
                result.error = "Failed to scrape issuances page"
                return result

            result.raw_markdown = scrape_result.markdown
            result.notices = self._parse_table(
                scrape_result.markdown,
                NoticeType.ISSUANCE
            )

            logger.info(
                "Scraped SRWMD issuances",
                total=result.notice_count,
                alachua=result.alachua_count
            )

        except Exception as e:
            logger.error("Failed to scrape SRWMD issuances", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def scrape_all(self) -> dict:
        """
        Scrape both applications and issuances.

        Returns:
            Dict with 'applications' and 'issuances' SRWMDScrapeResult
        """
        return {
            'applications': self.scrape_applications(),
            'issuances': self.scrape_issuances()
        }

    def scrape_permit_detail(self, permit_url: str) -> Optional[PermitDetail]:
        """
        Scrape the E-Permitting portal detail page for a permit.

        This page contains:
        - Full project information (applicant, owner, description, status)
        - List of attached documents (plans, reports, applications)

        Args:
            permit_url: URL to the E-Permitting detail page

        Returns:
            PermitDetail object with project info and documents, or None on failure
        """
        logger.info("Scraping permit detail page", url=permit_url)

        try:
            scrape_result = self.client.scrape(
                permit_url,
                formats=["markdown", "links"]
            )

            if not scrape_result.success:
                logger.error("Failed to scrape permit detail", url=permit_url)
                return None

            return self._parse_permit_detail(scrape_result.markdown, permit_url)

        except Exception as e:
            logger.error("Error scraping permit detail", url=permit_url, error=str(e))
            return None

    def _parse_permit_detail(self, markdown: str, url: str) -> Optional[PermitDetail]:
        """
        Parse permit detail from E-Permitting portal markdown.

        Args:
            markdown: Raw markdown content from detail page
            url: Source URL for reference

        Returns:
            PermitDetail object
        """
        try:
            # Helper to extract field value
            def extract_field(pattern: str, text: str) -> Optional[str]:
                match = re.search(pattern, text, re.IGNORECASE)
                return match.group(1).strip() if match else None

            # Extract project info fields
            project_number = extract_field(r'Project Number[:\s]+([^\n|]+)', markdown)
            project_name = extract_field(r'Project Name[:\s]+([^\n|]+)', markdown)
            permit_type = extract_field(r'Permit Type[:\s]+([^\n|]+)', markdown)
            county = extract_field(r'County[:\s]+([^\n|]+)', markdown)
            sequence_type = extract_field(r'Sequence Type[:\s]+([^\n|]+)', markdown)
            description = extract_field(r'Description[:\s]+([^\n|]+)', markdown)
            status = extract_field(r'Status[:\s]+([^\n|]+)', markdown)
            applicant = extract_field(r'Applicant[:\s]+([^\n|]+)', markdown)
            owner = extract_field(r'Owner[:\s]+([^\n|]+)', markdown)
            consultant = extract_field(r'Consultant[:\s]+([^\n|]+)', markdown)
            agent = extract_field(r'Agent[:\s]+([^\n|]+)', markdown)
            wetlands = extract_field(r'Wetlands[:\s]+([^\n|]+)', markdown)
            reviewers = extract_field(r'Reviewer\(s\)[:\s]+([^\n]+)', markdown)
            current_stage = extract_field(r'Current Process Stage[:\s]+([^\n|]+)', markdown)

            # Parse dates
            received_str = extract_field(r'Received[:\s]+(\d{2}/\d{2}/\d{4})', markdown)
            received_date = datetime.strptime(received_str, "%m/%d/%Y") if received_str else None

            # Parse documents table
            # Format: | Group Name | Document Name | Date | Size | Link | Comments |
            documents = []
            doc_pattern = r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*(\d{2}/\d{2}/\d{4})?\s*\|\s*(\d+)?\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^|]*)\s*\|'

            for match in re.finditer(doc_pattern, markdown):
                group_name = match.group(1).strip()
                doc_name = match.group(2).strip()
                date_str = match.group(3)
                size_str = match.group(4)
                link_text = match.group(5).strip()
                link_url = match.group(6).strip()
                comments = match.group(7).strip() if match.group(7) else None

                # Skip header rows
                if group_name.lower() == "group name" or "---" in group_name:
                    continue

                doc = PermitDocument(
                    group_name=group_name,
                    document_name=doc_name,
                    date=datetime.strptime(date_str, "%m/%d/%Y") if date_str else None,
                    size_bytes=int(size_str) if size_str else None,
                    download_url=link_url,
                    comments=comments
                )
                documents.append(doc)

            detail = PermitDetail(
                project_number=project_number or "Unknown",
                project_name=project_name or "Unknown",
                permit_type=permit_type or "Unknown",
                county=county or "Unknown",
                sequence_type=sequence_type,
                received_date=received_date,
                description=description,
                status=status,
                applicant=applicant,
                owner=owner,
                consultant=consultant,
                agent=agent,
                wetlands=wetlands,
                reviewers=reviewers,
                current_process_stage=current_stage,
                documents=documents,
                raw_content=markdown
            )

            logger.info(
                "Parsed permit detail",
                project_number=project_number,
                documents_found=len(documents)
            )

            return detail

        except Exception as e:
            logger.error("Failed to parse permit detail", error=str(e))
            return None

    def enrich_notice_with_detail(self, notice: PermitNotice) -> PermitNotice:
        """
        Fetch and attach detail page info to a permit notice.

        Args:
            notice: PermitNotice with permit_url

        Returns:
            PermitNotice with detail field populated
        """
        if not notice.permit_url:
            logger.warning("No permit URL for notice", notice_id=notice.notice_id)
            return notice

        detail = self.scrape_permit_detail(notice.permit_url)
        if detail:
            notice.detail = detail

        return notice

    def _parse_table(self, markdown: str, notice_type: NoticeType) -> List[PermitNotice]:
        """
        Parse permit notices from markdown table.

        Table formats:
        - Applications: RULE | RECEIVED | APPLICATION | PROJECT NAME | COUNTY
        - Issuances: RULE | ISSUED | PERMIT | PROJECT NAME | COUNTY

        Args:
            markdown: Raw markdown content
            notice_type: Type of notice (application or issuance)

        Returns:
            List of PermitNotice objects
        """
        notices = []

        # Find table rows in markdown
        # Markdown tables look like: | col1 | col2 | col3 |
        table_pattern = r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|'

        matches = re.findall(table_pattern, markdown)

        for match in matches:
            # Skip header row
            cols = [col.strip() for col in match]

            # Skip if this looks like a header
            if cols[0].upper() == "RULE" or "---" in cols[0]:
                continue

            # Skip empty rows
            if not cols[0] or not cols[3]:
                continue

            try:
                rule_type = cols[0]
                date_str = cols[1]
                permit_number = cols[2]
                project_name = cols[3]
                county = cols[4]

                # Extract permit number from markdown link if present
                # Format: [253436-1](url)
                link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', permit_number)
                if link_match:
                    permit_number = link_match.group(1)
                    permit_url = link_match.group(2)
                else:
                    permit_url = None

                # Parse date
                try:
                    date = datetime.strptime(date_str.strip(), "%m/%d/%Y")
                except ValueError:
                    date = None

                # Create notice ID
                notice_id = f"srwmd-{notice_type.value}-{permit_number}"

                notice = PermitNotice(
                    notice_id=notice_id,
                    notice_type=notice_type,
                    permit_number=permit_number.strip(),
                    rule_type=rule_type.strip(),
                    project_name=project_name.strip(),
                    county=county.strip(),
                    permit_type=PermitType.from_string(rule_type),
                    date=date,
                    permit_url=permit_url
                )

                notices.append(notice)

            except Exception as e:
                logger.warning("Failed to parse table row", row=cols, error=str(e))
                continue

        return notices

    # =========================================================================
    # HYBRID PIPELINE METHODS
    # =========================================================================

    def discover_permits(
        self,
        include_applications: bool = True,
        include_issuances: bool = True,
        county_filter: Optional[str] = None
    ) -> List[PermitNotice]:
        """
        Phase 1: DISCOVERY - Scrape permit notices.

        Args:
            include_applications: Include new applications
            include_issuances: Include issued permits
            county_filter: Optional county to filter (e.g., "Alachua")

        Returns:
            List of PermitNotice objects
        """
        logger.info(
            "Discovery phase: scraping SRWMD permits",
            applications=include_applications,
            issuances=include_issuances,
            county_filter=county_filter
        )

        all_notices = []

        if include_applications:
            apps = self.scrape_applications()
            if apps.success:
                all_notices.extend(apps.notices)

        if include_issuances:
            issued = self.scrape_issuances()
            if issued.success:
                all_notices.extend(issued.notices)

        # Apply county filter
        if county_filter:
            all_notices = [
                n for n in all_notices
                if n.county.lower().strip() == county_filter.lower()
            ]

        logger.info(
            "Discovery phase complete",
            total_found=len(all_notices)
        )

        return all_notices

    def sync_permits_to_database(
        self,
        notices: List[PermitNotice],
        db: "Database"
    ) -> dict:
        """
        Sync discovered permits to database.

        Args:
            notices: List of discovered permit notices
            db: Database instance

        Returns:
            Dict with 'new', 'updated', 'unchanged' counts
        """
        result = {'new': [], 'updated': [], 'unchanged': []}

        for notice in notices:
            source_id = f"srwmd-{notice.notice_type.value}s"
            existing = db.get_meeting(notice.notice_id, source_id)

            notice_data = {
                'meeting_id': notice.notice_id,
                'source_id': source_id,
                'title': f"{notice.rule_type}: {notice.project_name}",
                'meeting_date': notice.date,
                'board': notice.rule_type,
                'has_agenda': bool(notice.permit_url),
                'agenda_packet_url': notice.permit_url,
                'metadata': {
                    'permit_number': notice.permit_number,
                    'rule_type': notice.rule_type,
                    'permit_type': notice.permit_type.value,
                    'county': notice.county,
                    'project_name': notice.project_name,
                    'notice_type': notice.notice_type.value
                }
            }

            if not existing:
                result['new'].append(notice.notice_id)
                db.upsert_meeting(notice_data)
            else:
                result['unchanged'].append(notice.notice_id)

        logger.info(
            "Synced permits to database",
            new=len(result['new']),
            unchanged=len(result['unchanged'])
        )

        return result

    def run_hybrid_pipeline(
        self,
        db: "Database",
        county_filter: str = "Alachua",
        include_applications: bool = True,
        include_issuances: bool = True
    ) -> dict:
        """
        Run the full hybrid scraping pipeline for SRWMD permits.

        Args:
            db: Database instance
            county_filter: County to filter (default: Alachua)
            include_applications: Include new applications
            include_issuances: Include issued permits

        Returns:
            Dict with pipeline results
        """
        logger.info(
            "Starting SRWMD hybrid pipeline",
            county_filter=county_filter
        )

        results = {
            'source_id': 'srwmd-permits',
            'phase1_discovery': {},
            'permits_ready_for_analysis': []
        }

        # Phase 1: Discovery
        notices = self.discover_permits(
            include_applications=include_applications,
            include_issuances=include_issuances,
            county_filter=county_filter
        )

        if not notices:
            results['phase1_discovery'] = {'error': 'No permits found'}
            return results

        # Sync to database
        sync_result = self.sync_permits_to_database(notices, db)
        results['phase1_discovery'] = {
            'total_discovered': len(notices),
            'new': len(sync_result['new']),
            'unchanged': len(sync_result['unchanged']),
            'applications': len([n for n in notices if n.notice_type == NoticeType.APPLICATION]),
            'issuances': len([n for n in notices if n.notice_type == NoticeType.ISSUANCE])
        }

        results['permits_ready_for_analysis'] = sync_result['new']

        logger.info("SRWMD hybrid pipeline complete", results=results)
        return results


# Convenience functions
def scrape_srwmd_applications() -> SRWMDScrapeResult:
    """Scrape SRWMD permit applications."""
    scraper = SRWMDScraper()
    return scraper.scrape_applications()


def scrape_srwmd_issuances() -> SRWMDScrapeResult:
    """Scrape SRWMD permit issuances."""
    scraper = SRWMDScraper()
    return scraper.scrape_issuances()


def scrape_alachua_permits() -> dict:
    """Scrape all SRWMD permits filtered for Alachua County."""
    scraper = SRWMDScraper()
    results = scraper.scrape_all()
    return {
        'applications': results['applications'].alachua_notices,
        'issuances': results['issuances'].alachua_notices
    }


if __name__ == "__main__":
    # Test the scraper
    print("\n" + "="*60)
    print("SRWMD Permit Scraper Test")
    print("="*60)

    scraper = SRWMDScraper()

    # Test applications
    print("\n--- Permit Applications ---")
    apps = scraper.scrape_applications()
    print(f"Success: {apps.success}")
    print(f"Total: {apps.notice_count}")
    print(f"Alachua County: {apps.alachua_count}")

    if apps.alachua_notices:
        print("\nAlachua County Applications:")
        for notice in apps.alachua_notices[:5]:
            print(f"  {notice.date.strftime('%m/%d/%Y') if notice.date else 'N/A'} | {notice.permit_number} | {notice.project_name}")

    # Test issuances
    print("\n--- Permit Issuances ---")
    issued = scraper.scrape_issuances()
    print(f"Success: {issued.success}")
    print(f"Total: {issued.notice_count}")
    print(f"Alachua County: {issued.alachua_count}")

    if issued.alachua_notices:
        print("\nAlachua County Issuances:")
        for notice in issued.alachua_notices[:5]:
            print(f"  {notice.date.strftime('%m/%d/%Y') if notice.date else 'N/A'} | {notice.permit_number} | {notice.project_name}")
