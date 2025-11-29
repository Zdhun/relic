import os
from typing import List
from pydantic import BaseModel, Field

class Settings(BaseModel):
    DEFAULT_TIMEOUT: float = Field(default=10.0, description="Default HTTP timeout in seconds")
    MAX_RETRIES: int = Field(default=2, description="Max retries for HTTP requests")
    USER_AGENT: str = Field(default="AuditAI-Security-Scanner/1.0", description="User-Agent string")
    SCAN_PORTS: List[int] = Field(
        default=[21, 22, 25, 80, 110, 143, 443, 3306, 5432, 6379, 8080, 8443], 
        description="Ports to scan"
    )
    MAX_CRAWL_URLS: int = Field(default=20, description="Max URLs to crawl")
    RATE_LIMIT_DELAY: float = Field(default=0.3, description="Delay between requests in seconds")
    PORT_SCAN_TIMEOUT: float = Field(default=1.0, description="Timeout for port scan in seconds")

    RESPECT_ROBOTS: bool = Field(default=False, description="Whether to respect robots.txt")
    CRAWL_SCOPE: str = Field(default="subdomains", description="Crawl scope: 'host', 'subdomains', 'path'")
    STATIC_EXTENSIONS: List[str] = Field(
        default=["css", "js", "png", "jpg", "jpeg", "gif", "svg", "ico", "woff", "woff2", "ttf", "eot", "mp4", "webm", "mp3", "pdf", "zip", "tar", "gz"],
        description="Extensions to skip during crawl"
    )
    BLIND_SQLI_THRESHOLD: float = Field(default=5.0, description="Threshold in seconds for time-based SQLi detection")

    @classmethod
    def load(cls) -> "Settings":
        # Basic env var loading for key fields
        return cls(
            DEFAULT_TIMEOUT=float(os.getenv("SCANNER_DEFAULT_TIMEOUT", 10.0)),
            MAX_RETRIES=int(os.getenv("SCANNER_MAX_RETRIES", 2)),
            USER_AGENT=os.getenv("SCANNER_USER_AGENT", "AuditAI-Security-Scanner/1.0"),
            MAX_CRAWL_URLS=int(os.getenv("SCANNER_MAX_CRAWL_URLS", 20)),
            RATE_LIMIT_DELAY=float(os.getenv("SCANNER_RATE_LIMIT_DELAY", 0.3)),
            PORT_SCAN_TIMEOUT=float(os.getenv("SCANNER_PORT_SCAN_TIMEOUT", 1.0)),
            RESPECT_ROBOTS=os.getenv("SCANNER_RESPECT_ROBOTS", "false").lower() == "true",
            CRAWL_SCOPE=os.getenv("SCANNER_CRAWL_SCOPE", "subdomains"),
            BLIND_SQLI_THRESHOLD=float(os.getenv("SCANNER_BLIND_SQLI_THRESHOLD", 5.0)),
        )

settings = Settings.load()
