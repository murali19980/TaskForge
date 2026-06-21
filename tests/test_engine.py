import pytest
import asyncio
from pydantic import ValidationError
from taskforge.engine import TaskForgeEngine
from taskforge.llm_provider import MockLLMProvider, FailingMockLLM, DependencyMapResponse
from taskforge.models import CategoriesResponse, TasksResponse, TaskTree, DecomposeResponse, UsageStats

class SpyingMockProvider(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def generate_json(self, prompt: str, expected_schema):
        self.calls.append((prompt, expected_schema))
        return await super().generate_json(prompt, expected_schema)

@pytest.mark.asyncio
async def test_mock_provider_goals():
    provider = MockLLMProvider()
    
    # Test website/web app goal triggers web categories
    resp_web, _ = await provider.generate_json("Build a web app", CategoriesResponse)
    assert "Frontend" in resp_web.categories
    assert "Backend" in resp_web.categories

    # Test mobile goal triggers mobile categories
    resp_mobile, _ = await provider.generate_json("Build an iOS mobile application", CategoriesResponse)
    assert "iOS App" in resp_mobile.categories
    assert "Android App" in resp_mobile.categories

    # Test default categories
    resp_default, _ = await provider.generate_json("Learn to cook pizza", CategoriesResponse)
    assert "Planning" in resp_default.categories
    assert "Development" in resp_default.categories

@pytest.mark.asyncio
async def test_engine_successful_decomposition():
    provider = SpyingMockProvider()
    engine = TaskForgeEngine(
        architect_provider=provider,
        specialist_provider=provider,
        refiner_provider=provider
    )
    
    goal = "Build a web app"
    response = await engine.decompose_goal(goal)
    
    assert isinstance(response, DecomposeResponse)
    tree = response.task_tree
    assert tree.goal == goal
    assert len(tree.categories) > 0
    
    # Check that categories and tasks exist
    for cat in tree.categories:
        assert len(cat.tasks) > 0
        for task in cat.tasks:
            assert task.id is not None
            assert task.estimated_hours >= 0

    # Verify calls happened
    architect_calls = [c for c in provider.calls if c[1] is CategoriesResponse]
    specialist_calls = [c for c in provider.calls if c[1] is TasksResponse]
    refiner_calls = [c for c in provider.calls if c[1] is DependencyMapResponse]

    assert len(architect_calls) == 1
    assert len(specialist_calls) == len(tree.categories)
    assert len(refiner_calls) == 1

@pytest.mark.asyncio
async def test_engine_retry_with_failing_provider():
    failing_provider = FailingMockLLM()
    engine = TaskForgeEngine(
        architect_provider=failing_provider,
        specialist_provider=failing_provider,
        refiner_provider=failing_provider
    )
    
    goal = "Test retry"
    response = await engine.decompose_goal(goal)
    
    assert isinstance(response, DecomposeResponse)
    tree = response.task_tree
    assert tree.goal == goal
    assert failing_provider.call_count == 8

@pytest.mark.asyncio
async def test_engine_raises_on_empty_goal():
    mock_p = MockLLMProvider()
    engine = TaskForgeEngine(
        architect_provider=mock_p,
        specialist_provider=mock_p,
        refiner_provider=mock_p
    )
    with pytest.raises(ValueError, match="Goal cannot be empty"):
        await engine.decompose_goal("")

@pytest.mark.asyncio
async def test_engine_invalid_dependencies_handling():
    class BadDependencyProvider(MockLLMProvider):
        async def generate_json(self, prompt: str, expected_schema):
            if expected_schema is DependencyMapResponse:
                # Return dependency mapping pointing to a non-existent task ID
                usage = UsageStats(prompt_tokens=10, completion_tokens=10, total_tokens=20)
                return DependencyMapResponse(dependencies={"frontend_fe_setup": ["non_existent_id"]}), usage
            return await super().generate_json(prompt, expected_schema)

    bad_provider = BadDependencyProvider()
    engine = TaskForgeEngine(
        architect_provider=bad_provider,
        specialist_provider=bad_provider,
        refiner_provider=bad_provider
    )
    
    with pytest.raises(ValidationError):
        await engine.decompose_goal("Build a web app")
