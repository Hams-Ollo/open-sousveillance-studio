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
    error_info = None

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

            result = agent.run({"url": url})

            st.write("✅ Analysis complete!")
            status.update(label="Scout Agent Complete", state="complete", expanded=False)

            # Store result in session state
            st.session_state["last_scout_result"] = result
            st.session_state["scout_error"] = None

        except Exception as e:
            import traceback
            error_info = {
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            status.update(label="Scout Agent Failed", state="error")
            st.session_state["scout_error"] = error_info

    # Display error outside of status block to avoid nested expander issue
    if error_info:
        st.error(f"Error: {error_info['message']}")
        with st.expander("Full traceback"):
            st.code(error_info['traceback'])
        return

    # Display results
    display_scout_result(st.session_state.get("last_scout_result"))


def run_analyst_agent(topic: str, save_to_db: bool, show_prompt: bool):
    """Execute an Analyst agent and display results."""
    error_info = None

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
            st.session_state["analyst_error"] = None

        except Exception as e:
            import traceback
            error_info = {
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            status.update(label="Analyst Agent Failed", state="error")
            st.session_state["analyst_error"] = error_info

    # Display error outside of status block to avoid nested expander issue
    if error_info:
        st.error(f"Error: {error_info['message']}")
        with st.expander("Full traceback"):
            st.code(error_info['traceback'])
        return

    # Display results
    display_analyst_result(st.session_state.get("last_analyst_result"))


def display_scout_result(result):
    """Display a ScoutReport in a formatted way."""
    if not result:
        return

    st.subheader("📋 Scout Report")

    # Executive Summary
    exec_summary = getattr(result, 'executive_summary', '')
    if exec_summary:
        st.info(exec_summary)

    # Summary metrics
    items = getattr(result, 'items', [])
    alerts = getattr(result, 'alerts', [])
    priority_items = [i for i in items if getattr(i, 'priority_flag', False)]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        urgency = getattr(result, 'urgency_level', None)
        urgency_str = urgency.value if hasattr(urgency, 'value') else str(urgency) if urgency else 'UNKNOWN'
        if urgency_str == "RED":
            st.metric("Urgency", urgency_str, delta="🔴", delta_color="inverse")
        elif urgency_str == "YELLOW":
            st.metric("Urgency", urgency_str, delta="🟡", delta_color="off")
        elif urgency_str == "GREEN":
            st.metric("Urgency", urgency_str, delta="🟢", delta_color="normal")
        else:
            st.metric("Urgency", urgency_str, delta="❓")

    with col2:
        st.metric("Total Items", len(items))

    with col3:
        st.metric("Priority Flagged", len(priority_items), delta="⚠️" if priority_items else None)

    with col4:
        st.metric("Alerts", len(alerts))

    # Alerts section
    if alerts:
        st.subheader("🚨 Alerts")
        for alert in alerts:
            level = getattr(alert, 'level', None)
            level_str = level.value if hasattr(level, 'value') else str(level) if level else 'UNKNOWN'
            action_item = getattr(alert, 'action_item', 'No action specified')
            context = getattr(alert, 'context', '')
            deadline = getattr(alert, 'deadline', None)

            if level_str == "RED":
                icon = "🔴"
            elif level_str == "YELLOW":
                icon = "🟡"
            else:
                icon = "🟢"

            with st.expander(f"{icon} **{level_str}** - {action_item[:50]}...", expanded=True):
                st.write(f"**Action:** {action_item}")
                st.write(f"**Context:** {context}")
                if deadline:
                    st.caption(f"Deadline: {deadline}")

    # Priority Items Section (if any)
    if priority_items:
        st.subheader("⚠️ Priority Items (Watchlist Matches)")
        for item in priority_items:
            _display_meeting_item(item, highlight=True)

    # All Items by Category
    if items:
        st.subheader("📑 All Agenda Items")

        # Group items by category
        from collections import defaultdict
        by_category = defaultdict(list)
        for item in items:
            cat = getattr(item, 'category', None)
            cat_str = cat.value if hasattr(cat, 'value') else str(cat) if cat else 'other'
            by_category[cat_str].append(item)

        # Display by category
        category_labels = {
            'budget_finance': '💰 Budget & Finance',
            'land_use': '🏗️ Land Use & Development',
            'public_safety': '🚔 Public Safety',
            'infrastructure': '🛣️ Infrastructure',
            'personnel': '👥 Personnel',
            'contracts': '📝 Contracts',
            'environment': '🌿 Environment',
            'public_hearing': '🎤 Public Hearing',
            'consent': '✅ Consent Agenda',
            'intergovernmental': '🏛️ Intergovernmental',
            'community': '🎉 Community',
            'other': '📋 Other',
        }

        for cat_key, cat_items in by_category.items():
            cat_label = category_labels.get(cat_key, f"📋 {cat_key.replace('_', ' ').title()}")
            with st.expander(f"{cat_label} ({len(cat_items)} items)", expanded=False):
                for item in cat_items:
                    _display_meeting_item(item, highlight=getattr(item, 'priority_flag', False))

    # Full report JSON
    with st.expander("View Raw Report JSON"):
        st.json(result.model_dump() if hasattr(result, 'model_dump') else str(result))


def _display_meeting_item(item, highlight: bool = False):
    """Display a single MeetingItem."""
    topic = getattr(item, 'topic', 'Unknown')
    summary = getattr(item, 'summary', '')
    significance = getattr(item, 'significance', None)
    sig_str = significance.value if hasattr(significance, 'value') else str(significance) if significance else 'routine'
    priority_reason = getattr(item, 'priority_reason', '')
    watchlist_matches = getattr(item, 'watchlist_matches', [])
    agenda_id = getattr(item, 'agenda_id', '')
    outcome = getattr(item, 'outcome', '')

    # Significance indicators
    sig_icons = {'routine': '⚪', 'notable': '🔵', 'critical': '🔴'}
    sig_icon = sig_icons.get(sig_str, '⚪')

    # Build title
    title_prefix = "🚨 " if highlight else ""
    agenda_prefix = f"[{agenda_id}] " if agenda_id else ""

    st.markdown(f"**{title_prefix}{agenda_prefix}{topic}** {sig_icon}")

    if summary:
        st.write(summary)

    if highlight and priority_reason:
        st.warning(f"**Priority:** {priority_reason}")

    if highlight and watchlist_matches:
        st.caption(f"Matches: {', '.join(watchlist_matches)}")

    if outcome:
        st.caption(f"Outcome: {outcome}")

    st.divider()


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
