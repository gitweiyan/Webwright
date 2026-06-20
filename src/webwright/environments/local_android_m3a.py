from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel

from android_world.env import interface, json_action

from webwright.devices.a11y_forwarder_client import (
    A11yForwarderClient,
    to_representation_ui_elements,
    ui_elements_signature,
)
from webwright.devices.android_adb import AndroidAdbDriver
from webwright.devices.m3a_actuation import execute_u2_action


class _U2ControllerStub:
    """Minimal controller placeholder for ``AsyncEnv.controller``."""

    def __init__(self, screen_size: tuple[int, int]):
        self._screen_size = screen_size

    @property
    def device_screen_size(self) -> tuple[int, int]:
        return self._screen_size


class LocalAndroidM3aAsyncEnvConfig(BaseModel):
    device_serial: str | None = None
    connect_url: str | None = None
    forwarder_url: str = "http://127.0.0.1:8765"
    wait_after_action_seconds: float = 1.5
    stabilize_timeout_seconds: float = 6.0
    stabilize_sleep_seconds: float = 0.5
    stabilize_threshold: int = 3


class LocalAndroidM3aAsyncEnv(interface.AsyncEnv):
    """AndroidWorld ``AsyncEnv`` backed by forwarder UI tree + u2 actuation."""

    def __init__(self, config: LocalAndroidM3aAsyncEnvConfig | None = None, **kwargs):
        self.config = config or LocalAndroidM3aAsyncEnvConfig(**kwargs)
        self._driver = AndroidAdbDriver(serial=self.config.device_serial)
        self._forwarder = A11yForwarderClient(self.config.forwarder_url)
        self._controller_stub = _U2ControllerStub((1080, 2400))
        self.interaction_cache = ""
        self._prior_signature = ""

    @property
    def interaction_cache(self) -> str:
        return self._interaction_cache

    @interaction_cache.setter
    def interaction_cache(self, value: str) -> None:
        self._interaction_cache = value or ""

    @property
    def controller(self):
        return self._controller_stub

    def connect(self) -> None:
        self._driver.connect()
        self._refresh_screen_size()

    def reset(self, go_home: bool = False) -> interface.State:
        if go_home:
            self._driver.press("home")
            time.sleep(0.5)
        self.interaction_cache = ""
        self._prior_signature = ""
        return self.get_state(wait_to_stabilize=False)

    def get_state(self, wait_to_stabilize: bool = False) -> interface.State:
        if wait_to_stabilize:
            return self._get_stable_state()
        return self._build_state()

    def execute_action(self, action: json_action.JSONAction) -> None:
        if action.action_type == json_action.ANSWER:
            self.interaction_cache = action.text or ""
            return
        if action.action_type == json_action.STATUS:
            return

        state = self.get_state(wait_to_stabilize=False)
        execute_u2_action(
            action,
            state.ui_elements,
            self.logical_screen_size,
            self._driver,
        )
        time.sleep(max(0.0, self.config.wait_after_action_seconds))

    def hide_automation_ui(self) -> None:
        try:
            self._driver.shell("settings put system pointer_location 0")
        except Exception:
            return None

    def ask_question(self, question: str, timeout_seconds: float = -1.0) -> str | None:
        del question, timeout_seconds
        raise NotImplementedError("ask_question is not implemented.")

    @property
    def foreground_activity_name(self) -> str:
        return self._driver.current_app().get("activity", "")

    @property
    def device_screen_size(self) -> tuple[int, int]:
        return self._driver.window_size()

    @property
    def logical_screen_size(self) -> tuple[int, int]:
        return self.device_screen_size

    @property
    def orientation(self) -> int:
        return 0

    @property
    def physical_frame_boundary(self) -> tuple[int, int, int, int]:
        width, height = self.device_screen_size
        return (0, 0, width, height)

    def close(self) -> None:
        self._driver.close()

    def _refresh_screen_size(self) -> None:
        self._controller_stub = _U2ControllerStub(self._driver.window_size())

    def _build_state(self) -> interface.State:
        forwarder_elements = self._forwarder.fetch_ui_elements()
        ui_elements = to_representation_ui_elements(forwarder_elements)
        pixels = self._screenshot_pixels()
        return interface.State(
            pixels=pixels,
            forest=forwarder_elements,
            ui_elements=ui_elements,
            auxiliaries={"ui_elements_signature": ui_elements_signature(forwarder_elements)},
        )

    def _screenshot_pixels(self) -> np.ndarray:
        return self._driver.screenshot_pixels()

    def _get_stable_state(self) -> interface.State:
        threshold = max(1, self.config.stabilize_threshold)
        sleep_duration = max(0.0, self.config.stabilize_sleep_seconds)
        deadline = time.time() + max(0.0, self.config.stabilize_timeout_seconds)

        state = self._build_state()
        signature = str(state.auxiliaries.get("ui_elements_signature", ""))
        stable_checks = 1
        while stable_checks < threshold and time.time() < deadline:
            iteration_start = time.time()
            current_state = self._build_state()
            current_signature = str(current_state.auxiliaries.get("ui_elements_signature", ""))
            if current_signature == signature:
                stable_checks += 1
                if stable_checks >= threshold:
                    return current_state
            else:
                stable_checks = 1
                signature = current_signature
                state = current_state

            elapsed = time.time() - iteration_start
            remaining_sleep = sleep_duration - elapsed
            if remaining_sleep > 0:
                time.sleep(min(remaining_sleep, deadline - time.time()))

        return state


