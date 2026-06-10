from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from webwright.devices.snapshots import compact_android_hierarchy


class AndroidUiautomator2Driver:
    """Thin uiautomator2 adapter plus stable helper methods for generated code."""

    def __init__(self, *, serial: str | None = None, connect_url: str | None = None):
        self.serial = serial or ""
        self.connect_url = connect_url or ""
        self.raw: Any = None

    def connect(self) -> None:
        try:
            import uiautomator2 as u2
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "uiautomator2 is not installed. Install Android support with "
                "`pip install -e .[android]` or `pip install uiautomator2`."
            ) from exc

        target = self.connect_url or self.serial or None
        self.raw = u2.connect(target) if target else u2.connect()

    def close(self) -> None:
        return None

    def _device(self):
        if self.raw is None:
            raise RuntimeError("Android device is not connected.")
        return self.raw

    def get_info(self) -> dict[str, Any]:
        info = getattr(self._device(), "info", {})
        return dict(info) if isinstance(info, dict) else {"info": info}

    def current_app(self) -> dict[str, Any]:
        try:
            app = self._device().app_current()
        except Exception:
            return {"package": "", "activity": ""}
        if isinstance(app, dict):
            return {
                "package": str(app.get("package") or app.get("packageName") or ""),
                "activity": str(app.get("activity") or ""),
            }
        return {"package": "", "activity": str(app)}

    def launch_app(self, package: str, activity: str | None = None, *, stop: bool = False) -> None:
        if activity:
            self._device().app_start(package, activity, stop=stop)
        else:
            self._device().app_start(package, stop=stop)

    def stop_app(self, package: str) -> None:
        self._device().app_stop(package)

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._device().screenshot(str(path))

    def dump_hierarchy(self) -> str:
        return str(self._device().dump_hierarchy(compressed=True, pretty=True, max_depth=30))

    def click(self, x: int, y: int) -> None:
        self._device().click(int(x), int(y))

    def swipe(self, sx: int, sy: int, ex: int, ey: int, duration: float = 0.2) -> None:
        self._device().swipe(int(sx), int(sy), int(ex), int(ey), float(duration))

    def press(self, key: str) -> None:
        self._device().press(key)

    def input_text(self, text: str) -> None:
        self._device().send_keys(text)

    def wait_idle(self, timeout: float = 5.0) -> None:
        # uiautomator2 has no universal idle primitive; a short sleep is the safest
        # backend-neutral default, while generated code can use explicit waits.
        time.sleep(max(0.0, min(float(timeout), 30.0)))

    def snapshot_text(self, *, max_chars: int = 20000) -> str:
        return compact_android_hierarchy(self.dump_hierarchy(), max_chars=max_chars)

    def selector(self, **kwargs):
        """Return a raw uiautomator2 UiObject for advanced generated code."""
        return self._device()(**kwargs)

    def xpath(self, expression: str):
        """Return a raw uiautomator2 XPath selector."""
        return self._device().xpath(expression)

    def window_size(self) -> tuple[int, int]:
        size = self._device().window_size()
        return int(size[0]), int(size[1])

    def exists(self, **kwargs) -> bool:
        return bool(self.selector(**kwargs).exists)

    def exists_text(self, text: str) -> bool:
        return self.exists(text=text)

    def exists_desc(self, description: str) -> bool:
        return self.exists(description=description)

    def exists_resource_id(self, resource_id: str) -> bool:
        return self.exists(resourceId=resource_id)

    def wait(self, *, timeout: float = 10.0, **kwargs) -> bool:
        return bool(self.selector(**kwargs).wait(timeout=timeout))

    def wait_text(self, text: str, *, timeout: float = 10.0) -> bool:
        return self.wait(text=text, timeout=timeout)

    def wait_gone(self, *, timeout: float = 10.0, **kwargs) -> bool:
        return bool(self.selector(**kwargs).wait_gone(timeout=timeout))

    def click_text(self, text: str, *, timeout: float = 5.0) -> None:
        self._device()(text=text).click(timeout=timeout)

    def click_text_contains(self, text: str, *, timeout: float = 5.0) -> None:
        self._device()(textContains=text).click(timeout=timeout)

    def click_desc(self, description: str, *, timeout: float = 5.0) -> None:
        self._device()(description=description).click(timeout=timeout)

    def click_desc_contains(self, description: str, *, timeout: float = 5.0) -> None:
        self._device()(descriptionContains=description).click(timeout=timeout)

    def click_resource_id(self, resource_id: str, *, timeout: float = 5.0) -> None:
        self._device()(resourceId=resource_id).click(timeout=timeout)

    def click_if_exists(self, *, timeout: float = 5.0, **kwargs) -> bool:
        obj = self.selector(**kwargs)
        return bool(obj.click_exists(timeout=timeout))

    def click_if_text(self, text: str, *, timeout: float = 2.0) -> bool:
        """Click text only if present; return False instead of raising."""
        return self.click_if_exists(text=text, timeout=timeout)

    def submit_input(self, *, timeout: float = 3.0) -> bool:
        """Submit the active text field using common affordances (no app-specific ids)."""
        for label in ("搜索", "Search", "Go", "GO", "确定", "完成", "查询"):
            if self.click_if_exists(text=label, timeout=timeout):
                return True
        for label in ("Search", "搜索"):
            if self.click_if_exists(descriptionContains=label, timeout=timeout):
                return True
        if self.click_if_exists(className="android.widget.Button", timeout=timeout):
            return True
        try:
            self.press("enter")
            return True
        except Exception:
            return False

    def click_search_bar(
        self,
        *,
        resource_id: str | None = None,
        desc: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        """Open search via container or icon — not hint/placeholder text."""
        if resource_id:
            self.click_resource_id(resource_id, timeout=timeout)
            return
        if desc:
            self.click_desc(desc, timeout=timeout)
            return
        for expression in (
            '//*[contains(@resource-id, "Search") and @clickable="true"]',
            '//*[contains(@content-desc, "搜索") and @clickable="true"]',
            '//*[@class="android.widget.EditText"]',
        ):
            obj = self._device().xpath(expression)
            if obj.exists:
                obj.click(timeout=timeout)
                return
        raise RuntimeError(
            "No search bar found; inspect the UI snapshot for a search container resource-id."
        )

    def click_xpath(self, expression: str, *, timeout: float = 10.0) -> None:
        self._device().xpath(expression).click(timeout=timeout)

    def set_text(self, resource_id: str, text: str, *, timeout: float = 5.0) -> None:
        obj = self._device()(resourceId=resource_id)
        obj.wait(timeout=timeout)
        obj.set_text(text)

    def set_selector_text(self, text: str, *, timeout: float = 5.0, clear: bool = True, **kwargs) -> None:
        obj = self.selector(**kwargs)
        obj.wait(timeout=timeout)
        if clear:
            try:
                obj.clear_text()
            except Exception:
                pass
        obj.set_text(text)

    def scroll_to_text(self, text: str, *, max_swipes: int = 20) -> bool:
        return bool(self._device()(scrollable=True).scroll.to(text=text, max_swipes=max_swipes))

    def scroll_to_desc(self, description: str, *, max_swipes: int = 20) -> bool:
        return bool(
            self._device()(scrollable=True).scroll.to(
                description=description,
                max_swipes=max_swipes,
            )
        )

    def swipe_ext(self, direction: str, *, scale: float = 0.8) -> None:
        self._device().swipe_ext(direction, scale=scale)

    def drag_to(self, sx: int, sy: int, ex: int, ey: int, *, duration: float = 0.5) -> None:
        self._device().drag(int(sx), int(sy), int(ex), int(ey), duration=float(duration))

    def long_click(self, x: int, y: int, *, duration: float = 0.5) -> None:
        self._device().long_click(int(x), int(y), duration=float(duration))

    def clear_text(self, **kwargs) -> None:
        self.selector(**kwargs).clear_text()

    def hide_keyboard(self) -> None:
        self._device().set_fastinput_ime(False)
        try:
            self.press("back")
        except Exception:
            pass

    def set_fastinput_ime(self, enabled: bool = True) -> None:
        self._device().set_fastinput_ime(enabled)

    def wait_activity(self, activity: str, *, timeout: float = 10.0) -> bool:
        return bool(self._device().wait_activity(activity, timeout=timeout))

    def dump_window_hierarchy(self, *, compressed: bool = False, pretty: bool = False) -> str:
        return str(self._device().dump_hierarchy(compressed=compressed, pretty=pretty))
