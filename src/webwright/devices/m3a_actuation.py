from __future__ import annotations

import copy
import logging
import time
from typing import Any

from android_world.env import json_action
from android_world.env.adb_utils import get_adb_activity

from webwright.devices.android_adb import AndroidAdbDriver


def execute_u2_action(
    action: json_action.JSONAction,
    screen_elements: list[Any],
    screen_size: tuple[int, int],
    driver: AndroidAdbDriver,
) -> None:
    """Execute a JSONAction on a live device through uiautomator2."""
    if action.action_type in ["click", "double_tap", "long_press"]:
        idx = action.index
        x = action.x
        y = action.y
        if idx is not None:
            if idx < 0 or idx >= len(screen_elements):
                raise ValueError(
                    f"Invalid element index: {idx}, must be between 0 and "
                    f"{len(screen_elements) - 1}."
                )
            element = screen_elements[idx]
            if element.bbox_pixels is None:
                raise ValueError("Bbox is not present on element.")
            x, y = element.bbox_pixels.center
            x, y = int(x), int(y)
        elif x is not None and y is not None:
            x, y = int(x), int(y)
        else:
            raise ValueError(f"Invalid click action: {action}")

        if action.action_type == "click":
            driver.click(x, y)
        elif action.action_type == "double_tap":
            driver.click(x, y)
            time.sleep(0.1)
            driver.click(x, y)
        else:
            driver.long_click(x, y)

    elif action.action_type == "input_text":
        text = action.text
        if not text:
            logging.warning(
                "input_text action indicated, but no text provided. No action will be executed."
            )
            return

        if action.index is not None or (action.x is not None and action.y is not None):
            click_action = copy.deepcopy(action)
            click_action.action_type = "click"
            execute_u2_action(click_action, screen_elements, screen_size, driver)
            time.sleep(1.0)

        if action.clear_text:
            driver.shell("input keycombination 113 29 && input keyevent 67")
            time.sleep(1.0)

        driver.input_text(text)
        driver.press("enter")

    elif action.action_type == "keyboard_enter":
        driver.press("enter")

    elif action.action_type == "navigate_home":
        driver.press("home")

    elif action.action_type == "navigate_back":
        driver.press("back")

    elif action.action_type == "scroll":
        screen_width, screen_height = screen_size
        if action.index is not None:
            element = screen_elements[action.index]
            if element.bbox_pixels is None:
                raise ValueError("Bbox is not present on element.")
            x_min = max(element.bbox_pixels.x_min, 0)
            y_min = max(element.bbox_pixels.y_min, 0)
            x_max = min(element.bbox_pixels.x_max, screen_width)
            y_max = min(element.bbox_pixels.y_max, screen_height)
        else:
            x_min, y_min, x_max, y_max = (0, 0, screen_width, screen_height)

        start_x, start_y = (x_min + x_max) // 2, (y_min + y_max) // 2
        direction = action.direction
        if direction == "down":
            end_x, end_y = (x_min + x_max) // 2, y_min
        elif direction == "up":
            end_x, end_y = (x_min + x_max) // 2, y_max
        elif direction == "right":
            end_x, end_y = x_min, (y_min + y_max) // 2
        elif direction == "left":
            end_x, end_y = x_max, (y_min + y_max) // 2
        else:
            raise ValueError(f"Invalid scroll direction: {direction!r}")
        driver.swipe(start_x, start_y, end_x, end_y)

    elif action.action_type == "swipe":
        screen_width, screen_height = screen_size
        mid_x, mid_y = int(0.5 * screen_width), int(0.5 * screen_height)
        direction = action.direction
        if direction == "down":
            start_x, start_y = mid_x, 0
            end_x, end_y = mid_x, screen_height
        elif direction == "up":
            start_x, start_y = mid_x, screen_height
            end_x, end_y = mid_x, 0
        elif direction == "left":
            start_x, start_y = 0, mid_y
            end_x, end_y = screen_width, mid_y
        elif direction == "right":
            start_x, start_y = screen_width, mid_y
            end_x, end_y = 0, mid_y
        else:
            raise ValueError(f"Invalid swipe direction: {direction!r}")
        driver.swipe(start_x, start_y, end_x, end_y, duration=0.5)

    elif action.action_type == "open_app":
        app_name = action.app_name
        if not app_name:
            raise ValueError("No app name provided")
        _launch_app(app_name, driver)

    elif action.action_type == "wait":
        time.sleep(1.0)

    elif action.action_type == json_action.UNKNOWN:
        logging.warning("Unknown action type; no action will be executed.")

    else:
        raise ValueError(f"Unsupported action type for u2 actuation: {action.action_type}")


def _launch_app(app_name: str, driver: AndroidAdbDriver) -> None:
    activity = get_adb_activity(app_name)
    if activity is None:
        driver.launch_app(app_name)
        return
    package, act = activity.split("/", 1)
    driver.launch_app(package, act)
