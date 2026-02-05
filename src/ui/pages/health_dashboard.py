"""
Scraper Health Dashboard for Open Sousveillance Studio.

Displays real-time health status of all scrapers with:
- Status overview (healthy/degraded/failing counts)
- Per-scraper metrics table
- Recent alerts
- Health history charts
"""

import streamlit as st
from datetime import datetime, timedelta

from src.intelligence.health import get_health_service, HealthStatus
from src.logging_config import get_logger

logger = get_logger("ui.health_dashboard")


def render():
    """Render the health dashboard page."""
    st.header("🏥 Scraper Health Dashboard")
    
    # Get health service
    health_service = get_health_service()
    summary = health_service.get_summary()
    
    # Status overview cards
    st.subheader("Status Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    status_counts = summary.get("status_counts", {})
    
    with col1:
        healthy_count = status_counts.get("healthy", 0)
        st.metric(
            label="✅ Healthy",
            value=healthy_count,
            delta=None
        )
    
    with col2:
        degraded_count = status_counts.get("degraded", 0)
        st.metric(
            label="⚠️ Degraded",
            value=degraded_count,
            delta=None
        )
    
    with col3:
        failing_count = status_counts.get("failing", 0)
        st.metric(
            label="❌ Failing",
            value=failing_count,
            delta=None
        )
    
    with col4:
        unknown_count = status_counts.get("unknown", 0)
        st.metric(
            label="❓ Unknown",
            value=unknown_count,
            delta=None
        )
    
    # Scrapers needing attention
    needs_attention = summary.get("scrapers_needing_attention", [])
    if needs_attention:
        st.error(f"🚨 **{len(needs_attention)} scraper(s) need attention:** {', '.join(needs_attention)}")
    
    st.divider()
    
    # Scraper details table
    st.subheader("Scraper Status")
    
    scrapers = summary.get("scrapers", [])
    
    if not scrapers:
        st.info("No scraper health data yet. Run some scrapers to see health metrics.")
    else:
        # Build table data
        table_data = []
        for scraper in scrapers:
            status = scraper.get("status", "unknown")
            status_icon = {
                "healthy": "✅",
                "degraded": "⚠️",
                "failing": "❌",
                "unknown": "❓"
            }.get(status, "❓")
            
            last_attempt = scraper.get("last_attempt")
            if last_attempt:
                try:
                    last_dt = datetime.fromisoformat(last_attempt)
                    time_ago = datetime.now() - last_dt
                    if time_ago.total_seconds() < 60:
                        last_str = "Just now"
                    elif time_ago.total_seconds() < 3600:
                        last_str = f"{int(time_ago.total_seconds() / 60)} min ago"
                    elif time_ago.total_seconds() < 86400:
                        last_str = f"{int(time_ago.total_seconds() / 3600)} hrs ago"
                    else:
                        last_str = f"{int(time_ago.total_seconds() / 86400)} days ago"
                except:
                    last_str = last_attempt
            else:
                last_str = "Never"
            
            table_data.append({
                "Scraper": scraper.get("scraper_id", "Unknown"),
                "Status": f"{status_icon} {status.title()}",
                "Success Rate": f"{scraper.get('success_rate', 0):.1f}%",
                "Avg Duration": f"{scraper.get('avg_duration_ms', 0):.0f}ms",
                "Failures": scraper.get("consecutive_failures", 0),
                "Last Run": last_str,
            })
        
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True
        )
    
    st.divider()
    
    # Alerts section
    st.subheader("Recent Alerts")
    
    alerts = health_service.get_alerts()
    
    if not alerts:
        st.success("No pending alerts")
    else:
        for alert in reversed(alerts[-10:]):  # Show last 10
            is_degradation = alert.current_status.value in ["degraded", "failing"]
            
            if is_degradation:
                st.warning(f"⚠️ **{alert.scraper_id}**: {alert.message}")
            else:
                st.success(f"✅ **{alert.scraper_id}**: {alert.message}")
        
        if st.button("Clear Alerts"):
            health_service.clear_alerts()
            st.rerun()
    
    st.divider()
    
    # Scraper detail expanders
    st.subheader("Scraper Details")
    
    all_health = health_service.get_all_health()
    
    for scraper_id, health in all_health.items():
        status_icon = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.FAILING: "❌",
            HealthStatus.UNKNOWN: "❓"
        }.get(health.status, "❓")
        
        with st.expander(f"{status_icon} {scraper_id}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Success Rate", f"{health.success_rate * 100:.1f}%")
            with col2:
                st.metric("Avg Duration", f"{health.avg_duration_ms:.0f}ms")
            with col3:
                st.metric("Total Attempts", health.total_attempts)
            
            # Recent attempts
            if health.attempts:
                st.write("**Recent Attempts:**")
                attempt_data = []
                for attempt in health.attempts[-10:]:
                    attempt_data.append({
                        "Time": attempt.timestamp.strftime("%Y-%m-%d %H:%M"),
                        "Status": "✅ Success" if attempt.success else "❌ Failed",
                        "Items": attempt.items_found,
                        "Duration": f"{attempt.duration_ms:.0f}ms",
                        "Error": attempt.error_message[:50] if attempt.error_message else "-"
                    })
                
                st.dataframe(
                    list(reversed(attempt_data)),
                    use_container_width=True,
                    hide_index=True
                )
            
            # Reset button
            if st.button(f"Reset Health Data", key=f"reset_{scraper_id}"):
                health_service.reset_health(scraper_id)
                st.success(f"Health data reset for {scraper_id}")
                st.rerun()
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh"):
        st.rerun()


if __name__ == "__main__":
    render()
