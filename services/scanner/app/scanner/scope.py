from enum import Enum
from urllib.parse import urlparse, parse_qs
import tldextract
from typing import List, Set, Dict, Optional

class EndpointClass(str, Enum):
    AUTH_SSO = "AUTH_SSO"
    CONTENT_HTML = "CONTENT_HTML"
    API_JSON = "API_JSON"
    STATIC_ASSET = "STATIC_ASSET"
    REDIRECTOR = "REDIRECTOR"
    UNKNOWN = "UNKNOWN"

class ScopeManager:
    def __init__(self):
        # Use default cache dir or disable if needed. Default is usually fine.
        self.extract = tldextract.TLDExtract()

    def get_registrable_domain(self, url: str) -> str:
        """
        Returns the registrable domain (e.g., 'google.com' from 'mail.google.com').
        """
        extracted = self.extract(url)
        if not extracted.suffix:
            return extracted.domain # e.g. localhost
        return f"{extracted.domain}.{extracted.suffix}"

    def is_in_scope(self, url: str, initial_domain: str) -> bool:
        """
        Checks if the URL is within the scope of the initial domain (same registrable domain).
        """
        try:
            target_reg = self.get_registrable_domain(url)
            initial_reg = self.get_registrable_domain(initial_domain)
            return target_reg == initial_reg
        except Exception:
            return False

    def classify_endpoint(self, url: str, method: str = "GET", content_type: str = None) -> EndpointClass:
        """
        Classifies an endpoint based on URL structure, parameters, and content type.
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        params = parse_qs(query)
        
        # 1. Static Assets
        static_exts = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".mp3", ".pdf", ".zip", ".tar", ".gz"}
        if any(path.endswith(ext) for ext in static_exts):
            return EndpointClass.STATIC_ASSET

        # 2. Auth / SSO
        # Check path segments and query params
        auth_keywords = {"login", "signin", "signup", "register", "auth", "oauth", "sso", "saml", "openid", "connect", "consent", "account", "profile", "password", "reset", "session"}
        
        path_segments = set(path.strip("/").split("/"))
        if path_segments & auth_keywords:
            return EndpointClass.AUTH_SSO
            
        if any(kw in query for kw in auth_keywords):
             return EndpointClass.AUTH_SSO

        # 3. Redirectors
        # Look for params that look like URLs or specific keywords
        redirect_keywords = {"redirect", "url", "next", "continue", "dest", "destination", "go", "out", "view", "link", "target", "r", "u"}
        if set(params.keys()) & redirect_keywords:
             return EndpointClass.REDIRECTOR

        # 4. API / JSON
        if content_type and "application/json" in content_type.lower():
            return EndpointClass.API_JSON
        if "/api/" in path or path.endswith(".json") or "/v1/" in path or "/v2/" in path:
            return EndpointClass.API_JSON

        # 5. Content HTML
        if content_type and "text/html" in content_type.lower():
            return EndpointClass.CONTENT_HTML
            
        # Fallback for unknown content types that look like pages
        if not content_type and (path.endswith(".html") or path.endswith(".php") or path.endswith("/") or not "." in path.split("/")[-1]):
             return EndpointClass.CONTENT_HTML

        return EndpointClass.UNKNOWN
