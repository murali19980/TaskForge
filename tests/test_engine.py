import pytest
import asyncio
from pydantic import ValidationError
from taskforge.engine import TaskForgeEngine
from taskforge.llm_provider import MockLLMProvider, FailingMockLLM, DependencyMapResponse
from taskforge.models import CategoriesResponse, TasksResponse, TaskTree

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
    resp_web = await provider.generate_json("Build a web app", CategoriesResponse)
    assert "Frontend" in resp_web.categories
    assert "Backend" in resp_web.categories

    # Test mobile goal triggers mobile categories
    resp_mobile = await provider.generate_json("Build an iOS mobile application", CategoriesResponse)
    assert "iOS App" in resp_mobile.categories
    assert "Android App" in resp_mobile.categories

    # Test default categories
    resp_default = await provider.generate_json("Learn to cook pizza", CategoriesResponse)
    assert "Planning" in resp_default.categories
    assert "Development" in resp_default.categories

@pytest.mark.asyncio
async def test_engine_successful_decomposition():
    provider = SpyingMockProvider()
    engine = TaskForgeEngine(llm=provider)
    
    goal = "Build a web app"
    tree = await engine.decompose_goal(goal)
    
    assert isinstance(tree, TaskTree)
    assert tree.goal == goal
    assert len(tree.categories) > 0
    
    # Check that categories and tasks exist
    for cat in tree.categories:
        assert len(cat.tasks) > 0
        for task in cat.tasks:
            assert task.id is not None
            assert task.estimated_hours >= 0

    # Verify calls happened
    # 1 architect call, N specialist calls (for each category), 1 refiner call
    architect_calls = [c for c in provider.calls if c[1] is CategoriesResponse]
    specialist_calls = [c for c in provider.calls if c[1] is TasksResponse]
    refiner_calls = [c for c in provider.calls if c[1] is DependencyMapResponse]

    assert len(architect_calls) == 1
    assert len(specialist_calls) == len(tree.categories)
    assert len(refiner_calls) == 1

@pytest.mark.asyncio
async def test_engine_retry_with_failing_provider():
    # FailingMockLLM fails twice and succeeds on the 3rd attempt
    failing_provider = FailingMockLLM()
    engine = TaskForgeEngine(llm=failing_provider)
    
    goal = "Test retry"
    tree = await engine.decompose_goal(goal)
    
    assert isinstance(tree, TaskTree)
    # 2 failures on first step, 1 success on first step, 4 specialist calls, and 1 refiner call = 8 total calls
    assert failing_provider.call_count == 8

@pytest.mark.asyncio
async def test_engine_raises_on_empty_goal():
    engine = TaskForgeEngine(llm=MockLLMProvider())
    with pytest.raises(ValueError, match="Goal cannot be empty"):
        await engine.decompose_goal("")

@pytest.mark.asyncio
async def test_engine_invalid_dependencies_handling():
    # A custom mock provider that returns a dependency map pointing to a non-existent task ID
    class BadDependencyProvider(MockLLMProvider):
        async def generate_json(self, prompt: str, expected_schema):
            if expected_schema is DependencyMapResponse:
                return DependencyMapResponse(dependencies={"fe_setup": ["non_existent_id"]})
            return await super().generate_json(prompt, expected_schema)

    bad_provider = BadDependencyProvider()
    engine = TaskForgeEngine(llm=bad_provider)
    
    # Validation error should be raised (Pydantic ValidationError because of missing dependency ref)
    # Tenacity will retry it 3 times and then reraise the ValidationError
    with pytest.raises(ValidationError):
        await engine.decompose_goal("Build a web app")
