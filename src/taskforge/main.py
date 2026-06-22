import logging
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Security, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
import secrets
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import httpx
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import _rate_limit_exceeded_handler

from taskforge.exceptions import ValidationError
from taskforge.config import settings
from taskforge.database import init_db, get_session, Project
from taskforge.models import TaskTree, UsageStats, DecomposeResponse
from taskforge.llm_provider import OllamaProvider, OpenRouterProvider
from taskforge.engine import TaskForgeEngine

logger = logging.getLogger("taskforge.main")

# Background task registry – prevents asyncio from GC-ing running tasks (MED-3)
_background_tasks: set = set()


def _create_engine() -> TaskForgeEngine:
    """Construct the TaskForgeEngine with the appropriate LLM provider configuration."""
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


class DecomposeRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000, description="The high-level goal to decompose")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # CRIT-2: Enforce API_KEY in non-development environments
    env = os.getenv("ENV", "development").lower()
    if not settings.API_KEY:
        if env != "development":
            raise RuntimeError(
                "FATAL: API_KEY environment variable is not set. "
                "TaskForge refuses to start in non-development mode without authentication. "
                "Set ENV=development to bypass this check (local use only)."
            )
        logger.warning(
            "SECURITY WARNING: API_KEY is not configured – running in unauthenticated development mode. "
            "Set API_KEY in your .env to enable authentication."
        )

    # HIGH-6: Warn if running in production without HTTPS
    if env == "production":
        logger.warning(
            "PRODUCTION MODE: Ensure the service is behind a TLS-terminating reverse proxy (e.g. Nginx + Let's Encrypt). "
            "Transmitting Bearer tokens over plain HTTP is a critical security risk."
        )

    # Startup: initialize database tables
    await init_db()

    # MED-6: Construct engine singleton once – semaphores are shared across all requests
    app.state.engine = _create_engine()

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
    # Shutdown – cancel any remaining background tasks
    for t in list(_background_tasks):
        t.cancel()


try:
    _api_version = pkg_version("taskforge")
except Exception:
    _api_version = "1.0.0"

app = FastAPI(
    title="TaskForge API",
    description="Recursive AI task decomposition engine using local Ollama and OpenRouter models",
    version=_api_version,
    lifespan=lifespan
)

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configurations loaded from environment
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if origins:
    allow_creds = True
    if "*" in origins:
        logger.critical("CRITICAL SECURITY WARNING: Wildcard origin '*' allowed alongside allow_credentials=True. Setting allow_credentials to False to prevent security vulnerabilities.")
        allow_creds = False
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API Bearer Security
security = HTTPBearer(auto_error=False)


# API exception handlers
@app.exception_handler(PydanticValidationError)
async def validation_exception_handler(request, exc: PydanticValidationError):
    logger.error(f"Pydantic validation error: {exc.errors()}")
    env = os.getenv("ENV", "development").lower()
    if env == "development":
        detail = exc.errors()
    else:
        detail = "Validation failed. Details hidden for security."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail, "message": "Structured output validation failed"}
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    logger.error(f"ValidationError raised: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "message": "Invalid request parameter"}
    )

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not settings.API_KEY:
        # Dev mode: log a per-request warning and allow the call
        logger.debug("API_KEY not set – unauthenticated access allowed (development mode only)")
        return None
    if not credentials or not secrets.compare_digest(credentials.credentials, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return credentials.credentials


def get_engine(request: Request) -> TaskForgeEngine:
    """Return the shared engine singleton stored on app.state during lifespan startup."""
    return request.app.state.engine

@app.post("/decompose", response_model=DecomposeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def decompose(
    request: Request,
    payload: DecomposeRequest,
    engine: TaskForgeEngine = Depends(get_engine),
    db: AsyncSession = Depends(get_session),
    _auth = Depends(verify_api_key)
):
    try:
        # Check input length cap
        if len(payload.goal) > settings.MAX_INPUT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Goal length exceeds the maximum allowed limit of {settings.MAX_INPUT_LENGTH} characters."
            )

        # 1. Database-backed cache check
        result = await db.execute(
            select(Project).filter(Project.goal == payload.goal).order_by(Project.created_at.desc())
        )
        existing_project = result.scalars().first()
        if existing_project:
            logger.info(f"Database cache hit for goal: '{payload.goal}'")
            tree = TaskTree.model_validate(existing_project.task_tree_json)
            usage = UsageStats(
                prompt_tokens=existing_project.prompt_tokens,
                completion_tokens=existing_project.completion_tokens,
                total_tokens=existing_project.total_tokens,
                estimated_cost_usd=existing_project.estimated_cost_usd
            )
            return DecomposeResponse(task_tree=tree, usage=usage, cached=True)

        # 2. Run the decomposition engine
        response = await engine.decompose_goal(payload.goal)

        # Check cost limit
        if response.usage.estimated_cost_usd > settings.MAX_COST_PER_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estimated request cost (${response.usage.estimated_cost_usd:.5f}) exceeds the limit of ${settings.MAX_COST_PER_REQUEST}."
            )

        # 3. Save to database
        db_project = Project(
            goal=payload.goal,
            task_tree_json=response.task_tree.model_dump(),
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=response.usage.estimated_cost_usd
        )
        db.add(db_project)
        await db.commit()

        return response
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"ValidationError during decomposition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Goal decomposition failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal decomposition error. Check server logs."
        )

