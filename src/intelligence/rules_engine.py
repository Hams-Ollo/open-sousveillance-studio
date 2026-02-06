"""
Watchdog Rules Engine for civic alert generation.

Evaluates CivicEvents against configurable rules to generate
alerts for concerning civic activity.
"""

import re
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from src.intelligence.models import CivicEvent, EventType, Alert, AlertSeverity
from src.logging_config import get_logger

logger = get_logger("intelligence.rules_engine")


@dataclass
class Rule:
    """
    A watchdog rule for generating alerts.

    Rules define conditions that, when matched by a CivicEvent,
    generate an alert for citizen notification.
    """
    name: str
    description: str
    severity: AlertSeverity
    message_template: str

    # Conditions (all must match)
    event_types: List[EventType] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)
    any_tags: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    counties: List[str] = field(default_factory=list)

    # Text matching
    title_contains: List[str] = field(default_factory=list)
    title_regex: Optional[str] = None

    # Time-based conditions
    upcoming_within_hours: Optional[int] = None
    agenda_posted_within_hours: Optional[int] = None

    # Custom condition function (for advanced rules)
    custom_condition: Optional[Callable[[CivicEvent], bool]] = None

    enabled: bool = True

    def matches(self, event: CivicEvent) -> bool:
        """
        Check if an event matches this rule.

        Args:
            event: CivicEvent to evaluate

        Returns:
            True if all conditions match
        """
        if not self.enabled:
            return False

        # Event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Required tags (must have ALL)
        if self.required_tags and not event.matches_tags(self.required_tags):
            return False

        # Any tags (must have at least ONE)
        if self.any_tags and not event.matches_any_tag(self.any_tags):
            return False

        # Source filter
        if self.source_ids and event.source_id not in self.source_ids:
            return False

        # County filter
        if self.counties:
            event_county = None
            if event.location and event.location.county:
                event_county = event.location.county.lower()

            county_match = False
            for county in self.counties:
                county_lower = county.lower()
                if event_county == county_lower:
                    county_match = True
                    break
                # Also check tags
                if county_lower in event.tags or f"{county_lower}-county" in event.tags:
                    county_match = True
                    break

            if not county_match:
                return False

        # Title contains
        if self.title_contains:
            title_lower = event.title.lower()
            if not any(term.lower() in title_lower for term in self.title_contains):
                return False

        # Title regex
        if self.title_regex:
            if not re.search(self.title_regex, event.title, re.IGNORECASE):
                return False

        # Upcoming within hours
        if self.upcoming_within_hours:
            now = datetime.now()
            cutoff = now + timedelta(hours=self.upcoming_within_hours)
            if not (now <= event.timestamp <= cutoff):
                return False

        # Custom condition
        if self.custom_condition and not self.custom_condition(event):
            return False

        return True

    def generate_alert(self, event: CivicEvent) -> Alert:
        """
        Generate an alert for a matching event.

        Args:
            event: The matching CivicEvent

        Returns:
            Alert object
        """
        # Format message with event data
        message = self.message_template.format(
            title=event.title,
            source=event.source_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp.strftime("%Y-%m-%d %H:%M"),
            county=event.location.county if event.location else "Unknown",
        )

        alert_id = f"alert-{self.name}-{event.event_id}"

        return Alert(
            alert_id=alert_id,
            rule_name=self.name,
            severity=self.severity,
            message=message,
            event=event,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create a Rule from dictionary (e.g., from YAML)."""
        # Parse severity
        severity_str = data.get("severity", "info").lower()
        severity = AlertSeverity(severity_str)

        # Parse event types
        event_types = []
        for et in data.get("event_types", []):
            try:
                event_types.append(EventType(et))
            except ValueError:
                logger.warning(f"Unknown event type: {et}")

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            severity=severity,
            message_template=data.get("message", "{title}"),
            event_types=event_types,
            required_tags=data.get("required_tags", []),
            any_tags=data.get("any_tags", []),
            source_ids=data.get("source_ids", []),
            counties=data.get("counties", []),
            title_contains=data.get("title_contains", []),
            title_regex=data.get("title_regex"),
            upcoming_within_hours=data.get("upcoming_within_hours"),
            enabled=data.get("enabled", True),
        )


class RulesEngine:
    """
    Engine for evaluating events against watchdog rules.

    Loads rules from YAML configuration and evaluates CivicEvents
    to generate alerts for civic watchdog use cases.
    """

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize the rules engine.

        Args:
            rules_path: Path to YAML rules file. Defaults to
                       config/watchdog_rules.yaml
        """
        if rules_path is None:
            project_root = Path(__file__).parent.parent.parent
            rules_path = project_root / "config" / "watchdog_rules.yaml"

        self.rules_path = Path(rules_path)
        self.rules: List[Rule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from YAML file."""
        if not self.rules_path.exists():
            logger.warning(
                "Rules file not found, using default rules",
                path=str(self.rules_path)
            )
            self._load_default_rules()
            return

        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            for rule_data in data.get("rules", []):
                try:
                    rule = Rule.from_dict(rule_data)
                    self.rules.append(rule)
                except Exception as e:
                    logger.warning(
                        "Failed to load rule",
                        rule_name=rule_data.get("name"),
                        error=str(e)
                    )

            logger.info(
                "Loaded watchdog rules",
                count=len(self.rules),
                path=str(self.rules_path)
            )
        except Exception as e:
            logger.error("Failed to load rules file", error=str(e))
            self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default civic watchdog rules."""
        self.rules = [
            Rule(
                name="new-alachua-permit",
                description="Alert on new permit applications in Alachua County",
                severity=AlertSeverity.INFO,
                message_template="New permit application: {title}",
                event_types=[EventType.PERMIT_APPLICATION],
                counties=["Alachua"],
            ),
            Rule(
                name="rezoning-alert",
                description="Alert on rezoning-related events",
                severity=AlertSeverity.NOTABLE,
                message_template="Rezoning activity: {title}",
                required_tags=["rezoning"],
            ),
            Rule(
                name="upcoming-meeting-48h",
                description="Alert on meetings happening within 48 hours",
                severity=AlertSeverity.INFO,
                message_template="Upcoming meeting in 48 hours: {title}",
                event_types=[EventType.MEETING],
                upcoming_within_hours=48,
            ),
            Rule(
                name="environmental-concern",
                description="Alert on environmental-related items",
                severity=AlertSeverity.NOTABLE,
                message_template="Environmental item: {title}",
                any_tags=["environmental", "water", "aquifer", "wetland"],
            ),
            Rule(
                name="public-hearing",
                description="Alert on public hearings",
                severity=AlertSeverity.WARNING,
                message_template="Public hearing scheduled: {title}",
                required_tags=["public-hearing"],
            ),
        ]

        logger.info("Loaded default watchdog rules", count=len(self.rules))

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                return True
        return False

    def evaluate(self, event: CivicEvent) -> List[Alert]:
        """
        Evaluate an event against all rules.

        Args:
            event: CivicEvent to evaluate

        Returns:
            List of generated alerts (may be empty)
        """
        alerts = []

        for rule in self.rules:
            if rule.matches(event):
                alert = rule.generate_alert(event)
                alerts.append(alert)

                logger.debug(
                    "Rule matched",
                    rule=rule.name,
                    event_id=event.event_id,
                    severity=alert.severity.value
                )

        return alerts

    def evaluate_batch(self, events: List[CivicEvent]) -> List[Alert]:
        """
        Evaluate multiple events against all rules.

        Args:
            events: List of CivicEvents to evaluate

        Returns:
            List of all generated alerts
        """
        all_alerts = []

        for event in events:
            alerts = self.evaluate(event)
            all_alerts.extend(alerts)

        if all_alerts:
            logger.info(
                "Batch evaluation complete",
                events=len(events),
                alerts=len(all_alerts)
            )

        return all_alerts

    def get_rules_by_severity(self, severity: AlertSeverity) -> List[Rule]:
        """Get rules filtered by severity."""
        return [r for r in self.rules if r.severity == severity]

    def get_enabled_rules(self) -> List[Rule]:
        """Get only enabled rules."""
        return [r for r in self.rules if r.enabled]

    def save_rules(self) -> None:
        """Save current rules to YAML file."""
        rules_data = []
        for rule in self.rules:
            rule_dict = {
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
                "message": rule.message_template,
                "enabled": rule.enabled,
            }

            if rule.event_types:
                rule_dict["event_types"] = [et.value for et in rule.event_types]
            if rule.required_tags:
                rule_dict["required_tags"] = rule.required_tags
            if rule.any_tags:
                rule_dict["any_tags"] = rule.any_tags
            if rule.source_ids:
                rule_dict["source_ids"] = rule.source_ids
            if rule.counties:
                rule_dict["counties"] = rule.counties
            if rule.title_contains:
                rule_dict["title_contains"] = rule.title_contains
            if rule.title_regex:
                rule_dict["title_regex"] = rule.title_regex
            if rule.upcoming_within_hours:
                rule_dict["upcoming_within_hours"] = rule.upcoming_within_hours

            rules_data.append(rule_dict)

        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "rules": rules_data,
        }

        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.rules_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info("Saved watchdog rules", count=len(self.rules))


# Singleton instance
import threading

_rules_engine: Optional[RulesEngine] = None
_rules_lock = threading.Lock()


def get_rules_engine(rules_path: Optional[str] = None) -> RulesEngine:
    """
    Get the singleton RulesEngine instance.

    Args:
        rules_path: Optional custom rules path

    Returns:
        RulesEngine instance
    """
    global _rules_engine
    if _rules_engine is None:
        with _rules_lock:
            if _rules_engine is None:
                _rules_engine = RulesEngine(rules_path)
    return _rules_engine
