"""
Prompt Loader Utility for AI System Prompts.

This module provides a simple, cached loader for versioned AI prompt files.
Prompts are stored in the `prompts/` subdirectory as plain text files.

Usage:
    from app.ai.prompt_loader import load_prompt
    
    system_prompt = load_prompt("security_report_system_v1")
"""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory containing prompt files, relative to this module
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptLoadError(Exception):
    """Raised when a prompt file cannot be loaded."""
    pass


@lru_cache(maxsize=32)
def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt file by name.
    
    The prompt file is expected to be located at:
        <module_dir>/prompts/<prompt_name>.txt
    
    Args:
        prompt_name: Name of the prompt (without .txt extension).
                     Example: "security_report_system_v1"
    
    Returns:
        The content of the prompt file as a string.
    
    Raises:
        PromptLoadError: If the file is missing, unreadable, or empty.
    
    Note:
        Results are cached in-memory to avoid repeated disk I/O.
        Use `load_prompt.cache_clear()` to invalidate the cache if needed.
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
    
    if not prompt_path.exists():
        logger.error(
            "Prompt file not found: %s (error_type=PROMPT_LOAD_ERROR)",
            prompt_path
        )
        raise PromptLoadError(
            f"Prompt file not found: {prompt_name}.txt. "
            f"Expected at: {prompt_path}"
        )
    
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        logger.error(
            "Failed to read prompt file %s: %s (error_type=PROMPT_LOAD_ERROR)",
            prompt_path, e
        )
        raise PromptLoadError(
            f"Failed to read prompt file: {prompt_name}.txt. Error: {e}"
        ) from e
    
    if not content.strip():
        logger.error(
            "Prompt file is empty: %s (error_type=PROMPT_LOAD_ERROR)",
            prompt_path
        )
        raise PromptLoadError(
            f"Prompt file is empty: {prompt_name}.txt"
        )
    
    logger.debug("Loaded prompt: %s (%d chars)", prompt_name, len(content))
    return content


def get_prompt_path(prompt_name: str) -> Path:
    """
    Get the filesystem path for a prompt file.
    
    Useful for debugging or tooling that needs to locate prompt files.
    
    Args:
        prompt_name: Name of the prompt (without .txt extension).
    
    Returns:
        Path object pointing to the prompt file.
    """
    return PROMPTS_DIR / f"{prompt_name}.txt"


def clear_cache() -> None:
    """
    Clear the prompt cache.
    
    Useful during development or testing when prompt files may change.
    """
    load_prompt.cache_clear()
    logger.debug("Prompt cache cleared")
