from pathlib import Path

from webwright.devices.semantic_summary import semantic_android_summary
from webwright.devices.snapshots import compact_android_hierarchy


MESSAGES_RECIPIENT_XML = """
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" package="com.google.android.apps.messaging" bounds="[0,0][1080,2400]">
    <node text="To" class="android.widget.TextView" package="com.google.android.apps.messaging" bounds="[0,300][189,426]" />
    <node text="Type a name, phone number, or email" resource-id="com.google.android.apps.messaging:id/recipient_text_view" class="android.widget.MultiAutoCompleteTextView" package="com.google.android.apps.messaging" clickable="true" enabled="true" bounds="[189,300][954,426]" />
    <node text="New conversation" class="android.widget.TextView" package="com.google.android.apps.messaging" bounds="[157,180][617,252]" />
    <node text="Create group" class="android.widget.TextView" package="com.google.android.apps.messaging" clickable="true" enabled="true" bounds="[189,496][507,571]" />
    <node text="Ava Lewis" resource-id="com.google.android.apps.messaging:id/contact_name" class="android.widget.TextView" package="com.google.android.apps.messaging" bounds="[189,751][1038,826]" />
    <node class="android.view.ViewGroup" package="com.google.android.apps.messaging" clickable="true" enabled="true" bounds="[0,725][1080,922]" />
  </node>
</hierarchy>
"""


SETTINGS_SLIDER_XML = """
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,2400]">
    <node text="Display size and text" class="android.widget.TextView" package="com.android.settings" bounds="[157,180][700,252]" />
    <node text="Font size" class="android.widget.TextView" package="com.android.settings" bounds="[42,400][300,500]" />
    <node class="android.widget.SeekBar" package="com.android.settings" clickable="true" enabled="true" bounds="[300,420][1000,480]" />
    <node text="Display size" class="android.widget.TextView" package="com.android.settings" bounds="[42,520][300,620]" />
    <node class="android.widget.SeekBar" package="com.android.settings" clickable="true" enabled="true" bounds="[300,540][1000,600]" />
    <node text="Bold text" class="android.widget.TextView" package="com.android.settings" bounds="[42,640][300,740]" />
    <node text="Bold text" class="android.widget.Switch" package="com.android.settings" checked="false" clickable="true" enabled="true" bounds="[800,650][980,730]" />
    <node text="Dark theme" class="android.widget.TextView" package="com.android.settings" bounds="[42,760][300,860]" />
    <node text="Dark theme" class="android.widget.Switch" package="com.android.settings" checked="true" clickable="true" enabled="true" bounds="[800,770][980,850]" />
  </node>
</hierarchy>
"""


def test_semantic_summary_messages_recipient_page():
    summary = semantic_android_summary(MESSAGES_RECIPIENT_XML)

    assert "compose_recipient" in summary
    assert "recipient_text_view" in summary
    assert "set_selector_text" in summary
    assert 'label="To"' in summary
    assert "Ava Lewis" in summary
    assert len(summary) < 2000


def test_semantic_summary_settings_page_has_sliders_and_switches():
    summary = semantic_android_summary(SETTINGS_SLIDER_XML)

    assert "settings" in summary
    assert "slider" in summary
    assert "switch" in summary
    assert "Display size" in summary
    assert "driver.swipe" in summary


def test_semantic_summary_is_shorter_than_compact_hierarchy():
    xml_path = Path(
        "outputs/default/CheckConferenceAndSendSmsTask1_20260616_150935/hierarchy/step_0020.xml"
    )
    if not xml_path.exists():
        return

    xml = xml_path.read_text(encoding="utf-8")
    summary = semantic_android_summary(xml)
    compact = compact_android_hierarchy(xml)

    assert summary
    assert len(summary) < len(compact)


def test_semantic_summary_handles_invalid_xml():
    assert semantic_android_summary("") == ""
    assert semantic_android_summary("<hierarchy>") == ""


EVENT_DETAIL_XML = """
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" package="com.android.systemui" bounds="[0,0][1080,132]">
    <node text="10:33" class="android.widget.TextView" package="com.android.systemui" bounds="[42,1][183,132]" />
  </node>
  <node class="android.widget.FrameLayout" package="org.fossify.calendar" bounds="[0,0][1080,2400]">
    <node content-desc="Back" class="android.widget.ImageButton" package="org.fossify.calendar" clickable="true" enabled="true" bounds="[0,142][147,289]" />
    <node text="Edit Event" class="android.widget.TextView" package="org.fossify.calendar" bounds="[157,173][438,259]" />
    <node text="Conference in Paris" resource-id="org.fossify.calendar:id/event_title" class="android.widget.EditText" package="org.fossify.calendar" clickable="true" bounds="[42,342][1038,471]" />
    <node text="October 11 2025 (Sat)" resource-id="org.fossify.calendar:id/event_start_date" class="android.widget.TextView" package="org.fossify.calendar" clickable="true" bounds="[159,1057][743,1215]" />
    <node text="October 15 2025 (Wed)" resource-id="org.fossify.calendar:id/event_end_date" class="android.widget.TextView" package="org.fossify.calendar" clickable="true" bounds="[159,1215][771,1373]" />
  </node>
</hierarchy>
"""


CALENDAR_MONTH_XML = """
<hierarchy rotation="0">
  <node class="android.widget.FrameLayout" package="com.android.systemui" bounds="[0,0][1080,132]">
    <node text="10:29" class="android.widget.TextView" package="com.android.systemui" bounds="[42,1][183,132]" />
  </node>
  <node class="android.widget.FrameLayout" package="org.fossify.calendar" bounds="[0,132][1080,2337]">
    <node text="Search" content-desc="Search" resource-id="org.fossify.calendar:id/top_toolbar_search_icon" class="android.widget.ImageView" package="org.fossify.calendar" clickable="true" bounds="[42,153][147,279]" />
    <node text="Search" resource-id="org.fossify.calendar:id/top_toolbar_search" class="android.widget.EditText" package="org.fossify.calendar" clickable="true" bounds="[147,153][626,279]" />
    <node text="June" resource-id="org.fossify.calendar:id/top_value" class="android.widget.TextView" package="org.fossify.calendar" clickable="true" bounds="[147,300][933,452]" />
    <node content-desc="15 June" resource-id="org.fossify.calendar:id/month_view_background" class="android.view.View" package="org.fossify.calendar" clickable="true" bounds="[154,1145][308,1442]" />
    <node text="15 June" class="android.widget.TextView" package="org.fossify.calendar" clickable="true" bounds="[154,1145][308,1442]" />
  </node>
</hierarchy>
"""


def test_semantic_summary_event_back_uses_click_desc():
    summary = semantic_android_summary(EVENT_DETAIL_XML)

    assert "event_detail" in summary
    assert 'driver.click_desc("Back")' in summary
    assert 'driver.click_text("Back")' not in summary
    assert "[c" in summary and "info" in summary
    assert "event_start_date" in summary
    assert 'driver.click_text("October 11 2025 (Sat)")' not in summary


def test_semantic_summary_calendar_search_ignores_status_bar_and_grid_days():
    summary = semantic_android_summary(CALENDAR_MONTH_XML)

    assert 'label="Search"' in summary
    assert 'label="10:29"' not in summary
    assert "15 June" not in summary
    assert "month_view_background" not in summary
