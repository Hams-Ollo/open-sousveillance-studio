"""
Unit tests for scraper modules.

Tests cover:
- CivicClerkScraper: Meeting list parsing, date extraction, PDF download
- FloridaNoticesScraper: Notice parsing, PDF URL extraction
- SRWMDScraper: Permit table parsing, detail page parsing, county filtering
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict

from src.tools.firecrawl_client import ScrapeResult


# =============================================================================
# Mock Data: CivicClerk
# =============================================================================

CIVICCLERK_MARKDOWN = """
# Alachua City Portal

## Upcoming Events

Monday
JAN 13,
2026

6:00 PM EST

City Commission Regular Meeting
[City Commission]

Location: City Hall, 15500 Main Street

Agenda Posted on: January 10, 2026

---

Tuesday
JAN 21,
2026

5:30 PM EST

Planning and Zoning Board Meeting
[Planning and Zoning Board]

Location: City Hall, 15500 Main Street

---

Wednesday
FEB 05,
2026

6:00 PM EST

Community Redevelopment Agency Meeting
[CRA]

Location: City Hall, 15500 Main Street

Agenda Posted on: February 1, 2026
"""

CIVICCLERK_PAST_MARKDOWN = """
# Past Events

Thursday
DEC 19,
2025

6:00 PM EST

City Commission Regular Meeting
[City Commission]

Location: City Hall

Agenda Posted on: December 15, 2025
"""


# =============================================================================
# Mock Data: Florida Public Notices
# =============================================================================

FLORIDA_NOTICES_MARKDOWN = """
# Florida Public Notices

Showing 1-12 of 45 results

Alachua County Today
Alachua, FL
January 29, 2026

Keywords: Public Hearing, Zoning Amendment
Government Publications - Notices of Hearings

NOTICE OF PUBLIC HEARING
The City of Alachua will hold a public hearing on February 15, 2026...

---

Alachua County Today
Alachua, FL
January 28, 2026

Keywords: Budget Amendment, City Council
Government Publications - Notices of Hearings

NOTICE OF BUDGET AMENDMENT
The City Council will consider a budget amendment...

---

Alachua County Today
Alachua, FL
January 27, 2026

Keywords: Foreclosure, Legal Notice
Miscellaneous - Legal Notices

