"""
Extracted context from prompt library for agent use.

This module provides structured access to the domain context, entities,
and keywords defined in the prompt library.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from src.prompts.loader import get_prompt_loader
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
class AgentContext:
    """
    Structured context for agent prompts.
    
    Contains all domain-specific information extracted from the prompt library.
    """
    
    # Tara Development Portfolio
    tara_projects: list[TaraProject] = field(default_factory=list)
    tara_summary: str = ""
    
    # Environmental context
    environmental_context: str = ""
    
    # Tracked entities
    developer_entities: list[Entity] = field(default_factory=list)
    government_entities: list[Entity] = field(default_factory=list)
    opposition_entities: list[Entity] = field(default_factory=list)
    whistleblower_entities: list[Entity] = field(default_factory=list)
    
    # Keywords to flag
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
    
    def get_prompt_context(self) -> str:
        """
        Generate a formatted context block for injection into prompts.
        
        Returns:
            Formatted string suitable for LLM prompt injection.
        """
        return f"""## DOMAIN CONTEXT

### Core Identity
{self.core_identity}

### The Tara Development Portfolio
{self.tara_summary}

### Environmental Context
{self.environmental_context}

### Priority Keywords
Flag any content containing: {self.get_keywords_string()}

### Key Entities to Track
{self.get_entities_string()}

### Behavioral Standards
**You ALWAYS:**
{chr(10).join(f"- {rule}" for rule in self.always_rules)}

**You NEVER:**
{chr(10).join(f"- {rule}" for rule in self.never_rules)}
"""


def _build_context() -> AgentContext:
    """Build AgentContext from prompt library files."""
    loader = get_prompt_loader()
    context = AgentContext()
    
    try:
        # Load Alachua context
        alachua_content = loader.load_context()
        
        # Extract Tara summary
        tara_section = loader.extract_section(alachua_content, "The Tara Development Portfolio")
        if tara_section:
            context.tara_summary = tara_section[:1500]  # Truncate for prompt size
        
        # Extract environmental context
        env_section = loader.extract_section(alachua_content, "Environmental Context")
        if env_section:
            context.environmental_context = env_section[:1000]
        
        # Build Tara projects list
        context.tara_projects = [
            TaraProject("Tara Forest West", "395 acres", "540 lots", "Pending"),
            TaraProject("Tara Baywood", "36 acres", "211 townhomes", "Under construction"),
            TaraProject("Tara Forest East", "148 acres", "340 lots", "Under construction"),
            TaraProject("Tara April", "Stormwater", "N/A", "Awaiting final plat", "PSE22-0002"),
            TaraProject("Tara Phoenicia", "Mixed-use", "TBD", "Awaiting final plat"),
        ]
        
        # Build entity lists
        context.developer_entities = [
            Entity("Tara Forest, LLC", "Property owner"),
            Entity("Sayed Moukhtara", "Principal"),
            Entity("Clay Sweger", "Applicant agent", ["EDA Consultants"]),
            Entity("Jay Brown", "Site developer", ["JBPro"]),
            Entity("Holtzman Vogel", "Legal representation"),
        ]
        
        context.government_entities = [
            Entity("Mike DaRoza", "City Manager"),
            Entity("Adam Boukari", "Former City Manager"),
            Entity("Bryan Thomas", "City staff"),
            Entity("Tim Alexander", "SRWMD Asst. Exec. Dir."),
            Entity("Sara Ferson", "SRWMD District Engineer"),
        ]
        
        context.opposition_entities = [
            Entity("National Speleological Society", "Adjacent property owner", ["NSS"]),
            Entity("Jane Graham", "NSS legal counsel", ["Sunshine City Law"]),
            Entity("Bryan Buescher", "Coalition partner", ["Our Alachua Water"]),
            Entity("Prof. Thomas Sawicki, PhD", "NSS expert (biodiversity)"),
            Entity("Stephen Boyes, P.G.", "NSS expert (sinkhole risk)"),
        ]
        
        context.whistleblower_entities = [
            Entity("Justin Tabor", "Former Principal Planner", notes="Resigned early 2025, authored Open Letter"),
        ]
        
        # Priority keywords
        context.priority_keywords = [
            "Tara", "Tara April", "Tara Forest", "Tara Baywood", "Tara Phoenicia",
            "PSE22-0002", "Mill Creek", "Hornsby", "Santa Fe River",
            "karst", "sinkhole", "aquifer", "recharge", "cave",
            "Special Exception", "variance", "rezoning", "LDR 2.4.4",
            "Comprehensive Plan", "Land Development Code", "Objective 1.7",
            "environmental protection", "wetlands", "stormwater", "ERP",
            "public hearing", "quasi-judicial",
            "Sayed Moukhtara", "Clay Sweger", "EDA Consultants", "JBPro",
            "Apex Companies", "geophysical", "geological testing",
            "Justin Tabor", "Mike DaRoza", "Adam Boukari",
            "whistleblower", "ethics", "AICP",
        ]
        
        logger.debug("Loaded Alachua context", keywords_count=len(context.priority_keywords))
        
    except FileNotFoundError as e:
        logger.warning("Could not load Alachua context", error=str(e))
    
    try:
        # Load behavioral standards
        standards_content = loader.load_behavioral_standards()
        
        # Extract core identity
        identity_section = loader.extract_section(standards_content, "Core Identity")
        if identity_section:
            context.core_identity = identity_section[:500]
        
        # Extract always/never rules
        always_section = loader.extract_section(standards_content, "You ALWAYS")
        if always_section:
            context.always_rules = [
                "Cite sources for every factual claim",
                "Distinguish facts from inferences",
                "Flag uncertainty when confidence is below HIGH",
                "Prioritize actionable information",
            ]
        
        never_section = loader.extract_section(standards_content, "You NEVER")
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
