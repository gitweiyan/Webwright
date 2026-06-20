from webwright.devices.a11y_forwarder_client import BoundingBox, ForwarderUIElement
from webwright.utils.ui_signature import (
    normalize_signature_text,
    should_exclude_from_signature,
    ui_elements_signature,
)


def _clock_element(*, text: str) -> ForwarderUIElement:
    return ForwarderUIElement(
        index=0,
        text=text,
        content_description=f"{text} PM",
        package_name="com.android.systemui",
        resource_name="com.android.systemui:id/clock",
        bbox_pixels=BoundingBox(42, 128, 1, 132),
        is_clickable=False,
    )


def _app_button() -> ForwarderUIElement:
    return ForwarderUIElement(
        index=1,
        text="Clock",
        content_description="Clock",
        package_name="com.google.android.apps.nexuslauncher",
        resource_name=None,
        bbox_pixels=BoundingBox(832, 1004, 1873, 2068),
        is_clickable=True,
    )


def test_signature_ignores_systemui_clock_changes():
    before = [_clock_element(text="9:34"), _app_button()]
    after = [_clock_element(text="9:35"), _app_button()]
    assert ui_elements_signature(before) == ui_elements_signature(after)


def test_signature_changes_when_app_element_changes():
    before = [_app_button()]
    changed = ForwarderUIElement(
        index=1,
        text="Settings",
        content_description="Settings",
        package_name="com.google.android.apps.nexuslauncher",
        resource_name=None,
        bbox_pixels=BoundingBox(832, 1004, 1873, 2068),
        is_clickable=True,
    )
    after = [changed]
    assert ui_elements_signature(before) != ui_elements_signature(after)


def test_normalize_signature_text_replaces_clock_values():
    assert normalize_signature_text("9:34 PM") == "<T> PM"


def test_should_exclude_systemui_package():
    assert should_exclude_from_signature(
        package_name="com.android.systemui",
        resource_name="com.android.systemui:id/clock",
        bbox_y_max=132,
    )
