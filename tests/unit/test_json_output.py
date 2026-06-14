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


def test_extract_json_object_prefers_trailing_json_after_prose():
    raw = (
        "I need to create the config next.\n"
        '{"thought": "write plan", "bash_command": "echo ok > plan.md", "done": false, "final_response": ""}'
    )
    assert extract_json_object(raw) == raw.split("\n", 1)[1]


def test_salvage_json_from_nested_markdown_fence():
    raw = """Now I need to create self_reflect_config.json.
```json
{
  "thought": "create config",
  "bash_command": "echo '{\\"key\\": \\"value\\"}' > self_reflect_config.json",
  "done": false,
  "final_response": ""
}
```"""
    parsed = salvage_json_output(raw, action_field="bash_command")
    assert parsed is not None
    assert "self_reflect_config.json" in parsed["bash_command"]


def test_salvage_json_from_prose_then_fenced_block():
    raw = """Here is my response.
```json
{"thought": "tap", "bash_command": "ls plan.md", "done": false, "final_response": ""}
```"""
    parsed = salvage_json_output(raw, action_field="bash_command")
    assert parsed is not None
    assert parsed["bash_command"] == "ls plan.md"
