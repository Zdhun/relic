import pytest
from app.scanner.normalizer import normalize_target
from app.scanner.scoring import calculate_score
from app.scanner.models import Finding
from app.scanner.header_checks import check_security_headers

def test_normalizer_http_default_port():
    t = normalize_target("example.com")
    assert t.scheme == "http"
    assert t.port == 80
    assert t.full_url == "http://example.com/"

def test_normalizer_https_default_port():
    t = normalize_target("https://example.com")
    assert t.scheme == "https"
    assert t.port == 443
    assert t.full_url == "https://example.com/"

def test_normalizer_custom_port():
    t = normalize_target("http://example.com:8080")
    assert t.scheme == "http"
    assert t.port == 8080
    assert t.full_url == "http://example.com:8080/"

def test_scoring_penalties():
    findings = [
        Finding(title="High", severity="high", category="tls", description="d", recommendation="r"),
        Finding(title="Medium", severity="medium", category="headers", description="d", recommendation="r")
    ]
    score, grade = calculate_score(findings)
    # 100 - 25 - 10 = 65
    assert score == 65
    assert grade == "D"

def test_scoring_min_zero():
    findings = [Finding(title="Crit", severity="critical", category="tls", description="d", recommendation="r")] * 3
    score, grade = calculate_score(findings)
    # 100 - 120 = -20 -> 0
    assert score == 0
    assert grade == "F"

def test_header_checks_missing_hsts():
    headers = {"Content-Type": "text/html"}
    findings = check_security_headers(headers)
    assert any(f.title == "Missing HSTS Header" for f in findings)

def test_header_checks_present_hsts():
    headers = {"Strict-Transport-Security": "max-age=31536000"}
    findings = check_security_headers(headers)
    assert not any(f.title == "Missing HSTS Header" for f in findings)
