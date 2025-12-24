"""
AI Output Validation Module
===========================
Validates AI-generated reports against strict Pydantic schemas.
Provides structured fallback for invalid/untrusted outputs.

Usage:
    from app.ai.validation import validate_ai_report
    
    report_dict, is_valid = validate_ai_report(raw_text, scan_id="xxx")
    if not is_valid:
        # Handle fallback case
"""

import logging
from typing import Dict, Any, Tuple, Optional
from pydantic import ValidationError

from .utils import parse_ai_json
from .models import AIReport


logger = logging.getLogger(__name__)


# Fallback report when AI output is invalid
# Risk level "moyen" chosen deliberately:
# - "low" would mask potentially risky validation failure
# - "high" would create false urgency
# - "medium" signals caution without panic
FALLBACK_REPORT: Dict[str, Any] = {
    "global_score": {"letter": "?", "numeric": 0},
    "overall_risk_level": "moyen",
    "executive_summary": (
        "⚠️ L'analyse IA n'a pas pu être validée. "
        "Le rapport automatique est indisponible pour cette analyse. "
        "Veuillez consulter les résultats techniques bruts ou relancer l'analyse."
    ),
    "key_vulnerabilities": [],
    "site_map": {"total_pages": 0, "pages": []},
    "infrastructure": {},
    "model_name": "validation_failed",
}


def validate_ai_report(
    raw_text: str,
    scan_id: str,
    model_name: Optional[str] = None
) -> Tuple[Dict[str, Any], bool]:
    """
    Validates AI-generated text against the AIReport schema.
    
    This function:
    1. Parses JSON from raw text (handles markdown fencing)
    2. Validates against strict Pydantic schema
    3. Returns fallback on any error (never raises)
    
    Args:
        raw_text: Raw text response from AI (potentially with markdown fencing)
        scan_id: Scan identifier for structured logging
        model_name: Optional model name to inject into result
        
    Returns:
        Tuple of (report_dict, is_valid):
        - report_dict: Validated AIReport as dict, or fallback if invalid
        - is_valid: True if validation succeeded, False otherwise
        
    Note:
        This function NEVER raises exceptions. All errors result in
        fallback report with is_valid=False.
    """
    try:
        # Step 1: Parse JSON from raw text
        parsed_data = parse_ai_json(raw_text)
        
        # Step 2: Validate against Pydantic schema
        report = AIReport.model_validate(parsed_data)
        
        # Step 3: Convert to dict and inject model name if provided
        report_dict = report.model_dump()
        if model_name:
            report_dict["model_name"] = model_name
            
        return report_dict, True
        
    except ValueError as e:
        # JSON parsing failed (from parse_ai_json)
        _log_validation_error(scan_id, "JSON_PARSE_ERROR", str(e))
        return _create_fallback(model_name), False
        
    except ValidationError as e:
        # Pydantic validation failed
        error_summary = _summarize_validation_errors(e)
        _log_validation_error(scan_id, "SCHEMA_VALIDATION_ERROR", error_summary)
        return _create_fallback(model_name), False
        
    except Exception as e:
        # Unexpected error - still don't crash the pipeline
        _log_validation_error(scan_id, "UNEXPECTED_ERROR", str(e)[:200])
        return _create_fallback(model_name), False


def _log_validation_error(scan_id: str, error_type: str, error_summary: str) -> None:
    """
    Logs a structured validation error.
    
    Outputs a single structured log line with:
    - scan_id: For correlation
    - error_type: AI_VALIDATION_ERROR category
    - error_summary: First N chars of error (privacy + noise reduction)
    """
    logger.warning(
        "AI validation failed | scan_id=%s | error_type=%s | error_summary=%s",
        scan_id,
        error_type,
        error_summary[:500],  # Cap at 500 chars to avoid log bloat
    )


def _summarize_validation_errors(e: ValidationError) -> str:
    """
    Extracts a concise summary from Pydantic ValidationError.
    
    Takes first 3 errors max, formats as "field.path: message" strings.
    """
    errors = e.errors()
    if not errors:
        return "Unknown validation error"
    
    # Take first 3 errors max
    summaries = []
    for err in errors[:3]:
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        summaries.append(f"{loc}: {msg}")
    
    result = "; ".join(summaries)
    if len(errors) > 3:
        result += f" (+{len(errors) - 3} more)"
    return result


def _create_fallback(model_name: Optional[str]) -> Dict[str, Any]:
    """
    Creates a fallback report dict.
    
    Uses deepcopy-like behavior to ensure FALLBACK_REPORT isn't mutated.
    """
    fallback = {
        "global_score": FALLBACK_REPORT["global_score"].copy(),
        "overall_risk_level": FALLBACK_REPORT["overall_risk_level"],
        "executive_summary": FALLBACK_REPORT["executive_summary"],
        "key_vulnerabilities": [],
        "site_map": FALLBACK_REPORT["site_map"].copy(),
        "infrastructure": FALLBACK_REPORT["infrastructure"].copy(),
        "model_name": FALLBACK_REPORT["model_name"],
    }
    if model_name:
        fallback["model_name"] = f"{model_name} (validation_failed)"
    return fallback
