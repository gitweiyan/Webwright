#!/usr/bin/env python3
"""Run M3A benchmark scenarios with setup/teardown and print metrics."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
ANDROID_WORLD_ROOT = REPO_ROOT.parent

from webwright.utils.device_reset import clear_app_data, go_home  # noqa: E402

SCENARIOS = {
    "alarm": {
        "task": (
            'Set a weekend alarm for 8:25 a.m. with the ringtone "beebeep" '
            "and vibration off."
        ),
        "setup": lambda serial: (
            clear_app_data("com.google.android.deskclock", device_serial=serial),
            go_home(device_serial=serial),
        ),
        "teardown": lambda serial: (
            clear_app_data("com.google.android.deskclock", device_serial=serial),
            go_home(device_serial=serial),
        ),
    },
    "open_settings": {
        "task": "Open Settings",
        "setup": lambda serial: go_home(device_serial=serial),
        "teardown": lambda serial: go_home(device_serial=serial),
    },
}


def _latest_run_dir(output_root: Path, task_id: str) -> Path | None:
    candidates = sorted(output_root.glob(f"{task_id}_*"))
    return candidates[-1] if candidates else None


def _analyze_run(run_dir: Path) -> dict:
    trajectory_path = run_dir / "trajectory.json"
    raw_path = run_dir / "raw_responses.jsonl"
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    llm_calls = 0
    if raw_path.exists():
        llm_calls = sum(1 for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip())
    fact_steps = sum(
        1
        for step in trajectory.get("steps", [])
        if "FACT:" in str(step.get("summary", ""))
    )
    skipped = trajectory.get("summary_skipped_count")
    if skipped is None:
        skipped = sum(1 for step in trajectory.get("steps", []) if step.get("summary_skipped"))
    return {
        "run_dir": str(run_dir),
        "done": trajectory.get("done"),
        "exit_status": trajectory.get("exit_status"),
        "steps": len(trajectory.get("steps", [])),
        "summary_skipped_count": skipped,
        "fact_steps": fact_steps,
        "llm_calls": llm_calls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--device", default="emulator-5554")
    parser.add_argument("--step-limit", type=int, default=25)
    parser.add_argument("--output-root", default="outputs/m3a_benchmark")
    parser.add_argument("--skip-run", action="store_true", help="Only analyze latest run dir")
    args = parser.parse_args()

    scenario = SCENARIOS[args.scenario]
    task_id = f"bench_{args.scenario}"

    if not args.skip_run:
        scenario["setup"](args.device)
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{SRC_ROOT}:{ANDROID_WORLD_ROOT}"
        cmd = [
            sys.executable,
            "-m",
            "webwright.run.cli",
            "-c",
            "base.yaml",
            "-c",
            "local_android_m3a.yaml",
            "-c",
            "model_qwen_vision.yaml",
            "-c",
            f"environment.device_serial={args.device}",
            "-c",
            f"agent.step_limit={args.step_limit}",
            "-t",
            scenario["task"],
            "--task-id",
            task_id,
            "-o",
            args.output_root,
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=False)
        scenario["teardown"](args.device)
        if result.returncode != 0:
            print(f"FAIL: CLI exited with code {result.returncode}")
            return result.returncode

    run_dir = _latest_run_dir(REPO_ROOT / args.output_root, task_id)
    if run_dir is None:
        print("FAIL: no run directory found")
        return 1
    metrics = _analyze_run(run_dir)
    metrics["scenario"] = args.scenario
    metrics["device"] = args.device
    log_path = REPO_ROOT / args.output_root / "results.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    if metrics["exit_status"] == "billing_error":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
