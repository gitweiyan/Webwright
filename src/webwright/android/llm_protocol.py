"""Protocol for multimodal LLM backends used by M3A."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np


class MultimodalLlm(Protocol):
  """Interface for multimodal LLM wrappers."""

  def predict_mm(
      self, text_prompt: str, images: list[np.ndarray]
  ) -> tuple[str, bool | None, Any]:
    """Call multimodal LLM with a prompt and a list of images."""
