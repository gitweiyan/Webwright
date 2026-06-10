from pathlib import Path

from webwright.environments import get_environment
from webwright.environments import local_mobile


class FakeDriver:
    raw = "raw-device"

    def __init__(self, *, serial=None, connect_url=None):
        self.serial = serial
        self.connect_url = connect_url
        self.connected = False
        self.stopped = []

    def connect(self):
        self.connected = True

    def close(self):
        self.connected = False

    def get_info(self):
        return {"displayWidth": 1080, "displayHeight": 2400}

    def current_app(self):
        return {"package": "com.demo", "activity": ".MainActivity"}

    def launch_app(self, package, activity=None):
        self.launched = (package, activity)

    def stop_app(self, package):
        self.stopped.append(package)

    def screenshot(self, path: Path):
        path.write_bytes(b"fake-png")

    def dump_hierarchy(self):
        return """
        <hierarchy rotation="0">
          <node text="Login" resource-id="com.demo:id/login" class="android.widget.Button" clickable="true" enabled="true" bounds="[10,20][110,120]" />
        </hierarchy>
        """

    def click(self, x, y):
        self.clicked = (x, y)

    def swipe(self, sx, sy, ex, ey, duration=0.2):
        self.swiped = (sx, sy, ex, ey, duration)

    def press(self, key):
        self.pressed = key

    def input_text(self, text):
        self.input = text

    def wait_idle(self, timeout=5.0):
        self.idle_timeout = timeout

    def snapshot_text(self, *, max_chars=20000):
        return "snapshot"


def test_get_environment_resolves_local_android():
    env = get_environment({"environment_class": "local_android"})

    assert env.config.platform == "android"
    assert env.config.backend == "uiautomator2"


def test_local_mobile_environment_executes_python_code(tmp_path, monkeypatch):
    monkeypatch.setitem(local_mobile._DRIVER_MAPPING, ("android", "fake"), FakeDriver)
    env = local_mobile.LocalMobileEnvironment(
        platform="android",
        backend="fake",
        output_dir=tmp_path,
        app_package="com.demo",
    )

    env.prepare(task="tap login")
    result = env.execute({"python_code": "print(device)\ndriver.click(10, 20)"})
    env.close()

    observation = result["observation"]
    assert result["returncode"] == 0
    assert "raw-device" in result["output"]
    assert observation["current_app"]["package"] == "com.demo"
    assert "Login" in observation["ui_snapshot"]
    assert Path(observation["screenshot_path"]).exists()
    assert Path(observation["hierarchy_path"]).exists()


class ActivityTrackingDriver(FakeDriver):
    def __init__(self, *, serial=None, connect_url=None):
        super().__init__(serial=serial, connect_url=connect_url)
        self._activity_calls = 0

    def current_app(self):
        self._activity_calls += 1
        if self._activity_calls == 1:
            return {"package": "com.demo", "activity": ".HomeActivity"}
        return {"package": "com.demo", "activity": ".SearchActivity"}


def test_local_mobile_observation_tracks_activity_change(tmp_path, monkeypatch):
    monkeypatch.setitem(local_mobile._DRIVER_MAPPING, ("android", "fake"), ActivityTrackingDriver)
    env = local_mobile.LocalMobileEnvironment(
        platform="android",
        backend="fake",
        output_dir=tmp_path,
    )

    env.prepare(task="open search")
    result = env.execute({"python_code": "driver.click(10, 20)"})
    env.close()

    observation = result["observation"]
    assert observation["previous_activity"] == ".HomeActivity"
    assert observation["current_app"]["activity"] == ".SearchActivity"
    assert observation["activity_changed"] is True
