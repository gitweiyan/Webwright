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

"""Environment interface for real-time Android interaction."""

import abc
import dataclasses
from typing import Any

from webwright.android.json_action import JSONAction
from webwright.android.ui_element import UIElement


@dataclasses.dataclass(frozen=True)
class State:
  """State of the Android environment.

  Attributes:
    pixels: RGB array of current screen (``numpy.ndarray``).
    forest: Raw UI forest from the forwarder or accessibility service.
    ui_elements: Processed UI elements extracted from the forest.
    auxiliaries: Additional information about the state.
  """

  pixels: Any
  forest: Any
  ui_elements: list[UIElement]
  auxiliaries: dict[str, Any] | None = None


class AsyncEnv(abc.ABC):
  """Interface for interacting with a real-time Android device."""

  @property
  @abc.abstractmethod
  def controller(self) -> Any:
    """Returns the controller for the environment."""

  @abc.abstractmethod
  def reset(self, go_home: bool = False) -> State:
    """Reset the environment, optionally navigating home first."""

  @abc.abstractmethod
  def get_state(self, wait_to_stabilize: bool = False) -> State:
    """Gets the state of the environment; i.e., screenshot and UI tree."""

  def display_message(self, message: str, header: str = '') -> None:
    """Displays a message on the screen."""

  @abc.abstractmethod
  def ask_question(
      self, question: str, timeout_seconds: float = -1.0
  ) -> str | None:
    """Asks a question to a hypothetical user in the environment."""

  @abc.abstractmethod
  def execute_action(self, action: JSONAction) -> None:
    """Executes action on the environment."""

  @property
  @abc.abstractmethod
  def foreground_activity_name(self) -> str:
    """Returns the activity name of the app currently opened in foreground."""

  @property
  @abc.abstractmethod
  def device_screen_size(self) -> tuple[int, int]:
    """Returns the screen size of the environment in pixels: (width, height)."""

  @property
  @abc.abstractmethod
  def logical_screen_size(self) -> tuple[int, int]:
    """Retrieves the logical screen size of the Android device."""

  @abc.abstractmethod
  def close(self) -> None:
    """Closes the environment."""

  @property
  @abc.abstractmethod
  def interaction_cache(self) -> str:
    """Returns the interaction cache of the environment."""

  @abc.abstractmethod
  def hide_automation_ui(self) -> None:
    """Hides any automation UI overlays."""

  @property
  @abc.abstractmethod
  def orientation(self) -> int:
    """Returns the orientation of the environment."""

  @property
  @abc.abstractmethod
  def physical_frame_boundary(self) -> tuple[int, int, int, int]:
    """Returns the physical frame boundary of the environment."""
