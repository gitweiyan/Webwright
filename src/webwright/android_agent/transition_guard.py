from __future__ import annotations

from android_world.env import json_action

_ACTIONS_EXPECTING_UI_CHANGE = frozenset(
    {
        "click",
        "long_press",
        "input_text",
        "scroll",
        "open_app",
        "navigate_home",
        "navigate_back",
    }
)


def action_key(action: json_action.JSONAction) -> str:
    if action.action_type in {"click", "long_press", "input_text", "scroll"}:
        return f"{action.action_type}:{action.index}"
    if action.action_type == "open_app":
        return f"open_app:{action.app_name}"
    return action.action_type or "unknown"


def build_transition_facts(
    action: json_action.JSONAction,
    *,
    before_signature: str,
    after_signature: str,
    history: list[dict],
) -> str:
    """Return factual transition notes to prepend to the LLM summary."""
    ui_changed = before_signature != after_signature
    facts: list[str] = []

    if action.action_type in _ACTIONS_EXPECTING_UI_CHANGE and not ui_changed:
        facts.append(
            "FACT: UI signature unchanged after "
            f"{action.action_type} ({action_key(action)}). "
            "Do not assume the action succeeded."
        )

    repeat_count = 0
    current_key = action_key(action)
    for step in reversed(history):
        previous_action = step.get("action_output_json")
        if not isinstance(previous_action, json_action.JSONAction):
            continue
        if action_key(previous_action) != current_key:
            break
        if step.get("ui_changed") is False:
            repeat_count += 1
        else:
            break

    if repeat_count >= 1 and not ui_changed:
        facts.append(
            f"FACT: Same action repeated {repeat_count + 1} times without UI change. "
            "Switch strategy instead of retrying."
        )

    return " ".join(facts)
