from __future__ import annotations

import json
import re
from typing import Any


_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _balanced_json_object(text: str, start: int) -> str | None:
    if start < 0 or start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json_object(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None

    match = _FENCED_JSON.search(text)
    if match:
        return match.group(1).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    while start >= 0:
        candidate = _balanced_json_object(text, start)
        if candidate is not None:
            return candidate
        start = text.find("{", start + 1)
    return None


def salvage_json_output(raw: str, *, action_field: str = "bash_command") -> dict[str, Any] | None:
    candidate = extract_json_object(raw)
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if action_field not in parsed and "thought" not in parsed and "done" not in parsed:
        return None
    action_text = str(parsed.get(action_field, "") or "").strip()
    if action_text and bool(parsed.get("done", False)):
        parsed = dict(parsed)
        parsed["done"] = False
    return parsed
