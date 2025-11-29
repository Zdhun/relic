from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class TargetInfo:
    scheme: str
    hostname: str
    port: int
    full_url: str

def normalize_target(target: str) -> TargetInfo:
    """
    Normalizes a target string into a TargetInfo object.
    Handles schemes (http/https), defaults, and port extraction.
    """
    target = target.strip()
    
    # Add default scheme if missing
    if "://" not in target:
        target = f"http://{target}"
        
    parsed = urlparse(target)
    
    scheme = parsed.scheme if parsed.scheme in ("http", "https") else "http"
    hostname = parsed.hostname or parsed.path # Handle cases where hostname might be in path if parsing failed oddly, though adding scheme usually fixes it.
    
    # If urlparse fails to extract hostname (e.g. just "localhost"), fallback
    if not hostname:
        # This might happen if target was just "http://" which is invalid, but let's assume valid input for now or simple strings
        hostname = target.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]

    port = parsed.port
    
    if not port:
        port = 443 if scheme == "https" else 80
        
    # Reconstruct full URL to be clean (no trailing slashes if root, or keep path if provided?)
    # Requirement says "GET sur / ou sur le chemin de l'URL fournie".
    # So we keep the path if it exists, else "/"
    path = parsed.path if parsed.path else "/"
    
    # Re-assemble full_url to ensure it's valid
    # We use the normalized scheme and port
    netloc = f"{hostname}:{port}"
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
        
    full_url = f"{scheme}://{netloc}{path}"
    if parsed.query:
        full_url += f"?{parsed.query}"
    
    return TargetInfo(
        scheme=scheme,
        hostname=hostname,
        port=port,
        full_url=full_url
    )
