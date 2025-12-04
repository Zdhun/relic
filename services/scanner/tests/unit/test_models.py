import pytest
from datetime import datetime
from app.scanner.models import ScanResult, Finding, ScanLogEntry

def test_finding_model():
    """Verify Finding model initialization and defaults"""
    f = Finding(
        title="Title",
        severity="high",
        category="xss",
        description="Desc",
        recommendation="Rec"
    )
    assert f.title == "Title"
    assert f.owasp_refs == []
    assert f.id == ""

def test_scan_log_entry_model():
    """Verify ScanLogEntry model"""
    entry = ScanLogEntry(
        timestamp=datetime.utcnow(),
        level="INFO",
        message="Test"
    )
    assert entry.level == "INFO"

def test_scan_result_model():
    """Verify ScanResult model initialization and defaults"""
    result = ScanResult(
        target="http://example.com",
        grade="A",
        score=100,
        findings=[],
        logs=[],
        scanned_at=datetime.utcnow()
    )
    assert result.scan_status == "ok"
    assert result.visibility_level == "good"
    assert result.blocking_mechanism is None
