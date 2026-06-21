import pytest
import httpx
from taskforge.config import settings
from taskforge.llm_provider import OllamaProvider
from taskforge.models import CategoriesResponse, TasksResponse, DependencyMapResponse

def is_ollama_reachable() -> bool:
    try:
        response = httpx.get(settings.OLLAMA_HOST, timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

@pytest.mark.skipif(not is_ollama_reachable(), reason="Ollama is not running/reachable at startup")
@pytest.mark.asyncio
async def test_real_ollama_generate_categories():
    provider = OllamaProvider()
    # Pulling a simple goal
    prompt = "Decompose the goal: 'Create a personal website'"
    
    categories_resp, usage = await provider.generate_json(prompt, CategoriesResponse)
    
    assert isinstance(categories_resp, CategoriesResponse)
    assert len(categories_resp.categories) > 0
    assert usage.prompt_tokens >= 0
    assert usage.completion_tokens >= 0
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens
    assert usage.estimated_cost_usd == 0.0  # Local Ollama is free!
