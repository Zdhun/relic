import asyncio
import time
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from ..config import settings, Settings

class HttpClient:
    def __init__(self, config: Settings = settings, log_callback: Callable[[str, str], Awaitable[None]] = None):
        self.settings = config
        self.log_callback = log_callback
        self.client: Optional[httpx.AsyncClient] = None
        self.last_request_time = 0
        self.history: list[Dict[str, Any]] = []

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            verify=False, 
            follow_redirects=True, 
            timeout=self.settings.DEFAULT_TIMEOUT,
            headers={"User-Agent": self.settings.USER_AGENT}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
            self.client = None

    async def _ensure_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(
                verify=False, 
                follow_redirects=True, 
                timeout=self.settings.DEFAULT_TIMEOUT,
                headers={"User-Agent": self.settings.USER_AGENT}
            )

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    async def get(self, url: str, extra_headers: Dict[str, str] = None) -> Optional[httpx.Response]:
        """
        Performs a GET request to the specified URL with rate limiting and retries.
        Returns the response object or None if an error occurs.
        """
        await self._ensure_client()
        
        # Merge headers
        request_headers = {} # Client has default headers
        if extra_headers:
            request_headers.update(extra_headers)

        # Rate Limiting
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.settings.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.settings.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

        if self.log_callback:
            await self.log_callback("INFO", f"Requesting: {url}")

        start_time = time.time()
        retry_count = 0
        
        for attempt in range(self.settings.MAX_RETRIES + 1):
            try:
                response = await self.client.get(url, headers=request_headers)
                
                duration_ms = int((time.time() - start_time) * 1000)
                final_url = str(response.url)
                redirect_chain = [
                    {"status": r.status_code, "location": r.headers.get("Location")}
                    for r in response.history
                ]
                redirect_count = len(redirect_chain)

                if self.log_callback:
                    await self.log_callback("INFO", f"Response: {response.status_code} from {url} ({duration_ms}ms)")
                    await self.log_callback("INFO", f"Final URL: {final_url} (redirects: {redirect_count})")
                
                # Record history
                self.history.append({
                    "url": url,
                    "requested_url": url,
                    "final_url": final_url,
                    "redirect_chain": redirect_chain,
                    "method": "GET",
                    "request_headers": dict(response.request.headers),
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_ms": duration_ms,
                    "retry_count": retry_count
                })
                
                return response
                
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                if attempt < self.settings.MAX_RETRIES:
                    retry_count += 1
                    if self.log_callback:
                        await self.log_callback("WARNING", f"Request failed ({type(e).__name__}), retrying... ({retry_count}/{self.settings.MAX_RETRIES})")
                    await asyncio.sleep(1) # Wait a bit before retry
                    continue
                else:
                    # Log error or handle it in the engine
                    print(f"Request error for {url}: {e}")
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.history.append({
                        "url": url,
                        "method": "GET",
                        "request_headers": dict(request_headers), # Approximation
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                        "duration_ms": duration_ms,
                        "retry_count": retry_count
                    })
                    
                    return None
                    
            except Exception as e:
                print(f"Unexpected error for {url}: {e}")
                return None

    async def head(self, url: str) -> Optional[httpx.Response]:
        """
        Performs a HEAD request to the specified URL.
        """
        await self._ensure_client()
        
        # Rate Limiting (reusing logic)
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.settings.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.settings.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

        if self.log_callback:
            await self.log_callback("INFO", f"Checking (HEAD): {url}")

        try:
            response = await self.client.head(url)
            return response
        except Exception as e:
            # HEAD failed, might be 405 or connection error
            return None
