"""
Open Sousveillance Studio - Developer Console

A Streamlit-based testing and debugging interface for the civic intelligence system.

Run with: streamlit run src/ui/app.py
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Alachua Civic Intel - Dev Console",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import page modules
from src.ui.pages import agent_runner, prompt_inspector, source_tester, config_viewer, orchestrator_panel, health_dashboard


def check_api_keys() -> dict:
    """Check which API keys are configured."""
    return {
        "GOOGLE_API_KEY": bool(os.getenv("GOOGLE_API_KEY")),
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.getenv("SUPABASE_KEY")),
        "TAVILY_API_KEY": bool(os.getenv("TAVILY_API_KEY")),
        "FIRECRAWL_API_KEY": bool(os.getenv("FIRECRAWL_API_KEY")),
    }


def render_sidebar():
    """Render the sidebar with environment status and settings."""
    with st.sidebar:
        st.title("🔬 Dev Console")
        st.caption("Alachua Civic Intelligence Reporting Studio")

        st.divider()

        # Environment Status
        st.subheader("🔑 Environment Status")
        api_keys = check_api_keys()

        for key, configured in api_keys.items():
            if configured:
                st.success(f"✓ {key}", icon="✅")
            else:
                st.warning(f"✗ {key}", icon="⚠️")

        st.divider()

        # Target Data Sources - the URLs we're actively scraping
        st.subheader("🎯 Target Data Sources")

        st.markdown("**Municipal Meetings**")
        st.link_button(
            "📅 CivicClerk Portal",
            "https://alachuafl.portal.civicclerk.com/",
            use_container_width=True
        )

        st.markdown("**Public Notices**")
        st.link_button(
            "📰 Florida Public Notices",
            "https://floridapublicnotices.com/",
            use_container_width=True
        )

        st.markdown("**SRWMD Permits**")
        st.link_button(
            "📝 Permit Applications",
            "https://www.mysuwanneeriver.com/1616/Notice-of-Receipt-of-Applications",
            use_container_width=True
        )
        st.link_button(
            "✅ Permit Issuances",
            "https://www.mysuwanneeriver.com/1617/Notice-of-Permit-Issuance",
            use_container_width=True
        )

        st.divider()

        # Version info
        try:
            from src import __version__
            st.caption(f"Version: {__version__}")
        except ImportError:
            st.caption("Version: unknown")
        st.caption(f"Project: {PROJECT_ROOT.name}")


def main():
    """Main application entry point."""
    render_sidebar()

    # Main content area with tabs
    st.title("🔬 Open Sousveillance Studio - Developer Console")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎯 Orchestrator",
        "🏥 Health",
        "🤖 Agent Runner",
        "📝 Prompt Inspector",
        "🌐 Source Tester",
        "⚙️ Config Viewer"
    ])

    with tab1:
        orchestrator_panel.render()

    with tab2:
        health_dashboard.render()

    with tab3:
        agent_runner.render()

    with tab4:
        prompt_inspector.render()

    with tab5:
        source_tester.render()

    with tab6:
        config_viewer.render()


if __name__ == "__main__":
    main()
