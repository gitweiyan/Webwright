from __future__ import annotations

import pytest

from webwright.devices.android_uiautomator2 import normalize_xpath_position

lxml_etree = pytest.importorskip("lxml.etree")


def test_normalize_makes_trailing_index_select_nth_match():
    xml = """
    <hierarchy>
      <node class="LinearLayout">
        <node class="FrameLayout" resource-id="com.demo:id/icon_start_frame" content-desc="Make smaller"/>
        <node class="SeekBar" content-desc="Font size"/>
      </node>
      <node class="LinearLayout">
        <node class="FrameLayout" resource-id="com.demo:id/icon_start_frame" content-desc="Make smaller"/>
        <node class="SeekBar" content-desc="Display size"/>
      </node>
    </hierarchy>
    """
    root = lxml_etree.fromstring(xml)
    for node in root.xpath("//node"):
        node.tag = node.attrib.pop("class", "") or "node"

    selector = (
        '//*[@resource-id="com.demo:id/icon_start_frame" and @content-desc="Make smaller"]'
    )
    broken = f"{selector}[2]"
    fixed = normalize_xpath_position(broken)

    assert len(root.xpath(selector)) == 2
    assert len(root.xpath(broken)) == 0
    assert len(root.xpath(fixed)) == 1
