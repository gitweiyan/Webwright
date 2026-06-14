from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_LAYOUT_CLASS_HINTS = (
    "Layout",
    "ViewGroup",
    "RecyclerView",
    "ScrollView",
    "ListView",
)
_SEMANTIC_ATTRS = ("text", "content-desc", "resource-id")


@dataclass
class AndroidNodeSummary:
    depth: int
    class_name: str
    text: str
    content_desc: str
    resource_id: str
    clickable: bool
    enabled: bool
    checked: bool
    selected: bool
    bounds: str

    @property
    def has_semantics(self) -> bool:
        return bool(self.text or self.content_desc or self.resource_id)

    @property
    def is_interesting(self) -> bool:
        return self.has_semantics or self.clickable or self.checked or self.selected


def _bool_attr(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _shorten(value: str, limit: int = 80) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _class_short_name(class_name: str) -> str:
    return (class_name or "").rsplit(".", 1)[-1] or "Node"


def _bounds_center(bounds: str) -> tuple[int, int] | None:
    match = _BOUNDS_RE.fullmatch(bounds or "")
    if match is None:
        return None
    x1, y1, x2, y2 = [int(part) for part in match.groups()]
    return (x1 + x2) // 2, (y1 + y2) // 2


def _bounds_area(bounds: str) -> int:
    match = _BOUNDS_RE.fullmatch(bounds or "")
    if match is None:
        return 0
    x1, y1, x2, y2 = [int(part) for part in match.groups()]
    return max(0, x2 - x1) * max(0, y2 - y1)


# System/overlay packages that draw on top of every screen (status bar, nav bar,
# input method). They are never the "foreground app" the agent is interacting with.
_NON_FOREGROUND_PACKAGES = frozenset(
    {
        "com.android.systemui",
        "android",
    }
)


def foreground_package_from_hierarchy(xml: str) -> str:
    """Best-effort foreground app package derived from the dumped UI hierarchy.

    ``uiautomator2``'s ``app_current()`` (``dumpsys`` based) is known to return
    stale or wrong packages when sounds preview, transient windows appear, or other
    apps linger in recents. The dumped hierarchy, by contrast, only contains the
    windows that are actually on screen, so the package owning the largest visible
    region is a far more reliable signal — and, crucially, it is the SAME source the
    model reads as ``ui_snapshot``, keeping the two consistent.

    Returns an empty string when no usable package can be determined.
    """

    if not xml or not xml.strip():
        return ""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return ""

    best_package = ""
    best_area = 0
    for element, _depth in _walk(root):
        if element is root:
            continue
        package = (element.attrib.get("package") or "").strip()
        if not package or package in _NON_FOREGROUND_PACKAGES:
            continue
        area = _bounds_area(element.attrib.get("bounds", ""))
        if area > best_area:
            best_area = area
            best_package = package
    return best_package


def _summarize_element(element: ElementTree.Element, depth: int) -> AndroidNodeSummary:
    attrs = element.attrib
    return AndroidNodeSummary(
        depth=depth,
        class_name=_class_short_name(attrs.get("class", "")),
        text=_shorten(attrs.get("text", "")),
        content_desc=_shorten(attrs.get("content-desc", "")),
        resource_id=_shorten(attrs.get("resource-id", "")),
        clickable=_bool_attr(attrs.get("clickable")),
        enabled=_bool_attr(attrs.get("enabled")),
        checked=_bool_attr(attrs.get("checked")),
        selected=_bool_attr(attrs.get("selected")),
        bounds=attrs.get("bounds", ""),
    )


def _walk(element: ElementTree.Element, depth: int = 0):
    yield element, depth
    for child in list(element):
        yield from _walk(child, depth + 1)


def _line_for_node(node: AndroidNodeSummary) -> str:
    parts = [node.class_name]
    if node.text:
        parts.append(f'text="{node.text}"')
    if node.content_desc:
        parts.append(f'desc="{node.content_desc}"')
    if node.resource_id:
        parts.append(f'id="{node.resource_id}"')
    if node.clickable:
        parts.append("clickable=true")
    if node.checked:
        parts.append("checked=true")
    if node.selected:
        parts.append("selected=true")
    if not node.enabled:
        parts.append("enabled=false")
    if node.bounds:
        parts.append(f"bounds={node.bounds}")
        center = _bounds_center(node.bounds)
        if center is not None:
            parts.append(f"center=({center[0]},{center[1]})")
    return f"{'  ' * max(node.depth - 1, 0)}- " + " ".join(parts)


def _looks_like_layout(node: AndroidNodeSummary) -> bool:
    return any(hint in node.class_name for hint in _LAYOUT_CLASS_HINTS)


def compact_android_hierarchy(
    xml: str,
    *,
    max_chars: int = 20000,
    max_nodes: int = 160,
) -> str:
    """Turn uiautomator XML into a compact, model-readable accessibility tree."""

    if not xml.strip():
        return ""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        return f"(Could not parse Android hierarchy XML: {exc})"

    lines: list[str] = []
    package = root.attrib.get("package", "")
    bounds = root.attrib.get("bounds", "")
    header = "Android UI hierarchy"
    if package:
        header += f" package={package}"
    if bounds:
        header += f" bounds={bounds}"
    lines.append(header)

    emitted = 0
    for element, depth in _walk(root):
        if element is root:
            continue
        node = _summarize_element(element, depth)
        if not node.is_interesting:
            continue
        if _looks_like_layout(node) and not node.has_semantics and not node.clickable:
            continue
        lines.append(_line_for_node(node))
        emitted += 1
        if emitted >= max_nodes:
            lines.append(f"... [{emitted}+ nodes shown; remaining nodes omitted]")
            break

    output = "\n".join(lines)
    if len(output) <= max_chars:
        return output
    omitted = len(output) - max_chars
    return f"{output[:max_chars]}\n... [{omitted} characters omitted]"
