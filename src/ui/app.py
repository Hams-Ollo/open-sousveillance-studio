"""
Alachua Civic Intelligence - Developer Console

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
from src.ui.pages import agent_runner, prompt_inspector, source_tester, config_viewer


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
        st.caption("Alachua Civic Intelligence System")
        
        st.divider()
        
        # Environment Status
        st.subheader("Environment Status")
        api_keys = check_api_keys()
        
        for key, configured in api_keys.items():
            if configured:
                st.success(f"✓ {key}", icon="✅")
            else:
                st.warning(f"✗ {key}", icon="⚠️")
        
        st.divider()
        
        # Quick Links
        st.subheader("Quick Links")
        st.page_link("https://alachua.legistar.com/Calendar.aspx", label="Legistar Calendar", icon="📅")
        st.page_link("https://alachuacounty.us/", label="Alachua County", icon="🏛️")
        
        st.divider()
        
        # Version info
        st.caption("Version: 0.1.0-dev")
        st.caption(f"Project: {PROJECT_ROOT.name}")


def main():
    """Main application entry point."""
    render_sidebar()
    
    # Main content area with tabs
    st.title("🔬 Alachua Civic Intelligence - Developer Console")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 Agent Runner",
        "📝 Prompt Inspector", 
        "🌐 Source Tester",
        "⚙️ Config Viewer"
    ])
    
    with tab1:
        agent_runner.render()
    
    with tab2:
        prompt_inspector.render()
    
    with tab3:
        source_tester.render()
    
    with tab4:
        config_viewer.render()


if __name__ == "__main__":
    main()
