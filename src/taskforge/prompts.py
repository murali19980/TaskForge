# Prompt templates for task decomposition steps

ARCHITECT_PROMPT = """You are a software architect. Your job is to decompose a high-level goal into 4-6 distinct, logical, and sequential categories or workstreams.
Goal to decompose: "{goal}"

Generate a list of category names that cover this goal end-to-end. Output must follow the specified JSON schema.
"""

SPECIALIST_PROMPT = """You are a specialist engineer. Your job is to break down a specific project category within a larger goal into 5-8 granular, actionable, and concrete tasks.
Overall Project Goal: "{goal}"
Category to focus on: "{category}"

For each task, provide:
1. `id`: A unique snake_case string identifier (e.g., "setup_db_schema", "auth_middleware"). Do NOT use generic numbers or prefixes unless they represent logical order.
2. `title`: A short, descriptive title.
3. `description`: Detailed description of the implementation steps, tools, or patterns to use.
4. `estimated_hours`: Positive floating-point number representing estimated work time.

Output must follow the specified JSON schema.
"""

REFINER_PROMPT = """You are a senior project manager. Your job is to analyze a list of tasks in a project tree and establish dependency relationships between them.
Goal: "{goal}"

Here is the current task tree (without dependencies):
{tree}

Analyze the tasks and identify which tasks depend on other tasks before they can start.
For example, frontend components depend on database schema definition, or auth controller depends on DB setup.
Ensure there are NO circular dependencies.

Output must follow the specified JSON schema mapping task IDs to a list of dependency task IDs.
"""
