from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from webwright.utils.ui_signature import ui_elements_signature

_BBOX_RE = re.compile(
    r"BoundingBox\(x_min=([^,]+), x_max=([^,]+), y_min=([^,]+), y_max=([^)]+)\)"
)


@dataclass(frozen=True)
class BoundingBox:
    x_min: int
    x_max: int
    y_min: int
    y_max: int

    @property
    def center(self) -> tuple[int, int]:
        return (
            int((self.x_min + self.x_max) / 2),
            int((self.y_min + self.y_max) / 2),
        )


@dataclass(frozen=True)
class ForwarderUIElement:
    index: int
    class_name: str | None = None
    text: str | None = None
    content_description: str | None = None
    package_name: str | None = None
    resource_name: str | None = None
    bbox_pixels: BoundingBox | None = None
    is_clickable: bool = False
    is_visible: bool = True
    is_checked: bool | None = None
    is_checkable: bool | None = None
    is_selected: bool | None = None
    is_scrollable: bool | None = None


def parse_bounding_box(value: Any) -> BoundingBox | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return BoundingBox(
            x_min=int(value["x_min"]),
            x_max=int(value["x_max"]),
            y_min=int(value["y_min"]),
            y_max=int(value["y_max"]),
        )
    if isinstance(value, BoundingBox):
        return value
    text = str(value)
    match = _BBOX_RE.search(text)
    if not match:
        return None
    return BoundingBox(
        x_min=int(float(match.group(1))),
        x_max=int(float(match.group(2))),
        y_min=int(float(match.group(3))),
        y_max=int(float(match.group(4))),
    )


def parse_ui_element(row: dict[str, Any], *, index: int) -> ForwarderUIElement:
    return ForwarderUIElement(
        index=index,
        class_name=row.get("class_name"),
        text=row.get("text"),
        content_description=row.get("content_description"),
        package_name=row.get("package_name"),
        resource_name=row.get("resource_name"),
        bbox_pixels=parse_bounding_box(row.get("bbox_pixels")),
        is_clickable=bool(row.get("is_clickable")),
        is_visible=bool(row.get("is_visible", True)),
        is_checked=_optional_bool(row.get("is_checked")),
        is_checkable=_optional_bool(row.get("is_checkable")),
        is_selected=_optional_bool(row.get("is_selected")),
        is_scrollable=_optional_bool(row.get("is_scrollable")),
    )


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


class A11yForwarderClient:
    """Read UI trees from ``tools/a11y/grpc_receiver.py`` HTTP facade."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765", *, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def fetch_health(self) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.get(urljoin(self.base_url + "/", "health"))
            response.raise_for_status()
            return response.json()

    def fetch_ui_elements(self) -> list[ForwarderUIElement]:
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.get(urljoin(self.base_url + "/", "ui-elements"))
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(f"Expected JSON array from /ui-elements, got {type(payload)!r}")
        return [parse_ui_element(row, index=i) for i, row in enumerate(payload)]


def pick_click_target(elements: list[ForwarderUIElement]) -> ForwarderUIElement | None:
    """Pick the first clickable element with a bounding box."""
    for element in elements:
        if element.is_clickable and element.bbox_pixels is not None:
            return element
    for element in elements:
        if element.bbox_pixels is not None:
            return element
    return None


def elements_to_json(elements: list[ForwarderUIElement]) -> str:
    rows = []
    for element in elements:
        row: dict[str, Any] = {
            "index": element.index,
            "class_name": element.class_name,
            "text": element.text,
            "content_description": element.content_description,
            "package_name": element.package_name,
            "resource_name": element.resource_name,
            "is_clickable": element.is_clickable,
            "is_visible": element.is_visible,
        }
        if element.bbox_pixels is not None:
            row["bbox_pixels"] = {
                "x_min": element.bbox_pixels.x_min,
                "x_max": element.bbox_pixels.x_max,
                "y_min": element.bbox_pixels.y_min,
                "y_max": element.bbox_pixels.y_max,
            }
        rows.append(row)
    return json.dumps(rows, indent=2, ensure_ascii=False)


def to_representation_ui_elements(
    elements: list[ForwarderUIElement],
):
    """Convert forwarder elements to AndroidWorld ``UIElement`` objects."""
    from android_world.env import representation_utils

    out = []
    for element in elements:
        bbox = None
        if element.bbox_pixels is not None:
            bbox = representation_utils.BoundingBox(
                element.bbox_pixels.x_min,
                element.bbox_pixels.x_max,
                element.bbox_pixels.y_min,
                element.bbox_pixels.y_max,
            )
        out.append(
            representation_utils.UIElement(
                text=element.text,
                content_description=element.content_description,
                class_name=element.class_name,
                bbox_pixels=bbox,
                is_clickable=element.is_clickable,
                is_visible=element.is_visible,
                is_checked=element.is_checked,
                is_checkable=element.is_checkable,
                is_selected=element.is_selected,
                is_scrollable=element.is_scrollable,
                package_name=element.package_name,
                resource_name=element.resource_name,
            )
        )
    return out
