from urllib.parse import urlparse
import ipaddress
import socket

def is_authorized(target: str) -> bool:
    # Allow localhost and private IPs for this starter
    # Also allow specific test domains if needed, but strict by default
    try:
        if not target.startswith(("http://", "https://")):
            target = "http://" + target
            
        parsed = urlparse(target)
        hostname = parsed.hostname
        
        if not hostname:
            return False

        # Check if IP
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback
        except ValueError:
            # Resolve hostname
            try:
                if hostname == "localhost":
                    return True
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
                return ip.is_private or ip.is_loopback
            except socket.gaierror:
                return False # Cannot resolve
    except Exception:
        return False
