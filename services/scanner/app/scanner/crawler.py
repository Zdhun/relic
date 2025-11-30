import asyncio
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict, Any
from .http_client import HttpClient
from ..config import settings

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag in ['a', 'link', 'script', 'img', 'iframe']:
            for attr, value in attrs:
                if attr in ['href', 'src']:
                    if value:
                        self.links.add(value)

from .scope import ScopeManager, EndpointClass

class SimpleCrawler:
    def __init__(self, http_client: HttpClient, log_callback=None):
        self.http_client = http_client
        self.log_callback = log_callback
        self.scope_manager = ScopeManager()

    async def crawl_generator(self, start_url: str, initial_html: str = None, max_urls: int = settings.MAX_CRAWL_URLS):
        """
        Yields discovered assets as they are found.
        """
        visited_urls = set()
        start_parsed = urlparse(start_url)
        
        if self.log_callback:
            await self.log_callback("INFO", f"Starting streaming crawl on {start_url}")

        # Robots.txt check
        allowed_by_robots = True
        if settings.RESPECT_ROBOTS:
            try:
                robots_url = f"{start_parsed.scheme}://{start_parsed.netloc}/robots.txt"
                if self.log_callback:
                    await self.log_callback("INFO", f"Checking robots.txt at {robots_url}")
                
                resp = await self.http_client.get(robots_url)
                if resp and resp.status_code == 200:
                    disallowed_paths = []
                    for line in resp.text.splitlines():
                        if line.strip().lower().startswith("disallow:"):
                            path = line.split(":", 1)[1].strip()
                            if path:
                                disallowed_paths.append(path)
            except Exception as e:
                if self.log_callback:
                    await self.log_callback("WARNING", f"Failed to check robots.txt: {e}")

        # 1. Parse Links
        parser = LinkParser()
        if initial_html:
            parser.feed(initial_html)
        else:
            resp = await self.http_client.get(start_url)
            if resp:
                parser.feed(resp.text)
        
        # 2. Filter & Normalize
        candidates = set()
        for link in parser.links:
            full_url = urljoin(start_url, link)
            parsed = urlparse(full_url)
            
            # Smart Scoping using ScopeManager
            # We respect the CRAWL_SCOPE setting but use ScopeManager for domain logic
            in_scope = False
            
            if settings.CRAWL_SCOPE == "host":
                if parsed.netloc == start_parsed.netloc:
                    in_scope = True
            elif settings.CRAWL_SCOPE == "path":
                if parsed.netloc == start_parsed.netloc and parsed.path.startswith(start_parsed.path):
                    in_scope = True
            else:
                # Default / subdomains: use ScopeManager to check registrable domain
                if self.scope_manager.is_in_scope(full_url, start_url):
                    in_scope = True
            
            if not in_scope:
                continue

            # Static Asset Filtering
            clean_url = full_url.split('#')[0]
            ext = clean_url.split('.')[-1].lower() if '.' in clean_url.split('/')[-1] else ""
            if ext in settings.STATIC_EXTENSIONS:
                continue
                
            # Robots check
            if settings.RESPECT_ROBOTS and 'disallowed_paths' in locals():
                blocked = False
                for dp in disallowed_paths:
                    if parsed.path.startswith(dp):
                        blocked = True
                        break
                if blocked:
                    continue

            if clean_url != start_url and clean_url not in visited_urls:
                candidates.add(clean_url)

        # 3. Probe Candidates
        sorted_candidates = sorted(list(candidates))[:max_urls]
        
        for url in sorted_candidates:
            if self.log_callback:
                await self.log_callback("INFO", f"Discovered asset: {url}")
            
            status_code = None
            content_type = None
            
            # Try HEAD first
            resp = await self.http_client.head(url)
            if not resp or resp.status_code == 405:
                resp = await self.http_client.get(url)
            
            if resp:
                status_code = resp.status_code
                content_type = resp.headers.get("Content-Type")
            
            # Classify endpoint
            classification = self.scope_manager.classify_endpoint(url, content_type=content_type)
            
            asset = {
                "url": url,
                "status_code": status_code,
                "content_type": content_type,
                "classification": classification
            }
            yield asset

    async def crawl(self, start_url: str, initial_html: str = None, max_urls: int = settings.MAX_CRAWL_URLS) -> List[Dict[str, Any]]:
        """
        Legacy crawl method that returns a list.
        """
        discovered_assets = []
        async for asset in self.crawl_generator(start_url, initial_html, max_urls):
            discovered_assets.append(asset)
        
        if self.log_callback:
            await self.log_callback("INFO", f"Mini-crawl completed. Found {len(discovered_assets)} assets.")
            
        return discovered_assets
