"""
CLI entry point for Open Sousveillance Studio System.

Usage:
    python -m src.main --agent A1 --url https://example.com
    python -m src.main --agent A1 --critical
    python -m src.main --agent B1 --topic "Tara Forest Development"
    python -m src.main --list-agents
"""

import argparse
import sys
from src.agents import get_agent, get_agent_info, list_agents
from src.config import get_sources_by_priority


def get_database():
    """Lazy import database to avoid crashes if credentials missing."""
    from src.database import get_db
    return get_db()


def get_critical_urls() -> list[str]:
    """Get all critical priority source URLs from YAML config."""
    sources = get_sources_by_priority("critical")
    return [s.url for s in sources]


def main():
    parser = argparse.ArgumentParser(description="Open Sousveillance Studio System")
    parser.add_argument("--agent", type=str, help="Agent to run (e.g., A1, A2, B1)")
    parser.add_argument("--url", type=str, help="Target URL for the scout to monitor")
    parser.add_argument("--topic", type=str, help="Research topic for analysts")
    parser.add_argument("--critical", action="store_true", help="Run all CRITICAL sources from config")
    parser.add_argument("--save", action="store_true", help="Save result to Supabase")
    parser.add_argument("--list-agents", action="store_true", help="List all registered agents")

    args = parser.parse_args()

    if args.list_agents:
        print("Registered Agents:")
        for a in list_agents():
            print(f"  {a['id']}: Layer {a['layer']} - {a['description']}")
        return

    if not args.agent:
        parser.error("--agent is required (or use --list-agents)")

    try:
        info = get_agent_info(args.agent)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if info["layer"] == 1:
        # Scout agents
        agent = get_agent(args.agent, prompt_template="Standard Scout Prompt")

        targets = []
        if args.critical:
            print("🔍 Loading all CRITICAL sources from config...")
            targets = get_critical_urls()
        elif args.url:
            targets = [args.url]
        else:
            print("Error: Either --url or --critical is required for Scout agents.")
            sys.exit(1)

        for url in targets:
            try:
                print(f"🚀 Running Agent {args.agent} on {url}...")
                report = agent.run({"url": url})

                print("\n✅ Report Generated:")
                print(f"ID: {report.report_id}")
                print(f"Summary: {report.executive_summary}")
                print(f"Alerts: {len(report.alerts)}")

                if args.save:
                    print("💾 Saving to Supabase...")
                    get_database().save_report(report)
                    print("Done.")
            except Exception as e:
                print(f"❌ Error monitoring {url}: {e}")
                continue

    elif info["layer"] == 2:
        # Analyst agents
        agent = get_agent(args.agent)

        topic = args.topic or args.url or "Tara Forest Development"

        try:
            print(f"🧠 Running Analyst {args.agent} on topic: {topic}...")
            report = agent.run({"topic": topic})

            print("\n✅ Intelligence Report Generated:")
            print(f"ID: {report.report_id}")
            print(f"Executive Summary: {report.executive_summary}")

            if args.save:
                print("💾 Saving to Supabase...")
                get_database().save_report(report)
                print("Done.")

        except Exception as e:
            print(f"❌ Error running analyst: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
