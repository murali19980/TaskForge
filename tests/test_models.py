import pytest
from pydantic import ValidationError
from taskforge.models import Task, Category, TaskTree

def test_valid_task_tree():
    task1 = Task(id="task_1", title="Task 1", description="Desc 1", estimated_hours=2.5, dependencies=[])
    task2 = Task(id="task_2", title="Task 2", description="Desc 2", estimated_hours=4.0, dependencies=["task_1"])
    
    category = Category(name="Category A", tasks=[task1, task2])
    
    tree = TaskTree(goal="Test goal", categories=[category])
    assert tree.goal == "Test goal"
    assert len(tree.categories) == 1
    assert len(tree.categories[0].tasks) == 2

def test_duplicate_task_ids():
    task1 = Task(id="duplicate_id", title="Task 1", description="Desc 1", estimated_hours=1.0)
    task2 = Task(id="duplicate_id", title="Task 2", description="Desc 2", estimated_hours=2.0)
    
    cat1 = Category(name="Category A", tasks=[task1])
    cat2 = Category(name="Category B", tasks=[task2])
    
    with pytest.raises(ValidationError) as exc_info:
        TaskTree(goal="Goal with dupes", categories=[cat1, cat2])
    
    assert "Duplicate task ID found: duplicate_id" in str(exc_info.value)

def test_missing_dependency_reference():
    task1 = Task(id="task_1", title="Task 1", description="Desc 1", estimated_hours=1.0, dependencies=["non_existent_id"])
    cat = Category(name="Category A", tasks=[task1])
    
    with pytest.raises(ValidationError) as exc_info:
        TaskTree(goal="Goal with missing dep", categories=[cat])
        
    assert "depends on a non-existent task ID 'non_existent_id'" in str(exc_info.value)

def test_simple_dependency_cycle():
    task1 = Task(id="task_1", title="Task 1", description="Desc 1", estimated_hours=1.0, dependencies=["task_2"])
    task2 = Task(id="task_2", title="Task 2", description="Desc 2", estimated_hours=2.0, dependencies=["task_1"])
    cat = Category(name="Category A", tasks=[task1, task2])
    
    with pytest.raises(ValidationError) as exc_info:
        TaskTree(goal="Goal with cycle", categories=[cat])
        
    assert "Dependency cycle detected involving task" in str(exc_info.value)

def test_complex_dependency_cycle():
    task1 = Task(id="task_1", title="Task 1", description="Desc 1", estimated_hours=1.0, dependencies=["task_2"])
    task2 = Task(id="task_2", title="Task 2", description="Desc 2", estimated_hours=2.0, dependencies=["task_3"])
    task3 = Task(id="task_3", title="Task 3", description="Desc 3", estimated_hours=1.5, dependencies=["task_1"])
    cat = Category(name="Category A", tasks=[task1, task2, task3])
    
    with pytest.raises(ValidationError) as exc_info:
        TaskTree(goal="Goal with complex cycle", categories=[cat])
        
    assert "Dependency cycle detected involving task" in str(exc_info.value)

def test_negative_hours_invalid():
    with pytest.raises(ValidationError):
        Task(id="task_1", title="Task 1", description="Desc 1", estimated_hours=-1.5)
