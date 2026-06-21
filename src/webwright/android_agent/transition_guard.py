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

ACTIONS_EXPECTING_UI_CHANGE = _ACTIONS_EXPECTING_UI_CHANGE


def action_key(action: json_action.JSONAction) -> str:
    if action.action_type in {"click", "long_press", "input_text", "scroll"}:
        return f"{action.action_type}:{action.index}"
    if action.action_type == "open_app":
        return f"open_app:{action.app_name}"
    return action.action_type or "unknown"


_EXCLUSIVE_TOGGLE_CLASSES = frozenset(
    {
        "android.widget.RadioButton",
        "android.widget.CompoundButton",
    }
)


def _toggle_band_key(element: object) -> str | None:
    if not getattr(element, "is_checkable", None):
        return None
    class_name = getattr(element, "class_name", None) or ""
    if class_name not in _EXCLUSIVE_TOGGLE_CLASSES:
        return None
    bbox = getattr(element, "bbox_pixels", None)
    if bbox is None:
        return None
    return "|".join(
        [
            getattr(element, "package_name", None) or "",
            class_name,
            str(int(bbox.x_min)),
            str(int(bbox.x_max)),
        ]
    )


def detect_ambiguous_toggle_facts(elements: list[object]) -> str:
    """Flag exclusive toggle bands where more than one option appears checked."""
    bands: dict[str, list[object]] = {}
    for element in elements:
        key = _toggle_band_key(element)
        if key is None:
            continue
        bands.setdefault(key, []).append(element)

    facts: list[str] = []
    for band_elements in bands.values():
        if len(band_elements) < 2:
            continue
        checked = [element for element in band_elements if getattr(element, "is_checked", None)]
        if len(checked) <= 1:
            continue
        labels = ", ".join(
            f'"{getattr(element, "text", None) or getattr(element, "content_description", None) or "option"}"'
            for element in checked
        )
        facts.append(
            "FACT: Ambiguous toggle group — multiple options appear checked "
            f"({labels}). Try a different input path instead of clicking the same toggles."
        )
    return " ".join(facts)


def should_count_stuck_step(
    action: json_action.JSONAction,
    *,
    ui_changed: bool,
    previous_action: json_action.JSONAction | None,
) -> bool:
    if ui_changed:
        return False
    if action.action_type not in _ACTIONS_EXPECTING_UI_CHANGE:
        return False
    if previous_action is None:
        return False
    if previous_action.action_type not in _ACTIONS_EXPECTING_UI_CHANGE:
        return False
    return action_key(action) == action_key(previous_action)


def build_transition_facts(
    action: json_action.JSONAction,
    *,
    before_signature: str,
    after_signature: str,
    history: list[dict],
    after_ui_elements: list[object] | None = None,
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

    if after_ui_elements:
        ambiguous = detect_ambiguous_toggle_facts(after_ui_elements)
        if ambiguous:
            facts.append(ambiguous)

    return " ".join(facts)


def should_skip_summary_llm(action: json_action.JSONAction, *, ui_changed: bool) -> bool:
    return action.action_type in _ACTIONS_EXPECTING_UI_CHANGE and not ui_changed


def build_programmatic_summary(
    action: json_action.JSONAction,
    *,
    transition_facts: str,
) -> str:
    if transition_facts:
        return transition_facts
    return (
        f"No visible UI change after {action.action_type} ({action_key(action)}). "
        "Re-check the target index and try a different approach."
    )


def build_previous_step_feedback(history: list[dict]) -> str:
    """Facts from the latest executed step for the next action prompt."""
    if not history:
        return ""
    last_step = history[-1]
    facts = str(last_step.get("transition_facts") or "")
    if not facts:
        action = last_step.get("action_output_json")
        if not isinstance(action, json_action.JSONAction):
            return ""
        facts = build_transition_facts(
            action,
            before_signature=str(last_step.get("before_signature") or ""),
            after_signature=str(last_step.get("after_signature") or ""),
            history=history[:-1],
        )
    if not facts:
        return ""
    return f"Previous step result: {facts}\n\n"
