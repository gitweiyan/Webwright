from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from pydantic import BaseModel

from webwright.android import json_action, ui_element
from webwright.android_agent import m3a as m3a_module
from webwright.android_agent.base_agent import AgentInteractionResult
from webwright import Environment, Model
from webwright.environments.local_android_m3a import LocalAndroidM3aEnvironment
from webwright.android_agent import transition_guard
from webwright.utils.model_errors import ModelBillingError, raise_if_billing_error
from webwright.utils.ui_signature import ui_elements_signature
from webwright.utils.vision_images import compress_image_for_vision


class WebwrightMultimodalLlmWrapper:
    """Bridge Webwright vision models to M3A ``predict_mm``."""

    def __init__(
        self,
        model: Model,
        *,
        vision_image_max_bytes: int = 100_000,
        vision_image_max_long_edge: int | None = 1280,
    ):
        self._model = model
        self._vision_image_max_bytes = vision_image_max_bytes
        self._vision_image_max_long_edge = vision_image_max_long_edge

    def predict_mm(
        self, text_prompt: str, images: list[np.ndarray]
    ) -> tuple[str, bool | None, Any]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": text_prompt}]
        for image in images:
            jpeg_bytes = compress_image_for_vision(
                image,
                max_bytes=self._vision_image_max_bytes,
                max_long_edge=self._vision_image_max_long_edge,
            )
            encoded = base64.b64encode(jpeg_bytes).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{encoded}",
                    "detail": "high",
                }
            )
        try:
            raw_text = self._model([{"role": "user", "content": content}])
        except Exception as exc:  # noqa: BLE001 - surface billing failures explicitly
            raise_if_billing_error(exc)
            raise
        return raw_text, None, raw_text


class M3aAndroidAgentConfig(BaseModel):
    step_limit: int = 25
    wait_after_action_seconds: float = 2.0
    transition_pause: float | None = 1.0
    go_home_on_reset: bool = True
    vision_image_max_bytes: int = 100_000
    vision_image_max_long_edge: int | None = 1280
    max_stuck_steps: int = 3
    max_history_steps: int = 12
    action_image_mode: str = "som_only"
    output_path: Path | None = None


def _run_output_dir(output_path: Path | None) -> Path | None:
    if output_path is None:
        return None
    return output_path.parent


def _ui_element_to_dict(element: ui_element.UIElement) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in element.__dict__.items():
        if value is None:
            continue
        if isinstance(value, ui_element.BoundingBox):
            row[key] = {
                "x_min": int(value.x_min),
                "x_max": int(value.x_max),
                "y_min": int(value.y_min),
                "y_max": int(value.y_max),
            }
        else:
            row[key] = value
    return row


