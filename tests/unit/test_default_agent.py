from __future__ import annotations

from webwright.agents.default import AgentConfig, DefaultAgent, _is_observation_only_code
from webwright.exceptions import FormatError


class FakeEnv:
    def execute(self, action):
        return {
            "output": "",
            "observation": action.get("observation")
            or {
                "success": True,
                "current_app": {"package": "com.demo", "activity": ".ui.UserHomePageActivity"},
            },
        }

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {}


class FakeModel:
    def format_observation_messages(self, message, outputs, template_vars=None):
        return [{"role": "user", "content": "observation", "extra": {"observation": {}}}]

    def format_message(self, **kwargs):
        return kwargs

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {}


def _make_agent(**kwargs) -> DefaultAgent:
    config = AgentConfig(
        system_template="system",
        instance_template="instance",
        **kwargs,
    )
    if config.repeat_action_warning_threshold <= 0:
        config = config.model_copy(update={"repeat_action_warning_threshold": 2})
    return DefaultAgent(FakeModel(), FakeEnv(), **config.model_dump())


def _assistant(code: str) -> dict:
    return {
        "role": "assistant",
        "content": "thought",
        "extra": {"actions": [{"python_code": code}]},
    }


def _observation(*, activity: str, success: bool = True) -> dict:
    return {
        "role": "user",
        "content": "observation",
        "extra": {
            "observation": {
                "success": success,
                "current_app": {"package": "com.demo", "activity": activity},
            }
        },
    }


def test_action_step_records_pairs_assistant_actions_with_observations():
    agent = _make_agent()
    agent.messages = [
        _assistant("driver.click_text('A')"),
        _observation(activity=".HomeActivity"),
        _assistant("driver.click_text('B')"),
        _observation(activity=".SearchActivity", success=False),
    ]

    records = agent._action_step_records()

    assert len(records) == 2
    assert records[0]["code"] == "driver.click_text('A')"
    assert records[0]["activity"] == ".HomeActivity"
    assert records[0]["success"] is True
    assert records[1]["code"] == "driver.click_text('B')"
    assert records[1]["success"] is False


def test_recent_action_history_formats_last_steps():
    agent = _make_agent(action_history_steps=2)
    agent.messages = [
        _assistant("step one"),
        _observation(activity=".A"),
        _assistant("step two"),
        _observation(activity=".B"),
        _assistant("step three"),
        _observation(activity=".C"),
    ]

    history = agent._recent_action_history(2)

    assert "Step 2: step two" in history
    assert "activity=.B" in history
    assert "Step 3: step three" in history
    assert "activity=.C" in history
    assert "Step 1:" not in history


def test_repeat_action_warning_triggers_on_stuck_activity():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('明星狐')"),
        _observation(activity=".ui.UserHomePageActivity"),
    ]
    message = _assistant("driver.click_text('明星狐')")
    outputs = [
        {
            "observation": {
                "success": True,
                "current_app": {"activity": ".ui.UserHomePageActivity"},
            }
        }
    ]

    warning = agent._repeat_action_warning(message, outputs)

    assert warning is not None
    assert "Loop detected" in warning
    assert "driver.click_text('明星狐')" in warning


def test_repeat_action_warning_skips_observation_only_code():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("print(driver.current_app())"),
        _observation(activity=".Launcher"),
        _assistant("print(driver.current_app())"),
        _observation(activity=".Launcher"),
    ]
    message = _assistant("print(driver.current_app())")
    outputs = [{"observation": {"success": True, "current_app": {"activity": ".Launcher"}}}]

    assert agent._repeat_action_warning(message, outputs) is None


def test_repeat_action_warning_ignores_failed_attempts():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('App')"),
        _observation(activity=".Launcher", success=False),
    ]
    message = _assistant("driver.click_text('App')")
    outputs = [{"observation": {"success": True, "current_app": {"activity": ".Launcher"}}}]

    assert agent._repeat_action_warning(message, outputs) is None


def test_is_observation_only_code():
    assert _is_observation_only_code("print(driver.current_app())\nprint(driver.snapshot_text())")
    assert not _is_observation_only_code("driver.click_text('Go')")


def test_repeat_action_warning_ignored_when_activity_changes():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('明星狐')"),
        _observation(activity=".ui.UserHomePageActivity"),
        _assistant("driver.press('back')"),
        _observation(activity=".ui.homepage.MainActivity"),
    ]
    message = _assistant("driver.click_text('明星狐')")
    outputs = [
        {
            "observation": {
                "success": True,
                "current_app": {"activity": ".ui.homepage.MainActivity"},
            }
        }
    ]

    assert agent._repeat_action_warning(message, outputs) is None


