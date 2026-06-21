import asyncio
import os
import json
import logging
from dotenv import load_dotenv

# Load configuration settings
load_dotenv()

from taskforge.config import settings
from taskforge.database import init_db
from taskforge.llm_provider import OllamaProvider, OpenRouterProvider
from taskforge.engine import TaskForgeEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_real_llms")

async def main():
    print("==================================================")
    print("TaskForge Real LLM & Provider Verification Utility")
    print("==================================================")

    print("\n1. Initializing SQLite Database...")
    await init_db()

    print("\n2. Checking Provider Configurations...")
    print(f"Ollama Host:  {settings.OLLAMA_HOST}")
    print(f"Ollama Model: {settings.OLLAMA_MODEL}")

    # Check if OpenRouter is configured
    has_openrouter = bool(settings.OPENROUTER_API_KEY)
    print(f"OpenRouter API Key present: {has_openrouter}")
    if has_openrouter:
        print(f"OpenRouter Model:           {settings.OPENROUTER_MODEL}")

    print("\n3. Constructing Providers...")
    if has_openrouter:
        print("Using HYBRID configuration (OpenRouter + local Ollama)...")
        architect = OpenRouterProvider()
        specialist = OllamaProvider()
        refiner = OpenRouterProvider()
    else:
        print("Using LOCAL-ONLY configuration (Ollama for all steps)...")
        architect = OllamaProvider()
        specialist = OllamaProvider()
        refiner = OllamaProvider()

    engine = TaskForgeEngine(
        architect_provider=architect,
        specialist_provider=specialist,
        refiner_provider=refiner
    )

    goal = "Plan a birthday party"
    print(f"\n4. Triggering decomposition for goal: '{goal}'...")
    print("Note: This will perform REAL LLM requests. It may take some time depending on connections.")

    try:
        response = await engine.decompose_goal(goal)
        print("\n==================================================")
        print("SUCCESS! Decomposition Completed successfully.")
        print("==================================================")

        print(f"Goal: {response.task_tree.goal}")
        print("\nToken Usage Stats:")
        print(f"  Prompt Tokens:      {response.usage.prompt_tokens}")
        print(f"  Completion Tokens:  {response.usage.completion_tokens}")
        print(f"  Total Tokens:       {response.usage.total_tokens}")
        print(f"  Estimated Cost:     ${response.usage.estimated_cost_usd:.5f}")

        print("\nDecomposed Categories:")
        for cat in response.task_tree.categories:
            print(f"  Category: {cat.name} ({len(cat.tasks)} tasks)")
            for task in cat.tasks:
                print(f"    - [{task.id}] {task.title} ({task.estimated_hours} hrs)")
                if task.dependencies:
                    print(f"      depends on: {task.dependencies}")

    except Exception as e:
        print("\n==================================================")
        print("FAILED! Verification run encountered an error:")
        print(f"Error Details: {str(e)}")
        print("==================================================")
        if not has_openrouter:
            print("\nEnsure your local Ollama server is running with 'ollama serve' and the model is pulled.")
        else:
            print("\nEnsure both local Ollama is running and your OpenRouter API key is valid.")

if __name__ == "__main__":
    asyncio.run(main())
