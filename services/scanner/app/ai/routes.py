from fastapi import APIRouter
from .analyzer import analyzer

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.get("/providers/status")
async def get_ai_providers_status():
    """
    Returns the availability status of AI providers (Ollama, OpenRouter).
    """
    return analyzer.get_status()
