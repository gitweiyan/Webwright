from __future__ import annotations

import hashlib
import re
from typing import Protocol

_SYSTEM_PACKAGES = frozenset({"com.android.systemui", "android"})
_STATUS_BAR_MAX_Y = 132
_VOLATILE_RESOURCE_SUFFIXES = frozenset(
    {
        "clock",
        "wifi_signal",
        "mobile_combo",
        "battery",
    }
)
_TIME_TEXT_RE = re.compile(r"\d{1,2}:\d{2}")


class _SignatureElement(Protocol):
    text: str | None
    content_description: str | None
    package_name: str | None
    resource_name: str | None
    is_clickable: bool

    @property
    def bbox_pixels(self) -> object | None: ...


def short_resource_id(resource_name: str | None) -> str:
    if not resource_name:
        return ""
    tail = resource_name.rsplit("/", 1)[-1]
    return tail.rsplit(":", 1)[-1]


def normalize_signature_text(value: str | None) -> str:
    if not value:
        return ""
    return _TIME_TEXT_RE.sub("<T>", " ".join(value.split()))


def should_exclude_from_signature(
    *,
    package_name: str | None,
    resource_name: str | None,
    bbox_y_max: int | None,
) -> bool:
    package = package_name or ""
    if package in _SYSTEM_PACKAGES:
        return True
    if short_resource_id(resource_name) in _VOLATILE_RESOURCE_SUFFIXES:
        return True
    if bbox_y_max is not None and bbox_y_max <= _STATUS_BAR_MAX_Y and package in _SYSTEM_PACKAGES:
        return True
    return False


def signature_key_for_element(element: _SignatureElement) -> str | None:
    bbox = element.bbox_pixels
    bbox_y_max = getattr(bbox, "y_max", None) if bbox is not None else None
    if should_exclude_from_signature(
        package_name=element.package_name,
        resource_name=element.resource_name,
        bbox_y_max=bbox_y_max,
    ):
        return None

    bbox_text = ""
    if bbox is not None:
        bbox_text = (
            f"{int(bbox.x_min)},{int(bbox.y_min)},{int(bbox.x_max)},{int(bbox.y_max)}"
        )

    return "|".join(
        [
            element.package_name or "",
            element.resource_name or "",
            normalize_signature_text(element.text),
            normalize_signature_text(element.content_description),
            bbox_text,
            str(element.is_clickable),
        ]
    )


def ui_elements_signature(elements: list[_SignatureElement]) -> str:
    """Stable signature for screen-change detection with system-ui noise filtered."""
    parts: list[str] = []
    for element in elements:
        key = signature_key_for_element(element)
        if key is not None:
            parts.append(key)
    normalized = "\n".join(parts)
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
