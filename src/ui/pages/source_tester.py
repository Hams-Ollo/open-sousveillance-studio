"""
Source Tester Page - Test scraping and monitoring of data sources.
"""

import streamlit as st
import yaml
from pathlib import Path


@st.cache_data
def load_sources_config() -> dict:
    """Load sources from config/sources.yaml."""
    from src.config import CONFIG_DIR

    sources_file = CONFIG_DIR / "sources.yaml"
    if not sources_file.exists():
        return {}

    with open(sources_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_sources_by_tier(sources_config: dict) -> dict:
    """Organize sources by tier."""
    tiers = {}

    for tier_name, tier_data in sources_config.items():
        if isinstance(tier_data, dict) and 'sources' in tier_data:
            tiers[tier_name] = tier_data['sources']
        elif isinstance(tier_data, list):
            tiers[tier_name] = tier_data

    return tiers


def render():
    """Render the Source Tester tab."""
    st.header("🌐 Source Tester")
    st.caption("Test web scraping, content extraction, and Scout analysis")

    # Load sources
    try:
        sources_config = load_sources_config()
        sources_by_tier = get_sources_by_tier(sources_config)
    except Exception as e:
        st.error(f"Error loading sources: {e}")
        sources_by_tier = {}

    # Three modes: select from config, custom URL, or Scout analysis
    mode = st.radio(
        "Test Mode",
        options=["Scrape from Config", "Custom URL", "Scout Analysis"],
        horizontal=True,
        key="source_mode"
    )

    if mode == "Scrape from Config":
        render_config_source_selector(sources_by_tier)
    elif mode == "Custom URL":
        render_custom_url_tester()
    else:
        render_scout_analysis_tester()


def render_config_source_selector(sources_by_tier: dict):
    """Render source selection from config file."""
    if not sources_by_tier:
        st.warning("No sources found in config/sources.yaml")
        st.info("Add sources to the config file or use Custom URL mode")
        return

    # Tier selection
    col1, col2 = st.columns([1, 2])

    with col1:
        tier = st.selectbox(
            "Source Tier",
            options=list(sources_by_tier.keys()),
            key="source_tier"
        )

    with col2:
        sources_in_tier = sources_by_tier.get(tier, [])
        if sources_in_tier:
            source = st.selectbox(
                "Source",
                options=sources_in_tier,
                format_func=lambda x: x.get('name', x.get('id', 'Unknown')),
                key="selected_source"
            )
        else:
            st.info("No sources in this tier")
            return

    if source:
        display_source_details(source)

        st.divider()

        # Test scraping
        if st.button("🔍 Test Scrape", type="primary", use_container_width=True):
            test_scrape_source(source)


def display_source_details(source: dict):
    """Display details about a selected source."""
    with st.expander("Source Details", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {source.get('id', 'N/A')}")
            st.write(f"**Name:** {source.get('name', 'N/A')}")
            st.write(f"**Platform:** {source.get('platform', 'N/A')}")
            st.write(f"**Priority:** {source.get('priority', 'N/A')}")

        with col2:
            st.write(f"**Check Frequency:** {source.get('check_frequency', 'N/A')}")
            st.write(f"**Scraping Method:** {source.get('scraping_method', 'N/A')}")
            st.write(f"**Jurisdiction:** {source.get('jurisdiction', 'N/A')}")

        url = source.get('url', '')
        if url:
            st.write(f"**URL:** [{url}]({url})")

        if source.get('description'):
            st.write(f"**Description:** {source.get('description')}")

        if source.get('document_types'):
            st.write(f"**Document Types:** {', '.join(source.get('document_types', []))}")


def render_custom_url_tester():
    """Render custom URL testing interface."""
    st.subheader("Custom URL Test")

    url = st.text_input(
        "URL to Test",
        placeholder="https://example.com/page-to-scrape",
        key="custom_url"
    )

    col1, col2 = st.columns(2)
    with col1:
        scrape_method = st.selectbox(
            "Scraping Method",
            options=["firecrawl", "requests", "selenium"],
            key="scrape_method"
        )
    with col2:
        extract_format = st.selectbox(
            "Extract Format",
            options=["markdown", "html", "text"],
            key="extract_format"
        )

    if st.button("🔍 Test Scrape", type="primary", use_container_width=True):
        if not url:
            st.error("Please enter a URL")
            return

        test_scrape_url(url, scrape_method, extract_format)


def test_scrape_source(source: dict):
    """Test scraping a source from config."""
    url = source.get('url')
    if not url:
        st.error("Source has no URL configured")
        return

    source_id = source.get('id', '')
    scraping_config = source.get('scraping', {})
    custom_scraper = scraping_config.get('custom_scraper', '')

    # Use custom scraper if available
    if 'civicclerk' in source_id.lower() or 'CivicClerkScraper' in custom_scraper:
        test_civicclerk_scraper(source)
    elif 'florida-public-notices' in source_id.lower() or 'FloridaNoticesScraper' in custom_scraper:
        test_florida_notices_scraper(source)
    elif 'srwmd' in source_id.lower() or 'SRWMDScraper' in custom_scraper:
        test_srwmd_scraper(source)
    else:
        # Fall back to generic scraping
        scrape_method = scraping_config.get('method', 'firecrawl')
        test_scrape_url(url, scrape_method, "markdown")


def test_civicclerk_scraper(source: dict):
    """Test the CivicClerk scraper with hybrid pipeline support."""

    # Pipeline mode selection
    pipeline_mode = st.radio(
        "Pipeline Mode",
        options=["Discovery Only (Fast)", "Full Hybrid Pipeline"],
        horizontal=True,
        key="civicclerk_mode"
    )

    col1, col2 = st.columns(2)
    with col1:
        days_back = st.number_input("Days Back", min_value=0, max_value=90, value=30, key="days_back")
    with col2:
        days_forward = st.number_input("Days Forward", min_value=0, max_value=90, value=60, key="days_forward")

    if not st.button("� Run Pipeline", type="primary", use_container_width=True, key="run_civicclerk"):
        return

    with st.status("Running CivicClerk Pipeline...", expanded=True) as status:
        try:
            from src.tools.civicclerk_scraper import CivicClerkScraper
            from datetime import datetime, timedelta

            # Get site_id from config
            scraping_config = source.get('scraping', {})
            site_id = scraping_config.get('site_id', 'alachuafl')

            st.write(f"📍 Site ID: {site_id}")
            st.write(f"� Date Range: -{days_back} to +{days_forward} days")

            scraper = CivicClerkScraper(site_id=site_id)

            if pipeline_mode == "Discovery Only (Fast)":
                st.write("🔧 Running Discovery Phase only...")
                meetings = scraper.discover_meetings(
                    days_back=days_back,
                    days_forward=days_forward,
                    scroll_count=2
                )

                status.update(label="Discovery Complete", state="complete", expanded=False)

                # Display results
                st.subheader("📄 Discovery Results")

                now = datetime.now()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Meetings Found", len(meetings))
                with col2:
                    past = len([m for m in meetings if m.date < now])
                    st.metric("Past", past)
                with col3:
                    upcoming = len([m for m in meetings if m.date >= now])
                    st.metric("Upcoming", upcoming)

                # Meetings with agendas
                with_agenda = [m for m in meetings if m.has_agenda or m.has_agenda_packet]
                st.metric("With Agenda Posted", len(with_agenda))

                # Show meetings
                if meetings:
                    st.subheader("📅 Meetings in Date Range")
                    for meeting in meetings[:15]:
                        with st.expander(f"{meeting.date.strftime('%Y-%m-%d')} - {meeting.title}"):
                            st.write(f"**Board:** {meeting.board or 'N/A'}")
                            st.write(f"**Time:** {meeting.time or 'N/A'}")
                            st.write(f"**Has Agenda:** {'✅' if meeting.has_agenda else '❌'}")
                            st.write(f"**Has Agenda Packet:** {'✅' if meeting.has_agenda_packet else '❌'}")
                            if meeting.agenda_posted_date:
                                st.write(f"**Agenda Posted:** {meeting.agenda_posted_date.strftime('%Y-%m-%d')}")
                            st.write(f"**Meeting ID:** `{meeting.meeting_id}`")

            else:
                st.write("🔧 Running Full Hybrid Pipeline...")
                st.warning("Note: Full pipeline requires database connection and will download PDFs")

                try:
                    from src.database import get_db
                    db = get_db()

                    results = scraper.run_hybrid_pipeline(
                        db=db,
                        days_back=days_back,
                        days_forward=days_forward,
                        download_pdfs=True,
                        max_pdf_downloads=5
                    )

                    status.update(label="Pipeline Complete", state="complete", expanded=False)

                    # Display results
                    st.subheader("📄 Hybrid Pipeline Results")

                    # Phase 1 results
                    st.write("### Phase 1: Discovery")
                    p1 = results.get('phase1_discovery', {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Discovered", p1.get('total_discovered', 0))
                    with col2:
                        st.metric("New", p1.get('new', 0))
                    with col3:
                        st.metric("Updated", p1.get('updated', 0))
                    with col4:
                        st.metric("Unchanged", p1.get('unchanged', 0))

                    # Phase 2 results
                    st.write("### Phase 2: Detail (PDF Downloads)")
                    p2 = results.get('phase2_detail', {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Attempted", p2.get('attempted', 0))
                    with col2:
                        st.metric("Success", p2.get('success', 0))
                    with col3:
                        st.metric("Failed", p2.get('failed', 0))

                    # Ready for analysis
                    ready = results.get('meetings_ready_for_analysis', [])
                    st.success(f"✅ {len(ready)} meetings ready for Scout analysis")

                except ValueError as e:
                    st.error(f"Database not configured: {e}")
                    st.info("Set SUPABASE_URL and SUPABASE_KEY in .env to use full pipeline")

        except Exception as e:
            status.update(label="Pipeline Failed", state="error")
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())


def test_florida_notices_scraper(source: dict):
    """Test the Florida Public Notices scraper."""
    with st.status("Testing Florida Public Notices Scraper...", expanded=True) as status:
        try:
            st.write("🔧 Using FloridaNoticesScraper with Firecrawl Actions")

            from src.tools.florida_notices_scraper import FloridaNoticesScraper

            # Get filter config
            scraping_config = source.get('scraping', {})
            filters = scraping_config.get('filters', {})
            newspaper = filters.get('newspaper', 'Alachua County Today')
            county = filters.get('county', 'Alachua')

            st.write(f"📰 Newspaper: {newspaper}")
            st.write(f"📍 County: {county}")

            scraper = FloridaNoticesScraper()
            result = scraper.scrape_notices(newspaper=newspaper, county=county)

            status.update(label="Scrape Complete", state="complete", expanded=False)

            # Display results
            st.subheader("📄 Florida Public Notices Results")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Success", "✅" if result.success else "❌")
            with col2:
                st.metric("Notices Found", result.notice_count)
            with col3:
                st.metric("Total Available", result.total_results)

            if result.error:
                st.error(f"Error: {result.error}")

            # Show notices
            if result.notices:
                st.subheader("📋 Notices")
                for notice in result.notices[:10]:  # Show first 10
                    with st.expander(f"{notice.publication_date.strftime('%Y-%m-%d')} - {notice.subcategory or 'Notice'}"):
                        st.write(f"**Newspaper:** {notice.newspaper}")
                        st.write(f"**County:** {notice.county}")
                        st.write(f"**Category:** {notice.subcategory or 'N/A'}")
                        st.write(f"**Has PDF:** {'✅' if notice.has_pdf else '❌'}")
                        if notice.keywords:
                            st.write(f"**Keywords:** {notice.keywords[:200]}...")
                        if notice.pdf_url:
                            st.write(f"**PDF URL:** [{notice.pdf_url}]({notice.pdf_url})")

            # Raw markdown
            if result.raw_markdown:
                with st.expander("View Raw Markdown"):
                    st.text_area("Raw Content", result.raw_markdown[:5000], height=300)

        except Exception as e:
            status.update(label="Scrape Failed", state="error")
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())


def test_srwmd_scraper(source: dict):
    """Test the SRWMD permit scraper."""

    # Options
    col1, col2 = st.columns(2)
    with col1:
        include_apps = st.checkbox("Include Applications", value=True, key="srwmd_apps")
    with col2:
        include_issued = st.checkbox("Include Issuances", value=True, key="srwmd_issued")

    county_filter = st.selectbox(
        "County Filter",
        options=["All Counties", "Alachua"],
        index=1,  # Default to Alachua
        key="srwmd_county"
    )

    if st.button("🔍 Scrape SRWMD Permits", type="primary", use_container_width=True):
        with st.status("Scraping SRWMD Permits...", expanded=True) as status:
            try:
                from src.tools.srwmd_scraper import SRWMDScraper

                scraper = SRWMDScraper()

                all_notices = []

                # Scrape applications
                if include_apps:
                    st.write("📥 Scraping permit applications...")
                    apps = scraper.scrape_applications()
                    if apps.success:
                        all_notices.extend(apps.notices)
                        st.write(f"  Found {apps.notice_count} applications ({apps.alachua_count} in Alachua)")
                    else:
                        st.warning(f"Applications scrape failed: {apps.error}")

                # Scrape issuances
                if include_issued:
                    st.write("📥 Scraping permit issuances...")
                    issued = scraper.scrape_issuances()
                    if issued.success:
                        all_notices.extend(issued.notices)
                        st.write(f"  Found {issued.notice_count} issuances ({issued.alachua_count} in Alachua)")
                    else:
                        st.warning(f"Issuances scrape failed: {issued.error}")

                # Apply county filter
                if county_filter != "All Counties":
                    all_notices = [n for n in all_notices if n.county.lower() == county_filter.lower()]

                status.update(label="Scrape Complete", state="complete", expanded=False)

                # Display results
                st.subheader("📄 SRWMD Permit Results")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Permits", len(all_notices))
                with col2:
                    apps_count = len([n for n in all_notices if n.notice_type.value == "application"])
                    st.metric("Applications", apps_count)
                with col3:
                    issued_count = len([n for n in all_notices if n.notice_type.value == "issuance"])
                    st.metric("Issuances", issued_count)

                # Store notices in session state for detail fetching
                st.session_state['srwmd_notices'] = all_notices

                # Show permits in table
                if all_notices:
                    st.subheader("📋 Permits")

                    # Group by notice type
                    for notice_type in ["application", "issuance"]:
                        type_notices = [n for n in all_notices if n.notice_type.value == notice_type]
                        if type_notices:
                            st.write(f"### {'📝 Applications' if notice_type == 'application' else '✅ Issuances'}")

                            for i, notice in enumerate(type_notices[:15]):  # Show first 15
                                date_str = notice.date.strftime('%m/%d/%Y') if notice.date else 'N/A'
                                with st.expander(f"{date_str} | {notice.permit_number} | {notice.project_name[:50]}"):
                                    st.write(f"**Permit Number:** `{notice.permit_number}`")
                                    st.write(f"**Project Name:** {notice.project_name}")
                                    st.write(f"**Rule Type:** {notice.rule_type}")
                                    st.write(f"**County:** {notice.county}")
                                    st.write(f"**Date:** {date_str}")
                                    if notice.permit_url:
                                        st.write(f"**E-Permit Link:** [{notice.permit_url}]({notice.permit_url})")

                                        # Button to fetch detail
                                        if st.button(f"📄 Fetch Detail", key=f"detail_{notice.permit_number}_{i}"):
                                            with st.spinner("Fetching permit details..."):
                                                detail = scraper.scrape_permit_detail(notice.permit_url)
                                                if detail:
                                                    st.success(f"Found {len(detail.documents)} documents")
                                                    st.write(f"**Description:** {detail.description}")
                                                    st.write(f"**Applicant:** {detail.applicant}")
                                                    st.write(f"**Owner:** {detail.owner}")
                                                    st.write(f"**Status:** {detail.status}")
                                                    st.write(f"**Consultant:** {detail.consultant}")

                                                    if detail.documents:
                                                        st.write("**📎 Documents:**")
                                                        for doc in detail.documents:
                                                            size_mb = doc.size_bytes / 1024 / 1024 if doc.size_bytes else 0
                                                            st.write(f"  - {doc.document_name} ({size_mb:.1f} MB) - {doc.comments or 'No description'}")
                                                else:
                                                    st.error("Failed to fetch permit details")

            except Exception as e:
                status.update(label="Scrape Failed", state="error")
                st.error(f"Error: {str(e)}")
                import traceback
                with st.expander("Full traceback"):
                    st.code(traceback.format_exc())


def test_scrape_url(url: str, method: str, format: str):
    """Test scraping a URL and display results."""
    with st.status(f"Scraping {url}...", expanded=True) as status:
        try:
            st.write(f"🔧 Using method: {method}")

            if method == "firecrawl":
                result = scrape_with_firecrawl(url, format)
            elif method == "requests":
                result = scrape_with_requests(url)
            else:
                st.warning(f"Method '{method}' not implemented, using requests")
                result = scrape_with_requests(url)

            status.update(label="Scrape Complete", state="complete", expanded=False)

            # Store in session state
            st.session_state["last_scrape_result"] = result

        except Exception as e:
            status.update(label="Scrape Failed", state="error")
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())
            return

    # Display results
    display_scrape_result(st.session_state.get("last_scrape_result"))


def scrape_with_firecrawl(url: str, format: str) -> dict:
    """Scrape URL using our FirecrawlClient wrapper."""
    from src.tools.firecrawl_client import FirecrawlClient

    client = FirecrawlClient()
    result = client.scrape_page(url, wait_ms=2000)

    return {
        "method": "firecrawl",
        "url": url,
        "success": result.success,
        "content": result.markdown or "",
        "metadata": result.metadata or {},
        "error": result.error,
        "raw": {
            "markdown": result.markdown[:2000] if result.markdown else "",
            "success": result.success,
            "error": result.error
        }
    }


def scrape_with_requests(url: str) -> dict:
    """Scrape URL using requests library."""
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AlachiaCivicIntel/1.0)"
    })
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract text content
    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text(separator='\n', strip=True)

    return {
        "method": "requests",
        "url": url,
        "content": text,
        "metadata": {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "title": soup.title.string if soup.title else None
        },
        "raw": response.text[:5000]  # Truncate raw HTML
    }


