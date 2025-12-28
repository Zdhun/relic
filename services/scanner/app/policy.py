"""
Target Authorization Policy Module
==================================
Implements user authorization acknowledgement for the security scanner.

This module enforces a simple but critical security gate:
- Users must explicitly acknowledge they have permission to scan the target.

By default, ANY URL can be scanned as long as the user confirms authorization.
This is a portfolio/demo tool - the user is responsible for their actions.

Version: 1.1.0
Last Updated: 2024-12-28
"""

from urllib.parse import urlparse
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class PolicyError(Enum):
    """Error codes for policy violations."""
    MISSING_ACKNOWLEDGEMENT = "MISSING_ACKNOWLEDGEMENT"
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_SCHEME = "UNSUPPORTED_SCHEME"


@dataclass
class PolicyResult:
    """Result of a policy check."""
    allowed: bool
    error_code: Optional[PolicyError] = None
    message: Optional[str] = None
    details: Optional[dict] = None


def validate_url(target: str) -> PolicyResult:
    """
    Validate that the target is a valid HTTP/HTTPS URL.
    
    Args:
        target: Target URL or hostname
        
    Returns:
        PolicyResult indicating if URL is valid
    """
    # Check for explicit non-http schemes BEFORE normalization
    if "://" in target:
        scheme_part = target.lower().split("://")[0]
        if scheme_part not in ("http", "https"):
            return PolicyResult(
                allowed=False,
                error_code=PolicyError.UNSUPPORTED_SCHEME,
                message=f"Unsupported scheme '{scheme_part}'. Only http/https allowed",
                details={"target": target, "scheme": scheme_part}
            )
    
    # Normalize: add scheme if missing
    normalized = target if "://" in target else f"https://{target}"
    
    try:
        parsed = urlparse(normalized)
    except Exception as e:
        return PolicyResult(
            allowed=False,
            error_code=PolicyError.INVALID_URL,
            message=f"Invalid URL format: {e}",
            details={"target": target}
        )
    
    # Check we have a hostname
    if not parsed.hostname:
        return PolicyResult(
            allowed=False,
            error_code=PolicyError.INVALID_URL,
            message="No hostname found in URL",
            details={"target": target}
        )
    
    return PolicyResult(allowed=True)


def check_acknowledgement(authorized: bool) -> PolicyResult:
    """
    Check if the user has acknowledged authorization.
    
    Args:
        authorized: Boolean indicating user acknowledgement
        
    Returns:
        PolicyResult with allowed status
    """
    if not authorized:
        return PolicyResult(
            allowed=False,
            error_code=PolicyError.MISSING_ACKNOWLEDGEMENT,
            message="You must confirm authorization to scan the target. Set 'authorized: true' in request.",
            details={"required_field": "authorized", "expected_value": True}
        )
    return PolicyResult(allowed=True)


def validate_scan_request(target: str, authorized: bool) -> PolicyResult:
    """
    Validate a complete scan request.
    
    This is the main entry point for policy enforcement.
    Checks:
    1. User has acknowledged they have permission to scan
    2. Target URL is valid (http/https only)
    
    Args:
        target: Target URL to scan
        authorized: User acknowledgement flag
        
    Returns:
        PolicyResult indicating if scan should proceed
    """
    # Gate 1: Acknowledgement (must be true)
    ack_result = check_acknowledgement(authorized)
    if not ack_result.allowed:
        return ack_result
    
    # Gate 2: Valid URL format
    url_result = validate_url(target)
    if not url_result.allowed:
        return url_result
    
    return PolicyResult(allowed=True)


# Legacy compatibility function (deprecated)
def is_authorized(target: str) -> bool:
    """
    DEPRECATED: Use validate_scan_request() instead.
    
    Always returns True since we no longer restrict by network.
    Authorization is now handled via the 'authorized' request field.
    """
    return True
