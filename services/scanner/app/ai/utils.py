import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def parse_ai_json(text: str) -> Dict[str, Any]:
    """
    Parses a JSON string from an AI response, handling markdown code blocks
    and potential extra text.
    
    Args:
        text: The raw text response from the AI.
        
    Returns:
        The parsed JSON dictionary.
        
    Raises:
        ValueError: If the text cannot be parsed as JSON.
    """
    cleaned_text = text.strip()
    
    # Remove markdown code blocks if present
    if "```" in cleaned_text:
        # Try to extract content between first ```json (or just ```) and last ```
        lines = cleaned_text.splitlines()
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                if start_idx == -1:
                    start_idx = i
                else:
                    end_idx = i
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            # Extract content between the markers
            # We skip the start line (e.g. ```json) and end line (```)
            cleaned_text = "\n".join(lines[start_idx+1 : end_idx])
    
    # Further cleanup: find the first '{' and last '}'
    start_brace = cleaned_text.find("{")
    end_brace = cleaned_text.rfind("}")
    
    if start_brace != -1 and end_brace != -1:
        cleaned_text = cleaned_text[start_brace : end_brace + 1]
    else:
        # If no braces found, it's likely not a JSON object
        logger.error(f"No JSON object found in AI response: {text[:200]}...")
        raise ValueError("No JSON object found in AI response")

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI JSON. Error: {e}")
        logger.error(f"Cleaned text was: {cleaned_text}")
        logger.error(f"Original text was: {text}")
        raise ValueError(f"Invalid JSON format: {e}")
