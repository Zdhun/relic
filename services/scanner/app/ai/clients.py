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

    async def chat(self, system_prompt: str, user_prompt: str) -> Any:
        """
        Sends a chat request to Ollama.
        Retries connection a few times if Ollama is warming up.
        """
        import json
        
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
        
        print("\n" + "="*50)
        print(f"--- SYSTEM PROMPT ({self.model}) ---")
        print(system_prompt)
        print("-" * 20)
        print(f"--- USER PROMPT ({self.model}) ---")
        print(user_prompt)
        print("="*50 + "\n")
        print(f"--- STREAMING RESPONSE ({self.model}) ---")
        
        # Retry logic: Try 3 times with 2s delay
        import time
        import asyncio
        max_retries = 3
        # full_response = "" # No longer needed in generator
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    print(f"DEBUG: Starting stream request to {url}")
                    async with client.stream("POST", url, json=payload) as response:
                        print(f"DEBUG: Response status: {response.status_code}")
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
                                        print(chunk_content, end="", flush=True)
                                        yield chunk_content
                                    
                                    if chunk_data.get("done"):
                                        break
                                except json.JSONDecodeError:
                                    continue
                                
                    print("\n" + "="*50 + "\n")
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
                    # Async response body reading is different, skipping logging body for stream error to avoid complexity
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

    async def chat(self, system_prompt: str, user_prompt: str) -> Any:
        """Sends a chat request to OpenRouter."""
        if not self.is_available():
            raise ValueError("OpenRouter API key is missing")

        import json
        
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
            ],
            "stream": True
        }

        print("\n" + "="*50)
        print(f"--- SYSTEM PROMPT ({self.model}) ---")
        print(system_prompt)
        print("-" * 20)
        print(f"--- USER PROMPT ({self.model}) ---")
        print(user_prompt)
        print("="*50 + "\n")
        print(f"--- STREAMING RESPONSE ({self.model}) ---")

        # full_response = "" # No longer needed in generator
        try:
            print(f"DEBUG: Starting OpenRouter stream request to {url}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    print(f"DEBUG: OpenRouter Response status: {response.status_code}")
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
                                data_str = line[6:] # Strip "data: "
                                if data_str.strip() == b"[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(data_str)
                                    choices = chunk_data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            print(content, end="", flush=True)
                                            yield content
                                except json.JSONDecodeError:
                                    continue
            
            print("\n" + "="*50 + "\n")
            return

        except httpx.HTTPError as e:
            logger.error(f"OpenRouter HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter unexpected error: {e}")
            raise


class GroqClient:
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
            raise ValueError("Groq API key is missing")

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

        print("\n" + "="*50)
        print(f"--- SYSTEM PROMPT ({self.model}) ---")
        print(system_prompt)
        print("-" * 20)
        print(f"--- USER PROMPT ({self.model}) ---")
        print(user_prompt)
        print("="*50 + "\n")
        print(f"--- STREAMING RESPONSE ({self.model}) ---")

        try:
            print(f"DEBUG: Starting Groq stream request to {url}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    print(f"DEBUG: Groq Response status: {response.status_code}")
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
                                            print(content, end="", flush=True)
                                            yield content
                                except json.JSONDecodeError:
                                    continue
            
            print("\n" + "="*50 + "\n")
            return

        except httpx.HTTPError as e:
            logger.error(f"Groq HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Groq unexpected error: {e}")
            raise
