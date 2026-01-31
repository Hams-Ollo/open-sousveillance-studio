"""
Extracted context from prompt library and config files for agent use.

This module provides structured access to the domain context, entities,
and keywords defined in the prompt library and YAML configuration files.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

from src.prompts.loader import get_prompt_loader, get_config_loader
from src.logging_config import get_logger

logger = get_logger("prompts.context")


@dataclass
class TaraProject:
    """A Tara development project."""
    name: str
    size: str
    units: str
    status: str
    key_permit: Optional[str] = None


@dataclass
class Entity:
    """A tracked entity (person, organization, or location)."""
    name: str
    role: str
    aliases: list[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class WatchlistEntity:
    """An entity from the watchlist config."""
    id: str
    name: str
    priority: str  # critical, high, medium, low
    category: str  # projects, organizations, people, locations, topics
    keywords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class AgentContext:
    """
    Structured context for agent prompts.

    Contains domain-specific information from prompt library and config files.
    """

    # Instance info (from config)
    instance_name: str = ""
    municipality: str = ""

    # Tara Development Portfolio (legacy - from markdown)
    tara_projects: list[TaraProject] = field(default_factory=list)
    tara_summary: str = ""

    # Environmental context (from markdown)
    environmental_context: str = ""

    # Tracked entities (legacy - from markdown)
    developer_entities: list[Entity] = field(default_factory=list)
    government_entities: list[Entity] = field(default_factory=list)
    opposition_entities: list[Entity] = field(default_factory=list)
    whistleblower_entities: list[Entity] = field(default_factory=list)

    # Watchlist entities (from config - new approach)
    watchlist_entities: list[WatchlistEntity] = field(default_factory=list)

    # Keywords to flag (combined from config)
    priority_keywords: list[str] = field(default_factory=list)

    # Behavioral standards
    core_identity: str = ""
    always_rules: list[str] = field(default_factory=list)
    never_rules: list[str] = field(default_factory=list)

    def get_keywords_string(self) -> str:
        """Get keywords as comma-separated string."""
        return ", ".join(self.priority_keywords)

    def get_entities_string(self) -> str:
        """Get all entity names as comma-separated string."""
        all_entities = (
            self.developer_entities +
            self.government_entities +
            self.opposition_entities +
            self.whistleblower_entities
        )
        return ", ".join(e.name for e in all_entities)

    def get_watchlist_by_priority(self, priority: str) -> list[WatchlistEntity]:
        """Get watchlist entities at a specific priority level."""
        return [e for e in self.watchlist_entities if e.priority == priority]

    def get_prompt_context(self) -> str:
        """
        Generate a formatted context block for injection into prompts.

        Returns:
            Formatted string suitable for LLM prompt injection.
        """
        # Build watchlist section from config-driven entities
        critical_entities = self.get_watchlist_by_priority("critical")
        high_entities = self.get_watchlist_by_priority("high")

        critical_names = [e.name for e in critical_entities] if critical_entities else []
        high_names = [e.name for e in high_entities] if high_entities else []

        # Fallback to legacy entities if no config-driven ones
        if not critical_names:
            critical_names = [e.name for e in self.developer_entities]

        location_header = f"({self.municipality})" if self.municipality else "(Alachua, Florida)"

        return f"""## CIVIC INTELLIGENCE CONTEXT

### Your Mission
You are a civic intelligence agent providing COMPREHENSIVE coverage of government activity.
Your goal is to ensure citizens have complete awareness of what their government is doing.
Document ALL items - do not filter based on keywords. Flag priority items for extra attention.

### Behavioral Standards
**You ALWAYS:**
{chr(10).join(f"- {rule}" for rule in self.always_rules)}

**You NEVER:**
{chr(10).join(f"- {rule}" for rule in self.never_rules)}

---

## LOCAL CONTEXT {location_header}

### High-Priority Issues
The following issues require elevated attention when encountered:

**The Tara Development Portfolio:**
{self.tara_summary}

**Environmental Concerns:**
{self.environmental_context}

### Watchlist Entities (by Priority)
**CRITICAL (immediate attention):** {', '.join(critical_names) if critical_names else 'None configured'}
**HIGH (monitor closely):** {', '.join(high_names) if high_names else 'None configured'}

