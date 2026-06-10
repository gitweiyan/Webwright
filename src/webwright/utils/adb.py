from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from webwright import package_dir

_BUNDLED_ADB = package_dir.parent.parent / "assets" / "adb"


def find_adb() -> str:
    """Return path to adb, preferring the bundled ``assets/adb`` binary."""
    if _BUNDLED_ADB.is_file():
        if not os.access(_BUNDLED_ADB, os.X_OK):
            _BUNDLED_ADB.chmod(
                _BUNDLED_ADB.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        return str(_BUNDLED_ADB)
    return "adb"


def list_adb_devices() -> tuple[list[str], str | None]:
    """Run ``adb devices``, return (serial_numbers, error_or_none)."""
    try:
        result = subprocess.run(
            [find_adb(), "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return [], "adb not found (install Android platform-tools or place adb in assets/)"
    except subprocess.TimeoutExpired:
        return [], "adb devices timed out"
    except Exception as exc:
        return [], str(exc)

    if result.returncode != 0:
        return [], result.stderr.strip() or "adb devices failed"

    devices = [
        line.split("\t")[0]
        for line in result.stdout.splitlines()[1:]
        if line.strip() and "\tdevice" in line
    ]
    return devices, None
