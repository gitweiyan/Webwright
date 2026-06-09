from __future__ import annotations

import asyncio
import io
import json
import textwrap
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from webwright.devices.android_uiautomator2 import AndroidUiautomator2Driver
from webwright.devices.snapshots import compact_android_hierarchy

_DRIVER_MAPPING = {
    ("android", "uiautomator2"): AndroidUiautomator2Driver,
}


class LocalMobileEnvironmentConfig(BaseModel):
    platform: str = "android"
    backend: str = "uiautomator2"
    device_serial: str | None = None
    connect_url: str | None = None
    app_package: str | None = None
    app_activity: str | None = None
    launch_app_on_prepare: bool = True
    reset_app_on_prepare: bool = False
    keep_app_open_on_exit: bool = True
    output_dir: Path = Path("outputs/default")
    step_execution_timeout_ms: int = 20000
    observation_timeout_ms: int = 5000
    hierarchy_max_chars: int = 20000
    hierarchy_max_nodes: int = 160


class LocalMobileEnvironment:
    """Live local mobile device environment.

    The environment owns a device driver and executes each model action as an async
    Python snippet with ``device``, ``driver``, ``asyncio``, and ``task`` available.
    ``device`` is the raw backend object (uiautomator2 for Android); ``driver`` is a
    small cross-device adapter with helper methods and a stable observation format.
    """

    def __init__(self, *, config_class: type = LocalMobileEnvironmentConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.config.output_dir = self.config.output_dir.expanduser()
        self._step_index = 0
        self._prepared_task: dict[str, Any] = {}
        self._driver = None
        self._step_python_code = ""
        self._step_python_output = ""

    def _screenshots_dir(self) -> Path:
        return self.config.output_dir / "screenshots"

    def _steps_dir(self) -> Path:
        return self.config.output_dir / "steps"

    def _hierarchy_dir(self) -> Path:
        return self.config.output_dir / "hierarchy"

    def prepare(self, **kwargs) -> None:
        self._prepared_task = dict(kwargs)
        self._step_index = 0
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._steps_dir().mkdir(parents=True, exist_ok=True)
        self._screenshots_dir().mkdir(parents=True, exist_ok=True)
        self._hierarchy_dir().mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "task.json").write_text(
            json.dumps(kwargs, indent=2),
            encoding="utf-8",
        )

        self._driver = self._create_driver()
        self._driver.connect()
        if self.config.app_package:
            if self.config.reset_app_on_prepare:
                self._driver.stop_app(self.config.app_package)
            if self.config.launch_app_on_prepare:
                self._driver.launch_app(self.config.app_package, self.config.app_activity)

    def _create_driver(self):
        key = (self.config.platform.lower(), self.config.backend.lower())
        driver_class = _DRIVER_MAPPING.get(key)
        if driver_class is None:
            supported = ", ".join(f"{platform}/{backend}" for platform, backend in sorted(_DRIVER_MAPPING))
            raise ValueError(
                f"Unsupported mobile backend {self.config.platform}/{self.config.backend}. "
                f"Supported backends: {supported}"
            )
        return driver_class(serial=self.config.device_serial, connect_url=self.config.connect_url)

    def execute(self, action: dict[str, Any], cwd: str = "") -> dict[str, Any]:
        del cwd
        return asyncio.run(self._execute_async(action))

    async def _execute_async(self, action: dict[str, Any]) -> dict[str, Any]:
        self._step_index += 1
        self._step_python_output = ""
        self._step_python_code = str(action.get("python_code", "") or "")
        self._persist_step_code(self._step_python_code)

        success = True
        exception_text = ""
        try:
            if self._step_python_code.strip():
                await asyncio.wait_for(
                    self._run_python_code(self._step_python_code),
                    timeout=self.config.step_execution_timeout_ms / 1000,
                )
            await asyncio.sleep(max(0, self.config.observation_timeout_ms) / 1000)
        except Exception:
            success = False
            exception_text = traceback.format_exc()

        observation = self._capture_observation(
            success=success,
            exception_text=exception_text,
        )
        return {
            "output": self._step_python_output,
            "returncode": 0 if success else 1,
            "exception_info": exception_text,
            "observation": observation,
        }

    def _persist_step_code(self, python_code: str) -> None:
        step_path = self._steps_dir() / f"step_{self._step_index:04d}.py"
        step_path.write_text(python_code, encoding="utf-8")

        script_path = self.config.output_dir / "script.py"
        with script_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n\n# Step {self._step_index}\n")
            handle.write(python_code)
            handle.write("\n")

    async def _run_python_code(self, python_code: str) -> None:
        if self._driver is None:
            raise RuntimeError("Mobile environment was not prepared.")

        buffer = io.StringIO()
        globals_dict: dict[str, Any] = {"asyncio": asyncio}
        locals_dict: dict[str, Any] = {}
        wrapped = "async def __agent_step__(device, driver, task):\n"
        wrapped += textwrap.indent(python_code, "    ")
        with redirect_stdout(buffer), redirect_stderr(buffer):
            exec(wrapped, globals_dict, locals_dict)
            await locals_dict["__agent_step__"](
                self._driver.raw,
                self._driver,
                self._prepared_task,
            )
        self._step_python_output = buffer.getvalue()

    def _capture_observation(self, *, success: bool, exception_text: str) -> dict[str, Any]:
        screenshot_path: Path | None = None
        hierarchy_path: Path | None = None
        hierarchy_xml = ""
        ui_snapshot = ""
        current_app = {"package": "", "activity": ""}
        device_info: dict[str, Any] = {}

        if self._driver is not None:
            try:
                current_app = self._driver.current_app()
            except Exception:
                current_app = {"package": "", "activity": ""}
            try:
                device_info = self._driver.get_info()
            except Exception:
                device_info = {}
            try:
                screenshot_path = self._screenshots_dir() / f"step_{self._step_index:04d}.png"
                self._driver.screenshot(screenshot_path)
            except Exception:
                screenshot_path = None
            try:
                hierarchy_xml = self._driver.dump_hierarchy()
                hierarchy_path = self._hierarchy_dir() / f"step_{self._step_index:04d}.xml"
                hierarchy_path.write_text(hierarchy_xml, encoding="utf-8")
                ui_snapshot = compact_android_hierarchy(
                    hierarchy_xml,
                    max_chars=self.config.hierarchy_max_chars,
                    max_nodes=self.config.hierarchy_max_nodes,
                )
            except Exception:
                hierarchy_path = None
                ui_snapshot = ""

        return {
            "success": success,
            "exception": exception_text,
            "platform": self.config.platform,
            "backend": self.config.backend,
            "device_info": device_info,
            "current_app": current_app,
            "screenshot_path": str(screenshot_path) if screenshot_path is not None else "",
            "hierarchy_path": str(hierarchy_path) if hierarchy_path is not None else "",
            "ui_snapshot": ui_snapshot,
            "python_code": self._step_python_code,
            "python_output": self._step_python_output,
            "url": "",
            "title": current_app.get("activity", ""),
            "aria_snapshot": "",
            "console_output": "",
            "recent_console": "",
        }

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return {
            "output_dir": str(self.config.output_dir.resolve()),
            "platform": self.config.platform,
            "backend": self.config.backend,
            "device_serial": self.config.device_serial or "",
            "connect_url": self.config.connect_url or "",
            "app_package": self.config.app_package or "",
            "app_activity": self.config.app_activity or "",
            **kwargs,
        }

    def serialize(self) -> dict[str, Any]:
        return {
            "environment": {
                "config": self.config.model_dump(mode="json"),
                "environment_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
            }
        }

    def close(self) -> None:
        if self._driver is None:
            return
        try:
            if self.config.app_package and not self.config.keep_app_open_on_exit:
                self._driver.stop_app(self.config.app_package)
        finally:
            self._driver.close()
            self._driver = None
