"""
AI Analyzer Module
==================
Orchestrates AI analysis across multiple providers.

Provider priority (when auto-selecting):
1. Ollama (local) - if available
2. Groq (cloud) - if API key configured
"""

import logging
from typing import Dict, Any, Optional
from .clients import OllamaClient, GroqClient
from ..config import settings

logger = logging.getLogger(__name__)


class AiAnalyzer:
    """
    Main AI analysis orchestrator.
    
    Manages multiple AI providers and handles fallback logic.
    """
    
    def __init__(self):
        # Initialize clients with config settings
        self.ollama_client = OllamaClient(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.groq_client = GroqClient(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Checks availability of all providers.
        
        Returns status dict for each provider including:
        - available: whether the provider can be used
        - model: configured model name
        - configured: whether API key is set (for cloud providers)
        """
        ollama_status = self.ollama_client.is_available()
        groq_status = self.groq_client.is_available()
        
        return {
            "ollama": {
                "available": ollama_status,
                "model": self.ollama_client.model,
                "base_url": self.ollama_client.base_url
            },
            "groq": {
                "available": groq_status,
                "model": self.groq_client.model,
                "configured": bool(self.groq_client.api_key),
                "default": True  # Groq is the default cloud provider
            }
        }

    async def analyze(self, system_prompt: str, user_prompt: str, provider: Optional[str] = None) -> Any:
        """
        Sends prompts to the selected AI provider.
        
        Returns an async generator yielding chunks of the response.
        
        Args:
            system_prompt: System instructions for the AI
            user_prompt: User/scan data prompt
            provider: Explicit provider selection (ollama, groq)
                     If None, tries Ollama first, then Groq.
        
        Returns:
            Async generator yielding response chunks
            
        Raises:
            ValueError: If no provider is available
        """
        # Explicit provider selection
        if provider == "ollama":
            return self.ollama_client.chat(system_prompt, user_prompt)
        
        if provider == "groq":
            return self.groq_client.chat(system_prompt, user_prompt)
            
        # Default behavior: Try Ollama, fallback to Groq
        try:
            if self.ollama_client.is_available():
                logger.info("Using Ollama for analysis (local inference)")
                return self.ollama_client.chat(system_prompt, user_prompt)
            else:
                logger.info("Ollama unavailable, checking Groq")
        except Exception as e:
            logger.warning(f"Ollama failed: {e}. Checking Groq")
        
        # Fallback to Groq
        if self.groq_client.is_available():
            logger.info("Using Groq for analysis (cloud provider)")
            return self.groq_client.chat(system_prompt, user_prompt)
        
        raise ValueError(
            "No AI provider available. Options:\n"
            "1. Start Ollama locally (recommended for privacy)\n"
            "2. Set GROQ_API_KEY for Groq cloud analysis"
        )


# Global instance
analyzer = AiAnalyzer()
