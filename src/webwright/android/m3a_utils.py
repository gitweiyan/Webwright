# Copyright 2026 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utils for M3A."""

import json
import math
import re
from typing import Optional

import cv2
import numpy as np

from webwright.android import agent_utils
from webwright.android.ui_element import UIElement

TRIGGER_SAFETY_CLASSIFIER = 'Triggered LLM safety classifier.'


def _logical_to_physical(
    logical_coordinates: tuple[int, int],
    logical_screen_size: tuple[int, int],
    physical_frame_boundary: tuple[int, int, int, int],
    orientation: int,
) -> tuple[int, int]:
  x, y = logical_coordinates
  px0, py0, px1, py1 = physical_frame_boundary
  px, py = px1 - px0, py1 - py0
  lx, ly = logical_screen_size
  if orientation == 0:
    return (int(x * px / lx) + px0, int(y * py / ly) + py0)
  if orientation == 1:
    return (px - int(y * px / ly) + px0, int(x * py / lx) + py0)
  if orientation == 2:
    return (px - int(x * px / lx) + px0, py - int(y * py / ly) + py0)
  if orientation == 3:
    return (int(y * px / ly) + px0, py - int(x * py / lx) + py0)
  raise ValueError('Unsupported orientation.')


def _ui_element_logical_corner(
    ui_element: UIElement, orientation: int
) -> list[tuple[int, int]]:
  if ui_element.bbox_pixels is None:
    raise ValueError('UI element does not have bounding box.')
  if orientation == 0:
    return [
        (int(ui_element.bbox_pixels.x_min), int(ui_element.bbox_pixels.y_min)),
        (int(ui_element.bbox_pixels.x_max), int(ui_element.bbox_pixels.y_max)),
    ]
  if orientation == 1:
    return [
        (int(ui_element.bbox_pixels.x_min), int(ui_element.bbox_pixels.y_max)),
        (int(ui_element.bbox_pixels.x_max), int(ui_element.bbox_pixels.y_min)),
    ]
  if orientation == 2:
    return [
        (int(ui_element.bbox_pixels.x_max), int(ui_element.bbox_pixels.y_max)),
        (int(ui_element.bbox_pixels.x_min), int(ui_element.bbox_pixels.y_min)),
    ]
  if orientation == 3:
    return [
        (int(ui_element.bbox_pixels.x_max), int(ui_element.bbox_pixels.y_min)),
        (int(ui_element.bbox_pixels.x_min), int(ui_element.bbox_pixels.y_max)),
    ]
  raise ValueError('Unsupported orientation.')


def add_ui_element_mark(
    screenshot: np.ndarray,
    ui_element: UIElement,
    index: int | str,
    logical_screen_size: tuple[int, int],
    physical_frame_boundary: tuple[int, int, int, int],
    orientation: int,
):
  """Add mark (a bounding box plus index) for a UI element in the screenshot."""
  if ui_element.bbox_pixels:
    upper_left_logical, lower_right_logical = _ui_element_logical_corner(
        ui_element, orientation
    )
    upper_left_physical = _logical_to_physical(
        upper_left_logical,
        logical_screen_size,
        physical_frame_boundary,
        orientation,
    )
    lower_right_physical = _logical_to_physical(
        lower_right_logical,
        logical_screen_size,
        physical_frame_boundary,
        orientation,
    )
    x_scale = screenshot.shape[1] / physical_frame_boundary[2]
    y_scale = screenshot.shape[0] / physical_frame_boundary[3]
    iso_scale = math.sqrt(x_scale * x_scale + y_scale * y_scale)
    upper_left_physical = (
        int(upper_left_physical[0] * x_scale),
        int(upper_left_physical[1] * y_scale),
    )
    lower_right_physical = (
        int(lower_right_physical[0] * x_scale),
        int(lower_right_physical[1] * y_scale),
    )

    cv2.rectangle(
        screenshot,
        upper_left_physical,
        lower_right_physical,
        color=(0, 255, 0),
        thickness=int(2 * iso_scale),
    )
    screenshot[
        upper_left_physical[1]
        + int(1 * y_scale) : upper_left_physical[1]
        + int(25 * y_scale),
        upper_left_physical[0]
        + int(1 * x_scale) : upper_left_physical[0]
        + int(35 * x_scale),
        :,
    ] = (255, 255, 255)
    cv2.putText(
        screenshot,
        str(index),
        (
            upper_left_physical[0] + int(1 * x_scale),
            upper_left_physical[1] + int(20 * y_scale),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7 * iso_scale,
        (0, 0, 0),
        thickness=int(2 * iso_scale),
    )


def add_screenshot_label(screenshot: np.ndarray, label: str):
  """Add a text label to the right bottom of the screenshot."""
  height, width, _ = screenshot.shape
  screenshot[height - 30 : height, width - 150 : width, :] = (255, 255, 255)
  cv2.putText(
      screenshot,
      label,
      (width - 120, height - 5),
      cv2.FONT_HERSHEY_SIMPLEX,
      1,
      (0, 0, 0),
      thickness=2,
  )


def parse_reason_action_output(
    raw_reason_action_output: str,
) -> tuple[Optional[str], Optional[str]]:
  """Parses llm action reason output."""
  reason_result = re.search(
      r'Reason:(.*)Action:', raw_reason_action_output, flags=re.DOTALL
  )
  reason = reason_result.group(1).strip() if reason_result else None
  action_result = re.search(
      r'Action:(.*)', raw_reason_action_output, flags=re.DOTALL
  )
  action = action_result.group(1).strip() if action_result else None
  if action:
    extracted = agent_utils.extract_json(action)
    if extracted is not None:
      action = json.dumps(extracted)

  return reason, action


def validate_ui_element(
    ui_element: UIElement,
    screen_width_height_px: tuple[int, int],
) -> bool:
  """Used to filter out invalid UI element."""
  screen_width, screen_height = screen_width_height_px

  if not ui_element.is_visible:
    return False

  if ui_element.bbox_pixels:
    x_min = ui_element.bbox_pixels.x_min
    x_max = ui_element.bbox_pixels.x_max
    y_min = ui_element.bbox_pixels.y_min
    y_max = ui_element.bbox_pixels.y_max

    if (
        x_min >= x_max
        or x_min >= screen_width
        or x_max <= 0
        or y_min >= y_max
        or y_min >= screen_height
        or y_max <= 0
    ):
      return False

  return True
