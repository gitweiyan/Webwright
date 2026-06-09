from __future__ import annotations

from typer.testing import CliRunner

from webwright.run import cli


def test_root_command_accepts_run_options(monkeypatch):
    captured = {}

    def fake_run_one(**kwargs):
        captured.update(kwargs)
        return {"final_response": "ok"}

    monkeypatch.setattr(cli, "run_one", fake_run_one)
    result = CliRunner().invoke(
        cli.app,
        [
            "-c",
            "base.yaml",
            "-c",
            "local_android.yaml",
            "-t",
            "Open Settings",
            "--task-id",
            "android_settings_wifi",
            "-o",
            "outputs/android",
        ],
    )

    assert result.exit_code == 0
    assert captured["task"] == "Open Settings"
    assert captured["task_id"] == "android_settings_wifi"
    assert captured["config_spec"] == ["base.yaml", "local_android.yaml"]


def test_main_subcommand_still_accepts_run_options(monkeypatch):
    captured = {}

    def fake_run_one(**kwargs):
        captured.update(kwargs)
        return {"final_response": "ok"}

    monkeypatch.setattr(cli, "run_one", fake_run_one)
    result = CliRunner().invoke(
        cli.app,
        ["main", "-c", "base.yaml", "-t", "Open Settings"],
    )

    assert result.exit_code == 0
    assert captured["task"] == "Open Settings"
    assert captured["config_spec"] == ["base.yaml"]
