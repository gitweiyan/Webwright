from android_world.env import json_action

from webwright.android_agent.transition_guard import action_key, build_transition_facts


def test_action_key_for_click():
    action = json_action.JSONAction(action_type="click", index=5)
    assert action_key(action) == "click:5"


def test_build_transition_facts_flags_unchanged_ui():
    action = json_action.JSONAction(action_type="click", index=2)
    facts = build_transition_facts(
        action,
        before_signature="abc",
        after_signature="abc",
        history=[],
    )
    assert "FACT: UI signature unchanged" in facts


def test_build_transition_facts_flags_repeat_without_change():
    action = json_action.JSONAction(action_type="click", index=2)
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=2),
            "ui_changed": False,
        }
    ]
    facts = build_transition_facts(
        action,
        before_signature="abc",
        after_signature="abc",
        history=history,
    )
    assert "repeated 2 times" in facts


def test_build_transition_facts_silent_on_successful_change():
    action = json_action.JSONAction(action_type="click", index=2)
    facts = build_transition_facts(
        action,
        before_signature="abc",
        after_signature="def",
        history=[],
    )
    assert facts == ""
