import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.scanner.tls_checks import check_tls

@pytest.fixture
def mock_ssl_context():
    with patch("ssl.create_default_context") as mock_ctx:
        yield mock_ctx

@pytest.fixture
def mock_socket():
    with patch("socket.create_connection") as mock_sock:
        yield mock_sock

def test_tls_check_expired_cert(mock_ssl_context, mock_socket):
    """Verify detection of expired certificate"""
    mock_ssock = MagicMock()
    mock_ssock.version.return_value = "TLSv1.2"
    
    # Expired date
    expired_date = (datetime.utcnow() - timedelta(days=10)).strftime("%b %d %H:%M:%S %Y GMT")
    mock_ssock.getpeercert.return_value = {
        "notAfter": expired_date,
        "subject": [],
        "issuer": []
    }
    
    mock_ssl_context.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
    
    findings, _ = check_tls("example.com")
    
    assert any(f.title == "Certificate Expired" for f in findings)

def test_tls_check_near_expiration(mock_ssl_context, mock_socket):
    """Verify detection of certificate near expiration"""
    mock_ssock = MagicMock()
    mock_ssock.version.return_value = "TLSv1.2"
    
    # Expiring soon (10 days)
    soon_date = (datetime.utcnow() + timedelta(days=10)).strftime("%b %d %H:%M:%S %Y GMT")
    mock_ssock.getpeercert.return_value = {
        "notAfter": soon_date,
        "subject": [],
        "issuer": []
    }
    
    mock_ssl_context.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
    
    findings, _ = check_tls("example.com")
    
    assert any(f.title == "Certificate Near Expiration" for f in findings)

def test_tls_check_obsolete_protocol(mock_ssl_context, mock_socket):
    """Verify detection of obsolete TLS protocol"""
    mock_ssock = MagicMock()
    mock_ssock.version.return_value = "TLSv1" # Obsolete
    
    valid_date = (datetime.utcnow() + timedelta(days=100)).strftime("%b %d %H:%M:%S %Y GMT")
    mock_ssock.getpeercert.return_value = {
        "notAfter": valid_date,
        "subject": [],
        "issuer": []
    }
    
    mock_ssl_context.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
    
    findings, _ = check_tls("example.com")
    
    assert any(f.title == "Obsolete TLS Protocol" for f in findings)

def test_tls_check_valid(mock_ssl_context, mock_socket):
    """Verify valid TLS configuration"""
    mock_ssock = MagicMock()
    mock_ssock.version.return_value = "TLSv1.3"
    
    valid_date = (datetime.utcnow() + timedelta(days=100)).strftime("%b %d %H:%M:%S %Y GMT")
    mock_ssock.getpeercert.return_value = {
        "notAfter": valid_date,
        "subject": [],
        "issuer": []
    }
    
    mock_ssl_context.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
    
    findings, cert_info = check_tls("example.com")
    
    assert len(findings) == 0
    assert cert_info is not None
    assert cert_info["protocol"] == "TLSv1.3"
