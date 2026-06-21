import pytest
from taskforge.llm_provider import _strip_markdown_json

def test_strip_markdown_json_clean():
    clean_json = '{"key": "value", "bool": true}'
    assert _strip_markdown_json(clean_json) == clean_json

def test_strip_markdown_json_with_json_fence():
    fenced_json = '```json\n{"key": "value"}\n```'
    assert _strip_markdown_json(fenced_json) == '{"key": "value"}'

def test_strip_markdown_json_with_generic_fence():
    fenced_json = '```\n{"key": "value"}\n```'
    assert _strip_markdown_json(fenced_json) == '{"key": "value"}'

def test_strip_markdown_json_with_extra_text():
    dirty_json = 'Here is the response:\n```json\n{"key": "value"}\n```\nHope that helps!'
    assert _strip_markdown_json(dirty_json) == '{"key": "value"}'

def test_strip_markdown_json_no_fences_with_extra_text():
    dirty_json = 'Prefix text {"key": "value"} Suffix text'
    assert _strip_markdown_json(dirty_json) == '{"key": "value"}'