@app.post("/decompose/stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def decompose_stream(
    request: Request,
    payload: DecomposeRequest,
    engine: TaskForgeEngine = Depends(get_engine),
    db: AsyncSession = Depends(get_session),
    _auth = Depends(verify_api_key)
):
    # Check input length cap
    if len(payload.goal) > settings.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Goal length exceeds the maximum allowed limit of {settings.MAX_INPUT_LENGTH} characters."
        )

    async def event_generator():
        try:
            # 1. Database-backed cache check
            result = await db.execute(
                select(Project).filter(Project.goal == payload.goal).order_by(Project.created_at.desc())
            )
            existing_project = result.scalars().first()
            if existing_project:
                logger.info(f"Database cache hit for goal (stream): '{payload.goal}'")
                tree = TaskTree.model_validate(existing_project.task_tree_json)
                usage = UsageStats(
                    prompt_tokens=existing_project.prompt_tokens,
                    completion_tokens=existing_project.completion_tokens,
                    total_tokens=existing_project.total_tokens,
                    estimated_cost_usd=existing_project.estimated_cost_usd
                )
                resp = DecomposeResponse(task_tree=tree, usage=usage, cached=True)
                yield f"data: {json.dumps({'event': 'done', 'data': resp.model_dump()})}\n\n"
                return

            # 2. Run the decomposition engine with progress callbacks
            # MED-2: Bounded queue prevents unbounded memory growth if client is slow
            queue: asyncio.Queue = asyncio.Queue(maxsize=50)

            async def on_progress(event_data: dict):
                await queue.put(event_data)

            async def run_decomposition():
                try:
                    response = await engine.decompose_goal(payload.goal, on_progress=on_progress)

                    # Check cost limit
                    if response.usage.estimated_cost_usd > settings.MAX_COST_PER_REQUEST:
                        await queue.put({
                            "event": "error",
                            "message": f"Estimated request cost (${response.usage.estimated_cost_usd:.5f}) exceeds the limit of ${settings.MAX_COST_PER_REQUEST}."
                        })
                        return

                    # Save to database
                    db_project = Project(
                        goal=payload.goal,
                        task_tree_json=response.task_tree.model_dump(),
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        estimated_cost_usd=response.usage.estimated_cost_usd
                    )
                    db.add(db_project)
                    await db.commit()

                    await queue.put({"event": "done", "data": response.model_dump()})
                except ValidationError as ex:
                    logger.error(f"ValidationError during stream decomposition: {str(ex)}")
                    await queue.put({"event": "error", "message": str(ex)})
                except Exception as ex:
                    logger.exception("Decomposition stream failed in run_decomposition")
                    await queue.put({"event": "error", "message": "Internal decomposition error. Check server logs."})
                finally:
                    try:
                        await asyncio.wait_for(queue.put(None), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("SSE queue put(None) timed out. Falling back to put_nowait.")
                        try:
                            queue.put_nowait(None)
                        except asyncio.QueueFull:
                            logger.error("SSE queue is full. Could not put None sentinel.")

            # MED-3: Keep strong reference to task so GC doesn't cancel it mid-execution
            decompose_task = asyncio.create_task(run_decomposition())
            _background_tasks.add(decompose_task)
            decompose_task.add_done_callback(_background_tasks.discard)

            while True:
                if await request.is_disconnected():
                    logger.warning("Client disconnected from SSE stream. Cancelling background decomposition task.")
                    decompose_task.cancel()
                    break

                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"

        except ValidationError as e:
            logger.error(f"ValidationError in event generator: {str(e)}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            logger.exception("Error in event generator")
            yield f"data: {json.dumps({'event': 'error', 'message': 'Internal decomposition error. Check server logs.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/projects")
@limiter.limit("30/minute")
async def list_projects(
    request: Request,
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
            detail="Failed to retrieve projects. Check server logs."
        )

@app.get("/config")
async def get_config():
    """Return public configuration flags such as whether OpenRouter key is set."""
    return {
        "openrouter_configured": settings.is_openrouter_key_configured
    }

@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request, db: AsyncSession = Depends(get_session), _auth = Depends(verify_api_key)):
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
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
                if res.status_code == 200:
                    health_status["openrouter"] = "healthy"
                else:
                    health_status["openrouter"] = "unhealthy"
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

# Serve compiled frontend assets
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static_dist"))
if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        content={"message": "TaskForge API is running. Build frontend to view dashboard."},
        status_code=200
    )

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Exclude API endpoints from routing to catch-all
    if full_path.startswith(("decompose", "projects", "health", "config", "docs", "openapi.json")):
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Static index.html not found. Build frontend.")