def display_scrape_result(result: dict):
    """Display scrape results."""
    if not result:
        return

    st.subheader("📄 Scrape Results")

    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Method", result.get("method", "N/A"))
    with col2:
        content = result.get("content", "")
        st.metric("Content Length", f"{len(content):,} chars")
    with col3:
        metadata = result.get("metadata", {})
        st.metric("Title", (metadata.get("title", "N/A") or "N/A")[:20] + "...")

    # Content preview
    st.subheader("Content Preview")

    content = result.get("content", "")

    # Show first 2000 chars with option to expand
    preview_length = st.slider(
        "Preview length (chars)",
        min_value=500,
        max_value=min(len(content), 10000),
        value=2000,
        step=500,
        key="preview_length"
    )

    st.text_area(
        "Extracted Content",
        value=content[:preview_length],
        height=400,
        key="content_preview"
    )

    # Metadata
    with st.expander("View Metadata"):
        st.json(result.get("metadata", {}))

    # Raw response (truncated)
    with st.expander("View Raw Response (truncated)"):
        raw = result.get("raw", "")
        if isinstance(raw, dict):
            st.json(raw)
        else:
            st.code(str(raw)[:5000], language="html")


def render_scout_analysis_tester():
    """Render the Scout Analysis testing section."""
    st.subheader("🔍 Scout Analysis Tester")
    st.caption("Test tiered Scout analysis on meetings from the database")

    # Check for database connection
    try:
        from src.database import get_db
        db = get_db()
    except ValueError as e:
        st.warning(f"Database not configured: {e}")
        st.info("Set SUPABASE_URL and SUPABASE_KEY in .env to test Scout analysis")
        return
    except Exception as e:
        st.error(f"Database error: {e}")
        return

    # Source selection
    source_id = st.selectbox(
        "Select Source",
        options=["civicclerk-alachuafl", "florida-public-notices"],
        key="scout_source"
    )

    # Fetch meetings from database
    if st.button("📥 Load Meetings from Database", key="load_meetings"):
        with st.spinner("Loading meetings..."):
            meetings = db.get_meetings_by_source(source_id)
            st.session_state['loaded_meetings'] = meetings
            st.success(f"Loaded {len(meetings)} meetings")

    # Display loaded meetings
    if 'loaded_meetings' in st.session_state and st.session_state['loaded_meetings']:
        meetings = st.session_state['loaded_meetings']

        st.write(f"**{len(meetings)} meetings loaded**")

        # Categorize meetings
        with_pdf = [m for m in meetings if m.get('pdf_content')]
        without_pdf = [m for m in meetings if not m.get('pdf_content')]
        analyzed = [m for m in meetings if m.get('last_analyzed_at')]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("With PDF Content", len(with_pdf))
        with col2:
            st.metric("Metadata Only", len(without_pdf))
        with col3:
            st.metric("Already Analyzed", len(analyzed))

        # Select meeting to analyze
        meeting_options = {
            f"{m.get('meeting_date', 'Unknown')[:10]} - {m.get('title', 'Unknown')[:40]}": m
            for m in meetings[:20]  # Limit to 20 for UI
        }

        selected_label = st.selectbox(
            "Select Meeting to Analyze",
            options=list(meeting_options.keys()),
            key="selected_meeting"
        )

        if selected_label:
            selected_meeting = meeting_options[selected_label]

            # Show meeting details
            with st.expander("Meeting Details", expanded=True):
                st.write(f"**Meeting ID:** `{selected_meeting.get('meeting_id')}`")
                st.write(f"**Title:** {selected_meeting.get('title')}")
                st.write(f"**Date:** {selected_meeting.get('meeting_date')}")
                st.write(f"**Board:** {selected_meeting.get('board', 'N/A')}")
                st.write(f"**Has PDF Content:** {'✅' if selected_meeting.get('pdf_content') else '❌'}")
                st.write(f"**Already Analyzed:** {'✅' if selected_meeting.get('last_analyzed_at') else '❌'}")

                if selected_meeting.get('pdf_content'):
                    st.write(f"**PDF Content Length:** {len(selected_meeting.get('pdf_content')):,} chars")
                    with st.expander("Preview PDF Content"):
                        st.text_area(
                            "PDF Content",
                            selected_meeting.get('pdf_content', '')[:3000],
                            height=200
                        )

            # Run Scout Analysis
            if st.button("🚀 Run Scout Analysis", type="primary", key="run_scout"):
                with st.status("Running Scout Analysis...", expanded=True) as status:
                    try:
                        from src.agents.scout import ScoutAgent

                        analysis_type = "PDF" if selected_meeting.get('pdf_content') else "Metadata"
                        st.write(f"📊 Analysis Type: **{analysis_type}**")

                        scout = ScoutAgent(name="scout-tester")
                        report = scout.analyze_meeting(selected_meeting)

                        status.update(label="Analysis Complete", state="complete", expanded=False)

                        # Display report
                        st.subheader("📋 Scout Report")

                        st.write(f"**Report ID:** `{report.report_id}`")
                        st.write(f"**Period Covered:** {report.period_covered}")
                        st.write(f"**Executive Summary:** {report.executive_summary}")

                        # Items
                        st.write(f"### Agenda Items ({len(report.items)})")
                        for item in report.items:
                            priority_icon = "🚨" if item.priority_flag else ""
                            sig_icon = {"routine": "⚪", "notable": "🟡", "critical": "🔴"}.get(item.significance.value, "⚪")

                            with st.expander(f"{sig_icon} {priority_icon} {item.agenda_id or 'N/A'}: {item.topic}"):
                                st.write(f"**Summary:** {item.summary}")
                                st.write(f"**Category:** {item.category.value}")
                                st.write(f"**Significance:** {item.significance.value}")
                                if item.related_to:
                                    st.write(f"**Related To:** {', '.join(item.related_to)}")
                                if item.priority_flag:
                                    st.warning(f"**Priority Reason:** {item.priority_reason}")
                                    st.write(f"**Watchlist Matches:** {', '.join(item.watchlist_matches)}")

                        # Alerts
                        if report.alerts:
                            st.write(f"### Alerts ({len(report.alerts)})")
                            for alert in report.alerts:
                                level_color = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(alert.level.value, "⚪")
                                st.write(f"{level_color} **{alert.title}**")
                                st.write(f"   {alert.description}")
                                if alert.action_required:
                                    st.write(f"   📌 Action: {alert.action_required}")

                        # Option to save to database
                        if st.button("💾 Save Report & Mark Analyzed", key="save_report"):
                            db.save_report(report)
                            db.mark_meeting_analyzed(
                                selected_meeting.get('meeting_id'),
                                source_id,
                                report.report_id
                            )
                            st.success("Report saved and meeting marked as analyzed!")

                    except Exception as e:
                        status.update(label="Analysis Failed", state="error")
                        st.error(f"Error: {str(e)}")
                        import traceback
                        with st.expander("Full traceback"):
                            st.code(traceback.format_exc())
