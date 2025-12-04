import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scanner.crawler import SimpleCrawler, LinkParser

def test_link_parser():
    """Verify LinkParser extracts links correctly"""
    parser = LinkParser()
    html = """
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <img src="/image.png">
            <script src="/script.js"></script>
            <a href="http://external.com">External</a>
        </body>
    </html>
    """
    parser.feed(html)
    assert "/page1" in parser.links
    assert "/image.png" in parser.links
    assert "/script.js" in parser.links
    assert "http://external.com" in parser.links

@pytest.mark.asyncio
async def test_crawler_generator():
    """Verify crawler generator yields assets"""
    mock_client = AsyncMock()
    
    # Mock robots.txt (404)
    mock_client.get.return_value = MagicMock(status_code=404)
    
    # Mock HEAD/GET for assets
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_client.head.return_value = mock_resp
    
    crawler = SimpleCrawler(mock_client)
    
    initial_html = '<a href="/page1">Page 1</a>'
    
    assets = []
    async for asset in crawler.crawl_generator("http://example.com", initial_html):
        assets.append(asset)
        
    assert len(assets) == 1
    assert assets[0]["url"] == "http://example.com/page1"

@pytest.mark.asyncio
async def test_crawler_scope_filtering():
    """Verify crawler filters out-of-scope links"""
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(status_code=404) # Robots
    
    crawler = SimpleCrawler(mock_client)
    
    # External link
    initial_html = '<a href="http://external.com/page1">External</a>'
    
    assets = []
    async for asset in crawler.crawl_generator("http://example.com", initial_html):
        assets.append(asset)
        
    assert len(assets) == 0

@pytest.mark.asyncio
async def test_crawler_robots_txt():
    """Verify crawler respects robots.txt"""
    mock_client = AsyncMock()
    
    # Mock robots.txt
    mock_robots = MagicMock()
    mock_robots.status_code = 200
    mock_robots.text = "User-agent: *\nDisallow: /private"
    
    # Mock other responses
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    
    def side_effect(url):
        if "robots.txt" in url:
            return mock_robots
        return mock_ok
        
    mock_client.get.side_effect = side_effect
    mock_client.head.return_value = mock_ok
    
    with patch("app.config.settings.RESPECT_ROBOTS", True):
        crawler = SimpleCrawler(mock_client)
        
        initial_html = """
        <a href="/public">Public</a>
        <a href="/private/secret">Private</a>
        """
        
        assets = []
        async for asset in crawler.crawl_generator("http://example.com", initial_html):
            assets.append(asset)
            
        print(f"DEBUG: Assets found: {[a['url'] for a in assets]}")
        assert len(assets) == 1
        assert assets[0]["url"] == "http://example.com/public"
