import asyncio
import logging
import time
import httpx
from typing import Type
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from taskforge.config import settings
from taskforge.models import (
    TaskTree, 
    Category, 
    CategoriesResponse, 
    TasksResponse, 
    DependencyMapResponse
)
from taskforge.prompts import ARCHITECT_PROMPT, SPECIALIST_PROMPT, REFINER_PROMPT
from taskforge.llm_provider import BaseLLMProvider

logger = logging.getLogger("taskforge.engine")

class TaskForgeEngine:
    def __init__(self, llm: BaseLLMProvider, config=settings):
        self.llm = llm
        self.config = config
        logger.info("TaskForgeEngine initialized")

    async def _call_llm_with_timeout(self, prompt: str, schema: Type[BaseModel]) -> BaseModel:
        """Call LLM provider wrapping it with a 30-second timeout."""
        start_time = time.perf_counter()
        try:
            logger.debug(f"Calling LLM with prompt preview: {prompt[:100]}...")
            # Enforce 30 seconds timeout
            result = await asyncio.wait_for(
                self.llm.generate_json(prompt, schema), 
                timeout=30.0
            )
            duration = time.perf_counter() - start_time
            logger.info(f"LLM call to {schema.__name__} completed in {duration:.2f}s")
            return result
        except asyncio.TimeoutError:
            logger.error(f"LLM call timed out after 30 seconds")
            raise TimeoutError("LLM generation timed out after 30 seconds")
        except Exception as e:
            logger.error(f"LLM call failed with error: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ValidationError, httpx.HTTPError, ValueError, TimeoutError)),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Error occurred. Retrying decompose_goal attempt {retry_state.attempt_number}..."
        )
    )
    async def decompose_goal(self, goal: str) -> TaskTree:
        """
        Decomposes a high-level goal into a full TaskTree structure.
        Uses a map-reduce pattern:
          1. Map (Architect): Generate categories.
          2. Reduce (Specialists): Concurrently generate tasks per category.
          3. Refine (PM): Calculate dependencies and validate.
        """
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty")

        logger.info(f"Decomposing goal: '{goal}'")
        
        # Step 1: Map (Architect)
        architect_prompt = ARCHITECT_PROMPT.format(goal=goal)
        categories_resp: CategoriesResponse = await self._call_llm_with_timeout(
            architect_prompt, CategoriesResponse
        )
        categories_list = categories_resp.categories
        logger.info(f"Architect generated categories: {categories_list}")

        if not categories_list:
            raise ValueError("LLM generated empty category list")

        # Step 2: Reduce (Specialists) with Semaphore limit of 5
        semaphore = asyncio.Semaphore(5)

        async def generate_tasks_for_category(category_name: str) -> Category:
            async with semaphore:
                logger.info(f"Generating tasks for category: {category_name}")
                specialist_prompt = SPECIALIST_PROMPT.format(goal=goal, category=category_name)
                tasks_resp: TasksResponse = await self._call_llm_with_timeout(
                    specialist_prompt, TasksResponse
                )
                return Category(name=category_name, tasks=tasks_resp.tasks)

        # Launch category task generators concurrently
        tasks_futures = [generate_tasks_for_category(cat) for cat in categories_list]
        categories: list[Category] = await asyncio.gather(*tasks_futures)
        
        # Step 3: Refine (PM dependencies)
        # Construct temporary tree to serialize for PM analysis
        temp_tree = TaskTree(goal=goal, categories=categories)
        tree_dict = temp_tree.model_dump()
        
        refiner_prompt = REFINER_PROMPT.format(goal=goal, tree=str(tree_dict))
        dep_resp: DependencyMapResponse = await self._call_llm_with_timeout(
            refiner_prompt, DependencyMapResponse
        )
        dependency_map = dep_resp.dependencies
        logger.info(f"PM Refiner generated dependency map: {dependency_map}")

        # Apply dependencies to the categories/tasks structure
        # Build map of tasks by ID for easy lookup and modification
        tasks_by_id = {}
        for category in categories:
            for task in category.tasks:
                tasks_by_id[task.id] = task

        for task_id, dep_ids in dependency_map.items():
            if task_id in tasks_by_id:
                # Filter out any self-dependencies to avoid trivial cycles
                filtered_deps = [dep for dep in dep_ids if dep != task_id]
                tasks_by_id[task_id].dependencies = filtered_deps

        # Instantiate final tree which triggers validation (cycles, duplicate IDs, missing refs)
        final_tree = TaskTree(goal=goal, categories=categories)
        logger.info("Goal successfully decomposed and validated")
        return final_tree
