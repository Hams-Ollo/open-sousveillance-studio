"""
Agent Runner Page - Execute and test agents interactively.
"""

import streamlit as st
import json
from datetime import datetime


def render():
    """Render the Agent Runner tab."""
    st.header("🤖 Agent Runner")
    st.caption("Execute Scout and Analyst agents with custom inputs")
    
    # Agent selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        agent_type = st.selectbox(
            "Select Agent Type",
            options=["Scout (Layer 1)", "Analyst (Layer 2)"],
            key="agent_type"
        )
    
    with col2:
        if "Scout" in agent_type:
            agent_id = st.selectbox(
                "Select Agent",
                options=[
                    "A1 - Meeting Intelligence Scout",
                    "A2 - Permit Application Scout", 
                    "A3 - Legislative/Code Monitor",
                    "A4 - Public Records Scout"
                ],
                key="scout_agent"
            )
        else:
            agent_id = st.selectbox(
                "Select Agent",
                options=[
                    "B1 - Impact Assessment Analyst",
                    "B2 - Procedural Integrity Analyst"
                ],
                key="analyst_agent"
            )
    
    st.divider()
    
    # Input configuration based on agent type
    if "Scout" in agent_type:
        render_scout_inputs()
    else:
        render_analyst_inputs()


def render_scout_inputs():
    """Render inputs for Scout agents."""
    st.subheader("Scout Configuration")
    
    # URL input
    url = st.text_input(
        "Target URL",
        placeholder="https://alachua.legistar.com/...",
        help="The URL to scrape and analyze",
        key="scout_url"
    )
    
    # Optional: Select from known sources
    with st.expander("Or select from known sources"):
        st.info("Sources from config/sources.yaml will appear here")
        # TODO: Load sources from config
    
    # Additional options
    col1, col2 = st.columns(2)
    with col1:
        save_to_db = st.checkbox("Save report to Supabase", value=False, key="scout_save")
    with col2:
        show_prompt = st.checkbox("Show generated prompt", value=True, key="scout_show_prompt")
    
    st.divider()
    
    # Run button
    if st.button("▶️ Run Scout Agent", type="primary", use_container_width=True):
        if not url:
            st.error("Please enter a URL to analyze")
            return
        
        run_scout_agent(url, save_to_db, show_prompt)


def render_analyst_inputs():
    """Render inputs for Analyst agents."""
    st.subheader("Analyst Configuration")
    
    # Topic input
    topic = st.text_area(
        "Research Topic",
        placeholder="e.g., Mill Creek Sink development environmental impact",
        help="The topic for deep research and analysis",
        key="analyst_topic",
        height=100
    )
    
    # Additional context
    with st.expander("Additional Context (optional)"):
        context = st.text_area(
            "Background information",
            placeholder="Any additional context to provide to the analyst...",
            key="analyst_context",
            height=150
        )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        save_to_db = st.checkbox("Save report to Supabase", value=False, key="analyst_save")
    with col2:
        show_prompt = st.checkbox("Show generated prompt", value=True, key="analyst_show_prompt")
    
    st.divider()
    
    # Run button
    if st.button("▶️ Run Analyst Agent", type="primary", use_container_width=True):
        if not topic:
            st.error("Please enter a research topic")
            return
        
        run_analyst_agent(topic, save_to_db, show_prompt)


def run_scout_agent(url: str, save_to_db: bool, show_prompt: bool):
    """Execute a Scout agent and display results."""
    with st.status("Running Scout Agent...", expanded=True) as status:
        try:
            st.write("🔍 Fetching content from URL...")
            
            # Import here to avoid circular imports and show import errors
            from src.agents.scout import ScoutAgent
            from src.tools import monitor_url
            
            st.write("📊 Analyzing content with Gemini...")
            
            # Create and run agent
            agent = ScoutAgent(
                name=st.session_state.get("scout_agent", "A1").split(" - ")[0],
                prompt_template="Standard Scout Prompt"
            )
            
            # Show the prompt if requested
            if show_prompt:
                st.write("📝 Generated prompt:")
                # We'll capture the prompt in the agent execution
            
            result = agent.run({"url": url})
            
            st.write("✅ Analysis complete!")
            status.update(label="Scout Agent Complete", state="complete", expanded=False)
            
            # Store result in session state
            st.session_state["last_scout_result"] = result
            
        except Exception as e:
            status.update(label="Scout Agent Failed", state="error")
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())
            return
    
    # Display results
    display_scout_result(st.session_state.get("last_scout_result"))


def run_analyst_agent(topic: str, save_to_db: bool, show_prompt: bool):
    """Execute an Analyst agent and display results."""
    with st.status("Running Analyst Agent...", expanded=True) as status:
        try:
            st.write("🔬 Conducting deep research...")
            
            # Import here to avoid circular imports
            from src.agents.analyst import AnalystAgent
            
            st.write("📊 Analyzing findings with Gemini...")
            
            # Create and run agent
            agent = AnalystAgent(
                name=st.session_state.get("analyst_agent", "B1").split(" - ")[0]
            )
            
            result = agent.run({"topic": topic})
            
            st.write("✅ Analysis complete!")
            status.update(label="Analyst Agent Complete", state="complete", expanded=False)
            
            # Store result in session state
            st.session_state["last_analyst_result"] = result
            
        except Exception as e:
            status.update(label="Analyst Agent Failed", state="error")
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())
            return
    
    # Display results
    display_analyst_result(st.session_state.get("last_analyst_result"))


def display_scout_result(result):
    """Display a ScoutReport in a formatted way."""
    if not result:
        return
    
    st.subheader("📋 Scout Report")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        urgency = getattr(result, 'urgency_level', 'UNKNOWN')
        if urgency == "HIGH":
            st.metric("Urgency", urgency, delta="⚠️", delta_color="inverse")
        elif urgency == "MEDIUM":
            st.metric("Urgency", urgency, delta="📊")
        else:
            st.metric("Urgency", urgency, delta="✓", delta_color="normal")
    
    with col2:
        alerts = getattr(result, 'alerts', [])
        st.metric("Alerts", len(alerts))
    
    with col3:
        st.metric("Report ID", getattr(result, 'report_id', 'N/A')[:8] + "...")
    
    # Alerts section
    if alerts:
        st.subheader("🚨 Alerts")
        for alert in alerts:
            with st.expander(f"**{alert.title}** - {alert.urgency}", expanded=True):
                st.write(alert.description)
                if alert.keywords_matched:
                    st.caption(f"Keywords: {', '.join(alert.keywords_matched)}")
    
    # Full report JSON
    with st.expander("View Raw Report JSON"):
        st.json(result.model_dump() if hasattr(result, 'model_dump') else str(result))


def display_analyst_result(result):
    """Display an AnalystReport in a formatted way."""
    if not result:
        return
    
    st.subheader("📋 Analyst Report")
    
    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Report ID", getattr(result, 'report_id', 'N/A')[:8] + "...")
    with col2:
        st.metric("Topic", getattr(result, 'topic', 'N/A')[:30] + "...")
    
    # Analysis content
    if hasattr(result, 'analysis'):
        st.subheader("Analysis")
        st.write(result.analysis)
    
    # Recommendations
    if hasattr(result, 'recommendations') and result.recommendations:
        st.subheader("Recommendations")
        for rec in result.recommendations:
            st.write(f"• {rec}")
    
    # Full report JSON
    with st.expander("View Raw Report JSON"):
        st.json(result.model_dump() if hasattr(result, 'model_dump') else str(result))
