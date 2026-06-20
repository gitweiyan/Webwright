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


def test_should_skip_summary_llm_for_unchanged_click():
    action = json_action.JSONAction(action_type="click", index=2)
    from webwright.android_agent.transition_guard import should_skip_summary_llm

    assert should_skip_summary_llm(action, ui_changed=False) is True
    assert should_skip_summary_llm(action, ui_changed=True) is False


def test_build_programmatic_summary_includes_transition_facts():
    action = json_action.JSONAction(action_type="click", index=2)
    from webwright.android_agent.transition_guard import build_programmatic_summary

    text = build_programmatic_summary(
        action,
        transition_facts="FACT: UI signature unchanged after click (click:2).",
    )
    assert "FACT: UI signature unchanged" in text
