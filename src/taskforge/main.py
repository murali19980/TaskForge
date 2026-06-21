import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import httpx

from taskforge.config import settings
from taskforge.database import init_db, get_session, Project
from taskforge.models import TaskTree, UsageStats, DecomposeResponse
from taskforge.llm_provider import OllamaProvider, OpenRouterProvider
from taskforge.engine import TaskForgeEngine

logger = logging.getLogger("taskforge.main")

class DecomposeRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=1000, description="The high-level goal to decompose")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await init_db()
    
    # Check Ollama connectivity and log status
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(settings.OLLAMA_HOST)
            if res.status_code == 200:
                logger.info(f"Ollama check succeeded: reachable at {settings.OLLAMA_HOST}")
            else:
                logger.warning(f"Ollama check returned status {res.status_code} at {settings.OLLAMA_HOST}")
    except Exception as e:
        logger.error(f"Ollama is unreachable at startup on {settings.OLLAMA_HOST}: {str(e)}")
        
    yield
    # Shutdown
    pass

app = FastAPI(
    title="TaskForge API",
    description="Recursive AI task decomposition engine using local Ollama and OpenRouter models",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configurations loaded from environment
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Bearer Security
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not settings.API_KEY:
        # Bypassed if API_KEY setting is empty/None
        return None
    if not credentials or credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return credentials.credentials

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    logger.error(f"Pydantic validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Structured output validation failed"}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    logger.error(f"ValueError raised: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "message": "Invalid request parameter"}
    )

def get_engine() -> TaskForgeEngine:
    # If OpenRouter is configured, setup hybrid pipeline. Else fallback to Ollama for all steps.
    if settings.OPENROUTER_API_KEY:
        logger.info("Initializing TaskForgeEngine in hybrid mode (OpenRouter Architect/Refiner + Ollama Specialists)")
        architect = OpenRouterProvider()
        specialist = OllamaProvider()
        refiner = OpenRouterProvider()
    else:
        logger.info("Initializing TaskForgeEngine in local-only mode (Ollama for all steps)")
        architect = OllamaProvider()
        specialist = OllamaProvider()
        refiner = OllamaProvider()
        
    return TaskForgeEngine(
        architect_provider=architect,
        specialist_provider=specialist,
        refiner_provider=refiner
    )

@app.post("/decompose", response_model=DecomposeResponse)
async def decompose(
    request: DecomposeRequest,
    engine: TaskForgeEngine = Depends(get_engine),
    db: AsyncSession = Depends(get_session),
    _auth = Depends(verify_api_key)
):
    try:
        # 1. Database-backed cache check
        result = await db.execute(
            select(Project).filter(Project.goal == request.goal).order_by(Project.created_at.desc())
        )
        existing_project = result.scalars().first()
        if existing_project:
            logger.info(f"Database cache hit for goal: '{request.goal}'")
            tree = TaskTree.model_validate(existing_project.task_tree_json)
            usage = UsageStats(
                prompt_tokens=existing_project.prompt_tokens,
                completion_tokens=existing_project.completion_tokens,
                total_tokens=existing_project.total_tokens,
                estimated_cost_usd=existing_project.estimated_cost_usd
            )
            return DecomposeResponse(task_tree=tree, usage=usage, cached=True)

        # 2. Run the decomposition engine
        response = await engine.decompose_goal(request.goal)
        
        # 3. Save to database
        db_project = Project(
            goal=request.goal,
            task_tree_json=response.task_tree.model_dump(),
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=response.usage.estimated_cost_usd
        )
        db.add(db_project)
        # Flush to DB (get_session will commit automatically)
        await db.flush()
        
        return response
    except Exception as e:
        logger.exception("Goal decomposition failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decomposition failed: {str(e)}"
        )

@app.get("/projects")
async def list_projects(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _auth = Depends(verify_api_key)
):
    # Pagination boundaries validation
    if limit < 1:
        limit = 10
    elif limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    try:
        result = await db.execute(
            select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
        projects = result.scalars().all()
        return [
            {
                "id": p.id,
                "goal": p.goal,
                "task_tree": p.task_tree_json,
                "usage": {
                    "prompt_tokens": p.prompt_tokens,
                    "completion_tokens": p.completion_tokens,
                    "total_tokens": p.total_tokens,
                    "estimated_cost_usd": p.estimated_cost_usd
                },
                "created_at": p.created_at.isoformat()
            }
            for p in projects
        ]
    except Exception as e:
        logger.exception("Failed to query projects")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@app.get("/health")
async def health(db: AsyncSession = Depends(get_session)):
    health_status = {
        "status": "healthy",
        "database": "unhealthy",
        "ollama": "unhealthy",
        "openrouter": "unconfigured"
    }

    # Verify Database connectivity
    try:
        await db.execute(select(1))
        health_status["database"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed on database query: {str(e)}")
        health_status["status"] = "unhealthy"

    # Verify local Ollama API
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(settings.OLLAMA_HOST)
            if res.status_code == 200:
                health_status["ollama"] = "healthy"
            else:
                health_status["ollama"] = f"unhealthy (status {res.status_code})"
                health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Health check failed to contact Ollama: {str(e)}")
        health_status["status"] = "unhealthy"

    # Verify OpenRouter API (if key is set)
    if settings.OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                res = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                if res.status_code == 200:
                    health_status["openrouter"] = "healthy"
                else:
                    health_status["openrouter"] = f"unhealthy (status {res.status_code})"
                    health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(f"Health check failed to contact OpenRouter: {str(e)}")
            health_status["openrouter"] = "unhealthy"
            health_status["status"] = "unhealthy"
    else:
        health_status["openrouter"] = "disabled (no API key)"

    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
    return health_status
