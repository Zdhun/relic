"""
Policy Module Unit Tests
========================
Tests for target authorization policy enforcement.

Tests cover:
- URL validation
- User acknowledgement gate
- Complete scan request validation
"""

import pytest
from app.policy import (
    validate_url,
    check_acknowledgement,
    validate_scan_request,
    PolicyResult,
    PolicyError,
)


class TestValidateUrl:
    """Tests for URL validation."""
    
    def test_valid_https_url(self):
        """HTTPS URL should be valid."""
        result = validate_url("https://example.com")
        assert result.allowed
    
    def test_valid_http_url(self):
        """HTTP URL should be valid."""
        result = validate_url("http://example.com")
        assert result.allowed
    
    def test_url_without_scheme(self):
        """URL without scheme should be valid (defaults to https)."""
        result = validate_url("example.com")
        assert result.allowed
    
    def test_url_with_path(self):
        """URL with path should be valid."""
        result = validate_url("https://example.com/path/to/page")
        assert result.allowed
    
    def test_url_with_port(self):
        """URL with port should be valid."""
        result = validate_url("https://example.com:8080")
        assert result.allowed
    
    def test_localhost_url(self):
        """Localhost URL should be valid."""
        result = validate_url("http://localhost:3000")
        assert result.allowed
    
    def test_ip_address_url(self):
        """IP address URL should be valid."""
        result = validate_url("http://192.168.1.1")
        assert result.allowed
    
    def test_public_ip_url(self):
        """Public IP URL should be valid (no network restrictions)."""
        result = validate_url("http://8.8.8.8")
        assert result.allowed
    
    def test_ftp_scheme_rejected(self):
        """FTP scheme should be rejected."""
        result = validate_url("ftp://example.com")
        assert not result.allowed
        assert result.error_code == PolicyError.UNSUPPORTED_SCHEME
    
    def test_ssh_scheme_rejected(self):
        """SSH scheme should be rejected."""
        result = validate_url("ssh://example.com")
        assert not result.allowed
        assert result.error_code == PolicyError.UNSUPPORTED_SCHEME
    
    def test_file_scheme_rejected(self):
        """File scheme should be rejected."""
        result = validate_url("file:///etc/passwd")
        assert not result.allowed
        assert result.error_code == PolicyError.UNSUPPORTED_SCHEME


class TestCheckAcknowledgement:
    """Tests for user acknowledgement gate."""
    
    def test_authorized_true_allowed(self):
        """authorized=True should pass."""
        result = check_acknowledgement(True)
        assert result.allowed
    
    def test_authorized_false_rejected(self):
        """authorized=False should be rejected."""
        result = check_acknowledgement(False)
        assert not result.allowed
        assert result.error_code == PolicyError.MISSING_ACKNOWLEDGEMENT


class TestValidateScanRequest:
    """Tests for complete scan request validation."""
    
    def test_missing_acknowledgement_rejected(self):
        """Missing acknowledgement should be rejected first."""
        result = validate_scan_request("https://example.com", authorized=False)
        assert not result.allowed
        assert result.error_code == PolicyError.MISSING_ACKNOWLEDGEMENT
    
    def test_valid_request_allowed(self):
        """Valid request with acknowledgement should pass."""
        result = validate_scan_request("https://example.com", authorized=True)
        assert result.allowed
    
    def test_any_url_allowed_with_acknowledgement(self):
        """Any valid URL should be allowed if user acknowledges."""
        # Public URL
        result = validate_scan_request("https://google.com", authorized=True)
        assert result.allowed
        
        # Public IP
        result = validate_scan_request("http://8.8.8.8", authorized=True)
        assert result.allowed
        
        # Private IP
        result = validate_scan_request("http://192.168.1.1", authorized=True)
        assert result.allowed
        
        # Localhost
        result = validate_scan_request("http://localhost:3000", authorized=True)
        assert result.allowed
    
    def test_invalid_scheme_rejected(self):
        """Invalid scheme should be rejected even with acknowledgement."""
        result = validate_scan_request("ftp://example.com", authorized=True)
        assert not result.allowed
        assert result.error_code == PolicyError.UNSUPPORTED_SCHEME