def _save_screenshot(path: Path, pixels: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    jpeg_path = path if path.suffix.lower() in {".jpg", ".jpeg"} else path.with_suffix(".jpg")
    jpeg_bytes = compress_image_for_vision(pixels, max_bytes=150_000, max_long_edge=1280)
    jpeg_path.write_bytes(jpeg_bytes)


def _action_to_dict(action: Any) -> dict[str, Any] | None:
    if action is None:
        return None
    if isinstance(action, json_action.JSONAction):
        return {
            "action_type": action.action_type,
            "index": action.index,
            "x": action.x,
            "y": action.y,
            "text": action.text,
            "direction": action.direction,
            "app_name": action.app_name,
            "goal_status": action.goal_status,
        }
    return {"raw": str(action)}


def _persist_step_artifacts(
    step_index: int,
    step_data: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Write per-step files and return a compact JSON-serializable record."""
    step_name = f"step_{step_index:04d}"
    screenshots_dir = output_dir / "screenshots"
    ui_elements_dir = output_dir / "ui_elements"
    steps_dir = output_dir / "steps"

    screenshot_before = screenshots_dir / f"{step_name}_before.jpg"
    screenshot_after = screenshots_dir / f"{step_name}_after.jpg"
    ui_elements_path = ui_elements_dir / f"{step_name}_before.json"
    ui_elements_after_path = ui_elements_dir / f"{step_name}_after.json"
    step_record_path = steps_dir / f"{step_name}.json"

    before_ui = step_data.get("before_ui_elements") or []
    after_ui = step_data.get("after_ui_elements") or []
    before_signature = step_data.get("before_signature") or ui_elements_signature(before_ui)
    after_signature = step_data.get("after_signature")
    if after_signature is None and after_ui:
        after_signature = ui_elements_signature(after_ui)

    before_pixels = step_data.get("before_screenshot_with_som")
    if isinstance(before_pixels, np.ndarray):
        _save_screenshot(screenshot_before, before_pixels)

    after_pixels = step_data.get("after_screenshot_with_som")
    if isinstance(after_pixels, np.ndarray):
        _save_screenshot(screenshot_after, after_pixels)

    ui_elements_dir.mkdir(parents=True, exist_ok=True)
    ui_elements_path.write_text(
        json.dumps(
            {
                "before_signature": before_signature,
                "before": [_ui_element_to_dict(el) for el in before_ui],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if after_ui:
        ui_elements_after_path.write_text(
            json.dumps(
                {
                    "after_signature": after_signature,
                    "after": [_ui_element_to_dict(el) for el in after_ui],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    action = _action_to_dict(step_data.get("action_output_json"))
    compact = {
        "step": step_index,
        "action": action,
        "action_reason": step_data.get("action_reason"),
        "action_output": step_data.get("action_output"),
        "summary": step_data.get("summary"),
        "before_signature": before_signature,
        "after_signature": after_signature,
        "ui_changed": step_data.get("ui_changed"),
        "summary_skipped": step_data.get("summary_skipped", False),
        "screenshot_before": str(screenshot_before.relative_to(output_dir))
        if screenshot_before.exists()
        else None,
        "screenshot_after": str(screenshot_after.relative_to(output_dir))
        if screenshot_after.exists()
        else None,
        "ui_elements_before": str(ui_elements_path.relative_to(output_dir)),
        "ui_elements_after": str(ui_elements_after_path.relative_to(output_dir))
        if after_ui
        else None,
    }

    steps_dir.mkdir(parents=True, exist_ok=True)
    step_record_path.write_text(json.dumps(compact, indent=2, ensure_ascii=False), encoding="utf-8")
    return compact


class M3aAndroidAgent:
    """Webwright agent that runs one M3A step per ``run`` loop iteration."""

    def __init__(self, model: Model, env: Environment, **kwargs):
        if not isinstance(env, LocalAndroidM3aEnvironment):
            raise TypeError("M3aAndroidAgent requires LocalAndroidM3aEnvironment.")
        self.model = model
        self.env = env
        self.config = M3aAndroidAgentConfig(**kwargs)
        self._m3a: m3a_module.M3A | None = None

    def _ensure_m3a(self) -> m3a_module.M3A:
        if self._m3a is None:
            self._m3a = m3a_module.M3A(
                self.env.async_env,
                WebwrightMultimodalLlmWrapper(
                    self.model,
                    vision_image_max_bytes=self.config.vision_image_max_bytes,
                    vision_image_max_long_edge=self.config.vision_image_max_long_edge,
                ),
                wait_after_action_seconds=self.config.wait_after_action_seconds,
                max_history_steps=self.config.max_history_steps,
                action_image_mode=self.config.action_image_mode,
            )
            if self.config.transition_pause is not None:
                self._m3a.transition_pause = self.config.transition_pause
        return self._m3a

    def run(self, task: str, **kwargs) -> dict[str, Any]:
        del kwargs
        m3a = self._ensure_m3a()
        m3a.reset(go_home_on_reset=self.config.go_home_on_reset)
        output_dir = _run_output_dir(self.config.output_path)

        steps: list[dict[str, Any]] = []
        done = False
        final_response = ""
        exit_status = "step_limit"
        stuck_steps = 0
        summary_skipped_count = 0
        previous_action: json_action.JSONAction | None = None
        try:
            for step_index in range(1, self.config.step_limit + 1):
                result: AgentInteractionResult = m3a.step(task)
                step_data = result.data
                if step_data.get("summary_skipped"):
                    summary_skipped_count += 1
                if output_dir is not None:
                    steps.append(_persist_step_artifacts(step_index, step_data, output_dir))
                else:
                    steps.append(
                        {
                            "step": step_index,
                            "action": _action_to_dict(step_data.get("action_output_json")),
                            "summary": step_data.get("summary"),
                            "ui_changed": step_data.get("ui_changed"),
                            "summary_skipped": step_data.get("summary_skipped", False),
                        }
                    )
                done = result.done
                action_json = step_data.get("action_output_json")
                if action_json is not None and getattr(action_json, "action_type", None) == "answer":
                    final_response = getattr(action_json, "text", "") or final_response

                if isinstance(action_json, json_action.JSONAction):
                    if step_data.get("ui_changed") is True:
                        stuck_steps = 0
                    elif transition_guard.should_count_stuck_step(
                        action_json,
                        ui_changed=bool(step_data.get("ui_changed")),
                        previous_action=previous_action,
                    ):
                        stuck_steps += 1
                    previous_action = action_json

                if (
                    self.config.max_stuck_steps > 0
                    and stuck_steps >= self.config.max_stuck_steps
                ):
                    exit_status = "stuck"
                    break

                if done:
                    exit_status = "done"
                    break
        except ModelBillingError:
            exit_status = "billing_error"
            done = False

        payload = {
            "task": task,
            "done": done,
            "steps": steps,
            "final_response": final_response,
            "submission": final_response,
            "exit_status": exit_status,
            "summary_skipped_count": summary_skipped_count,
        }
        if self.config.output_path is not None:
            self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.output_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        return payload

    def save(self, path: Path | None, *extra_dicts) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "agent": self.config.model_dump(mode="json"),
            "history": (self._m3a.history if self._m3a is not None else []),
        }
        for extra in extra_dicts:
            if isinstance(extra, dict):
                merged.update(extra)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(merged, indent=2, default=str), encoding="utf-8")
        return merged
