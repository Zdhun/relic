import asyncio
from typing import List, Dict, Any, Callable, Awaitable
from urllib.parse import urljoin
from .http_client import HttpClient

class PathDiscoverer:
    """
    Performs dictionary-based path discovery to find sensitive endpoints.
    """
    
    # Common sensitive paths to check
    PATHS_TO_CHECK = [
        "/admin",
        "/login",
        "/auth",
        "/dashboard",
        "/api",
        "/config",
        "/backup",
        "/backup.zip",
        "/phpinfo.php",
        "/.env",
        "/.git/HEAD",
        "/robots.txt",
        "/sitemap.xml"
    ]
    
    # Paths that are considered "sensitive" if found
    SENSITIVE_MARKERS = {
        "/admin", "/.env", "/.git/HEAD", "/backup.zip", "/phpinfo.php", "/config"
    }

    # Login path patterns to detect redirects
    LOGIN_PATTERNS = [
        "/login",
        "/signin",
        "/sign-in",
        "/auth/login",
        "/auth/signin",
        "/account/login",
        "/user/login"
    ]

    def __init__(self, http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None):
        self.http_client = http_client
        self.log_callback = log_callback

    async def run(self, base_url: str) -> List[Dict[str, Any]]:
        """
        Probes the base_url for common paths.
        """
        if self.log_callback:
            await self.log_callback("INFO", "Starting path discovery...")
            
        discovered_paths = []
        
        # Ensure base_url doesn't end with slash for cleaner joins if paths start with slash
        # But urljoin handles it well.
        
        tasks = []
        for path in self.PATHS_TO_CHECK:
            tasks.append(self._check_path(base_url, path))
            
        # Run concurrently
        results = await asyncio.gather(*tasks)
        
        # Filter out None results (if any) and add to list
        interesting_count = 0
        for res in results:
            if res:
                discovered_paths.append(res)
                if res.get("sensitive"):
                    interesting_count += 1
        
        if self.log_callback:
            await self.log_callback("INFO", f"Path discovery completed. Found {interesting_count} interesting endpoints.")
            
        return discovered_paths

    async def _check_path(self, base_url: str, path: str) -> Dict[str, Any]:
        full_url = urljoin(base_url, path)
        
        try:
            # Use GET to follow redirects and see final URL
            response = await self.http_client.get(full_url)
            
            if response:
                status = response.status_code
                
                # We are interested in 200, 301, 302, 401, 403
                if status in [200, 301, 302, 401, 403]:
                    is_sensitive_pattern = path in self.SENSITIVE_MARKERS
                    
                    # Analyze for login redirect
                    final_url = str(response.url)
                    final_path = final_url.replace(response.url.scheme + "://" + response.url.netloc, "")
                    
                    # Check if final URL matches login patterns
                    is_login_redirect = False
                    for login_pat in self.LOGIN_PATTERNS:
                        if login_pat in final_path.lower():
                            is_login_redirect = True
                            break
                    
                    # Determine classification
                    access_control = "unknown"
                    sensitive = False
                    reason = ""
                    
                    if is_sensitive_pattern:
                        if is_login_redirect:
                            sensitive = False
                            access_control = "login_redirect"
                            reason = "Endpoint appears protected by authentication (redirect to login)."
                        elif status in [401, 403]:
                            sensitive = False # It's protected, so not "exposed" in a dangerous way (though existence is known)
                            access_control = "restricted"
                            reason = f"Endpoint exists but is restricted ({status})."
                        else:
                            # Direct access (200) or other redirect not to login
                            sensitive = True
                            access_control = "direct"
                            reason = f"Potentially sensitive endpoint exposed: {path}"
                    else:
                        # Non-sensitive path (e.g. robots.txt)
                        sensitive = False
                        access_control = "direct" if status == 200 else "unknown"
                        reason = f"Discovered path: {path}"

                    result = {
                        "url": full_url,
                        "status_code": status,
                        "content_type": response.headers.get("Content-Type", ""),
                        "sensitive": sensitive,
                        "access_control": access_control,
                        "reason": reason,
                        "final_url": final_url
                    }
                        
                    return result
                    
        except Exception:
            pass
            
        return None
