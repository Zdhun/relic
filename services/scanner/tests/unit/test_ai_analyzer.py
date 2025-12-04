import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.ai.analyzer import AiAnalyzer

@pytest.fixture
def mock_ollama():
    with patch("app.ai.analyzer.OllamaClient") as mock:
        yield mock

@pytest.fixture
def mock_openrouter():
    with patch("app.ai.analyzer.OpenRouterClient") as mock:
        yield mock

def test_analyzer_initialization(mock_ollama, mock_openrouter):
    """Verify analyzer initializes clients"""
    analyzer = AiAnalyzer()
    assert analyzer.ollama_client is not None
    assert analyzer.openrouter_client is not None

def test_get_status(mock_ollama, mock_openrouter):
    """Verify status reporting"""
    mock_ollama.return_value.is_available.return_value = True
    mock_ollama.return_value.model = "llama2"
    mock_ollama.return_value.base_url = "http://localhost:11434"
    
    mock_openrouter.return_value.is_available.return_value = False
    mock_openrouter.return_value.model = "gpt-4"
    mock_openrouter.return_value.api_key = None
    
    analyzer = AiAnalyzer()
    status = analyzer.get_status()
    
    assert status["ollama"]["available"] == True
    assert status["openrouter"]["available"] == False

@pytest.mark.asyncio
async def test_analyze_explicit_ollama(mock_ollama, mock_openrouter):
    """Verify explicit provider selection (Ollama)"""
    mock_ollama.return_value.chat = AsyncMock(return_value="Ollama Response")
    
    analyzer = AiAnalyzer()
    # analyze returns the coroutine from chat(), so we need to await it
    response = await (await analyzer.analyze("sys", "user", provider="ollama"))
    
    assert response == "Ollama Response"
    mock_ollama.return_value.chat.assert_called_once()
    mock_openrouter.return_value.chat.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_fallback_logic(mock_ollama, mock_openrouter):
    """Verify fallback to OpenRouter when Ollama is unavailable"""
    mock_ollama.return_value.is_available.return_value = False
    mock_openrouter.return_value.chat = AsyncMock(return_value="OpenRouter Response")
    
    analyzer = AiAnalyzer()
    response = await (await analyzer.analyze("sys", "user"))
    
    assert response == "OpenRouter Response"
    mock_openrouter.return_value.chat.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_fallback_on_error(mock_ollama, mock_openrouter):
    """Verify fallback to OpenRouter when Ollama raises exception"""
    mock_ollama.return_value.is_available.return_value = True
    mock_ollama.return_value.chat.side_effect = Exception("Ollama Error")
    
    mock_openrouter.return_value.chat = AsyncMock(return_value="OpenRouter Response")
    
    analyzer = AiAnalyzer()
    response = await (await analyzer.analyze("sys", "user"))
    
    assert response == "OpenRouter Response"
    mock_openrouter.return_value.chat.assert_called_once()
