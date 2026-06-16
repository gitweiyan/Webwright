from __future__ import annotations

from webwright.devices.android_uiautomator2 import (
    AndroidUiautomator2Driver,
    normalize_xpath_position,
)


class FakeUiObject:
    def __init__(self):
        self.exists = True
        self.info = {"checked": True}
        self.calls = []

    def click(self, timeout=None):
        self.calls.append(("click", timeout))

    def click_exists(self, timeout=None):
        self.calls.append(("click_exists", timeout))
        return True

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        return True

    def wait_gone(self, timeout=None):
        self.calls.append(("wait_gone", timeout))
        return True

    def set_text(self, text):
        self.calls.append(("set_text", text))

    def clear_text(self):
        self.calls.append(("clear_text",))


class FakeScroll:
    def __init__(self):
        self.calls = []

    def to(self, **kwargs):
        self.calls.append(kwargs)
        return True


class FakeScrollableObject(FakeUiObject):
    def __init__(self):
        super().__init__()
        self.scroll = FakeScroll()


class FakeXpath:
    def __init__(self):
        self.calls = []
        self.exists = False

    def click(self, timeout=None):
        self.calls.append(("click", timeout))


class FakeDevice:
    def __init__(self):
        self.objects = []
        self.xpath_objects = []
        self.fastinput = None
        self.pressed = []

    def __call__(self, **kwargs):
        obj = FakeScrollableObject() if kwargs.get("scrollable") else FakeUiObject()
        obj.kwargs = kwargs
        self.objects.append(obj)
        return obj

    def xpath(self, expression):
        obj = FakeXpath()
        obj.expression = expression
        self.xpath_objects.append(obj)
        return obj

    def window_size(self):
        return 1080, 2400

    def set_fastinput_ime(self, enabled):
        self.fastinput = enabled

    def press(self, key):
        self.pressed.append(key)


def test_android_driver_selector_helpers_call_uiautomator_shapes():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    assert driver.exists_text("Wi-Fi") is True
    assert raw.objects[-1].kwargs == {"text": "Wi-Fi"}

    driver.click_text_contains("Wi", timeout=3)
    assert raw.objects[-1].kwargs == {"textContains": "Wi"}
    assert raw.objects[-1].calls == [("click", 3)]

    driver.set_selector_text("hello", resourceId="com.demo:id/input")
    assert raw.objects[-1].kwargs == {"resourceId": "com.demo:id/input"}
    assert raw.objects[-1].calls == [("wait", 5.0), ("clear_text",), ("set_text", "hello")]

    assert driver.scroll_to_text("System") is True
    assert raw.objects[-1].kwargs == {"scrollable": True}
    assert raw.objects[-1].scroll.calls == [{"text": "System", "max_swipes": 20}]

    driver.click_xpath('//*[@text="Wi-Fi"]', timeout=7)
    assert raw.xpath_objects[-1].expression == '//*[@text="Wi-Fi"]'
    assert raw.xpath_objects[-1].calls == [("click", 7)]

    assert driver.window_size() == (1080, 2400)


def test_normalize_xpath_position_wraps_document_order_index():
    expr = '//*[@resource-id="com.example:id/action" and @content-desc="Remove"][2]'
    assert normalize_xpath_position(expr) == (
        '(//*[@resource-id="com.example:id/action" and @content-desc="Remove"])[2]'
    )


def test_normalize_xpath_position_leaves_step_local_index_unchanged():
    assert normalize_xpath_position('//LinearLayout[1]/Button[2]') == '//LinearLayout[1]/Button[2]'


def test_normalize_xpath_position_leaves_already_grouped_unchanged():
    expr = '(//*[@content-desc="Remove"])[2]'
    assert normalize_xpath_position(expr) == expr


def test_android_driver_click_xpath_rewrites_trailing_document_index():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    driver.click_xpath('//*[@content-desc="Remove"][2]')
    assert raw.xpath_objects[-1].expression == '(//*[@content-desc="Remove"])[2]'


def test_android_driver_submit_input_prefers_visible_submit_label():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    assert driver.submit_input() is True
    assert raw.objects[-1].kwargs == {"text": "搜索"}
    assert raw.objects[-1].calls == [("click_exists", 3)]


def test_android_driver_click_if_text():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    assert driver.click_if_text("重新再试", timeout=2) is True
    assert raw.objects[-1].kwargs == {"text": "重新再试"}
    assert raw.objects[-1].calls == [("click_exists", 2)]


def test_android_driver_click_search_bar_prefers_resource_id():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    driver.click_search_bar(resource_id="com.sohu.sohuvideo:id/rcSearchContainer")
    assert raw.objects[-1].kwargs == {"resourceId": "com.sohu.sohuvideo:id/rcSearchContainer"}
    assert raw.objects[-1].calls == [("click", 5.0)]


def test_android_driver_click_search_bar_xpath_fallback():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    def xpath(expression):
        obj = FakeXpath()
        obj.expression = expression
        obj.exists = expression.startswith('//*[contains(@resource-id, "Search")')
        raw.xpath_objects.append(obj)
        return obj

    raw.xpath = xpath

    driver.click_search_bar()
    assert raw.xpath_objects[0].expression == '//*[contains(@resource-id, "Search") and @clickable="true"]'
    assert raw.xpath_objects[0].calls == [("click", 5.0)]


def test_android_driver_keyboard_helpers():
    raw = FakeDevice()
    driver = AndroidUiautomator2Driver()
    driver.raw = raw

    driver.set_fastinput_ime(True)
    assert raw.fastinput is True

    driver.hide_keyboard()
    assert raw.fastinput is False
    assert raw.pressed == ["back"]
