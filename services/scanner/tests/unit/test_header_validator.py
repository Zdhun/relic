import pytest
from app.scanner.header_checks import check_security_headers

def test_missing_hsts_header():
    """HSTS header should be detected as missing"""
    headers = {"Content-Type": "text/html"}
    findings = check_security_headers(headers)
    assert any(f.title == "Missing HSTS Header" for f in findings)

def test_missing_csp_header():
    """CSP header should be detected as missing"""
    headers = {"Content-Type": "text/html"}
    findings = check_security_headers(headers)
    assert any(f.title == "Missing Content-Security-Policy" for f in findings)

def test_csp_unsafe_eval():
    """CSP with unsafe-eval should be flagged"""
    headers = {
        "Content-Security-Policy": "default-src 'self' 'unsafe-eval'",
        "Strict-Transport-Security": "max-age=31536000"
    }
    findings = check_security_headers(headers)
    assert any(f.title == "CSP permissive (unsafe-eval)" for f in findings)

def test_csp_unsafe_inline():
    """CSP with unsafe-inline should be flagged"""
    headers = {
        "Content-Security-Policy": "default-src 'self' 'unsafe-inline'",
        "Strict-Transport-Security": "max-age=31536000"
    }
    findings = check_security_headers(headers)
    assert any(f.title == "CSP permissive (unsafe-inline)" for f in findings)

def test_missing_x_frame_options():
    """X-Frame-Options should be detected as missing"""
    headers = {"Content-Type": "text/html"}
    findings = check_security_headers(headers)
    assert any(f.title == "Missing X-Frame-Options" for f in findings)

def test_secure_headers_present():
    """No findings if all headers are secure"""
    headers = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=()"
    }
    findings = check_security_headers(headers)
    assert len(findings) == 0
