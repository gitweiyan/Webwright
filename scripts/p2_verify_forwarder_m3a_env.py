#!/usr/bin/env python3
"""P2: verify forwarder AsyncEnv + ADB JSONAction execution (no LLM).

Requires:
  1. emulator/device connected via adb
  2. grpc_receiver running with forwarder configured:
     python tools/a11y/grpc_receiver.py --device emulator-5554 --setup --serve

Note: actuation uses ADB (not uiautomator2) so the forwarder accessibility
service stays active.

Success criteria:
  - get_state() returns ui_elements and RGB screenshot ndarray
  - execute_action(JSONAction click by index) changes ui_elements signature
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from webwright.android import json_action
from webwright.devices.a11y_forwarder_client import ui_elements_signature
from webwright.environments.local_android_m3a import LocalAndroidM3aAsyncEnv


def _pick_click_target_index(ui_elements) -> int | None:
    for index, element in enumerate(ui_elements):
        if element.is_clickable and element.bbox_pixels is not None:
            return index
    for index, element in enumerate(ui_elements):
        if element.bbox_pixels is not None:
            return index
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P2 forwarder M3A env verification")
    parser.add_argument("--device", default="emulator-5554")
    parser.add_argument("--forwarder-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output-dir", default="outputs/p2_forwarder_m3a")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = LocalAndroidM3aAsyncEnv(
        device_serial=args.device,
        forwarder_url=args.forwarder_url,
    )
    try:
        env.connect()
        health = env._forwarder.fetch_health()
        print("health:", health)
        if not health.get("has_forest"):
            print("FAIL: forwarder has no forest. Start grpc_receiver + setup_forwarder first.")
            return 1

        state = env.get_state()
        if not state.ui_elements:
            print("FAIL: get_state().ui_elements is empty")
            return 1
        if state.pixels is None or state.pixels.size == 0:
            print("FAIL: get_state().pixels is empty")
            return 1
        if not isinstance(state.pixels, np.ndarray):
            print(f"FAIL: pixels type is {type(state.pixels)!r}, expected ndarray")
            return 1

        before_sig = str(state.auxiliaries.get("ui_elements_signature", ""))
        print(
            f"before: elements={len(state.ui_elements)} "
            f"pixels={state.pixels.shape} signature={before_sig}"
        )

        screenshot_before = output_dir / "screenshot_before.png"
        from PIL import Image

        Image.fromarray(state.pixels).save(screenshot_before)
        print(f"saved screenshot: {screenshot_before}")

        target_index = _pick_click_target_index(state.ui_elements)
        if target_index is None:
            print("FAIL: no element with bbox to click")
            return 1
        target = state.ui_elements[target_index]
        center = target.bbox_pixels.center if target.bbox_pixels else None
        print(
            "click target:",
            {
                "index": target_index,
                "resource_name": target.resource_name,
                "content_description": target.content_description,
                "center": center,
            },
        )

        env.execute_action(json_action.JSONAction(action_type="click", index=target_index))
        after_state = env.get_state()
        after_sig = str(after_state.auxiliaries.get("ui_elements_signature", ""))
        print(
            f"after: elements={len(after_state.ui_elements)} "
            f"pixels={after_state.pixels.shape} signature={after_sig}"
        )

        screenshot_after = output_dir / "screenshot_after.png"
        Image.fromarray(after_state.pixels).save(screenshot_after)
        print(f"saved screenshot: {screenshot_after}")

        if before_sig == after_sig:
            print("FAIL: ui_elements signature unchanged after JSONAction click")
            return 1

        print("PASS: P2 forwarder AsyncEnv + ADB JSONAction verified")
        return 0
    finally:
        env.close()


if __name__ == "__main__":
    raise SystemExit(main())
