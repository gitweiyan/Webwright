from webwright.android_agent.m3a import _trim_history_summaries


def test_trim_history_summaries_keeps_recent_steps():
    history = [f"step {index}" for index in range(1, 6)]
    trimmed = _trim_history_summaries(history, max_history_steps=3)
    assert trimmed[0] == "(Steps 1-2 omitted from history)"
    assert trimmed[-3:] == ["step 3", "step 4", "step 5"]


def test_trim_history_summaries_noop_when_within_limit():
    history = ["step 1", "step 2"]
    assert _trim_history_summaries(history, max_history_steps=12) == history
