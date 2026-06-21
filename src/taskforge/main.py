import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from taskforge.config import settings
from taskforge.database import init_db, get_session, Project
from taskforge.models import TaskTree
from taskforge.llm_provider import OllamaProvider
from taskforge.engine import TaskForgeEngine

logger = logging.getLogger("taskforge.main")

class DecomposeRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="The high-level goal to decompose")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="TaskForge API",
    description="Recursive AI task decomposition engine using local Ollama models",
    version="0.1.0",
    lifespan=lifespan
)

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
    # Use standard OllamaProvider by default
    provider = OllamaProvider()
    return TaskForgeEngine(llm=provider)

@app.post("/decompose", response_model=TaskTree)
async def decompose(
    request: DecomposeRequest,
    engine: TaskForgeEngine = Depends(get_engine),
    db: AsyncSession = Depends(get_session)
):
    try:
        # Run the decomposition engine
        task_tree = await engine.decompose_goal(request.goal)
        
        # Save to database
        db_project = Project(
            goal=request.goal,
            task_tree_json=task_tree.model_dump()
        )
        db.add(db_project)
        # Flush to DB (get_session will commit automatically on block completion)
        await db.flush()
        
        return task_tree
    except Exception as e:
        logger.exception("Goal decomposition failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decomposition failed: {str(e)}"
        )

@app.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        projects = result.scalars().all()
        return [
            {
                "id": p.id,
                "goal": p.goal,
                "task_tree": p.task_tree_json,
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
