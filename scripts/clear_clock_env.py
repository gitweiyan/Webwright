#!/usr/bin/env python3
"""Reset Clock app state on the emulator before alarm benchmarks."""

from __future__ import annotations

import argparse

from webwright.utils.device_reset import clear_app_data, go_home

CLOCK_PACKAGE = "com.google.android.deskclock"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="emulator-5554")
    args = parser.parse_args()
    clear_app_data(CLOCK_PACKAGE, device_serial=args.device)
    go_home(device_serial=args.device)
    print(f"Cleared {CLOCK_PACKAGE} on {args.device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
