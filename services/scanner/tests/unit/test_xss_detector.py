import pytest
from app.scanner.xss_detector import XSSDetector, XSSContext

@pytest.fixture
def detector():
    return XSSDetector()

def test_generate_payloads(detector):
    """Verify payload generation"""
    canary = "TESTCANARY"
    payloads = detector.generate_payloads(canary)
    
    assert len(payloads) > 0
    assert all(canary in p for p in payloads)
    assert canary in payloads # Simple reflection check

def test_analyze_response_no_reflection(detector):
    """Verify no context found if canary not present"""
    contexts = detector.analyze_response("<html><body>Hello</body></html>", "CANARY")
    assert len(contexts) == 0

def test_analyze_response_html_text(detector):
    """Verify detection in HTML text"""
    html = "<html><body>Hello CANARY</body></html>"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "html_text"
    assert contexts[0].tag_name == "body"
    assert contexts[0].is_executable == False

def test_analyze_response_attribute_value(detector):
    """Verify detection in attribute value"""
    html = "<input value='CANARY'>"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "attribute_value"
    assert contexts[0].attribute_name == "value"
    assert contexts[0].is_executable == False

def test_analyze_response_event_handler(detector):
    """Verify detection in event handler (executable)"""
    html = "<img onmouseover='alert(\"CANARY\")'>"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "attribute_value"
    assert contexts[0].attribute_name == "onmouseover"
    assert contexts[0].is_executable == True

def test_analyze_response_script_block(detector):
    """Verify detection in script block"""
    html = "<script>var x = 'CANARY';</script>"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "script_block"
    assert contexts[0].is_executable == True

def test_analyze_response_comment(detector):
    """Verify detection in comment"""
    html = "<!-- CANARY -->"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "comment"
    assert contexts[0].is_executable == False

def test_analyze_response_javascript_protocol(detector):
    """Verify detection in javascript: protocol"""
    html = "<a href='javascript:alert(\"CANARY\")'>Click</a>"
    contexts = detector.analyze_response(html, "CANARY")
    
    assert len(contexts) == 1
    assert contexts[0].context_type == "attribute_value"
    assert contexts[0].attribute_name == "href"
    assert contexts[0].is_executable == True
