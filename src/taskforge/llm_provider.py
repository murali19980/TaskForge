import json
import logging
import re
import asyncio
from typing import Type, Protocol, Any
import httpx
from pydantic import BaseModel
from taskforge.models import (
    CategoriesResponse,
    TasksResponse,
    DependencyMapResponse,
    Task,
    UsageStats
)
from taskforge.config import settings

logger = logging.getLogger("taskforge.llm_provider")

class BaseLLMProvider(Protocol):
    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        """Sends prompt to LLM and returns validated Pydantic model response with UsageStats."""
        ...

class OllamaProvider:
    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        logger.info(f"OllamaProvider initialized with host={self.host}, model={self.model}")

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        url = f"{self.host.rstrip('/')}/api/generate"

        # We pass the schema directly to Ollama's format field to force JSON conforming to the schema
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": expected_schema.model_json_schema(),
            "options": {
                "temperature": 0.1
            }
        }

        logger.debug(f"Sending payload to Ollama: {payload}")

        async with httpx.AsyncClient(timeout=float(settings.LLM_REQUEST_TIMEOUT)) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "").strip()

                logger.debug(f"Raw Ollama response: {response_text}")

                # Parse response_text into JSON
                parsed_json = json.loads(response_text)

                # Validate using Pydantic model
                model_inst = expected_schema.model_validate(parsed_json)

                # Extract token usage from Ollama metadata
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                total_tokens = prompt_tokens + completion_tokens

                usage = UsageStats(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=0.0
                )

                return model_inst, usage

            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama returned HTTP error status: {e.response.status_code}")
                raise
            except httpx.HTTPError as e:
                logger.error(f"HTTP error contacting Ollama: {str(e)}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode response as JSON: {response_text}. Error: {str(e)}")
                raise ValueError(f"Ollama returned invalid JSON: {str(e)}")
            except Exception as e:
                logger.error(f"Validation or unexpected error: {str(e)}")
                raise

class OpenRouterProvider:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model
        if model:
            self.model_list = [model]
        else:
            self.model_list = settings.openrouter_model_list
            self.model = self.model_list[0] if self.model_list else settings.OPENROUTER_MODEL
        logger.info(f"OpenRouterProvider initialized with models={self.model_list}")

    async def generate_json(self, prompt: str, expected_schema: Type[BaseModel]) -> tuple[BaseModel, UsageStats]:
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing. Set OPENROUTER_API_KEY in your config/.env file.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TaskForge"
        }

        # Enforce json_object mode and pass the expected schema description in the system prompt
        schema_desc = json.dumps(expected_schema.model_json_schema(), indent=2)
        system_prompt = (
            "You are a helpful software architecture assistant.\n"
            "You MUST return a JSON object that adheres EXACTLY to the following JSON Schema:\n"
            f"{schema_desc}\n"
            "Output only the raw JSON object, without markdown block wrappers or extra text."
        )

        last_exception = None
        for model in self.model_list:
            logger.info(f"OpenRouter attempting generation using model '{model}'...")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }

            max_attempts = 3
            try:
                async with httpx.AsyncClient(timeout=float(settings.LLM_REQUEST_TIMEOUT)) as client:
                    for attempt in range(1, max_attempts + 1):
                        try:
                            response = await client.post(url, json=payload, headers=headers)
                            response.raise_for_status()
                            data = response.json()

                            # Catch API errors
                            if "error" in data:
                                err_msg = data["error"].get("message", "Unknown OpenRouter error")
                                raise ValueError(f"OpenRouter API returned error: {err_msg}")

                            response_text = data["choices"][0]["message"]["content"].strip()
                            logger.debug(f"Raw OpenRouter response: {response_text}")

                            parsed_json = json.loads(response_text)
                            model_inst = expected_schema.model_validate(parsed_json)

                            # Extract token usage
                            usage_data = data.get("usage", {})
                            prompt_tokens = usage_data.get("prompt_tokens", 0)
                            completion_tokens = usage_data.get("completion_tokens", 0)
                            total_tokens = usage_data.get("total_tokens", 0)

                            # Price per 1M tokens mapping: (input_cost_usd, output_cost_usd)
                            PRICING = {
                                "google/gemini-2.5-flash:free": (0.0, 0.0),
                                "google/gemini-2.5-flash": (0.075, 0.30),
                                "mistralai/mistral-nemo:free": (0.0, 0.0),
                                "mistralai/mistral-nemo": (0.17, 0.17),
                                "openai/gpt-4o-mini": (0.150, 0.60),
                                "openrouter/free": (0.0, 0.0),
                            }

                            rates = PRICING.get(model, (0.150, 0.60))  # Default fallback gpt-4o-mini
                            input_cost = (prompt_tokens * rates[0]) / 1_000_000
                            output_cost = (completion_tokens * rates[1]) / 1_000_000
                            estimated_cost = input_cost + output_cost

                            usage = UsageStats(
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,
                                estimated_cost_usd=estimated_cost
                            )

                            return model_inst, usage

                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 429:
                                retry_after = 2.0  # default backoff
                                retry_after_hdr = e.response.headers.get("Retry-After")
                                if retry_after_hdr:
                                    try:
                                        retry_after = float(retry_after_hdr)
                                    except ValueError:
                                        pass
                                logger.warning(
                                    f"OpenRouter rate limit (429) hit for model '{model}'. "
                                    f"Retry-After header: {retry_after_hdr}. "
                                    f"Waiting {retry_after}s before retry attempt {attempt}/{max_attempts}..."
                                )
                                if attempt == max_attempts:
                                    logger.error(f"Max rate limit retries reached for model '{model}'.")
                                    raise
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                logger.error(f"OpenRouter returned HTTP error status: {e.response.status_code} - {e.response.text}")
                                raise
                        except httpx.HTTPError as e:
                            logger.error(f"HTTP error contacting OpenRouter: {str(e)}")
                            raise
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode response as JSON: {response_text}. Error: {str(e)}")
                            raise ValueError(f"OpenRouter returned invalid JSON: {str(e)}")
                        except Exception as e:
                            logger.error(f"Validation or unexpected error in OpenRouter call: {str(e)}")
                            raise
            except Exception as e:
                logger.warning(f"OpenRouter model '{model}' failed with error: {e}. Trying next model in fallback list...")
                last_exception = e
                continue

        raise last_exception or ValueError("All OpenRouter models in fallback list failed.")

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
            # Try to identify category in prompt (e.g. Category to focus on: "Frontend")
            category_match = re.search(r"Category to focus on:\s*[\"']([^\"']+)[\"']", prompt, re.IGNORECASE)
            category_name = category_match.group(1) if category_match else "Development"

            # Fetch predefined tasks or fallback to generic Development
            tasks = self.category_tasks.get(category_name, self.category_tasks["Development"])
            return TasksResponse(tasks=tasks), usage

        elif expected_schema is DependencyMapResponse:
            # Parse prompt to see what task IDs are in the tree
            found_ids = set(re.findall(r'"id":\s*["\']([^"\']+)["\']', prompt))
            if not found_ids:
                found_ids = set(re.findall(r"'id':\s*['\"]([^'\"]+)['\"]", prompt))

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
