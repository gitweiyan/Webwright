from webwright.devices.a11y_forwarder_client import (
    parse_bounding_box,
    parse_ui_element,
    pick_click_target,
    ui_elements_signature,
)


def test_parse_bounding_box_from_string():
    bbox = parse_bounding_box("BoundingBox(x_min=0, x_max=126, y_min=132, y_max=279)")
    assert bbox is not None
    assert bbox.center == (63, 205)


def test_parse_ui_element_and_signature():
    element = parse_ui_element(
        {
            "class_name": "android.widget.Button",
            "text": "OK",
            "resource_name": "com.demo:id/ok",
            "bbox_pixels": "BoundingBox(x_min=10, x_max=110, y_min=20, y_max=120)",
            "is_clickable": True,
            "is_visible": True,
        },
        index=0,
    )
    assert element.bbox_pixels is not None
    assert pick_click_target([element]) is element
    sig = ui_elements_signature([element])
    assert len(sig) == 16


def test_pick_click_target_prefers_clickable():
    clickable = parse_ui_element(
        {
            "class_name": "android.widget.Button",
            "bbox_pixels": "BoundingBox(x_min=1, x_max=2, y_min=3, y_max=4)",
            "is_clickable": True,
        },
        index=0,
    )
    plain = parse_ui_element(
        {
            "class_name": "android.widget.TextView",
            "bbox_pixels": "BoundingBox(x_min=5, x_max=6, y_min=7, y_max=8)",
            "is_clickable": False,
        },
        index=1,
    )
    assert pick_click_target([plain, clickable]) is clickable
