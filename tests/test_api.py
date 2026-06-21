import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from taskforge.main import app, get_engine
from taskforge.database import Base, get_session, Project
from taskforge.llm_provider import MockLLMProvider
from taskforge.engine import TaskForgeEngine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Setup in-memory database for testing isolation
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def override_get_session():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Bypass API key authentication for API tests
from taskforge.config import settings
settings.API_KEY = None

def override_get_engine():
    # Use MockLLMProvider for API tests to avoid calling real Ollama endpoint
    mock_provider = MockLLMProvider()
    return TaskForgeEngine(
        architect_provider=mock_provider,
        specialist_provider=mock_provider,
        refiner_provider=mock_provider
    )

# Apply dependency overrides
app.dependency_overrides[get_session] = override_get_session
app.dependency_overrides[get_engine] = override_get_engine

@pytest.mark.asyncio
async def test_decompose_endpoint_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/decompose", json={"goal": "Build a web app"})
        assert response.status_code == 200
        
        data = response.json()
        assert "task_tree" in data
        assert data["task_tree"]["goal"] == "Build a web app"
        assert len(data["task_tree"]["categories"]) > 0
        
        # Verify schema structure of categories and tasks
        category = data["task_tree"]["categories"][0]
        assert "name" in category
        assert "tasks" in category
        assert len(category["tasks"]) > 0
        
        task = category["tasks"][0]
        assert "id" in task
        assert "title" in task
        assert "description" in task
        assert "estimated_hours" in task
        assert "dependencies" in task
        assert "usage" in data
        assert data["cached"] is False

@pytest.mark.asyncio
async def test_decompose_endpoint_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Empty string goal should fail validation
        response = await ac.post("/decompose", json={"goal": ""})
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_list_projects_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Assert list is initially empty
        response = await ac.get("/projects")
        assert response.status_code == 200
        assert response.json() == []

        # 2. Decompose a goal to insert a project
        post_response = await ac.post("/decompose", json={"goal": "Build mobile application"})
        assert post_response.status_code == 200

        # 3. Assert project lists correctly with database persistence
        get_response = await ac.get("/projects")
        assert get_response.status_code == 200
        data = get_response.json()
        assert len(data) == 1
        assert data[0]["goal"] == "Build mobile application"
        assert "task_tree" in data[0]
        assert "id" in data[0]
        assert "created_at" in data[0]
        assert "usage" in data[0]

@pytest.mark.asyncio
async def test_decompose_caching():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First call - fresh generation
        resp1 = await ac.post("/decompose", json={"goal": "Unique Cache Test"})
        assert resp1.status_code == 200
        assert resp1.json()["cached"] is False
        
        # Second call - loaded from cache
        resp2 = await ac.post("/decompose", json={"goal": "Unique Cache Test"})
        assert resp2.status_code == 200
        assert resp2.json()["cached"] is True

@pytest.mark.asyncio
async def test_list_projects_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Add 3 projects
        await ac.post("/decompose", json={"goal": "Project A"})
        await ac.post("/decompose", json={"goal": "Project B"})
        await ac.post("/decompose", json={"goal": "Project C"})
        
        # Test Limit 2
        res_limit = await ac.get("/projects?limit=2")
        assert res_limit.status_code == 200
        assert len(res_limit.json()) == 2
        
        # Test Offset 2
        res_offset = await ac.get("/projects?limit=2&offset=2")
        assert res_offset.status_code == 200
        assert len(res_offset.json()) == 1

@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        # Health check might return 503 if local Ollama server is not running, which is expected.
        # But it should return a valid JSON structure describing components health.
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "ollama" in data
        assert "openrouter" in data
