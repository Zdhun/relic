import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
from services.scanner.app.scanner.http_client import HttpClient

async def test_retry_logic():
    print("Testing Retry Logic...")
    
    # Mock log callback
    mock_log = AsyncMock()
    
    client = HttpClient(timeout=1, rate_limit=10, log_callback=mock_log)
    
    # Mock httpx.AsyncClient.get to raise TimeoutException on first call, then succeed
    with patch("httpx.AsyncClient.get", side_effect=[httpx.TimeoutException("Timeout!"), MagicMock(status_code=200, url="http://example.com", history=[], headers={})]) as mock_get:
        response = await client.get("http://example.com")
        
        if response and response.status_code == 200:
            print("SUCCESS: Retry worked, got 200 OK.")
        else:
            print("FAILURE: Retry failed.")
            
        # Check history
        if client.history:
            entry = client.history[0]
            print(f"Metrics: duration={entry.get('duration_ms')}ms, retries={entry.get('retry_count')}")
            if entry.get('retry_count') == 1:
                print("SUCCESS: Retry count is correct (1).")
            else:
                print(f"FAILURE: Retry count is {entry.get('retry_count')}, expected 1.")
        else:
            print("FAILURE: No history recorded.")

async def test_rate_limit():
    print("\nTesting Rate Limiting (3 req/sec)...")
    client = HttpClient(timeout=1, rate_limit=3)
    
    start_time = time.time()
    
    # Mock successful response
    mock_response = MagicMock(status_code=200, url="http://example.com", history=[], headers={})
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        for i in range(4):
            await client.get(f"http://example.com/{i}")
            
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Sent 4 requests in {duration:.2f} seconds.")
    
    # 4 requests with 3 req/sec limit:
    # Req 1: t=0
    # Req 2: t=0.33
    # Req 3: t=0.66
    # Req 4: t=1.0
    # Expected duration approx 1.0s
    
    if duration >= 0.9:
        print("SUCCESS: Rate limiting appears to work (duration >= 0.9s).")
    else:
        print("FAILURE: Too fast! Rate limiting might be broken.")

async def main():
    await test_retry_logic()
    await test_rate_limit()

if __name__ == "__main__":
    # Add project root to path
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    
    asyncio.run(main())
