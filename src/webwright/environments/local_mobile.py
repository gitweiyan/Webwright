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
from webwright.devices.snapshots import (
    compact_android_hierarchy,
    foreground_package_from_hierarchy,
)
from webwright.utils.adb import list_adb_devices


def _ui_signature(snapshot: str) -> str:
    """Stable short signature of a UI snapshot, used for screen-change detection."""
    import hashlib

    normalized = " ".join((snapshot or "").split())
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]

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
        self._previous_ui_signature = ""

    def _screenshots_dir(self) -> Path:
        return self.config.output_dir / "screenshots"

    def _steps_dir(self) -> Path:
        return self.config.output_dir / "steps"

    def _hierarchy_dir(self) -> Path:
        return self.config.output_dir / "hierarchy"

    def prepare(self, **kwargs) -> None:
        self._prepared_task = dict(kwargs)
        self._step_index = 0
        self._previous_ui_signature = ""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._steps_dir().mkdir(parents=True, exist_ok=True)
        self._screenshots_dir().mkdir(parents=True, exist_ok=True)
        self._hierarchy_dir().mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "task.json").write_text(
            json.dumps(kwargs, indent=2),
            encoding="utf-8",
        )

        self._driver = self._create_driver()
        self._ensure_device_available()
        try:
            self._driver.connect()
        except Exception as exc:
            raise RuntimeError(
                f"Failed to connect to Android device. "
                f"Verify the device is connected and USB debugging is enabled. "
                f"Run 'python -m webwright.run.doctor' to diagnose.\n"
                f"Original error: {exc}"
            ) from exc
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

    def _ensure_device_available(self) -> None:
        """Check that at least one authorized Android device is connected via ADB."""
        if self.config.platform != "android":
            return
        devices, error = list_adb_devices()
        if error is not None:
            raise RuntimeError(
                f"Cannot check Android device status: {error}\n"
                f"Run 'python -m webwright.run.doctor' to diagnose."
            )
        if not devices:
            raise RuntimeError(
                "No authorized Android device found via ADB.\n"
                "Connect a device with USB debugging enabled, or start an emulator.\n"
                "Run 'python -m webwright.run.doctor' to diagnose."
            )
        if self.config.device_serial and self.config.device_serial not in devices:
            raise RuntimeError(
                f"Configured device serial '{self.config.device_serial}' not found "
                f"among connected devices: {', '.join(devices)}"
            )

    def execute(self, action: dict[str, Any], cwd: str = "") -> dict[str, Any]:
        del cwd
        return asyncio.run(self._execute_async(action))

    async def _execute_async(self, action: dict[str, Any]) -> dict[str, Any]:
        self._step_index += 1
        self._step_python_output = ""
        self._step_python_code = str(action.get("python_code", "") or "")
        self._persist_step_code(self._step_python_code)

        activity_before = ""
        if self._driver is not None:
            try:
                activity_before = self._driver.current_app().get("activity", "")
            except Exception:
                activity_before = ""

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
            activity_before=activity_before,
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

    def _capture_observation(
        self,
        *,
        success: bool,
        exception_text: str,
        activity_before: str = "",
    ) -> dict[str, Any]:
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

        # Reconcile the reported foreground app with the dumped hierarchy. ``app_current()``
        # can lag behind or report a stale/background package (e.g. a lingering Maps
        # activity) while the UI snapshot the model actually reads shows a different app.
        # The hierarchy only contains on-screen windows, so prefer its package and avoid
        # surfacing a contradictory ``current_app`` that derails the agent.
        foreground_package = foreground_package_from_hierarchy(hierarchy_xml)
        app_current_mismatch = False
        if foreground_package and foreground_package != current_app.get("package", ""):
            app_current_mismatch = True
            current_app = {
                "package": foreground_package,
                # ``app_current()`` activity belongs to the wrong package here, so it is
                # unreliable; drop it rather than show a misleading activity name.
                "activity": "",
            }

        ui_signature = _ui_signature(ui_snapshot)
        screen_changed = bool(
            self._previous_ui_signature
            and ui_signature
            and self._previous_ui_signature != ui_signature
        )
        if ui_signature:
            self._previous_ui_signature = ui_signature

        activity_after = current_app.get("activity", "")
        activity_changed = (
            bool(activity_before)
            and bool(activity_after)
            and activity_before != activity_after
        )

        return {
            "success": success,
            "exception": exception_text,
            "platform": self.config.platform,
            "backend": self.config.backend,
            "device_info": device_info,
            "current_app": current_app,
            "previous_activity": activity_before,
            "activity_changed": activity_changed,
            "screen_changed": screen_changed,
            "ui_signature": ui_signature,
            "app_current_mismatch": app_current_mismatch,
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
