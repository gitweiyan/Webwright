from webwright.devices.snapshots import compact_android_hierarchy


def test_compact_android_hierarchy_keeps_semantic_nodes():
    xml = """
    <hierarchy rotation="0">
      <node index="0" text="" class="android.widget.FrameLayout" bounds="[0,0][1080,2400]">
        <node index="1" text="Phone" resource-id="com.demo:id/phone" class="android.widget.EditText" clickable="true" enabled="true" bounds="[72,620][1008,720]" />
        <node index="2" text="Login" content-desc="submit login" resource-id="com.demo:id/login" class="android.widget.Button" clickable="true" enabled="true" bounds="[72,800][1008,900]" />
      </node>
    </hierarchy>
    """

    snapshot = compact_android_hierarchy(xml)

    assert "EditText" in snapshot
    assert 'text="Phone"' in snapshot
    assert 'id="com.demo:id/login"' in snapshot
    assert "center=(540,850)" in snapshot


def test_compact_android_hierarchy_handles_invalid_xml():
    snapshot = compact_android_hierarchy("<hierarchy>")

    assert "Could not parse" in snapshot
