"""
Tests for PDF, JSON and Markdown report generation.
"""

import pytest
from datetime import datetime, UTC
from app.pdf import generate_pdf, generate_ai_pdf, generate_json, generate_markdown
from app.models import ScanResult, Finding, ScanLog


@pytest.fixture
def sample_result():
    """Creates a sample ScanResult using the Pydantic model from app.models."""
    return ScanResult(
        scan_id="test-scan-123",
        target="http://example.com",
        status="completed",
        grade="B",
        score=75,
        findings=[
            Finding(
                title="Test Finding",
                severity="high",
                category="xss",
                description="This is a test vulnerability description.",
                recommendation="Fix it by doing XYZ."
            )
        ],
        logs=[
            ScanLog(
                timestamp=datetime.now(UTC),
                level="INFO",
                message="Scan started"
            )
        ],
        timestamp=datetime.now(UTC),
        response_time_ms=100,
        debug_info=None,
        scan_status="ok",
        blocking_mechanism=None,
        visibility_level="good"
    )


def test_generate_pdf(sample_result):
    """Verify PDF generation returns bytes."""
    pdf_bytes = generate_pdf(sample_result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert b"%PDF" in pdf_bytes


def test_generate_ai_pdf(sample_result):
    """Verify AI PDF generation returns bytes."""
    ai_summary = {
        "global_score": {"numeric": 75, "letter": "B"},
        "overall_risk_level": "Moyen",
        "executive_summary": "This is a test executive summary for the security audit.",
        "key_vulnerabilities": [
            {
                "title": "Test Vulnerability",
                "severity": "high",
                "area": "Application",
                "explanation_simple": "This is a simple explanation.",
                "fix_recommendation": "Apply this fix."
            }
        ],
        "infrastructure": {
            "hosting_provider": "Test Provider",
            "tls_issuer": "Let's Encrypt",
            "server_header": "nginx",
            "ip": "192.168.1.1"
        },
        "site_map": {"total_pages": 2, "pages": ["/", "/about"]}
    }
    pdf_bytes = generate_ai_pdf(sample_result, ai_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert b"%PDF" in pdf_bytes


def test_generate_json(sample_result):
    """Verify JSON generation."""
    json_str = generate_json(sample_result)
    assert isinstance(json_str, str)
    assert "http://example.com" in json_str
    assert "Test Finding" in json_str


def test_generate_markdown(sample_result):
    """Verify Markdown generation."""
    md_str = generate_markdown(sample_result)
    assert isinstance(md_str, str)
    assert "# AuditAI Security Report" in md_str
    assert "Test Finding" in md_str
    assert "http://example.com" in md_str