### Priority Keywords
Flag (but don't filter) items containing: {self.get_keywords_string()}
"""


def _build_context() -> AgentContext:
    """Build AgentContext from prompt library and config files."""
    prompt_loader = get_prompt_loader()
    config_loader = get_config_loader()
    context = AgentContext()

    # Load from config files (new approach)
    try:
        # Load instance info
        instance_config = config_loader.load_instance()
        instance_info = instance_config.get('instance', {})
        context.instance_name = instance_info.get('name', '')

        jurisdiction = instance_config.get('jurisdiction', {})
        municipalities = jurisdiction.get('municipalities', [])
        primary_muni = next((m for m in municipalities if m.get('primary')), None)
        context.municipality = primary_muni.get('name', '') if primary_muni else ''

        logger.debug("Loaded instance config", instance=context.instance_name)
    except FileNotFoundError:
        logger.warning("Could not load instance config, using defaults")

    # Load watchlist entities from config
    try:
        entities_config = config_loader.load_entities()

        for category in ['projects', 'organizations', 'people', 'locations', 'topics']:
            items = entities_config.get(category, [])
            for item in items:
                entity = WatchlistEntity(
                    id=item.get('id', ''),
                    name=item.get('name', ''),
                    priority=item.get('priority', 'medium'),
                    category=category,
                    keywords=item.get('keywords', []),
                    aliases=item.get('aliases', []),
                    description=item.get('description', item.get('notes', ''))
                )
                context.watchlist_entities.append(entity)

        # Build priority keywords from config
        context.priority_keywords = config_loader.get_all_watchlist_keywords()

        logger.debug("Loaded watchlist from config",
                    entities_count=len(context.watchlist_entities),
                    keywords_count=len(context.priority_keywords))
    except FileNotFoundError:
        logger.warning("Could not load entities config, using legacy approach")

    # Load from prompt library (legacy approach - still useful for rich context)
    try:
        alachua_content = prompt_loader.load_context()

        # Extract Tara summary
        tara_section = prompt_loader.extract_section(alachua_content, "The Tara Development Portfolio")
        if tara_section:
            context.tara_summary = tara_section[:1500]

        # Extract environmental context
        env_section = prompt_loader.extract_section(alachua_content, "Environmental Context")
        if env_section:
            context.environmental_context = env_section[:1000]

        # Build Tara projects list (legacy)
        context.tara_projects = [
            TaraProject("Tara Forest West", "395 acres", "540 lots", "Pending"),
            TaraProject("Tara Baywood", "36 acres", "211 townhomes", "Under construction"),
            TaraProject("Tara Forest East", "148 acres", "340 lots", "Under construction"),
            TaraProject("Tara April", "Stormwater", "N/A", "Awaiting final plat", "PSE22-0002"),
            TaraProject("Tara Phoenicia", "Mixed-use", "TBD", "Awaiting final plat"),
        ]

        # Legacy entity lists (kept for backward compatibility)
        context.developer_entities = [
            Entity("Tara Forest, LLC", "Property owner"),
            Entity("Sayed Moukhtara", "Principal"),
        ]
        context.government_entities = [
            Entity("Mike DaRoza", "City Manager"),
        ]
        context.opposition_entities = [
            Entity("National Speleological Society", "Adjacent property owner", ["NSS"]),
        ]
        context.whistleblower_entities = [
            Entity("Justin Tabor", "Former Principal Planner"),
        ]

        logger.debug("Loaded Alachua context from prompt library")

    except FileNotFoundError as e:
        logger.warning("Could not load Alachua context", error=str(e))

    try:
        # Load behavioral standards
        standards_content = prompt_loader.load_behavioral_standards()

        # Extract core identity
        identity_section = prompt_loader.extract_section(standards_content, "Core Identity")
        if identity_section:
            context.core_identity = identity_section[:500]

        # Extract always/never rules
        always_section = prompt_loader.extract_section(standards_content, "You ALWAYS")
        if always_section:
            context.always_rules = [
                "Cite sources for every factual claim",
                "Distinguish facts from inferences",
                "Flag uncertainty when confidence is below HIGH",
                "Prioritize actionable information",
            ]

        never_section = prompt_loader.extract_section(standards_content, "You NEVER")
        if never_section:
            context.never_rules = [
                "Fabricate meeting dates, times, vote counts, names, or URLs",
                "Assume information not explicitly stated in sources",
                "Editorialize or express political opinions",
                "Skip verification to appear more comprehensive",
            ]

        logger.debug("Loaded behavioral standards")

    except FileNotFoundError as e:
        logger.warning("Could not load behavioral standards", error=str(e))

    return context


@lru_cache(maxsize=1)
def get_alachua_context() -> AgentContext:
    """
    Get the cached Alachua context.

    Returns:
        AgentContext with all domain-specific information.
    """
    return _build_context()
