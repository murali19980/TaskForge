import asyncio
import re
import logging
import time
import httpx
from typing import Type
from pydantic import BaseModel, ValidationError as PydanticValidationError
from taskforge.exceptions import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from taskforge.config import settings
from taskforge.models import (
    TaskTree,
    Category,
    CategoriesResponse,
    TasksResponse,
    DependencyMapResponse,
    UsageStats,
    DecomposeResponse
)
from taskforge.prompts import ARCHITECT_PROMPT, SPECIALIST_PROMPT, REFINER_PROMPT
from taskforge.llm_provider import BaseLLMProvider, OllamaProvider, OpenRouterProvider

logger = logging.getLogger("taskforge.engine")

class TaskForgeEngine:
    def __init__(
        self,
        architect_provider: BaseLLMProvider,
        specialist_provider: BaseLLMProvider,
        refiner_provider: BaseLLMProvider,
        config=settings
    ):
        self.architect_provider = architect_provider
        self.specialist_provider = specialist_provider
        self.refiner_provider = refiner_provider
        self.config = config
        # Separate semaphores for Ollama and OpenRouter configurable via env/settings
        self._ollama_semaphore = asyncio.Semaphore(config.OLLAMA_MAX_CONCURRENT)
        self._openrouter_semaphore = asyncio.Semaphore(config.OPENROUTER_MAX_CONCURRENT)
        logger.info(
            f"TaskForgeEngine initialized (Ollama concurrency: {config.OLLAMA_MAX_CONCURRENT}, "
            f"OpenRouter concurrency: {config.OPENROUTER_MAX_CONCURRENT})"
        )

    async def _execute_provider_call(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        schema: Type[BaseModel]
    ) -> tuple[BaseModel, UsageStats]:
        # Select the correct semaphore based on provider type
        if isinstance(provider, OpenRouterProvider) or provider.__class__.__name__ == "OpenRouterProvider":
            sem = self._openrouter_semaphore
        else:
            sem = self._ollama_semaphore

        start_time = time.perf_counter()
        try:
            logger.debug(f"Calling LLM provider {provider.__class__.__name__} ({getattr(provider, 'model', 'N/A')}) with prompt preview: {prompt[:100]}...")
            async with sem:
                result, usage = await asyncio.wait_for(
                    provider.generate_json(prompt, schema),
                    timeout=float(self.config.LLM_REQUEST_TIMEOUT)
                )
            duration = time.perf_counter() - start_time
            logger.info(f"LLM call to {schema.__name__} completed in {duration:.2f}s using {provider.__class__.__name__} ({getattr(provider, 'model', 'N/A')})")
            return result, usage
        except asyncio.TimeoutError:
            logger.error(f"LLM call timed out after {self.config.LLM_REQUEST_TIMEOUT} seconds")
            raise TimeoutError(f"LLM generation timed out after {self.config.LLM_REQUEST_TIMEOUT} seconds")

    async def _call_llm_with_timeout(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        schema: Type[BaseModel]
    ) -> tuple[BaseModel, UsageStats]:
        """Call LLM provider with per-provider semaphores, timeout, and model fallback chain."""
        is_openrouter = isinstance(provider, OpenRouterProvider) or provider.__class__.__name__ == "OpenRouterProvider"

        try:
            return await self._execute_provider_call(provider, prompt, schema)
        except Exception as e:
            if not is_openrouter:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
                raise

            current_model = getattr(provider, "model", None)
            if current_model != "openrouter/free":
                logger.warning(
                    f"Primary OpenRouter model '{current_model}' failed with error: {e}. "
                    "Trying fallback model 'openrouter/free'..."
                )
                try:
                    fallback_provider = OpenRouterProvider(api_key=getattr(provider, "api_key", None), model="openrouter/free")
                    return await self._execute_provider_call(fallback_provider, prompt, schema)
                except Exception as fallback_err:
                    logger.warning(
                        f"Fallback OpenRouter model 'openrouter/free' failed with error: {fallback_err}. "
                        "Falling back to local Ollama..."
                    )
            else:
                logger.warning(f"OpenRouter 'openrouter/free' failed with error: {e}. Falling back to local Ollama...")

            try:
                ollama_provider = OllamaProvider(host=self.config.OLLAMA_HOST, model=self.config.OLLAMA_MODEL)
                logger.info(f"Using local Ollama fallback model '{self.config.OLLAMA_MODEL}'...")
                return await self._execute_provider_call(ollama_provider, prompt, schema)
            except Exception as ollama_err:
                logger.error(f"Local Ollama fallback also failed: {ollama_err}")
                raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((PydanticValidationError, httpx.HTTPError, ValueError, TimeoutError)),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Error occurred. Retrying decompose_goal attempt {retry_state.attempt_number}..."
        )
    )
    async def decompose_goal(self, goal: str, on_progress = None) -> DecomposeResponse:
        """
        Decomposes a high-level goal into a full TaskTree structure.
        Uses a map-reduce pattern with token tracking:
          1. Map (Architect): Generate categories.
          2. Reduce (Specialists): Concurrently generate tasks per category.
          3. Refine (PM): Calculate dependencies and validate.
        """
        if not goal or not goal.strip():
            raise ValidationError("Goal cannot be empty")

        if len(goal) > self.config.MAX_INPUT_LENGTH:
            raise ValidationError(f"Goal exceeds maximum length of {self.config.MAX_INPUT_LENGTH} characters")

        logger.info(f"Decomposing goal: '{goal}'")

        # Prepare safe version of goal for prompt inclusion (escaping braces and adding delimiters)
        escaped_goal = goal.replace("{", "{{").replace("}", "}}")
        prompt_goal = f"<USER_GOAL>\n{escaped_goal}\n</USER_GOAL>"

        # Step 1: Map (Architect)
        if on_progress:
            await on_progress({"event": "architect_start"})

        architect_prompt = ARCHITECT_PROMPT.format(goal=prompt_goal)
        categories_resp, arch_usage = await self._call_llm_with_timeout(
            self.architect_provider, architect_prompt, CategoriesResponse
        )
        categories_list = categories_resp.categories
        logger.info(f"Architect generated categories: {categories_list}")

        if on_progress:
            await on_progress({"event": "architect_done", "categories": categories_list})

        if not categories_list:
            raise ValueError("LLM generated empty category list")

        # Step 2: Reduce (Specialists)
        if on_progress:
            await on_progress({"event": "specialists_start", "categories": categories_list})

        async def generate_tasks_for_category(category_name: str) -> tuple[Category, UsageStats]:
            if on_progress:
                await on_progress({"event": "specialist_start", "category": category_name})
            logger.info(f"Generating tasks for category: {category_name}")
            specialist_prompt = SPECIALIST_PROMPT.format(goal=prompt_goal, category=category_name)
            tasks_resp, spec_usage = await self._call_llm_with_timeout(
                self.specialist_provider, specialist_prompt, TasksResponse
            )
            # Prefix task IDs with category slug to prevent duplicate collisions across categories
            cat_slug = re.sub(r'[^a-z0-9]+', '_', category_name.lower()).strip('_')
            prefixed_tasks = []
            for task in tasks_resp.tasks:
                if not task.id.startswith(cat_slug):
                    task.id = f"{cat_slug}_{task.id}"
                prefixed_tasks.append(task)

            if on_progress:
                await on_progress({
                    "event": "specialist_done",
                    "category": category_name,
                    "task_count": len(prefixed_tasks)
                })
            return Category(name=category_name, tasks=prefixed_tasks), spec_usage

        # Launch category task generators concurrently
        tasks_futures = [generate_tasks_for_category(cat) for cat in categories_list]
        specialist_results = await asyncio.gather(*tasks_futures)

        categories = [r[0] for r in specialist_results]
        specialist_usages = [r[1] for r in specialist_results]

        # Step 3: Refine (PM dependencies)
        if on_progress:
            await on_progress({"event": "refiner_start"})

        temp_tree = TaskTree(goal=goal, categories=categories)
        tree_json = temp_tree.model_dump_json()

        refiner_prompt = REFINER_PROMPT.format(goal=prompt_goal, tree=tree_json)
        dep_resp, ref_usage = await self._call_llm_with_timeout(
            self.refiner_provider, refiner_prompt, DependencyMapResponse
        )
        dependency_map = dep_resp.dependencies
        logger.info(f"PM Refiner generated dependency map: {dependency_map}")

        if on_progress:
            await on_progress({"event": "refiner_done"})

        # Apply dependencies
        tasks_by_id = {}
        for category in categories:
            for task in category.tasks:
                tasks_by_id[task.id] = task

        for task_id, dep_ids in dependency_map.items():
            if task_id in tasks_by_id:
                filtered_deps = [dep for dep in dep_ids if dep != task_id]
                tasks_by_id[task_id].dependencies = filtered_deps

        # Instantiate final tree which triggers validation
        final_tree = TaskTree(goal=goal, categories=categories)

        # Aggregate token usage statistics
        total_prompt = arch_usage.prompt_tokens + ref_usage.prompt_tokens + sum(u.prompt_tokens for u in specialist_usages)
        total_completion = arch_usage.completion_tokens + ref_usage.completion_tokens + sum(u.completion_tokens for u in specialist_usages)
        total_tokens = arch_usage.total_tokens + ref_usage.total_tokens + sum(u.total_tokens for u in specialist_usages)
        total_cost = arch_usage.estimated_cost_usd + ref_usage.estimated_cost_usd + sum(u.estimated_cost_usd for u in specialist_usages)

        usage = UsageStats(
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_tokens,
            estimated_cost_usd=total_cost
        )

        logger.info(f"Goal successfully decomposed. Total tokens used: {total_tokens}, cost: ${total_cost:.5f}")
        return DecomposeResponse(task_tree=final_tree, usage=usage, cached=False)
