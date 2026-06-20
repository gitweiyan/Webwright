from __future__ import annotations

import time

from webwright.devices.android_adb import AndroidAdbDriver


def go_home(*, device_serial: str | None = None) -> None:
    AndroidAdbDriver(serial=device_serial or "").press("home")
    time.sleep(0.5)


def press_back(*, device_serial: str | None = None, times: int = 1) -> None:
    driver = AndroidAdbDriver(serial=device_serial or "")
    for _ in range(max(1, times)):
        driver.press("back")
        time.sleep(0.3)


def clear_app_data(package: str, *, device_serial: str | None = None) -> None:
    AndroidAdbDriver(serial=device_serial or "").shell(f"pm clear {package}")
    time.sleep(0.5)


def force_stop(package: str, *, device_serial: str | None = None) -> None:
    AndroidAdbDriver(serial=device_serial or "").shell(f"am force-stop {package}")
    time.sleep(0.3)
