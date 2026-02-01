"""
Orchestrator Control Panel - Streamlit UI
==========================================

Provides a visual interface for:
- Viewing configured sources and their status
- Running the pipeline manually
- Monitoring job progress
- Viewing run history and results
"""

import streamlit as st
from datetime import datetime
from typing import Optional

from src.logging_config import get_logger

logger = get_logger("ui.orchestrator")


def render():
    """Render the Orchestrator control panel."""
    st.header("🎯 Orchestrator Control Panel")

    st.markdown("""
    The Orchestrator coordinates scraping, analysis, and reporting across all data sources.
    Use this panel to monitor status, run jobs manually, and view results.
    """)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "▶️ Run Pipeline", "📜 History"])

    with tab1:
        render_dashboard()

    with tab2:
        render_run_panel()

    with tab3:
        render_history()


def render_dashboard():
    """Render the main dashboard with source status."""
    st.subheader("Source Status")

    try:
        from src.orchestrator import Orchestrator

        # Initialize orchestrator (cached)
        if 'orchestrator' not in st.session_state:
            with st.spinner("Initializing Orchestrator..."):
                st.session_state['orchestrator'] = Orchestrator()

        orchestrator = st.session_state['orchestrator']

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        total_sources = len(orchestrator.sources)
        due_sources = orchestrator.get_due_sources()

        with col1:
            st.metric("Total Sources", total_sources)
        with col2:
            st.metric("Due for Check", len(due_sources))
        with col3:
            st.metric("Scrapers Ready", len(orchestrator.scrapers))
        with col4:
            # Count by priority
            critical = len([s for s in orchestrator.sources.values() if s.priority == "critical"])
            st.metric("Critical Priority", critical)

        # Source list
        st.subheader("📋 Configured Sources")

        # Group by scraper availability
        sources_with_scraper = []
        sources_without_scraper = []

        for source_id, source in orchestrator.sources.items():
            scraper = orchestrator._get_scraper_for_source(source)
            if scraper:
                sources_with_scraper.append((source_id, source))
            else:
                sources_without_scraper.append((source_id, source))

        # Show sources with scrapers
        st.write("### ✅ Active Sources (Scraper Available)")
        for source_id, source in sources_with_scraper:
            is_due = source in due_sources
            due_badge = "🔴 DUE" if is_due else "🟢 OK"

            with st.expander(f"{due_badge} {source.name} (`{source_id}`)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Priority:** {source.priority}")
                    st.write(f"**Frequency:** {source.check_frequency}")
                with col2:
                    st.write(f"**Platform:** {source.platform}")
                    st.write(f"**URL:** [{source.url}]({source.url})")

                if source.document_types:
                    st.write(f"**Document Types:** {', '.join(source.document_types)}")

        # Show sources without scrapers
        if sources_without_scraper:
            st.write("### ⏸️ Inactive Sources (No Scraper)")
            for source_id, source in sources_without_scraper[:10]:  # Limit display
                st.write(f"- `{source_id}` - {source.name}")

            if len(sources_without_scraper) > 10:
                st.write(f"  ... and {len(sources_without_scraper) - 10} more")

    except Exception as e:
        st.error(f"Failed to load Orchestrator: {str(e)}")
        import traceback
        with st.expander("Full traceback"):
            st.code(traceback.format_exc())


