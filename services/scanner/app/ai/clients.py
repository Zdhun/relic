"""
AI Provider Clients
====================
HTTP clients for various LLM providers.

Supported providers:
- Ollama (local inference)
- Groq (cloud provider - default)
"""

import httpx
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for local Ollama LLM inference."""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = 120.0  # Increased to 120s for larger models

    def is_available(self) -> bool:
        """Checks if Ollama is reachable."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False

    async def chat(self, system_prompt: str, user_prompt: str) -> Any:
        """
        Sends a chat request to Ollama.
        Retries connection a few times if Ollama is warming up.
        """
        import json
        import asyncio
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True
        }
        
        logger.info(f"Sending request to Ollama at {url} with model {self.model}")
        
        # Retry logic: Try 3 times with 2s delay
        max_retries = 3
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Starting stream request to {url}")
                    async with client.stream("POST", url, json=payload) as response:
                        logger.debug(f"Response status: {response.status_code}")
                        response.raise_for_status()
                        
                        buffer = b""
                        async for chunk in response.aiter_bytes():
                            buffer += chunk
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                if not line:
                                    continue
                                try:
                                    chunk_data = json.loads(line)
                                    chunk_content = chunk_data.get("message", {}).get("content", "")
                                    if chunk_content:
                                        yield chunk_content
                                    
                                    if chunk_data.get("done"):
                                        break
                                except json.JSONDecodeError:
                                    continue
                                    
                    return

                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Ollama connection failed (attempt {attempt+1}/{max_retries}). Retrying in 2s... Error: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Ollama connection failed after {max_retries} attempts: {e}")
                        raise
                except httpx.HTTPError as e:
                    logger.error(f"Ollama HTTP error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Ollama unexpected error: {e}")
                    raise


class GroqClient:
    """Client for Groq AI API (default cloud provider)."""
    
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = 120.0

    def is_available(self) -> bool:
        """Checks if Groq is configured (API key present)."""
        return bool(self.api_key and self.api_key.strip())

    async def chat(self, system_prompt: str, user_prompt: str) -> Any:
        """Sends a chat request to Groq."""
        if not self.is_available():
            raise ValueError("Groq API key is missing. Set GROQ_API_KEY environment variable.")

        import json
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True
        }

        logger.info(f"Sending request to Groq with model {self.model}")

        try:
            logger.debug(f"Starting Groq stream request to {url}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    logger.debug(f"Groq Response status: {response.status_code}")
                    response.raise_for_status()
                    
                    buffer = b""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith(b"data: "):
                                data_str = line[6:]  # Strip "data: "
                                if data_str.strip() == b"[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(data_str)
                                    choices = chunk_data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
            
            return

        except httpx.HTTPError as e:
            logger.error(f"Groq HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Groq unexpected error: {e}")
            raise
