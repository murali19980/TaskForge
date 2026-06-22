import re
import httpx
import logging
from typing import Type
from pydantic import BaseModel

from taskforge.models import (
    CategoriesResponse,
    TasksResponse,
    DependencyMapResponse,
    Task,
    UsageStats
)

logger = logging.getLogger("taskforge.mocks")

class MockLLMProvider:
    """
    Deterministic mock provider that varies its output based on search keywords in the prompt/goal.
    Used for unit testing without a running Ollama container.
    """
    def __init__(self):
        logger.info("MockLLMProvider initialized")
        # Define predefined tasks and dependencies for categories
        self.category_tasks = {
            "Frontend": [
                Task(id="fe_setup", title="Setup frontend project", description="Initialize React & Vite", estimated_hours=4.0),
                Task(id="fe_components", title="Build UI components", description="Build button, card, input fields", estimated_hours=8.0),
                Task(id="fe_state", title="Implement state management", description="Configure Redux/Zustand store", estimated_hours=6.0),
                Task(id="fe_auth", title="Connect login pages", description="Integrate authentication endpoint", estimated_hours=5.0),
                Task(id="fe_deploy", title="Bundle and deploy", description="Build production bundle and deploy", estimated_hours=3.0),
            ],
            "Backend": [
                Task(id="be_setup", title="Setup FastAPI application", description="Install dependencies and setup basic structure", estimated_hours=4.0),
                Task(id="be_models", title="Design database models", description="Create SQLAlchemy async models", estimated_hours=5.0),
                Task(id="be_auth", title="Implement auth controller", description="Create JWT token auth endpoints", estimated_hours=6.0),
                Task(id="be_endpoints", title="Create project API routes", description="Define CRUD endpoints for projects", estimated_hours=8.0),
                Task(id="be_tests", title="Write integration tests", description="Write Pytest tests for API endpoints", estimated_hours=6.0),
            ],
            "Database": [
                Task(id="db_init", title="Setup SQLite connection pool", description="Initialize engine and async session maker", estimated_hours=3.0),
                Task(id="db_migrations", title="Setup Alembic migrations", description="Initialize Alembic and configure env.py", estimated_hours=4.0),
                Task(id="db_seed", title="Create seed data script", description="Write scripts to pre-populate DB for development", estimated_hours=3.0),
                Task(id="db_backup", title="Setup backups", description="Write automation script to backup SQLite database", estimated_hours=2.0),
                Task(id="db_optimize", title="Add indexes", description="Analyze query plans and optimize keys", estimated_hours=3.0),
            ],
            "DevOps": [
                Task(id="do_docker", title="Containerize application", description="Write Dockerfiles and docker-compose.yml", estimated_hours=4.0),
                Task(id="do_ci", title="Configure CI workflow", description="Setup Github Actions checks", estimated_hours=3.0),
                Task(id="do_logs", title="Setup Prometheus monitoring", description="Integrate monitoring metrics", estimated_hours=5.0),
                Task(id="do_ssl", title="Configure Nginx and SSL", description="Setup reverse proxy with Let's Encrypt", estimated_hours=4.0),
                Task(id="do_deploy", title="Deploy to staging VPS", description="Configure automation and run app", estimated_hours=5.0),
            ],
            "UI Design": [
                Task(id="ui_wireframes", title="Design Wireframes", description="Create low-fidelity layout plans", estimated_hours=8.0),
                Task(id="ui_mockups", title="Design High-Fidelity Mockups", description="Create UI designs in Figma", estimated_hours=12.0),
                Task(id="ui_design_system", title="Create Design System", description="Define color palettes and components", estimated_hours=6.0),
            ],
            "API Integration": [
                Task(id="api_client", title="Setup HTTP Client", description="Implement custom Axios/Retrofit client", estimated_hours=4.0),
                Task(id="api_sync", title="Sync Offline Storage", description="Design offline SQLite cache synchronization", estimated_hours=8.0),
            ],
            "iOS App": [
                Task(id="ios_setup", title="Initialize Swift Project", description="Configure bundle ID and project settings", estimated_hours=4.0),
                Task(id="ios_ui", title="Implement SwiftUI Views", description="Build views from mockups", estimated_hours=16.0),
            ],
            "Android App": [
                Task(id="and_setup", title="Initialize Kotlin Project", description="Configure gradle settings and package", estimated_hours=4.0),
                Task(id="and_ui", title="Implement Compose UI", description="Build jetpack compose screens", estimated_hours=16.0),
            ],
            "Planning": [
                Task(id="plan_spec", title="Write Technical Specification", description="Detail system requirements", estimated_hours=8.0),
                Task(id="plan_architecture", title="Design System Architecture", description="Create ERD diagrams and system flowcharts", estimated_hours=6.0),
            ],
            "Development": [
                Task(id="dev_db", title="Initialize database schema", description="Create tables and initial setup", estimated_hours=5.0),
                Task(id="dev_api", title="Implement core endpoints", description="Create API routing and controllers", estimated_hours=12.0),
            ],
            "Testing": [
                Task(id="test_unit", title="Write Unit Tests", description="Write tests for business logic", estimated_hours=8.0),
                Task(id="test_integration", title="Write Integration Tests", description="Write tests verifying DB and API interaction", estimated_hours=8.0),
            ],
            "Deployment": [
                Task(id="dep_env", title="Setup production server", description="Install dependencies and systemd services", estimated_hours=6.0),
                Task(id="dep_build", title="Build production assets", description="Generate static bundle and check artifacts", estimated_hours=3.0),
            ]
        }

        # Defined static dependencies
        self.predefined_dependencies = {
            "fe_components": ["fe_setup"],
            "fe_state": ["fe_components"],
            "fe_auth": ["fe_state", "be_auth"],
            "fe_deploy": ["fe_components", "fe_state"],
            "be_models": ["be_setup"],
            "be_auth": ["be_models"],
            "be_endpoints": ["be_models", "be_auth"],
            "be_tests": ["be_endpoints"],
            "do_ci": ["fe_setup", "be_setup"],
            "do_deploy": ["fe_deploy", "be_tests"],
            "api_sync": ["api_client"],
            "ios_ui": ["ios_setup"],
            "and_ui": ["and_setup"],
            "dev_api": ["dev_db"],
            "test_integration": ["test_unit"],
            "dep_build": ["dep_env"]
        }

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        usage = UsageStats(prompt_tokens=100, completion_tokens=150, total_tokens=250, estimated_cost_usd=0.00015)

        # Check target schema type
        if expected_schema is CategoriesResponse:
            if re.search(r"web app|website", prompt, re.IGNORECASE):
                categories = ["Frontend", "Backend", "Database", "DevOps"]
            elif re.search(r"mobile|app", prompt, re.IGNORECASE):
                categories = ["UI Design", "API Integration", "iOS App", "Android App"]
            else:
                categories = ["Planning", "Development", "Testing", "Deployment"]
            return CategoriesResponse(categories=categories), usage

        elif expected_schema is TasksResponse:
            # Try to identify category in prompt
            category_match = re.search(r"Category to focus on:\s*[\"']([^\"']+)[\"']", prompt, re.IGNORECASE)
            category_name = category_match.group(1) if category_match else "Development"

            # Fetch predefined tasks or fallback to generic Development
            tasks = self.category_tasks.get(category_name, self.category_tasks["Development"])
            return TasksResponse(tasks=tasks), usage

        elif expected_schema is DependencyMapResponse:
            # Parse prompt to see what task IDs are in the tree
            found_ids = re.findall(r'"id"\s*:\s*"([^"]+)"', prompt)

            dependencies = {}
            for task_id in found_ids:
                deps = self.predefined_dependencies.get(task_id, [])
                filtered_deps = [d for d in deps if d in found_ids]
                dependencies[task_id] = filtered_deps

            return DependencyMapResponse(dependencies=dependencies), usage

        raise ValueError(f"MockLLMProvider does not support target schema: {expected_schema}")

class FailingMockLLM(MockLLMProvider):
    """
    Mock LLM provider that fails on the first two calls and succeeds on the third attempt
    to test the engine's tenacity retry behavior.
    """
    def __init__(self):
        super().__init__()
        self.call_count = 0

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        self.call_count += 1
        if self.call_count <= 2:
            logger.warning(f"FailingMockLLM simulating failure (call_count={self.call_count})")
            raise httpx.ConnectError("Connection timed out (simulated failure)")
        return await super().generate_json(prompt, expected_schema)
