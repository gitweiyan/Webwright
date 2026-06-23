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


def _latest_run_dir(output_root: Path, task_id: str) -> Path | None:
    candidates = sorted(output_root.glob(f"{task_id}_*"))
    return candidates[-1] if candidates else None


def _aggregate_metrics(runs: list[dict]) -> dict:
    if not runs:
        return {}
    done_count = sum(1 for run in runs if run.get("done"))
    return {
        "repeat": len(runs),
        "success_rate": done_count / len(runs),
        "done_count": done_count,
        "avg_steps": sum(run["steps"] for run in runs) / len(runs),
        "avg_llm_calls": sum(run["llm_calls"] for run in runs) / len(runs),
        "avg_summary_skipped_count": sum(run["summary_skipped_count"] for run in runs) / len(runs),
        "avg_fact_steps": sum(run["fact_steps"] for run in runs) / len(runs),
        "runs": runs,
    }


def _run_scenario(
    *,
    scenario: dict,
    task_id: str,
    device: str,
    step_limit: int,
    output_root: Path,
) -> int:
    scenario["setup"](device)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
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
        f"environment.device_serial={device}",
        "-c",
        f"agent.step_limit={step_limit}",
        "-t",
        scenario["task"],
        "--task-id",
        task_id,
        "-o",
        str(output_root),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=False)
    scenario["teardown"](device)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--device", default="emulator-5554")
    parser.add_argument("--step-limit", type=int, default=25)
    parser.add_argument("--output-root", default="outputs/m3a_benchmark")
    parser.add_argument("--repeat", type=int, default=1, help="Run scenario N times and aggregate metrics")
    parser.add_argument("--skip-run", action="store_true", help="Only analyze latest run dir")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")

    scenario = SCENARIOS[args.scenario]
    task_id = f"bench_{args.scenario}"
    output_root = REPO_ROOT / args.output_root
    log_path = output_root / "results.jsonl"

    if not args.skip_run:
        run_metrics: list[dict] = []
        exit_code = 0
        for attempt in range(1, args.repeat + 1):
            if args.repeat > 1:
                print(f"=== Run {attempt}/{args.repeat} ===")
            code = _run_scenario(
                scenario=scenario,
                task_id=task_id,
                device=args.device,
                step_limit=args.step_limit,
                output_root=output_root,
            )
            if code != 0:
                print(f"FAIL: CLI exited with code {code}")
                exit_code = code
            run_dir = _latest_run_dir(output_root, task_id)
            if run_dir is None:
                print("FAIL: no run directory found")
                return 1
            metrics = _analyze_run(run_dir)
            metrics["scenario"] = args.scenario
            metrics["device"] = args.device
            metrics["attempt"] = attempt
            metrics["repeat_total"] = args.repeat
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(metrics, ensure_ascii=False) + "\n")
            run_metrics.append(metrics)
            print(json.dumps(metrics, indent=2, ensure_ascii=False))
            if metrics["exit_status"] == "billing_error":
                return 2

        if args.repeat > 1:
            summary = _aggregate_metrics(run_metrics)
            summary["scenario"] = args.scenario
            summary["device"] = args.device
            print(json.dumps({"aggregate": summary}, indent=2, ensure_ascii=False))
        return exit_code

    run_dir = _latest_run_dir(output_root, task_id)
    if run_dir is None:
        print("FAIL: no run directory found")
        return 1
    metrics = _analyze_run(run_dir)
    metrics["scenario"] = args.scenario
    metrics["device"] = args.device
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    if metrics["exit_status"] == "billing_error":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
