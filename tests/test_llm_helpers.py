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


def test_strip_markdown_json_braces_in_strings():
    json_str = '{"description": "curly { brace } here", "id": "1"}'
    assert _strip_markdown_json(json_str) == json_str


def test_strip_markdown_json_with_garbage_and_braces_in_strings():
    dirty = 'Some prefix text {"description": "curly { brace } here", "id": "1"} some suffix'
    assert _strip_markdown_json(dirty) == '{"description": "curly { brace } here", "id": "1"}'

