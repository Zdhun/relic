import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

@pytest.fixture
def sample_scan_results() -> Dict[str, Any]:
    """Sample scan results for testing"""
    return {
        "url": "https://example.com",
        "timestamp": datetime.now(),
        "headers": {
            "Server": "Apache/2.4.1",
            "X-Frame-Options": "SAMEORIGIN"
        },
        "vulnerabilities": [
            {
                "type": "XSS",
                "severity": "high",
                "parameter": "search",
                "payload": "<script>alert('test')</script>"
            },
            {
                "type": "Missing HSTS",
                "severity": "medium"
            }
        ],
        "open_ports": [80, 443],
        "crawled_urls": ["https://example.com", "https://example.com/about"]
    }

@pytest.fixture
def sample_ai_report(sample_scan_results) -> Dict[str, Any]:
    """Sample AI analysis report"""
    return {
        "score": 65,
        "grade": "D",
        "summary": "Le site présente plusieurs failles critiques.",
        "top_vulnerabilities": [
            {
                "name": "XSS Reflected",
                "technical_explanation": "...",
                "business_impact": "...",
                "remediation": "..."
            }
        ]
    }
