"""
AI Analyzer Unit Tests
======================
Tests for the AI analyzer module and provider selection.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.ai.analyzer import AiAnalyzer


@pytest.fixture
def mock_ollama():
    with patch("app.ai.analyzer.OllamaClient") as mock:
        yield mock


@pytest.fixture
def mock_groq():
    with patch("app.ai.analyzer.GroqClient") as mock:
        yield mock


def test_analyzer_initialization(mock_ollama, mock_groq):
    """Verify analyzer initializes all clients."""
    analyzer = AiAnalyzer()
    assert analyzer.ollama_client is not None
    assert analyzer.groq_client is not None


def test_get_status(mock_ollama, mock_groq):
    """Verify status reporting for all providers."""
    mock_ollama.return_value.is_available.return_value = True
    mock_ollama.return_value.model = "gpt-oss:20b"
    mock_ollama.return_value.base_url = "http://localhost:11434"
    
    mock_groq.return_value.is_available.return_value = True
    mock_groq.return_value.model = "llama-3.3-70b-versatile"
    mock_groq.return_value.api_key = "test-key"
    
    analyzer = AiAnalyzer()
    status = analyzer.get_status()
    
    assert status["ollama"]["available"] == True
    assert status["groq"]["available"] == True


@pytest.mark.asyncio
async def test_analyze_explicit_ollama(mock_ollama, mock_groq):
    """Verify explicit provider selection (Ollama)."""
    mock_ollama.return_value.chat = AsyncMock(return_value="Ollama Response")
    
    analyzer = AiAnalyzer()
    response = await (await analyzer.analyze("sys", "user", provider="ollama"))
    
    assert response == "Ollama Response"
    mock_ollama.return_value.chat.assert_called_once()
    mock_groq.return_value.chat.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_explicit_groq(mock_ollama, mock_groq):
    """Verify explicit provider selection (Groq)."""
    mock_groq.return_value.chat = AsyncMock(return_value="Groq Response")
    
    analyzer = AiAnalyzer()
    response = await (await analyzer.analyze("sys", "user", provider="groq"))
    
    assert response == "Groq Response"
    mock_groq.return_value.chat.assert_called_once()
    mock_ollama.return_value.chat.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_fallback_to_groq(mock_ollama, mock_groq):
    """Verify fallback to Groq when Ollama is unavailable."""
    mock_ollama.return_value.is_available.return_value = False
    mock_groq.return_value.is_available.return_value = True
    mock_groq.return_value.chat = AsyncMock(return_value="Groq Response")
    
    analyzer = AiAnalyzer()
    response = await (await analyzer.analyze("sys", "user"))
    
    assert response == "Groq Response"
    mock_groq.return_value.chat.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_no_provider_raises(mock_ollama, mock_groq):
    """Verify ValueError when no provider is available."""
    mock_ollama.return_value.is_available.return_value = False
    mock_groq.return_value.is_available.return_value = False
    
    analyzer = AiAnalyzer()
    
    with pytest.raises(ValueError, match="No AI provider available"):
        await analyzer.analyze("sys", "user")
