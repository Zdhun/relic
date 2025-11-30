import httpx
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = 120.0  # Increased to 120s for larger models

    def is_available(self) -> bool:
        """Checks if Ollama is reachable."""
        try:
            # Simple health check, e.g. listing tags or just root
            # Ollama usually exposes GET /api/tags
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a chat request to Ollama.
        Retries connection a few times if Ollama is warming up.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        
        logger.info(f"Sending request to Ollama at {url} with model {self.model}")
        
        # Retry logic: Try 3 times with 2s delay
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = httpx.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ollama connection failed (attempt {attempt+1}/{max_retries}). Retrying in 2s... Error: {e}")
                    time.sleep(2)
                else:
                    logger.error(f"Ollama connection failed after {max_retries} attempts: {e}")
                    raise
            except httpx.HTTPError as e:
                logger.error(f"Ollama HTTP error: {e}")
                if e.response:
                    logger.error(f"Ollama response body: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Ollama unexpected error: {e}")
                raise

class OpenRouterClient:
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = 60.0

    def is_available(self) -> bool:
        """Checks if OpenRouter is configured (API key present)."""
        # We could do a small test call, but for now just check API key presence
        return bool(self.api_key and self.api_key.strip())

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Sends a chat request to OpenRouter."""
        if not self.is_available():
            raise ValueError("OpenRouter API key is missing")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Optional: Add site URL/name for OpenRouter rankings
            "HTTP-Referer": "http://localhost:3000", 
            "X-Title": "Relic Security Scanner"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            # OpenAI-compatible response format
            # {"choices": [{"message": {"content": "..."}}]}
            choices = data.get("choices", [])
            if not choices:
                return ""
            return choices[0].get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error(f"OpenRouter HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter unexpected error: {e}")
            raise
