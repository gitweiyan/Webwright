from __future__ import annotations

import re
import subprocess
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


class AndroidAdbDriver:
    """ADB-backed Android control that does not enable uiautomator2 accessibility."""

    def __init__(self, *, serial: str | None = None):
        self.serial = serial or ""

    def _adb_base(self) -> list[str]:
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        return cmd

    def _run(self, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self._adb_base(), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def connect(self) -> None:
        devices = self._run("devices").stdout.splitlines()[1:]
        authorized = [line.split()[0] for line in devices if "\tdevice" in line]
        if not authorized:
            raise RuntimeError("No authorized Android device found via ADB.")
        if self.serial and self.serial not in authorized:
            raise RuntimeError(
                f"Configured device serial '{self.serial}' not found among: {', '.join(authorized)}"
            )

    def close(self) -> None:
        return None

    def window_size(self) -> tuple[int, int]:
        output = self._run("shell", "wm", "size").stdout
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", output)
        if not match:
            match = re.search(r"Override size:\s*(\d+)x(\d+)", output)
        if not match:
            raise RuntimeError(f"Unable to parse wm size output: {output!r}")
        return int(match.group(1)), int(match.group(2))

    def current_app(self) -> dict[str, str]:
        try:
            output = self._run("shell", "dumpsys", "window", "windows").stdout
        except subprocess.CalledProcessError:
            return {"package": "", "activity": ""}
        match = re.search(r"mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/]+)/([^\}]+)\}", output)
        if not match:
            return {"package": "", "activity": ""}
        return {"package": match.group(1), "activity": match.group(2)}

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = subprocess.check_output([*self._adb_base(), "exec-out", "screencap", "-p"], timeout=30)
        path.write_bytes(raw)

    def screenshot_pixels(self) -> np.ndarray:
        raw = subprocess.check_output([*self._adb_base(), "exec-out", "screencap", "-p"], timeout=30)
        image = Image.open(BytesIO(raw))
        return np.asarray(image.convert("RGB"))

    def click(self, x: int, y: int) -> None:
        self._run("shell", "input", "tap", str(int(x)), str(int(y)))

    def long_click(self, x: int, y: int, *, duration: float = 0.5) -> None:
        self._run(
            "shell",
            "input",
            "swipe",
            str(int(x)),
            str(int(y)),
            str(int(x)),
            str(int(y)),
            str(int(max(100, duration * 1000))),
        )

    def swipe(self, sx: int, sy: int, ex: int, ey: int, duration: float = 0.2) -> None:
        self._run(
            "shell",
            "input",
            "swipe",
            str(int(sx)),
            str(int(sy)),
            str(int(ex)),
            str(int(ey)),
            str(int(max(1, duration * 1000))),
        )

    def press(self, key: str) -> None:
        mapping = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "enter": "KEYCODE_ENTER",
        }
        keycode = mapping.get(key.lower(), key)
        self._run("shell", "input", "keyevent", keycode)

    def input_text(self, text: str) -> None:
        escaped = text.replace(" ", "%s")
        self._run("shell", "input", "text", escaped)

    def launch_app(self, package: str, activity: str | None = None) -> None:
        if activity:
            component = activity if "/" in activity else f"{package}/{activity}"
            self._run("shell", "am", "start", "-n", component)
        else:
            self._run("shell", "monkey", "-p", package, "1")
        time.sleep(0.5)

    def shell(self, command: str) -> str:
        return self._run("shell", command).stdout
