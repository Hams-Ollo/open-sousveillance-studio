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
    st.caption("Test web scraping and content extraction from data sources")
    
    # Load sources
    try:
        sources_config = load_sources_config()
        sources_by_tier = get_sources_by_tier(sources_config)
    except Exception as e:
        st.error(f"Error loading sources: {e}")
        sources_by_tier = {}
    
    # Two modes: select from config or enter custom URL
    mode = st.radio(
        "Source Selection",
        options=["Select from Config", "Custom URL"],
        horizontal=True,
        key="source_mode"
    )
    
    if mode == "Select from Config":
        render_config_source_selector(sources_by_tier)
    else:
        render_custom_url_tester()


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
    
    scrape_method = source.get('scraping_method', 'firecrawl')
    test_scrape_url(url, scrape_method, "markdown")


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
    """Scrape URL using Firecrawl."""
    import os
    
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not configured")
    
    from firecrawl import FirecrawlApp
    
    client = FirecrawlApp(api_key=api_key)
    result = client.scrape_url(url, params={"formats": [format]})
    
    return {
        "method": "firecrawl",
        "url": url,
        "content": result.get(format, result.get("markdown", "")),
        "metadata": result.get("metadata", {}),
        "raw": result
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
