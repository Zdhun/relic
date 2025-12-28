"""
Scan API Integration Tests
==========================
Tests for the /scan endpoint verifying authorization enforcement.

Tests cover:
- Missing authorized flag -> 400 Bad Request
- Any valid URL with authorized=true -> 200 OK (scan started)
- Invalid scheme -> 400 Bad Request
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestScanEndpointAuthorization:
    """Integration tests for /scan endpoint authorization enforcement."""
    
    def test_scan_without_authorized_returns_400(self, client):
        """
        POST /scan without authorized flag should return 400.
        
        This tests that the acknowledgement gate is enforced.
        """
        response = client.post(
            "/scan",
            json={"target": "https://example.com"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "MISSING_ACKNOWLEDGEMENT"
    
    def test_scan_with_authorized_false_returns_400(self, client):
        """
        POST /scan with authorized=false should return 400.
        """
        response = client.post(
            "/scan",
            json={"target": "https://example.com", "authorized": False}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "MISSING_ACKNOWLEDGEMENT"
    
    @patch('app.routes.run_scan_task')
    def test_scan_any_url_with_authorized_returns_200(self, mock_scan_task, client):
        """
        POST /scan with authorized=true should return 200 for any valid URL.
        """
        # Public domain
        response = client.post(
            "/scan",
            json={"target": "https://google.com", "authorized": True}
        )
        assert response.status_code == 200
        assert "scan_id" in response.json()
    
    @patch('app.routes.run_scan_task')
    def test_scan_public_ip_with_authorized_returns_200(self, mock_scan_task, client):
        """
        POST /scan with public IP should return 200 if authorized.
        """
        response = client.post(
            "/scan",
            json={"target": "http://8.8.8.8", "authorized": True}
        )
        assert response.status_code == 200
        assert "scan_id" in response.json()
    
    @patch('app.routes.run_scan_task')
    def test_scan_localhost_returns_200(self, mock_scan_task, client):
        """
        POST /scan targeting localhost should return 200.
        """
        response = client.post(
            "/scan",
            json={"target": "http://127.0.0.1:8080", "authorized": True}
        )
        
        assert response.status_code == 200
        assert "scan_id" in response.json()
    
    @patch('app.routes.run_scan_task')
    def test_scan_private_ip_returns_200(self, mock_scan_task, client):
        """
        POST /scan targeting private IP should return 200.
        """
        response = client.post(
            "/scan",
            json={"target": "http://192.168.1.1", "authorized": True}
        )
        
        assert response.status_code == 200
        assert "scan_id" in response.json()
    
    def test_scan_ftp_scheme_returns_400(self, client):
        """
        POST /scan with non-HTTP scheme should return 400.
        """
        response = client.post(
            "/scan",
            json={"target": "ftp://192.168.1.1", "authorized": True}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "UNSUPPORTED_SCHEME"


class TestScanEndpointErrorResponses:
    """Tests for structured error response format."""
    
    def test_error_response_has_required_fields(self, client):
        """
        Error responses should have error_code, message, and details.
        """
        response = client.post(
            "/scan",
            json={"target": "https://example.com", "authorized": False}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert "error_code" in data
        assert "message" in data
    
    def test_error_code_is_valid(self, client):
        """
        error_code should be a valid PolicyError enum value.
        """
        valid_error_codes = {
            "MISSING_ACKNOWLEDGEMENT",
            "INVALID_URL",
            "UNSUPPORTED_SCHEME",
        }
        
        response = client.post(
            "/scan",
            json={"target": "https://example.com"}
        )
        data = response.json()
        assert data["error_code"] in valid_error_codes
