import pytest
from unittest.mock import MagicMock
from streamlit.testing.v1 import AppTest

def test_streamlit_app_renders(mocker):
    # Mock requests.get for historical runs
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {
            "id": 1,
            "goal": "Test goal",
            "task_tree": {
                "goal": "Test goal",
                "categories": [
                    {
                        "name": "Category 1",
                        "tasks": [
                            {
                                "id": "task_1",
                                "title": "Task 1",
                                "description": "Desc 1",
                                "estimated_hours": 2.0,
                                "dependencies": []
                            }
                        ]
                    }
                ]
            },
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 150,
                "total_tokens": 250,
                "estimated_cost_usd": 0.0001
            },
            "created_at": "2026-06-21T06:58:55"
        }
    ]
    
    # Mock requests.post for goal decomposition
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "task_tree": {
            "goal": "New goal",
            "categories": []
        },
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 50,
            "total_tokens": 100,
            "estimated_cost_usd": 0.0
        },
        "cached": False
    }

    # Initialize and run Streamlit AppTest
    at = AppTest.from_file("frontend/streamlit_app.py")
    at.run()
    
    # Check that app starts up without exceptions
    assert not at.exception
    
    # Verify the input and action controls are present
    assert len(at.text_area) == 1
    assert len(at.text_input) == 1  # API key sidebar input
    
    goal_input = at.text_area[0]
    goal_input.input("Build a website").run()
    
    # Locate and trigger the decompose button
    decompose_btn = None
    for btn in at.button:
        if btn.label == "Decompose Goal":
            decompose_btn = btn
            break
            
    assert decompose_btn is not None
    decompose_btn.click().run()
    
    # Verify that request.post was called to submit the goal
    assert not at.exception
    mock_post.assert_called_once()
