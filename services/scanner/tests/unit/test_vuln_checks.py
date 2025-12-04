import pytest
from unittest.mock import AsyncMock, MagicMock
from app.scanner.vuln_checks import check_exposure, check_sensitive_url, check_https_enforcement
from app.scanner.models import Finding

@pytest.mark.asyncio
async def test_check_exposure_server_header():
    """Verify detection of exposed Server header"""
    headers = {"Server": "Apache/2.4.41", "Content-Type": "text/html"}
    findings = await check_exposure(headers)
    assert len(findings) == 1
    assert findings[0].title == "Server Header Exposed"
    assert "Apache/2.4.41" in findings[0].description

@pytest.mark.asyncio
async def test_check_exposure_x_powered_by():
    """Verify detection of exposed X-Powered-By header"""
    headers = {"X-Powered-By": "PHP/7.4", "Content-Type": "text/html"}
    findings = await check_exposure(headers)
    assert len(findings) == 1
    assert findings[0].title == "X-Powered-By Header Exposed"

@pytest.mark.asyncio
async def test_check_sensitive_url_found():
    """Verify detection of sensitive files"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE"
    mock_client.get.return_value = mock_response
    
    findings, _ = await check_sensitive_url("http://example.com/.env", mock_client)
    
    assert len(findings) == 1
    assert findings[0].title == "Sensitive Information Exposure"
    assert "AWS Access Key" in findings[0].description

@pytest.mark.asyncio
async def test_check_sensitive_url_not_found():
    """Verify no finding if sensitive file not found"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response
    
    findings, _ = await check_sensitive_url("http://example.com/.env", mock_client)
    
    assert len(findings) == 0

@pytest.mark.asyncio
async def test_check_https_enforcement_missing():
    """Verify detection of missing HTTPS enforcement"""
    mock_client = AsyncMock()
    mock_target_info = MagicMock()
    mock_target_info.scheme = "http"
    mock_target_info.full_url = "http://example.com"
    mock_target_info.hostname = "example.com"
    
    # Mock HTTP response (no redirect)
    mock_http_resp = MagicMock()
    mock_http_resp.url = "http://example.com" # Stays on HTTP
    
    # Mock HTTPS response (reachable)
    mock_https_resp = MagicMock()
    mock_https_resp.status_code = 200
    
    mock_client.get.side_effect = [mock_http_resp, mock_https_resp]
    
    findings, debug = await check_https_enforcement(mock_target_info, mock_client)
    
    assert len(findings) == 1
    assert findings[0].title == "Le site est accessible en HTTP (HTTPS non imposé)"
    assert debug["outcome"] == "fail"

@pytest.mark.asyncio
async def test_check_https_enforcement_present():
    """Verify pass if HTTP redirects to HTTPS"""
    mock_client = AsyncMock()
    mock_target_info = MagicMock()
    mock_target_info.scheme = "http"
    mock_target_info.full_url = "http://example.com"
    
    # Mock HTTP response (redirects to HTTPS)
    mock_http_resp = MagicMock()
    mock_http_resp.url = "https://example.com" 
    
    mock_client.get.return_value = mock_http_resp
    
    findings, debug = await check_https_enforcement(mock_target_info, mock_client)
    
    assert len(findings) == 0
    assert debug["http_redirected_to_https"] == True
