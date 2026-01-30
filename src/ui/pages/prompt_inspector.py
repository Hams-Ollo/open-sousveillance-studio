"""
Prompt Inspector Page - View and debug prompts sent to LLMs.
"""

import streamlit as st
from pathlib import Path


@st.cache_data
def load_prompt_file(filepath: str) -> str:
    """Load a prompt file from the prompt library."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading file: {e}"


@st.cache_data
def get_prompt_files() -> dict:
    """Get all prompt files from the prompt library."""
    from src.config import PROMPT_LIB_DIR
    
    prompt_files = {}
    
    # Config files
    config_dir = PROMPT_LIB_DIR / "config"
    if config_dir.exists():
        prompt_files["Config"] = list(config_dir.glob("*.md"))
    
    # Layer 1 - Scouts
    scouts_dir = PROMPT_LIB_DIR / "layer-1-scouts"
    if scouts_dir.exists():
        prompt_files["Layer 1 - Scouts"] = list(scouts_dir.glob("*.md"))
    
    # Layer 2 - Analysts
    analysts_dir = PROMPT_LIB_DIR / "layer-2-analysts"
    if analysts_dir.exists():
        prompt_files["Layer 2 - Analysts"] = list(analysts_dir.glob("*.md"))
    
    return prompt_files


def render():
    """Render the Prompt Inspector tab."""
    st.header("📝 Prompt Inspector")
    st.caption("View and debug prompts from the prompt library")
    
    # Get prompt files
    try:
        prompt_files = get_prompt_files()
    except Exception as e:
        st.error(f"Error loading prompt files: {e}")
        return
    
    if not prompt_files:
        st.warning("No prompt files found in prompt_library/")
        return
    
    # Category selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        category = st.selectbox(
            "Category",
            options=list(prompt_files.keys()),
            key="prompt_category"
        )
    
    with col2:
        files_in_category = prompt_files.get(category, [])
        if files_in_category:
            selected_file = st.selectbox(
                "Prompt File",
                options=files_in_category,
                format_func=lambda x: x.name,
                key="prompt_file"
            )
        else:
            st.info("No files in this category")
            return
    
    st.divider()
    
    # Display prompt content
    if selected_file:
        display_prompt_content(selected_file)
    
    st.divider()
    
    # Context preview section
    render_context_preview()


def display_prompt_content(filepath: Path):
    """Display the content of a prompt file."""
    content = load_prompt_file(str(filepath))
    
    # File info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File", filepath.name)
    with col2:
        st.metric("Size", f"{len(content):,} chars")
    with col3:
        st.metric("Lines", content.count('\n') + 1)
    
    # Content display with syntax highlighting
    st.subheader(f"📄 {filepath.name}")
    
    # Show as markdown or code
    view_mode = st.radio(
        "View Mode",
        options=["Rendered Markdown", "Raw Text"],
        horizontal=True,
        key="prompt_view_mode"
    )
    
    if view_mode == "Rendered Markdown":
        with st.container(height=500):
            st.markdown(content)
    else:
        st.code(content, language="markdown", line_numbers=True)


def render_context_preview():
    """Preview the context that gets injected into agent prompts."""
    st.subheader("🔧 Agent Context Preview")
    st.caption("This is the context that gets injected into agent prompts at runtime")
    
    with st.expander("View Injected Context", expanded=False):
        try:
            from src.prompts import get_alachua_context
            
            context = get_alachua_context()
            
            # Display context components
            tab1, tab2, tab3, tab4 = st.tabs([
                "Full Context", 
                "Keywords", 
                "Entities",
                "Behavioral Standards"
            ])
            
            with tab1:
                st.code(context.get_prompt_context(), language="markdown")
            
            with tab2:
                keywords = context.priority_keywords
                if keywords:
                    st.write("**Priority Keywords:**")
                    cols = st.columns(3)
                    for i, kw in enumerate(keywords):
                        cols[i % 3].write(f"• {kw}")
                else:
                    st.info("No keywords loaded")
            
            with tab3:
                entities_str = context.get_entities_string()
                if entities_str:
                    st.write("**Tracked Entities:**")
                    st.text(entities_str)
                else:
                    st.info("No entities loaded")
            
            with tab4:
                if context.behavioral_standards:
                    st.markdown(context.behavioral_standards)
                else:
                    st.info("No behavioral standards loaded")
                    
        except Exception as e:
            st.error(f"Error loading context: {e}")
            import traceback
            st.code(traceback.format_exc())
