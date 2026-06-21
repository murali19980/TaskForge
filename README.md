# TaskForge

TaskForge is a recursive AI task decomposition engine powered by local Ollama models. It decomposes high-level user goals into structured, hierarchical categories and tasks with auto-detected dependency relationships, storing the generated project trees in a SQLite database.

## Features

- **Recursive Map-Reduce Decomposition**:
  - **Map (Architect)**: Generates high-level project categories.
  - **Reduce (Specialists)**: Concurrently generates granular tasks for each category under rate-limiting semaphores.
  - **Refine (Project Manager)**: Computes task dependencies and constructs a valid directed acyclic graph (DAG).
- **Strict Pydantic Validation**: Automatically validates schema adherence, task ID uniqueness, and dependency resolution.
- **Dependency Cycle Detection**: Ensures no circular dependencies exist before finalizing the task tree.
- **Local Ollama Integration**: Powered by `qwen2.5-coder:3b` with forced JSON schema mode.
- **Robust Error Handling**: Retry mechanisms with exponential backoff on LLM call validation errors.

## Installation

1. Clone or download the repository.
2. Initialize and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the package and development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running the API

1. Start the Ollama server and pull the default model:
   ```bash
   ollama pull qwen2.5-coder:3b
   ```
2. Start the FastAPI development server:
   ```bash
   uvicorn src.taskforge.main:app --reload
   ```
3. Access the interactive API docs at `http://127.0.0.1:8000/docs`.
