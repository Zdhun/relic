import pytest
from app.scanner.waf_detection import detect_waf_and_visibility

# Mock objects for http_traffic
class MockResponse:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}

def test_detect_waf_normal_site():
    """Test a normal site with mostly 200 OK responses."""
    traffic = [
        MockResponse(200),
        MockResponse(200),
        MockResponse(404),
        MockResponse(200),
        MockResponse(301),
    ]
    # Need > 4 paths for good visibility
    discovered_paths = [
        {"path": "/"},
        {"path": "/dashboard"},
        {"path": "/login"},
        {"path": "/search"},
        {"path": "/about"},
    ]
    debug_info = {"http_traffic": traffic, "discovered_paths": discovered_paths}
    
    result = detect_waf_and_visibility(debug_info)
    
    assert result["scan_status"] == "ok"
    assert result["blocking_mechanism"] is None
    assert result["visibility_level"] == "good"

def test_detect_waf_vercel_challenge():
    """Test detection of Vercel challenge headers with high block rate."""
    # Needs >= 60% blocked
    traffic = [
        MockResponse(403, {"x-vercel-mitigated": "challenge"}),
        MockResponse(403, {"x-vercel-mitigated": "challenge"}),
        MockResponse(403, {"x-vercel-mitigated": "challenge"}), # 3/3 = 100%
    ]
    debug_info = {"http_traffic": traffic}
    
    result = detect_waf_and_visibility(debug_info)
    
    assert result["scan_status"] == "blocked"
    assert result["blocking_mechanism"] == "waf_challenge"
    assert result["visibility_level"] == "poor"

def test_detect_waf_vercel_token():
    """Test detection of Vercel challenge token."""
    # Even if token is present, we need high block rate for 'blocked' status in new logic?
    # The code says: if challenge_headers_detected and blocked_ratio >= 0.6
    
    # Case 1: Token present but mostly 200s (maybe we passed the challenge?)
    traffic = [
        MockResponse(200, {"x-vercel-challenge-token": "some-token"}),
        MockResponse(200),
    ]
    debug_info = {"http_traffic": traffic}
    result = detect_waf_and_visibility(debug_info)
    # Should be OK because not blocked
    assert result["scan_status"] == "ok" 
    
    # Case 2: Token present and blocked
    traffic_blocked = [
        MockResponse(403, {"x-vercel-challenge-token": "some-token"}),
        MockResponse(403),
    ]
    debug_info_blocked = {"http_traffic": traffic_blocked}
    result_blocked = detect_waf_and_visibility(debug_info_blocked)
    
    assert result_blocked["scan_status"] == "blocked"
    assert result_blocked["blocking_mechanism"] == "waf_challenge"

def test_detect_waf_generic_blocking():
    """Test generic WAF blocking based on status codes."""
    traffic = [MockResponse(403)] * 9 + [MockResponse(200)] # 90% blocked
    debug_info = {"http_traffic": traffic}
    
    result = detect_waf_and_visibility(debug_info)
    
    assert result["scan_status"] == "blocked"
    assert result["blocking_mechanism"] == "generic_waf"
    assert result["visibility_level"] == "poor"

def test_detect_waf_no_traffic():
    """Test with empty traffic."""
    debug_info = {"http_traffic": []}
    
    result = detect_waf_and_visibility(debug_info)
    
    assert result["scan_status"] == "ok"
    assert result["blocking_mechanism"] is None
    assert result["visibility_level"] == "none"

def test_detect_waf_mixed_traffic_not_blocked():
    """Test mixed traffic that shouldn't trigger WAF detection (e.g. 404s)."""
    traffic = [
        MockResponse(200),
        MockResponse(404),
        MockResponse(404),
        MockResponse(500),
        MockResponse(200),
    ]
    # Blocked count (403/401/429) is 0.
    debug_info = {"http_traffic": traffic}
    
    result = detect_waf_and_visibility(debug_info)
    
    assert result["scan_status"] == "ok"
    assert result["blocking_mechanism"] is None
    assert result["visibility_level"] == "partial"
