import pytest
from datetime import datetime
from app.pdf import generate_pdf, generate_ai_pdf, generate_json, generate_markdown
from app.scanner.models import ScanResult, Finding

@pytest.fixture
def sample_result():
    return ScanResult(
        target="http://example.com",
        grade="B",
        score=75,
        findings=[
            Finding(
                title="Test Finding",
                severity="high",
                category="xss",
                description="Description",
                recommendation="Fix it"
            )
        ],
        logs=[],
        scanned_at=datetime.utcnow(),
        response_time_ms=100
    )

def test_generate_pdf(sample_result):
    """Verify PDF generation returns bytes"""
    pdf_bytes = generate_pdf(sample_result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert b"%PDF" in pdf_bytes

def test_generate_ai_pdf(sample_result):
    """Verify AI PDF generation returns bytes"""
    ai_summary = {
        "global_score": {"numeric": 75, "letter": "B"},
        "executive_summary": "Summary",
        "key_vulnerabilities": [],
        "infrastructure": {},
        "site_map": {"pages": []}
    }
    pdf_bytes = generate_ai_pdf(sample_result, ai_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert b"%PDF" in pdf_bytes

def test_generate_json(sample_result):
    """Verify JSON generation"""
    json_str = generate_json(sample_result)
    assert isinstance(json_str, str)
    assert "http://example.com" in json_str

def test_generate_markdown(sample_result):
    """Verify Markdown generation"""
    md_str = generate_markdown(sample_result)
    assert isinstance(md_str, str)
    assert "# AuditAI Security Report" in md_str
    assert "Test Finding" in md_str
