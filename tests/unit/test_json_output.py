from __future__ import annotations

from webwright.models.base import parse_json_output
from webwright.utils.json_output import extract_json_object, salvage_json_output


def test_salvage_json_from_markdown_fence():
    raw = """Here is the step:
```json
{"thought": "tap", "python_code": "driver.click_text(\\"Go\\")", "done": false, "final_response": ""}
```"""
    parsed = salvage_json_output(raw, action_field="python_code")
    assert parsed is not None
    assert parsed["python_code"] == 'driver.click_text("Go")'


def test_parse_json_output_falls_back_to_salvage():
    raw = (
        "I will click next.\n"
        '{"thought": "tap", "python_code": "driver.press(\\"back\\")", "done": false, "final_response": ""}'
    )
    parsed = parse_json_output(raw, action_field="python_code")
    assert parsed["python_code"] == 'driver.press("back")'


def test_extract_json_object_returns_none_for_plain_prose():
    assert extract_json_object("I will click the search button next.") is None
