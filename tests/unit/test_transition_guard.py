from types import SimpleNamespace

from android_world.env import json_action

from webwright.android_agent.transition_guard import (
    action_key,
    build_action_prompt_feedback,
    build_index_drift_warning,
    build_previous_step_feedback,
    build_transition_facts,
    detect_ambiguous_toggle_facts,
    element_target_key,
    element_target_label,
    format_action_selected_prefix,
    should_count_stuck_step,
)


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


def test_build_previous_step_feedback_after_unchanged_click():
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=2),
            "before_signature": "abc",
            "after_signature": "abc",
            "ui_changed": False,
        }
    ]
    from webwright.android_agent.transition_guard import build_previous_step_feedback

    feedback = build_previous_step_feedback(history)
    assert feedback.startswith("Previous step result: FACT:")
    assert "unchanged" in feedback


def test_build_previous_step_feedback_empty_on_success():
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=2),
            "before_signature": "abc",
            "after_signature": "def",
            "ui_changed": True,
        }
    ]
    from webwright.android_agent.transition_guard import build_previous_step_feedback

    assert build_previous_step_feedback(history) == ""


def test_build_programmatic_summary_includes_transition_facts():
    action = json_action.JSONAction(action_type="click", index=2)
    from webwright.android_agent.transition_guard import build_programmatic_summary

    text = build_programmatic_summary(
        action,
        transition_facts="FACT: UI signature unchanged after click (click:2).",
    )
    assert "FACT: UI signature unchanged" in text


def test_should_count_stuck_step_only_for_same_action_key():
    click_six = json_action.JSONAction(action_type="click", index=6)
    click_seven = json_action.JSONAction(action_type="click", index=7)

    assert should_count_stuck_step(
        click_six,
        ui_changed=False,
        previous_action=click_six,
    )
    assert not should_count_stuck_step(
        click_six,
        ui_changed=False,
        previous_action=click_seven,
    )
    assert not should_count_stuck_step(
        click_six,
        ui_changed=True,
        previous_action=click_six,
    )


def test_detect_ambiguous_toggle_facts_for_am_pm_band():
    elements = [
        SimpleNamespace(
            text="AM",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=771, x_max=908),
        ),
        SimpleNamespace(
            text="PM",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=771, x_max=908),
        ),
    ]
    facts = detect_ambiguous_toggle_facts(elements)
    assert "Ambiguous toggle group" in facts
    assert "AM" in facts
    assert "PM" in facts


def test_detect_ambiguous_toggle_facts_ignores_multi_select_days():
    elements = [
        SimpleNamespace(
            text="Sat",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=100, x_max=200),
        ),
        SimpleNamespace(
            text="Sun",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=300, x_max=400),
        ),
    ]
    assert detect_ambiguous_toggle_facts(elements) == ""


def test_build_transition_facts_includes_ambiguous_toggle():
    action = json_action.JSONAction(action_type="click", index=6)
    elements = [
        SimpleNamespace(
            text="AM",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=771, x_max=908),
        ),
        SimpleNamespace(
            text="PM",
            content_description=None,
            class_name="android.widget.CompoundButton",
            package_name="com.google.android.deskclock",
            is_checkable=True,
            is_checked=True,
            bbox_pixels=SimpleNamespace(x_min=771, x_max=908),
        ),
    ]
    facts = build_transition_facts(
        action,
        before_signature="abc",
        after_signature="def",
        history=[],
        after_ui_elements=elements,
    )
    assert "Ambiguous toggle group" in facts


def test_build_previous_step_feedback_uses_stored_transition_facts():
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=6),
            "before_signature": "abc",
            "after_signature": "def",
            "ui_changed": True,
            "transition_facts": "FACT: Ambiguous toggle group — multiple options appear checked.",
        }
    ]
    feedback = build_previous_step_feedback(history)
    assert "Ambiguous toggle group" in feedback


def test_element_target_key_and_label():
    element = SimpleNamespace(
        text="",
        content_description="Make larger",
        resource_name="com.android.settings:id/icon_end_frame",
        class_name="android.widget.FrameLayout",
    )
    assert "Make larger" in element_target_key(element)
    assert element_target_label(element) == "Make larger"


def test_build_index_drift_warning_when_index_remaps():
    make_larger = SimpleNamespace(
        text="",
        content_description="Make larger",
        resource_name="com.android.settings:id/icon_end_frame",
        class_name="android.widget.FrameLayout",
    )
    notification = SimpleNamespace(
        text="",
        content_description="Digital Wellbeing notification: Need time to focus?",
        resource_name="",
        class_name="android.widget.ImageView",
    )
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=15),
            "action_target_key": element_target_key(make_larger),
            "action_target_label": "Make larger",
        }
    ]
    warning = build_index_drift_warning(history, [make_larger] * 15 + [notification])
    assert "Index 15 no longer refers" in warning
    assert "Make larger" in warning
    assert "Digital Wellbeing" in warning


def test_build_action_prompt_feedback_includes_drift_and_previous_facts():
    make_larger = SimpleNamespace(
        text="",
        content_description="Make larger",
        resource_name="com.android.settings:id/icon_end_frame",
        class_name="android.widget.FrameLayout",
    )
    notification = SimpleNamespace(
        text="",
        content_description="Digital Wellbeing notification: Need time to focus?",
        resource_name="",
        class_name="android.widget.ImageView",
    )
    history = [
        {
            "action_output_json": json_action.JSONAction(action_type="click", index=15),
            "action_target_key": element_target_key(make_larger),
            "action_target_label": "Make larger",
            "before_signature": "abc",
            "after_signature": "abc",
            "ui_changed": False,
        }
    ]
    feedback = build_action_prompt_feedback(
        history,
        current_ui_elements=[make_larger] * 15 + [notification],
    )
    assert "Index 15 no longer refers" in feedback
    assert "Previous step result: FACT:" in feedback


def test_format_action_selected_prefix_includes_target_label():
    prefix = format_action_selected_prefix(
        '{"action_type": "click", "index": 15}',
        "Make larger",
    )
    assert "target: Make larger" in prefix
