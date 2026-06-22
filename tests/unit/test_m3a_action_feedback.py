from webwright.android_agent.m3a import _action_selection_prompt


def test_action_prompt_includes_previous_step_feedback():
    prompt = _action_selection_prompt(
        "Open Settings",
        ["Step 1- tried something"],
        "UI element 0: {}",
        step_feedback="Previous step result: FACT: UI signature unchanged after click (click:2).\n\n",
    )
    assert "Previous step result: FACT:" in prompt
    assert prompt.index("Previous step result:") < prompt.index("Here is a history")


def test_action_prompt_includes_evidence_and_completion_rules():
    prompt = _action_selection_prompt("Open Settings", [], "UI element 0: {}")
    assert "Verification Before Completion:" in prompt
    assert "Evidence Quality:" in prompt
    assert "Conflicting Evidence:" in prompt
