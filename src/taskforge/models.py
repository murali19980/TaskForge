from typing import Optional
from pydantic import BaseModel, Field, model_validator

class Task(BaseModel):
    id: str = Field(..., description="Unique alphanumeric identifier for the task, e.g. 'auth_api' or 'db_migration'")
    title: str = Field(..., description="Short summary of the task")
    description: str = Field(..., description="Detailed description of what needs to be done")
    estimated_hours: float = Field(..., ge=0, description="Estimated time required to complete the task in hours")
    dependencies: list[str] = Field(default_factory=list, description="List of task IDs that this task depends on")

class Category(BaseModel):
    name: str = Field(..., description="Name of the category, e.g. 'Backend Development'")
    tasks: list[Task] = Field(default_factory=list, description="List of tasks in this category")

class TaskTree(BaseModel):
    goal: str = Field(..., description="The high-level goal being decomposed")
    categories: list[Category] = Field(default_factory=list, description="Grouped categories of tasks")

    @model_validator(mode="after")
    def validate_tree(self) -> "TaskTree":
        all_task_ids = set()
        dependencies_to_check = []

        for category in self.categories:
            for task in category.tasks:
                if task.id in all_task_ids:
                    raise ValueError(f"Duplicate task ID found: {task.id}")
                all_task_ids.add(task.id)
                dependencies_to_check.append((task.id, task.dependencies))

        # Verify all dependencies exist in the tree
        for task_id, deps in dependencies_to_check:
            for dep_id in deps:
                if dep_id not in all_task_ids:
                    raise ValueError(f"Task '{task_id}' depends on a non-existent task ID '{dep_id}'")

        # Verify cycle detection
        visited = {}  # node -> state: 0 (unvisited), 1 (visiting), 2 (visited)
        dep_map = {task.id: task.dependencies for cat in self.categories for task in cat.tasks}

        def has_cycle(node: str) -> bool:
            state = visited.get(node, 0)
            if state == 1:
                return True  # Found a back edge / cycle
            if state == 2:
                return False  # Already processed

            visited[node] = 1
            for neighbor in dep_map.get(node, []):
                if has_cycle(neighbor):
                    return True
            visited[node] = 2
            return False

        for node in all_task_ids:
            if visited.get(node, 0) == 0:
                if has_cycle(node):
                    raise ValueError(f"Dependency cycle detected involving task '{node}'")

        return self

# LLM Wrapper response models for schema-guided output
class CategoriesResponse(BaseModel):
    categories: list[str] = Field(..., description="List of high-level category names")

class TasksResponse(BaseModel):
    tasks: list[Task] = Field(..., description="List of granular tasks generated for a category")

class DependencyMapResponse(BaseModel):
    dependencies: dict[str, list[str]] = Field(
        ...,
        description="A mapping from each task ID to a list of its dependency task IDs"
    )

class UsageStats(BaseModel):
    prompt_tokens: int = Field(default=0, description="Tokens used in the request prompt")
    completion_tokens: int = Field(default=0, description="Tokens generated in the completion")
    total_tokens: int = Field(default=0, description="Total tokens used")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated OpenRouter cost in USD")

class DecomposeResponse(BaseModel):
    task_tree: TaskTree = Field(..., description="Decomposed task tree structure")
    usage: UsageStats = Field(default_factory=UsageStats, description="Tokens usage stats")
    cached: bool = Field(default=False, description="Whether the result was retrieved from persistent cache")