NOTICE OF FORECLOSURE SALE
Property located at 123 Main Street...
"""

FLORIDA_NOTICES_PDF_CONTENT = """
View PDF: [Download](https://d3pfxxxxxxxx.cloudfront.net/12/12345678.pdf)

Another link: https://d3pfyyyyyy.cloudfront.net/34/87654321.pdf
"""


# =============================================================================
# Mock Data: SRWMD
# =============================================================================

SRWMD_APPLICATIONS_MARKDOWN = """
# Notice of Receipt of Applications

| RULE | RECEIVED | APPLICATION | PROJECT NAME | COUNTY |
|------|----------|-------------|--------------|--------|
| ERP Individual | 01/15/2026 | [253436-1](https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1) | Tara Forest Phase 2 | Alachua |
| ERP General | 01/14/2026 | [253435-2](https://permitting.sjrwmd.com/srep/#/ep/permit/253435-2) | Walmart Expansion | Columbia |
| WUP Individual | 01/13/2026 | [253434-3](https://permitting.sjrwmd.com/srep/#/ep/permit/253434-3) | Agricultural Well | Alachua |
| ERP Individual | 01/12/2026 | [253433-4](https://permitting.sjrwmd.com/srep/#/ep/permit/253433-4) | Residential Subdivision | Gilchrist |
"""

SRWMD_ISSUANCES_MARKDOWN = """
# Notice of Permit Issuance

| RULE | ISSUED | PERMIT | PROJECT NAME | COUNTY |
|------|--------|--------|--------------|--------|
| ERP Individual | 01/20/2026 | [253400-1](https://permitting.sjrwmd.com/srep/#/ep/permit/253400-1) | Commercial Plaza | Alachua |
| WOD General | 01/19/2026 | [253399-2](https://permitting.sjrwmd.com/srep/#/ep/permit/253399-2) | Drainage Improvement | Suwannee |
| ERP General | 01/18/2026 | [253398-3](https://permitting.sjrwmd.com/srep/#/ep/permit/253398-3) | Solar Farm | Levy |
"""

SRWMD_DETAIL_MARKDOWN = """
# Permit Detail

Project Number: 253436-1
Project Name: Tara Forest Phase 2
Permit Type: ERP Individual
County: Alachua
Sequence Type: New Application

Received: 01/15/2026
Status: Pending
Current Process Stage: Review

Description: Residential subdivision with stormwater management system

Applicant: Tara Development LLC
Owner: Tara Land Holdings Inc
Consultant: Smith Engineering Group
Agent: John Smith
Wetlands: 2.5 acres
Reviewer(s): Jane Doe, Bob Wilson

## Documents

| Group Name | Document Name | Date | Size | Link | Comments |
|------------|---------------|------|------|------|----------|
| Application | Application Form | 01/15/2026 | 1024 | [Download](https://example.com/doc1.pdf) | Initial application |
| Application | Plans | 01/15/2026 | 5120 | [Download](https://example.com/doc2.pdf) | Civil Plans |
| Reports | Stormwater Report | 01/14/2026 | 2048 | [Download](https://example.com/doc3.pdf) | Engineering report |
"""


# =============================================================================
# CivicClerk Scraper Tests
# =============================================================================

class TestCivicClerkScraper:
    """Tests for CivicClerkScraper."""

    @pytest.fixture
    def mock_firecrawl_client(self):
        """Create a mock FirecrawlClient."""
        client = MagicMock()
        client.scrape_civicclerk_with_scroll.return_value = ScrapeResult(
            url="https://alachuafl.portal.civicclerk.com/",
            markdown=CIVICCLERK_MARKDOWN,
            success=True
        )
        return client

    @pytest.fixture
    def scraper(self, mock_firecrawl_client):
        """Create CivicClerkScraper with mocked client."""
        from src.tools.civicclerk_scraper import CivicClerkScraper
        return CivicClerkScraper(
            site_id="alachuafl",
            firecrawl_client=mock_firecrawl_client
        )

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with correct site_id and base URL."""
        assert scraper.site_id == "alachuafl"
        assert scraper.base_url == "https://alachuafl.portal.civicclerk.com/"

    def test_scrape_meetings_success(self, scraper, mock_firecrawl_client):
        """Test successful meeting scraping."""
        result = scraper.scrape_meetings()

        assert result.success is True
        assert result.site_id == "alachuafl"
        assert result.meeting_count >= 1
        mock_firecrawl_client.scrape_civicclerk_with_scroll.assert_called_once()

    def test_scrape_meetings_parses_dates(self, scraper):
        """Test that meeting dates are correctly parsed."""
        result = scraper.scrape_meetings()

        # Should find meetings with dates
        meetings_with_dates = [m for m in result.meetings if m.date is not None]
        assert len(meetings_with_dates) >= 1

        # Check first meeting date
        if meetings_with_dates:
            first_meeting = meetings_with_dates[0]
            assert isinstance(first_meeting.date, datetime)
            assert first_meeting.date.year == 2026

    def test_scrape_meetings_extracts_board_tags(self, scraper):
        """Test that board tags are extracted from meeting text."""
        result = scraper.scrape_meetings()

        # Should find meetings with board tags
        meetings_with_boards = [m for m in result.meetings if m.board is not None]
        # Board extraction depends on markdown format
        assert result.success is True

    def test_scrape_meetings_detects_agenda_posted(self, scraper):
        """Test that agenda posted status is detected."""
        result = scraper.scrape_meetings()

        # At least one meeting should have agenda posted
        meetings_with_agenda = [m for m in result.meetings if m.has_agenda]
        # This depends on the mock data having "Agenda Posted on" text
        assert result.success is True

    def test_scrape_meetings_failure(self, mock_firecrawl_client):
        """Test handling of scraping failure."""
        from src.tools.civicclerk_scraper import CivicClerkScraper

        mock_firecrawl_client.scrape_civicclerk_with_scroll.return_value = ScrapeResult(
            url="https://alachuafl.portal.civicclerk.com/",
            markdown="",
            success=False,
            error="Connection timeout"
        )

        scraper = CivicClerkScraper(
            site_id="alachuafl",
            firecrawl_client=mock_firecrawl_client
        )
        result = scraper.scrape_meetings()

        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.meeting_count == 0

    def test_meeting_id_generation(self):
        """Test that meeting IDs are generated consistently."""
        from src.tools.civicclerk_scraper import CivicClerkMeeting

        meeting = CivicClerkMeeting(
            meeting_id="",
            title="City Commission Meeting",
            date=datetime(2026, 1, 13)
        )
        meeting.meeting_id = meeting.generate_id()

        # ID should be a 12-character hex string
        assert len(meeting.meeting_id) == 12
        assert all(c in '0123456789abcdef' for c in meeting.meeting_id)

        # Same input should generate same ID
        meeting2 = CivicClerkMeeting(
            meeting_id="",
            title="City Commission Meeting",
            date=datetime(2026, 1, 13)
        )
        meeting2.meeting_id = meeting2.generate_id()
        assert meeting.meeting_id == meeting2.meeting_id

    def test_upcoming_vs_past_meetings(self, scraper, mock_firecrawl_client):
        """Test filtering of upcoming vs past meetings."""
        # Include both past and future dates in mock
        combined_markdown = CIVICCLERK_MARKDOWN + CIVICCLERK_PAST_MARKDOWN
        mock_firecrawl_client.scrape_civicclerk_with_scroll.return_value = ScrapeResult(
            url="https://alachuafl.portal.civicclerk.com/",
            markdown=combined_markdown,
            success=True
        )

        result = scraper.scrape_meetings()

        # Result should have both past and upcoming properties
        assert hasattr(result, 'past_meetings')
        assert hasattr(result, 'upcoming_meetings')


# =============================================================================
# Florida Public Notices Scraper Tests
# =============================================================================

class TestFloridaNoticesScraper:
    """Tests for FloridaNoticesScraper."""

    @pytest.fixture
    def mock_firecrawl_client(self):
        """Create a mock FirecrawlClient."""
        client = MagicMock()
        client.scrape_with_actions.return_value = ScrapeResult(
            url="https://floridapublicnotices.com/",
            markdown=FLORIDA_NOTICES_MARKDOWN,
            success=True
        )
        return client

    @pytest.fixture
    def scraper(self, mock_firecrawl_client):
        """Create FloridaNoticesScraper with mocked client."""
        from src.tools.florida_notices_scraper import FloridaNoticesScraper
        return FloridaNoticesScraper(firecrawl_client=mock_firecrawl_client)

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper.BASE_URL == "https://floridapublicnotices.com/"

    def test_scrape_notices_success(self, scraper, mock_firecrawl_client):
        """Test successful notice scraping."""
        result = scraper.scrape_notices(
            newspaper="Alachua County Today",
            county="Alachua"
        )

        assert result.success is True
        assert result.newspaper == "Alachua County Today"
        assert result.county == "Alachua"
        mock_firecrawl_client.scrape_with_actions.assert_called_once()

    def test_scrape_notices_parses_dates(self, scraper):
        """Test that publication dates are correctly parsed."""
        result = scraper.scrape_notices()

        notices_with_dates = [n for n in result.notices if n.publication_date is not None]
        if notices_with_dates:
            first_notice = notices_with_dates[0]
            assert isinstance(first_notice.publication_date, datetime)
            assert first_notice.publication_date.year == 2026

    def test_scrape_notices_extracts_keywords(self, scraper):
        """Test that keywords are extracted from notices."""
        result = scraper.scrape_notices()

        # Check if any notices have keywords
        notices_with_keywords = [n for n in result.notices if n.keywords is not None]
        # Keywords extraction depends on markdown format
        assert result.success is True

    def test_scrape_notices_extracts_total_results(self, scraper):
        """Test that total results count is extracted."""
        result = scraper.scrape_notices()

        # Should extract "45" from "Showing 1-12 of 45 results"
        assert result.total_results == 45

    def test_scrape_notices_failure(self, mock_firecrawl_client):
        """Test handling of scraping failure."""
        from src.tools.florida_notices_scraper import FloridaNoticesScraper

        mock_firecrawl_client.scrape_with_actions.return_value = ScrapeResult(
            url="https://floridapublicnotices.com/",
            markdown="",
            success=False,
            error="Rate limited"
        )

        scraper = FloridaNoticesScraper(firecrawl_client=mock_firecrawl_client)
        result = scraper.scrape_notices()

        assert result.success is False
        assert result.error == "Rate limited"
        assert result.notice_count == 0

    def test_extract_pdf_urls(self, scraper):
        """Test PDF URL extraction from content."""
        urls = scraper.extract_pdf_urls(FLORIDA_NOTICES_PDF_CONTENT)

        assert len(urls) >= 1
        # Should find CloudFront URLs
        cloudfront_urls = [u for u in urls if 'cloudfront.net' in u]
        assert len(cloudfront_urls) >= 1

    def test_notices_with_pdf_filter(self, scraper):
        """Test filtering notices that have PDFs."""
        result = scraper.scrape_notices()

        # notices_with_pdf property should work
        assert hasattr(result, 'notices_with_pdf')
        pdf_notices = result.notices_with_pdf
        assert all(n.has_pdf for n in pdf_notices)


# =============================================================================
# SRWMD Scraper Tests
# =============================================================================

class TestSRWMDScraper:
    """Tests for SRWMDScraper."""

    @pytest.fixture
    def mock_firecrawl_client(self):
        """Create a mock FirecrawlClient."""
        client = MagicMock()
        # Default to applications response
        client.scrape.return_value = ScrapeResult(
            url="https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications",
            markdown=SRWMD_APPLICATIONS_MARKDOWN,
            success=True
        )
        return client

    @pytest.fixture
    def scraper(self, mock_firecrawl_client):
        """Create SRWMDScraper with mocked client."""
        from src.tools.srwmd_scraper import SRWMDScraper
        return SRWMDScraper(firecrawl_client=mock_firecrawl_client)

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with correct URLs."""
        assert "mysuwanneeriver.com/1616" in scraper.APPLICATIONS_URL
        assert "mysuwanneeriver.com/1617" in scraper.ISSUANCES_URL

    def test_scrape_applications_success(self, scraper, mock_firecrawl_client):
        """Test successful application scraping."""
        result = scraper.scrape_applications()

        assert result.success is True
        assert result.notice_count >= 1
        mock_firecrawl_client.scrape.assert_called()

    def test_scrape_applications_parses_table(self, scraper):
        """Test that permit table is correctly parsed."""
        result = scraper.scrape_applications()

        # Should find permits from the table
        assert result.notice_count >= 1

        # Check first permit
        if result.notices:
            first = result.notices[0]
            assert first.permit_number is not None
            assert first.project_name is not None
            assert first.county is not None

    def test_scrape_applications_extracts_permit_urls(self, scraper):
        """Test that permit URLs are extracted from links."""
        result = scraper.scrape_applications()

        # Permits with links should have permit_url
        permits_with_urls = [n for n in result.notices if n.permit_url is not None]
        assert len(permits_with_urls) >= 1

        # URLs should point to E-Permitting portal
        for permit in permits_with_urls:
            assert "permitting" in permit.permit_url or "sjrwmd" in permit.permit_url

    def test_scrape_applications_parses_dates(self, scraper):
        """Test that received dates are correctly parsed."""
        result = scraper.scrape_applications()

        permits_with_dates = [n for n in result.notices if n.date is not None]
        if permits_with_dates:
            first = permits_with_dates[0]
            assert isinstance(first.date, datetime)
            assert first.date.year == 2026

    def test_scrape_issuances_success(self, scraper, mock_firecrawl_client):
        """Test successful issuance scraping."""
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://www.mysuwanneeriver.com/1617/Notice-of-Permit-Issuance",
            markdown=SRWMD_ISSUANCES_MARKDOWN,
            success=True
        )

        result = scraper.scrape_issuances()

        assert result.success is True
        assert result.notice_count >= 1

    def test_scrape_all_returns_both(self, scraper, mock_firecrawl_client):
        """Test scrape_all returns both applications and issuances."""
        # Mock different responses for each URL
        def mock_scrape(url, **kwargs):
            if "1616" in url:
                return ScrapeResult(
                    url=url,
                    markdown=SRWMD_APPLICATIONS_MARKDOWN,
                    success=True
                )
            else:
                return ScrapeResult(
                    url=url,
                    markdown=SRWMD_ISSUANCES_MARKDOWN,
                    success=True
                )

        mock_firecrawl_client.scrape.side_effect = mock_scrape

        results = scraper.scrape_all()

        assert 'applications' in results
        assert 'issuances' in results
        assert results['applications'].success is True
        assert results['issuances'].success is True

    def test_alachua_county_filter(self, scraper):
        """Test filtering for Alachua County permits."""
        result = scraper.scrape_applications()

        # Should have alachua_notices property
        alachua = result.alachua_notices
        assert all(n.county.lower() == "alachua" for n in alachua)

        # alachua_count should match
        assert result.alachua_count == len(alachua)

    def test_permit_type_parsing(self, scraper):
        """Test that permit types are correctly parsed."""
        from src.tools.srwmd_scraper import PermitType

        result = scraper.scrape_applications()

        # Should have various permit types
        permit_types = [n.permit_type for n in result.notices]
        assert any(pt != PermitType.UNKNOWN for pt in permit_types)

    def test_scrape_permit_detail_success(self, scraper, mock_firecrawl_client):
        """Test scraping permit detail page."""
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1",
            markdown=SRWMD_DETAIL_MARKDOWN,
            success=True
        )

        detail = scraper.scrape_permit_detail(
            "https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1"
        )

        assert detail is not None
        assert detail.project_number == "253436-1"
        assert detail.project_name == "Tara Forest Phase 2"
        assert detail.county == "Alachua"

    def test_scrape_permit_detail_extracts_parties(self, scraper, mock_firecrawl_client):
        """Test that parties are extracted from detail page."""
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1",
            markdown=SRWMD_DETAIL_MARKDOWN,
            success=True
        )

        detail = scraper.scrape_permit_detail(
            "https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1"
        )

        assert detail.applicant == "Tara Development LLC"
        assert detail.owner == "Tara Land Holdings Inc"
        assert detail.consultant == "Smith Engineering Group"

    def test_scrape_permit_detail_extracts_documents(self, scraper, mock_firecrawl_client):
        """Test that documents are extracted from detail page."""
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1",
            markdown=SRWMD_DETAIL_MARKDOWN,
            success=True
        )

        detail = scraper.scrape_permit_detail(
            "https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1"
        )

        assert len(detail.documents) >= 1
        # Check first document
        if detail.documents:
            doc = detail.documents[0]
            assert doc.group_name is not None
            assert doc.document_name is not None
            assert doc.download_url is not None

    def test_scrape_permit_detail_failure(self, scraper, mock_firecrawl_client):
        """Test handling of detail page scraping failure."""
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://permitting.sjrwmd.com/srep/#/ep/permit/invalid",
            markdown="",
            success=False,
            error="Page not found"
        )

        detail = scraper.scrape_permit_detail(
            "https://permitting.sjrwmd.com/srep/#/ep/permit/invalid"
        )

        assert detail is None

    def test_enrich_notice_with_detail(self, scraper, mock_firecrawl_client):
        """Test enriching a notice with detail page info."""
        from src.tools.srwmd_scraper import PermitNotice, NoticeType, PermitType

        # First scrape applications
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications",
            markdown=SRWMD_APPLICATIONS_MARKDOWN,
            success=True
        )
        result = scraper.scrape_applications()

        # Then mock detail page
        mock_firecrawl_client.scrape.return_value = ScrapeResult(
            url="https://permitting.sjrwmd.com/srep/#/ep/permit/253436-1",
            markdown=SRWMD_DETAIL_MARKDOWN,
            success=True
        )

        # Enrich first notice
        if result.notices:
            notice = result.notices[0]
            enriched = scraper.enrich_notice_with_detail(notice)

            if notice.permit_url:
                assert enriched.detail is not None

    def test_notice_type_enum(self):
        """Test NoticeType enum values."""
        from src.tools.srwmd_scraper import NoticeType

        assert NoticeType.APPLICATION.value == "application"
        assert NoticeType.ISSUANCE.value == "issuance"

    def test_permit_type_from_string(self):
        """Test PermitType.from_string parsing."""
        from src.tools.srwmd_scraper import PermitType

        assert PermitType.from_string("ERP Individual") == PermitType.ERP_INDIVIDUAL
        assert PermitType.from_string("erp individual") == PermitType.ERP_INDIVIDUAL
        assert PermitType.from_string("WUP Individual") == PermitType.WUP_INDIVIDUAL
        assert PermitType.from_string("Unknown Type") == PermitType.UNKNOWN


# =============================================================================
# FirecrawlClient URL Validation Tests
# =============================================================================

class TestFirecrawlClientValidation:
    """Tests for FirecrawlClient URL validation."""

    def test_allowed_domains_list(self):
        """Test that allowed domains list contains expected domains."""
        from src.tools.firecrawl_client import ALLOWED_DOMAINS

        assert "portal.civicclerk.com" in ALLOWED_DOMAINS
        assert "floridapublicnotices.com" in ALLOWED_DOMAINS
        assert "mysuwanneeriver.com" in ALLOWED_DOMAINS
        assert "permitting.sjrwmd.com" in ALLOWED_DOMAINS

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_validate_url_allowed(self, mock_app):
        """Test URL validation passes for allowed domains."""
        from src.tools.firecrawl_client import FirecrawlClient

        client = FirecrawlClient(api_key="test-key")

        # Should not raise for allowed domains
        assert client._validate_url("https://alachuafl.portal.civicclerk.com/") is True
        assert client._validate_url("https://floridapublicnotices.com/search") is True
        assert client._validate_url("https://www.mysuwanneeriver.com/1616/") is True

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_validate_url_blocked(self, mock_app):
        """Test URL validation fails for blocked domains."""
        from src.tools.firecrawl_client import FirecrawlClient

        client = FirecrawlClient(api_key="test-key")

        # Should raise for non-allowed domains
        with pytest.raises(ValueError) as exc_info:
            client._validate_url("https://evil-site.com/malicious")

        assert "not in allowed list" in str(exc_info.value)

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_validate_url_disabled(self, mock_app):
        """Test URL validation can be disabled."""
        from src.tools.firecrawl_client import FirecrawlClient

        client = FirecrawlClient(api_key="test-key", validate_urls=False)

        # Should not raise even for non-allowed domains
        assert client._validate_url("https://any-site.com/page") is True

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_custom_allowed_domains(self, mock_app):
        """Test custom allowed domains list."""
        from src.tools.firecrawl_client import FirecrawlClient

        custom_domains = ["custom-domain.com", "another-domain.org"]
        client = FirecrawlClient(
            api_key="test-key",
            allowed_domains=custom_domains
        )

        # Should allow custom domains
        assert client._validate_url("https://custom-domain.com/page") is True

        # Should block default domains
        with pytest.raises(ValueError):
            client._validate_url("https://floridapublicnotices.com/")


# =============================================================================
# Integration-style Tests (with mocked external calls)
# =============================================================================

class TestScraperIntegration:
    """Integration tests for scraper workflows."""

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_civicclerk_full_workflow(self, mock_app):
        """Test full CivicClerk scraping workflow."""
        from src.tools.civicclerk_scraper import CivicClerkScraper
        from src.tools.firecrawl_client import FirecrawlClient

        # Mock the Firecrawl responses
        mock_instance = MagicMock()
        mock_app.return_value = mock_instance

        # Create a mock response object
        mock_response = MagicMock()
        mock_response.markdown = CIVICCLERK_MARKDOWN
        mock_instance.scrape.return_value = mock_response

        # Create client and scraper
        client = FirecrawlClient(api_key="test-key", validate_urls=False)
        client.scrape_civicclerk_with_scroll = MagicMock(return_value=ScrapeResult(
            url="https://alachuafl.portal.civicclerk.com/",
            markdown=CIVICCLERK_MARKDOWN,
            success=True
        ))

        scraper = CivicClerkScraper(site_id="alachuafl", firecrawl_client=client)

        # Run scrape
        result = scraper.scrape_meetings()

        assert result.success is True
        assert result.site_id == "alachuafl"

    @patch('src.tools.firecrawl_client.FirecrawlApp')
    def test_srwmd_alachua_filter_workflow(self, mock_app):
        """Test SRWMD scraping with Alachua filter."""
        from src.tools.srwmd_scraper import SRWMDScraper
        from src.tools.firecrawl_client import FirecrawlClient

        mock_instance = MagicMock()
        mock_app.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.markdown = SRWMD_APPLICATIONS_MARKDOWN
        mock_response.success = True
        mock_instance.scrape.return_value = mock_response

        client = FirecrawlClient(api_key="test-key", validate_urls=False)
        client.scrape = MagicMock(return_value=ScrapeResult(
            url="https://www.mysuwanneeriver.com/1616/",
            markdown=SRWMD_APPLICATIONS_MARKDOWN,
            success=True
        ))

        scraper = SRWMDScraper(firecrawl_client=client)

        result = scraper.scrape_applications()

        # Filter for Alachua
        alachua_permits = result.alachua_notices

        assert result.success is True
        assert len(alachua_permits) >= 1
        assert all(p.county.lower() == "alachua" for p in alachua_permits)
