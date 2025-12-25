import logging
from typing import Dict, Any, Optional
from .clients import OllamaClient, OpenRouterClient, GroqClient
from ..config import settings

logger = logging.getLogger(__name__)

class AiAnalyzer:
    def __init__(self):
        # Initialize clients with config settings
        self.ollama_client = OllamaClient(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.openrouter_client = OpenRouterClient(
            model=settings.OPENROUTER_MODEL,
            api_key=settings.OPENROUTER_API_KEY
        )
        self.groq_client = GroqClient(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY
        )

    def get_status(self) -> Dict[str, Any]:
        """Checks availability of all providers."""
        ollama_status = self.ollama_client.is_available()
        openrouter_status = self.openrouter_client.is_available()
        groq_status = self.groq_client.is_available()
        
        return {
            "ollama": {
                "available": ollama_status,
                "model": self.ollama_client.model,
                "base_url": self.ollama_client.base_url
            },
            "openrouter": {
                "available": openrouter_status,
                "model": self.openrouter_client.model,
                "configured": bool(self.openrouter_client.api_key)
            },
            "groq": {
                "available": groq_status,
                "model": self.groq_client.model,
                "configured": bool(self.groq_client.api_key)
            }
        }

    async def analyze(self, system_prompt: str, user_prompt: str, provider: Optional[str] = None) -> Any:
        """
        Sends prompts to the selected AI provider.
        Returns an async generator yielding chunks of the response.
        If provider is None, tries Ollama first, then falls back to OpenRouter, then Groq.
        """
        if provider == "ollama":
            return self.ollama_client.chat(system_prompt, user_prompt)
        
        if provider == "openrouter":
            return self.openrouter_client.chat(system_prompt, user_prompt)
        
        if provider == "groq":
            return self.groq_client.chat(system_prompt, user_prompt)
            
        # Default behavior: Try Ollama, fallback to OpenRouter, then Groq
        try:
            if self.ollama_client.is_available():
                logger.info("Using Ollama for analysis")
                return self.ollama_client.chat(system_prompt, user_prompt)
            else:
                logger.warning("Ollama unavailable, falling back to OpenRouter")
        except Exception as e:
            logger.warning(f"Ollama failed: {e}. Falling back to OpenRouter")
        
        # Try OpenRouter
        if self.openrouter_client.is_available():
            logger.info("Using OpenRouter for analysis")
            return self.openrouter_client.chat(system_prompt, user_prompt)
        
        # Final fallback to Groq
        if self.groq_client.is_available():
            logger.info("Using Groq for analysis")
            return self.groq_client.chat(system_prompt, user_prompt)
        
        raise ValueError("No AI provider available. Please configure Ollama, OpenRouter, or Groq.")

# Global instance
analyzer = AiAnalyzer()

