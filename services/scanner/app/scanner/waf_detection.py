from typing import Dict, Optional, List, Any

def detect_waf_and_visibility(scan_debug_info: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Analyzes the scan results (specifically HTTP traffic and headers) to detect
    if the scan was blocked by a WAF or a challenge page (like Vercel).

    Args:
        scan_debug_info: The 'debug_info' dictionary from the ScanResult.
                         Expected to contain "http_traffic" (list of requests/responses).

    Returns:
        A dictionary with keys:
        - "scan_status": "ok", "blocked_by_waf", or "error"
        - "blocking_mechanism": e.g., "vercel_challenge", "generic_waf", or None
        - "visibility_level": "none", "very_low", "partial", "good"
    """
    
    http_traffic = scan_debug_info.get("http_traffic", [])
    
    if not http_traffic:
        # If no traffic at all, it's likely an error or host unreachable, 
        # but from a WAF perspective we can't say much. 
        # However, if the scan failed before HTTP, this function might not even be called 
        # or it might be called with empty list.
        # Let's assume "ok" but visibility "none" if we really have no data, 
        # or maybe it's better to rely on the caller to handle empty traffic.
        # But per spec, we return default "ok" if not blocked.
        return {
            "scan_status": "ok",
            "blocking_mechanism": None,
            "visibility_level": "none"
        }

    total_requests = len(http_traffic)
    blocked_count = 0
    challenge_headers_detected = False
    detected_mechanism = None
    
    # Heuristics for blocking
    # 1. Status codes: 403, 401, 429 are strong indicators of blocking if prevalent.
    # 2. Headers: Specific headers like x-vercel-mitigated.
    
    # We'll count "successful" (2xx/3xx) vs "blocked" (403/401/429)
    
    successful_count = 0
    blocked_count = 0
    
    # Track if we found any "application" 200 OK (not just challenge page)
    # Challenge pages often return 403, but sometimes 200 with specific content.
    # Vercel challenge usually returns 403.
    found_app_200 = False
    
    for entry in http_traffic:
        if isinstance(entry, dict):
            status = entry.get('status_code')
            headers = entry.get('headers', {})
        else:
            status = getattr(entry, 'status_code', None)
            headers = getattr(entry, 'headers', {})
            
        if status in [403, 401, 429]:
            blocked_count += 1
        elif status and 200 <= status < 400:
            successful_count += 1
            # Simple heuristic: if we have a 200 that is NOT a challenge page, it might be app content.
            # But if we are in a challenge loop, we might not get any 200.
            found_app_200 = True
            
        # Check headers for specific signatures
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        if "x-vercel-mitigated" in headers_lower and headers_lower["x-vercel-mitigated"] == "challenge":
            challenge_headers_detected = True
            detected_mechanism = "vercel_challenge"
        elif "x-vercel-challenge-token" in headers_lower:
            challenge_headers_detected = True
            detected_mechanism = "vercel_challenge"
            
    
    # Decision Logic
    is_blocked = False
    scan_status = "ok"
    visibility = "good"
    
    # Calculate blocked ratio
    blocked_ratio = 0.0
    if total_requests > 0:
        blocked_ratio = blocked_count / total_requests
        
    # Strict Vercel Challenge Detection
    # >= 60% 403s AND header present AND no normal 200s (implied by high block ratio usually, but let's be strict)
    if challenge_headers_detected and blocked_ratio >= 0.6:
        is_blocked = True
        scan_status = "blocked"
        detected_mechanism = "waf_challenge" # Standardized name as per request
        visibility = "poor"
        
    # Generic Blocking (fallback if no specific header but high block rate)
    elif blocked_ratio > 0.8:
        is_blocked = True
        scan_status = "blocked"
        detected_mechanism = "generic_waf"
        visibility = "poor"
        
    # Partial Blocking (future proofing)
    elif blocked_ratio > 0.3:
         # Some blocking but not total
         scan_status = "partial"
         visibility = "limited"
         detected_mechanism = "rate_limited" if not detected_mechanism else detected_mechanism

    if is_blocked:
        return {
            "scan_status": scan_status,
            "blocking_mechanism": detected_mechanism,
            "visibility_level": visibility
        }
    elif scan_status == "partial":
         return {
            "scan_status": "partial",
            "blocking_mechanism": detected_mechanism,
            "visibility_level": visibility
        }
    else:
        # Not blocked by WAF
        # Calculate visibility for normal sites
        
        # Check discovered paths count
        discovered_paths = scan_debug_info.get("discovered_paths", [])
        unique_paths = len(set(p.get("path", "") for p in discovered_paths if isinstance(p, dict)))
        
        # Also consider http traffic unique URLs if paths not populated
        if not unique_paths:
             unique_urls = set()
             for entry in http_traffic:
                 if isinstance(entry, dict):
                     url = entry.get("url")
                 else:
                     url = getattr(entry, "url", None)
                 
                 if url:
                     # Simple path extraction
                     try:
                         from urllib.parse import urlparse
                         path = urlparse(str(url)).path
                         if path and path != "/":
                             unique_urls.add(path)
                     except:
                         pass
             unique_paths = len(unique_urls)

        if total_requests == 0:
            visibility = "none"
        elif successful_count > 0:
            # Heuristic: At least 4 unique paths for "good" visibility
            if unique_paths >= 4:
                visibility = "good"
            elif unique_paths > 0:
                visibility = "partial" # Changed from "limited" to match previous logic/request nuances
            else:
                visibility = "partial"
        else:
            visibility = "partial"
            
        return {
            "scan_status": "ok",
            "blocking_mechanism": None,
            "visibility_level": visibility
        }

# Scenarios:
# 1. Normal Site:
#    - 10 requests: 8x 200 OK, 2x 404 Not Found.
#    - blocked_count = 0. Ratio = 0.0.
#    - No challenge headers.
#    -> scan_status="ok", blocking_mechanism=None, visibility_level="good"

# 2. Vercel Challenge:
#    - 5 requests: All 403 Forbidden.
#    - Headers contain "x-vercel-mitigated": "challenge".
#    - challenge_headers_detected = True.
#    -> scan_status="blocked_by_waf", blocking_mechanism="vercel_challenge", visibility_level="none"

# 3. Generic WAF (Aggressive):
#    - 20 requests: 1x 200 (homepage), 19x 403 (scans).
#    - blocked_count = 19. Ratio = 0.95 (> 0.8).
#    - No specific headers.
#    -> scan_status="blocked_by_waf", blocking_mechanism="generic_waf", visibility_level="very_low"