def test_execute_actions_attaches_action_history_to_observation_template():
    captured: dict[str, str] = {}

    class RecordingModel(FakeModel):
        def format_observation_messages(self, message, outputs, template_vars=None):
            captured["action_history"] = (template_vars or {}).get("action_history", "")
            return [self.format_message(role="user", content="observation")]

    agent = _make_agent(attach_action_history=True, action_history_steps=8)
    agent.model = RecordingModel()
    agent.messages = [
        _assistant("driver.click_text('搜狐视频')"),
        _observation(activity=".MainActivity"),
    ]

    agent.execute_actions(
        {
            "role": "assistant",
            "content": "open search",
            "extra": {"actions": [{"python_code": "driver.click_search_bar()"}]},
        }
    )

    assert "Step 1: driver.click_text('搜狐视频')" in captured["action_history"]
    assert "activity=.MainActivity" in captured["action_history"]


def test_run_stops_after_max_format_errors_without_progress():
    class FailingModel(FakeModel):
        def query(self, messages):
            raise FormatError(
                self.format_message(
                    role="user",
                    content="format error",
                    extra={"interrupt_type": "FormatError"},
                )
            )

    agent = _make_agent(max_format_errors_without_progress=3)
    agent.model = FailingModel()
    result = agent.run(task="demo")

    assert result["exit_status"] == "FormatErrorExceeded"
    assert agent.n_format_errors == 3


def test_execute_actions_emits_repeat_warning_message():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('明星狐')"),
        _observation(activity=".ui.UserHomePageActivity"),
    ]

    agent.execute_actions(
        {
            "role": "assistant",
            "content": "retry",
            "extra": {"actions": [{"python_code": "driver.click_text('明星狐')"}]},
        }
    )

    warning_messages = [
        msg
        for msg in agent.messages
        if msg.get("extra", {}).get("interrupt_type") == "RepeatActionWarning"
    ]
    assert len(warning_messages) == 1
    assert "Loop detected" in warning_messages[0]["content"]


def _observation_sig(*, signature: str, activity: str = ".A", success: bool = True) -> dict:
    return {
        "role": "user",
        "content": "observation",
        "extra": {
            "observation": {
                "success": success,
                "current_app": {"package": "com.demo", "activity": activity},
                "ui_signature": signature,
            }
        },
    }


def test_repeat_action_warning_uses_ui_signature_when_activity_flaps():
    """Loop is detected even though current_app/activity flaps (the maps quirk)."""
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('BeeBeep Alarm')"),
        _observation_sig(signature="sig-ringtone", activity=".MapsActivity"),
    ]
    message = _assistant("driver.click_text('BeeBeep Alarm')")
    outputs = [
        {
            "observation": {
                "success": True,
                "current_app": {"activity": ".RingtonePickerActivity"},
                "ui_signature": "sig-ringtone",
            }
        }
    ]

    warning = agent._repeat_action_warning(message, outputs)

    assert warning is not None
    assert "Loop detected" in warning


def test_repeat_action_warning_suppressed_when_ui_signature_changes():
    agent = _make_agent(repeat_action_warning_threshold=2)
    agent.messages = [
        _assistant("driver.click_text('Next')"),
        _observation_sig(signature="sig-1", activity=".A"),
    ]
    message = _assistant("driver.click_text('Next')")
    outputs = [
        {
            "observation": {
                "success": True,
                "current_app": {"activity": ".A"},
                "ui_signature": "sig-2",
            }
        }
    ]

    assert agent._repeat_action_warning(message, outputs) is None


def test_execute_actions_stops_after_max_repeat_actions():
    code = "driver.click_text('BeeBeep Alarm')"

    class StuckEnv(FakeEnv):
        def execute(self, action):
            return {
                "output": "",
                "observation": {
                    "success": True,
                    "current_app": {"package": "com.demo", "activity": ".Picker"},
                    "ui_signature": "stuck-sig",
                },
            }

    agent = _make_agent(
        repeat_action_warning_threshold=2,
        max_repeat_actions_before_stop=3,
    )
    agent.env = StuckEnv()
    # Seed one prior identical action that left the same signature.
    agent.messages = [
        _assistant(code),
        _observation_sig(signature="stuck-sig", activity=".Picker"),
    ]

    exit_seen = False
    for _ in range(5):
        added = agent.execute_actions(
            {
                "role": "assistant",
                "content": "retry",
                "extra": {"actions": [{"python_code": code}]},
            }
        )
        if added and added[-1].get("role") == "exit":
            exit_seen = True
            assert added[-1]["extra"]["exit_status"] == "RepeatActionStuck"
            break

    assert exit_seen
    assert agent._repeat_actions_in_a_row >= 3
