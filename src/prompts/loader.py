"""
Prompt loader utility for loading prompts from the prompt_library directory.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from src.config import PROMPT_LIB_DIR
from src.logging_config import get_logger

logger = get_logger("prompts.loader")


class PromptLoader:
    """
    Loads and parses prompt files from the prompt_library directory.
    
    Supports extracting specific sections from markdown prompt files.
    """
    
    def __init__(self, prompt_lib_dir: Path = PROMPT_LIB_DIR):
        self.prompt_lib_dir = prompt_lib_dir
        logger.debug("PromptLoader initialized", path=str(prompt_lib_dir))
    
    def load_file(self, relative_path: str) -> str:
        """
        Load a prompt file by relative path.
        
        Args:
            relative_path: Path relative to prompt_library/ (e.g., "config/alachua-context.md")
        
        Returns:
            Full content of the file.
        
        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        filepath = self.prompt_lib_dir / relative_path
        if not filepath.exists():
            logger.error("Prompt file not found", path=str(filepath))
            raise FileNotFoundError(f"Prompt file not found: {filepath}")
        
        content = filepath.read_text(encoding="utf-8")
        logger.debug("Loaded prompt file", path=relative_path, length=len(content))
        return content
    
    def extract_section(self, content: str, section_header: str) -> Optional[str]:
        """
        Extract a specific section from markdown content.
        
        Args:
            content: Full markdown content.
            section_header: Header text to find (e.g., "ALACHUA CONTEXT BLOCK").
        
        Returns:
            Content of the section, or None if not found.
        """
        # Find the section header (any heading level)
        pattern = rf"^#+\s*{re.escape(section_header)}\s*$"
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        
        if not match:
            return None
        
        start = match.end()
        
        # Find the next heading at same or higher level
        header_level = content[match.start():match.end()].count('#')
        next_header_pattern = rf"^#{{{1},{header_level}}}\s+\S"
        next_match = re.search(next_header_pattern, content[start:], re.MULTILINE)
        
        if next_match:
            end = start + next_match.start()
        else:
            end = len(content)
        
        section = content[start:end].strip()
        return section
    
    def load_scout_prompt(self, agent_id: str) -> Optional[str]:
        """
        Load a scout agent prompt by ID.
        
        Args:
            agent_id: Agent ID (e.g., "A1", "A2").
        
        Returns:
            Prompt content or None if not found.
        """
        prompt_map = {
            "A1": "layer-1-scouts/A1-meeting-intelligence-scout.md",
            "A2": "layer-1-scouts/A2-permit-application-scout.md",
            "A3": "layer-1-scouts/A3-legislative-code-monitor.md",
            "A4": "layer-1-scouts/A4-document-tracker.md",
        }
        
        path = prompt_map.get(agent_id.upper())
        if not path:
            logger.warning("Unknown scout agent ID", agent_id=agent_id)
            return None
        
        try:
            return self.load_file(path)
        except FileNotFoundError:
            return None
    
    def load_analyst_prompt(self, agent_id: str) -> Optional[str]:
        """
        Load an analyst agent prompt by ID.
        
        Args:
            agent_id: Agent ID (e.g., "B1", "B2").
        
        Returns:
            Prompt content or None if not found.
        """
        prompt_map = {
            "B1": "layer-2-analysts/B1-impact-assessment-analyst.md",
            "B2": "layer-2-analysts/B2-procedural-integrity-analyst.md",
        }
        
        path = prompt_map.get(agent_id.upper())
        if not path:
            logger.warning("Unknown analyst agent ID", agent_id=agent_id)
            return None
        
        try:
            return self.load_file(path)
        except FileNotFoundError:
            return None
    
    def load_context(self) -> str:
        """Load the shared Alachua context block."""
        return self.load_file("config/alachua-context.md")
    
    def load_behavioral_standards(self) -> str:
        """Load the agent behavioral standards."""
        return self.load_file("config/agent-behavioral-standards.md")


@lru_cache(maxsize=1)
def get_prompt_loader() -> PromptLoader:
    """Get singleton PromptLoader instance."""
    return PromptLoader()