def render_run_panel():
    """Render the pipeline run controls."""
    st.subheader("Run Pipeline")

    try:
        from src.orchestrator import Orchestrator

        if 'orchestrator' not in st.session_state:
            st.warning("Please visit the Dashboard tab first to initialize the Orchestrator.")
            return

        orchestrator = st.session_state['orchestrator']

        # Source selection
        st.write("### Select Sources")

        run_mode = st.radio(
            "Run Mode",
            options=["Due Sources Only", "All Active Sources", "Select Specific"],
            horizontal=True
        )

        selected_sources = []

        if run_mode == "Select Specific":
            # Get sources with scrapers
            available_sources = [
                source_id for source_id, source in orchestrator.sources.items()
                if orchestrator._get_scraper_for_source(source)
            ]

            selected_sources = st.multiselect(
                "Sources to Run",
                options=available_sources,
                default=[]
            )

        # Options
        st.write("### Options")
        col1, col2 = st.columns(2)

        with col1:
            skip_analysis = st.checkbox(
                "Skip Analysis",
                value=False,
                help="Skip Scout Agent analysis (faster, discovery only)"
            )

        with col2:
            force_run = st.checkbox(
                "Force Run",
                value=False,
                help="Run even if sources are not due"
            )

        # Run button
        st.write("---")

        if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
            pipeline_result = None
            pipeline_error = None

            with st.status("Running Pipeline...", expanded=True) as status:
                try:
                    # Determine source IDs
                    if run_mode == "Select Specific":
                        source_ids = selected_sources if selected_sources else None
                    elif run_mode == "All Active Sources":
                        source_ids = [
                            sid for sid, s in orchestrator.sources.items()
                            if orchestrator._get_scraper_for_source(s)
                        ]
                    else:
                        source_ids = None  # Will use due sources

                    st.write(f"📋 Sources to run: {source_ids or 'Due sources'}")
                    st.write(f"⏭️ Skip analysis: {skip_analysis}")
                    st.write(f"💪 Force run: {force_run}")

                    # Run pipeline
                    pipeline_result = orchestrator.run_pipeline(
                        source_ids=source_ids,
                        skip_analysis=skip_analysis,
                        force=force_run or (run_mode == "All Active Sources")
                    )

                    # Store result
                    if 'pipeline_runs' not in st.session_state:
                        st.session_state['pipeline_runs'] = []
                    st.session_state['pipeline_runs'].append(pipeline_result)

                    status.update(label="Pipeline Complete!", state="complete")

                except Exception as e:
                    status.update(label="Pipeline Failed", state="error")
                    pipeline_error = str(e)
                    import traceback
                    pipeline_error_trace = traceback.format_exc()

            # Show results OUTSIDE the status block to avoid nested expanders
            if pipeline_result:
                st.success(f"Pipeline completed: {pipeline_result.successful_jobs}/{len(pipeline_result.jobs)} jobs successful")

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Items Discovered", pipeline_result.total_discovered)
                with col2:
                    st.metric("New Items", pipeline_result.total_new)
                with col3:
                    st.metric("Analyzed", pipeline_result.total_analyzed)

                # Job details
                st.write("### Job Results")
                for job in pipeline_result.jobs:
                    status_emoji = "✅" if job.status.value == "completed" else "❌"
                    with st.expander(f"{status_emoji} {job.source_id}"):
                        st.write(f"**Status:** {job.status.value}")
                        st.write(f"**Duration:** {job.duration_seconds:.1f}s")
                        st.write(f"**Discovered:** {job.items_discovered}")
                        st.write(f"**New:** {job.items_new}")
                        st.write(f"**Analyzed:** {job.items_analyzed}")
                        if job.error:
                            st.error(f"Error: {job.error}")

            elif pipeline_error:
                st.error(f"Pipeline failed: {pipeline_error}")
                with st.expander("Full traceback"):
                    st.code(pipeline_error_trace)

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_history():
    """Render pipeline run history."""
    st.subheader("Run History")

    runs = st.session_state.get('pipeline_runs', [])

    if not runs:
        st.info("No pipeline runs yet. Use the 'Run Pipeline' tab to start a run.")
        return

    st.write(f"**Total Runs:** {len(runs)}")

    # Show runs in reverse chronological order
    for i, run in enumerate(reversed(runs)):
        run_num = len(runs) - i

        with st.expander(f"Run #{run_num}: {run.run_id}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Started:** {run.started_at.strftime('%H:%M:%S')}")
                if run.completed_at:
                    duration = (run.completed_at - run.started_at).total_seconds()
                    st.write(f"**Duration:** {duration:.1f}s")

            with col2:
                st.write(f"**Jobs:** {len(run.jobs)}")
                st.write(f"**Successful:** {run.successful_jobs}")
                st.write(f"**Failed:** {run.failed_jobs}")

            with col3:
                st.write(f"**Discovered:** {run.total_discovered}")
                st.write(f"**New:** {run.total_new}")
                st.write(f"**Analyzed:** {run.total_analyzed}")

            # Job breakdown
            st.write("**Jobs:**")
            for job in run.jobs:
                status_emoji = "✅" if job.status.value == "completed" else "❌"
                st.write(f"  {status_emoji} {job.source_id}: {job.items_new} new")


if __name__ == "__main__":
    render()
