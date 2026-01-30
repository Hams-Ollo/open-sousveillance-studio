"""
Config Viewer Page - View and inspect configuration files.
"""

import streamlit as st
import yaml
from pathlib import Path


@st.cache_data
def load_yaml_file(filepath: str) -> dict:
    """Load a YAML configuration file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data
def get_config_files() -> list:
    """Get all config files."""
    from src.config import CONFIG_DIR
    
    config_files = []
    if CONFIG_DIR.exists():
        config_files.extend(CONFIG_DIR.glob("*.yaml"))
        config_files.extend(CONFIG_DIR.glob("*.yml"))
    
    return sorted(config_files)


def render():
    """Render the Config Viewer tab."""
    st.header("⚙️ Config Viewer")
    st.caption("View and inspect YAML configuration files")
    
    # Get config files
    try:
        config_files = get_config_files()
    except Exception as e:
        st.error(f"Error loading config files: {e}")
        config_files = []
    
    if not config_files:
        st.warning("No configuration files found in config/")
        return
    
    # File selection
    selected_file = st.selectbox(
        "Select Configuration File",
        options=config_files,
        format_func=lambda x: x.name,
        key="config_file"
    )
    
    if selected_file:
        display_config_file(selected_file)
    
    st.divider()
    
    # Environment variables section
    render_env_vars_section()


def display_config_file(filepath: Path):
    """Display the content of a config file."""
    st.subheader(f"📄 {filepath.name}")
    
    # File info
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Path: {filepath}")
    with col2:
        try:
            size = filepath.stat().st_size
            st.caption(f"Size: {size:,} bytes")
        except:
            pass
    
    # Load and display
    config_data = load_yaml_file(str(filepath))
    
    if "error" in config_data:
        st.error(f"Error loading file: {config_data['error']}")
        return
    
    # View mode
    view_mode = st.radio(
        "View Mode",
        options=["Tree View", "Raw YAML", "JSON"],
        horizontal=True,
        key="config_view_mode"
    )
    
    if view_mode == "Tree View":
        render_tree_view(config_data)
    elif view_mode == "Raw YAML":
        # Read raw file content
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        st.code(raw_content, language="yaml", line_numbers=True)
    else:
        st.json(config_data)


def render_tree_view(data: dict, level: int = 0):
    """Render config data as a tree view without nested expanders."""
    indent = "  " * level
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                st.markdown(f"{indent}**{key}:**")
                render_tree_view(value, level + 1)
            elif isinstance(value, list):
                st.markdown(f"{indent}**{key}:** ({len(value)} items)")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        name = item.get('name', item.get('id', f'Item {i}'))
                        with st.expander(f"{indent}  {name}", expanded=False):
                            for k, v in item.items():
                                if not isinstance(v, (dict, list)):
                                    st.write(f"**{k}:** {v}")
                                else:
                                    st.write(f"**{k}:** {type(v).__name__}")
                    else:
                        st.write(f"{indent}  • {item}")
            else:
                st.write(f"{indent}**{key}:** {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                name = item.get('name', item.get('id', f'Item {i}'))
                with st.expander(f"{name}", expanded=False):
                    for k, v in item.items():
                        if not isinstance(v, (dict, list)):
                            st.write(f"**{k}:** {v}")
                        else:
                            st.write(f"**{k}:** {type(v).__name__}")
            else:
                st.write(f"• {item}")
    else:
        st.write(data)


def render_env_vars_section():
    """Render environment variables section."""
    st.subheader("🔐 Environment Variables")
    st.caption("Current environment configuration (values hidden for security)")
    
    import os
    
    # List of relevant env vars to check
    env_vars = [
        ("GOOGLE_API_KEY", "Google Gemini API"),
        ("SUPABASE_URL", "Supabase URL"),
        ("SUPABASE_KEY", "Supabase Key"),
        ("TAVILY_API_KEY", "Tavily Search API"),
        ("FIRECRAWL_API_KEY", "Firecrawl API"),
        ("CELERY_BROKER_URL", "Celery Broker"),
        ("CELERY_RESULT_BACKEND", "Celery Backend"),
        ("LOG_LEVEL", "Log Level"),
        ("LOG_FORMAT", "Log Format"),
        ("HOST", "Server Host"),
        ("PORT", "Server Port"),
    ]
    
    # Create a table
    data = []
    for var_name, description in env_vars:
        value = os.getenv(var_name)
        if value:
            # Mask the value for security
            if "KEY" in var_name or "SECRET" in var_name:
                display_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            elif "URL" in var_name:
                display_value = value[:30] + "..." if len(value) > 30 else value
            else:
                display_value = value
            status = "✅ Set"
        else:
            display_value = "-"
            status = "⚠️ Not Set"
        
        data.append({
            "Variable": var_name,
            "Description": description,
            "Status": status,
            "Value": display_value
        })
    
    # Display as dataframe
    import pandas as pd
    df = pd.DataFrame(data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Variable": st.column_config.TextColumn("Variable", width="medium"),
            "Description": st.column_config.TextColumn("Description", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Value": st.column_config.TextColumn("Value", width="medium"),
        }
    )
    
    # .env file check
    from src.config import BASE_DIR
    env_file = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"
    
    col1, col2 = st.columns(2)
    with col1:
        if env_file.exists():
            st.success("✓ .env file exists")
        else:
            st.warning("⚠️ .env file not found")
    with col2:
        if env_example.exists():
            st.info("📄 .env.example available")