class LocalAndroidM3aEnvironmentConfig(BaseModel):
    environment_class: str = "local_android_m3a"
    device_serial: str | None = None
    connect_url: str | None = None
    forwarder_url: str = "http://127.0.0.1:8765"
    output_dir: Path = Path("outputs/default")
    wait_after_action_seconds: float = 1.5
    step_limit: int = 5


class LocalAndroidM3aEnvironment:
    """Webwright environment wrapper around ``LocalAndroidM3aAsyncEnv``."""

    def __init__(self, *, config_class: type = LocalAndroidM3aEnvironmentConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.config.output_dir = self.config.output_dir.expanduser()
        self._async_env: LocalAndroidM3aAsyncEnv | None = None
        self._prepared_task: dict[str, Any] = {}

    @property
    def async_env(self) -> LocalAndroidM3aAsyncEnv:
        if self._async_env is None:
            raise RuntimeError("Environment was not prepared.")
        return self._async_env

    def prepare(self, **kwargs) -> None:
        self._prepared_task = dict(kwargs)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "task.json").write_text(
            json.dumps(kwargs, indent=2),
            encoding="utf-8",
        )
        self._async_env = LocalAndroidM3aAsyncEnv(
            device_serial=self.config.device_serial,
            connect_url=self.config.connect_url,
            forwarder_url=self.config.forwarder_url,
            wait_after_action_seconds=self.config.wait_after_action_seconds,
        )
        self._async_env.connect()
        health = self._async_env._forwarder.fetch_health()
        if not health.get("has_forest"):
            raise RuntimeError(
                "Forwarder has no forest. Start grpc_receiver with --setup --serve first."
            )

    def execute(self, action: dict[str, Any], cwd: str = "") -> dict[str, Any]:
        del cwd
        raise NotImplementedError(
            "local_android_m3a uses M3A JSON actions via M3aAndroidAgent, not python_code steps."
        )

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        del kwargs
        return {
            "platform": "android",
            "backend": "forwarder+u2",
            "device_serial": self.config.device_serial or "",
            "forwarder_url": self.config.forwarder_url,
        }

    def serialize(self) -> dict[str, Any]:
        return self.config.model_dump()

    def close(self) -> None:
        if self._async_env is not None:
            self._async_env.close()
            self._async_env = None
