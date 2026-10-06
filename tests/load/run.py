#!/usr/bin/env python3
"""Run one load test and write everything it produced to out/<run-id>/.

  run.py smoke       --base-url http://127.0.0.1:8000
  run.py pilot       --variant ec2 --base-url URL --repeat 1
  run.py ladder      --variant ec2 --base-url URL --level 100 --repeat 1
  run.py saturation  --variant ec2 --base-url URL --repeat 1
  run.py scaleout    --variant ec2 --base-url URL --repeat 1 [--users-high 200]
  run.py replace     --variant ec2 --base-url URL --repeat 1
  run.py singapore   --variant ec2 --base-url URL --repeat 1 --location singapore-laptop

The schedule of every type is fixed here (docs/plans/load-harness.md, section 6) so A and B always get the same test.
Prints the expected duration and approximate cost first and waits for a yes. Needs LOADTEST_PASSWORD in the environment.
It never starts or stops AWS resources.
"""
import argparse
import json
import math
import os
import platform
import re
import shlex
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
SEED_DEFAULT = 42
THINK = 36
WARMUP = 120
LADDER = {1: (1, 600), 10: (1, 600), 100: (2, 300), 1000: (5, 300)}  # level -> (spawn rate/s, measure seconds)
SATURATION_STEPS = [1, 2, 4, 8, 16, 32, 64]
STEP_SECONDS, STEP_DISCARD = 120, 30
SCALEOUT_LOW, SCALEOUT_BASE_S, SCALEOUT_HOLD_S, SCALEOUT_DOWN_S = 10, 180, 900, 300
REPLACE_USERS, REPLACE_TOTAL_S, REPLACE_KILL_AT_S = 100, 1200, 300
ABORT = {"after": 60, "window": 60, "err": 0.20, "p95_ms": 10000}          # plan section 3
ABORT_RELAXED = {"after": 60, "window": 120, "err": 0.50, "p95_ms": None}   # scale-out and replacement runs
MIX = {"shopper": 0.90, "abandoner": 0.075, "buyer": 0.025}


def plan_for(args):
    """Everything the test does, as data: stages for the load shape, measurement windows, abort rule."""
    t = args.type
    if t == "smoke":
        return dict(think=3, mix=MIX, sequence=["buyer", "abandoner", "shopper"], abort={}, units=0,
                    stages=[dict(duration=75, users=2, spawn_rate=1)],
                    windows=[dict(label="all", start=0, end=75, users=2)], markers={})
    if t in ("pilot", "ladder", "singapore"):
        level = 1000 if t == "pilot" else 10 if t == "singapore" else args.level
        if level not in LADDER:
            sys.exit(f"STOP: --level must be one of {sorted(LADDER)}")
        spawn, measure = LADDER[level]
        ramp = math.ceil(level / spawn)
        total = ramp + WARMUP + measure
        return dict(think=THINK, mix=MIX, abort=ABORT, units=1, level=level,
                    stages=[dict(duration=total, users=level, spawn_rate=spawn)],
                    windows=[dict(label=f"u{level}", start=ramp + WARMUP, end=total, users=level)],
                    markers={"ramp_end": ramp})
    if t == "saturation":
        stages = [dict(duration=STEP_SECONDS, users=u, spawn_rate=max(u, 10)) for u in SATURATION_STEPS]
        windows = [dict(label=f"u{u}", start=i * STEP_SECONDS + STEP_DISCARD, end=(i + 1) * STEP_SECONDS, users=u)
                   for i, u in enumerate(SATURATION_STEPS)]
        return dict(think=0, mix=MIX, abort=ABORT, units=1, stages=stages, windows=windows, markers={})
    if t == "scaleout":
        high = args.users_high
        stages = [dict(duration=SCALEOUT_BASE_S, users=SCALEOUT_LOW, spawn_rate=1),
                  dict(duration=SCALEOUT_HOLD_S, users=high, spawn_rate=5),
                  dict(duration=SCALEOUT_DOWN_S, users=SCALEOUT_LOW, spawn_rate=5)]
        total = sum(s["duration"] for s in stages)
        return dict(think=THINK, mix=MIX, abort=ABORT_RELAXED, units=2, stages=stages,
                    windows=[dict(label="all", start=0, end=total, users=high)],
                    markers={"step_up": SCALEOUT_BASE_S, "step_down": SCALEOUT_BASE_S + SCALEOUT_HOLD_S})
    if t == "replace":
        return dict(think=THINK, mix=MIX, abort=ABORT_RELAXED, units=2,
                    stages=[dict(duration=REPLACE_TOTAL_S, users=REPLACE_USERS, spawn_rate=2)],
                    windows=[dict(label="all", start=0, end=REPLACE_TOTAL_S, users=REPLACE_USERS)],
                    markers={"kill_at": REPLACE_KILL_AT_S})
    sys.exit(f"STOP: unknown run type {t}")


def run_id_for(args, date):
    token = {"ladder": f"ladder-u{args.level}", "smoke": "smoke"}.get(args.type, args.type)
    prefix = "RES-03" if args.type in ("scaleout", "replace") else "LOAD"
    return f"{prefix}-{args.variant}-{token}-r{args.repeat}_{date}"


# --- context recorded in run.json ---------------------------------------------------------------------------

def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=HERE).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def clock_offset_ms():
    m = re.search(r"System time\s*:\s*([\d.]+) seconds (fast|slow)", sh(["chronyc", "tracking"]))
    return round(float(m.group(1)) * 1000, 3) * (1 if m.group(2) == "fast" else -1) if m else None


def instance_type():
    if os.environ.get("LOAD_GENERATOR_INSTANCE_TYPE"):
        return os.environ["LOAD_GENERATOR_INSTANCE_TYPE"]
    try:  # IMDSv2; only answers on EC2
        base = "http://169.254.169.254/latest/"
        token = urllib.request.urlopen(urllib.request.Request(
            base + "api/token", method="PUT", headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=1).read().decode()
        return urllib.request.urlopen(urllib.request.Request(
            base + "meta-data/instance-type", headers={"X-aws-ec2-metadata-token": token}), timeout=1).read().decode()
    except Exception:
        return "unknown"


def locust_version():
    try:
        from importlib.metadata import version
        return version("locust")
    except Exception:
        return "unknown"


# --- cost and duration shown before the run ----------------------------------------------------------------

def estimate(plan, variant, prices, seconds):
    hours = seconds / 3600
    if variant not in ("ec2", "fargate"):
        return hours, 0.0  # local run: nothing is billed
    unit = common.unit_hour(prices, variant)
    hourly = prices["generator_c5_large_hour"] + common.fixed_hour(prices) + unit * plan["units"] + prices["rds_t4g_small_hour"]
    return hours, hourly * hours


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("type", choices=["smoke", "pilot", "ladder", "saturation", "scaleout", "replace", "singapore"])
    ap.add_argument("--variant", choices=["ec2", "fargate", "local"], default=None)
    ap.add_argument("--base-url", default=os.environ.get("LOAD_BASE_URL", ""))
    ap.add_argument("--level", type=int, default=0, help="ladder only: 1, 10, 100 or 1000 users")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--users-high", type=int, default=200, help="scaleout only: users after the step up")
    ap.add_argument("--processes", type=int, default=None, help="Locust worker processes (default 2; smoke 1)")
    ap.add_argument("--location", default="unknown", help="where the generator runs, e.g. us-east-1 or singapore-laptop")
    ap.add_argument("--out-root", default=str(HERE / "out"))
    ap.add_argument("--yes", action="store_true", help="skip the confirmation question")
    args = ap.parse_args()

    if args.type == "smoke":
        args.variant = args.variant or "local"
    if not args.variant:
        sys.exit("STOP: --variant ec2|fargate is required")
    if args.type == "ladder" and not args.level:
        sys.exit("STOP: ladder needs --level 1|10|100|1000")
    if not os.environ.get("LOADTEST_PASSWORD"):
        sys.exit("STOP: set LOADTEST_PASSWORD (see .env.example)")
    try:
        origin = common.check_base_url(args.base_url)
    except ValueError as exc:
        sys.exit(f"STOP: {exc}")
    host = origin.split("//", 1)[1].split(":")[0]
    expected = {h: v for v, h in common.HOSTS_BY_VARIANT.items()}.get(host, "local")
    if args.variant != expected:
        sys.exit(f"STOP: --variant {args.variant} does not match target {host} (that would label {expected} data as {args.variant})")

    plan = plan_for(args)
    processes = args.processes or (1 if args.type == "smoke" else 2)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = run_id_for(args, date)
    out_dir = Path(args.out_root) / run_id
    if out_dir.exists():
        sys.exit(f"STOP: {out_dir} exists; raw output is never overwritten (use another --repeat)")

    seconds = sum(s["duration"] for s in plan["stages"])
    prices = json.loads((HERE / "prices.json").read_text())
    hours, cost = estimate(plan, args.variant, prices, seconds + 60)
    schedule = ", ".join("%d users for %d s" % (s["users"], s["duration"]) for s in plan["stages"])
    unverified = "" if prices.get("verified_by_user") else "  (prices.json is NOT yet verified by the user)"
    print(f"Run        {run_id}\nTarget     {origin}  (variant {args.variant})\nSchedule   {schedule}\n"
          f"Think time {plan['think']} s   seed {args.seed}   Locust processes {processes}\n"
          f"Expected   {seconds // 60} min {seconds % 60} s of load ({hours * 60:.0f} min with start-up)\n"
          f"Cost       {'none (local)' if args.variant == 'local' else f'about USD {cost:.2f} for the stack, generator and database while this runs{unverified}'}")
    if args.type == "replace":
        print(f"           You must kill ONE unit about {REPLACE_KILL_AT_S} s after the start; this script will say when.")
    if not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        sys.exit("Not started.")

    out_dir.mkdir(parents=True)
    config = dict(out_dir=str(out_dir), seed=args.seed, think=plan["think"], mix=plan["mix"], processes=processes,
                  stages=plan["stages"], abort=plan["abort"], sequence=plan.get("sequence"))
    command = [sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"), "--headless", "--host", origin,
               "--csv", str(out_dir / "locust"), "--csv-full-history", "--html", str(out_dir / "report.html"),
               "--exit-code-on-error", "0"] + (["--processes", str(processes)] if processes > 1 else [])
    meta = dict(
        run_id=run_id, type=args.type, variant=args.variant, level=plan.get("level"), repeat=args.repeat, seed=args.seed,
        harness_version=common.HARNESS_VERSION, locust_version=locust_version(), python=platform.python_version(),
        git_commit=sh(["git", "rev-parse", "HEAD"]), git_dirty_harness=bool(sh(["git", "status", "--porcelain", "--", "."])),
        command_line=shlex.join(sys.argv), locust_command=shlex.join(command), base_url=origin,
        generator=dict(location=args.location, instance_type=instance_type(), clock_offset_ms=clock_offset_ms()),
        plan=dict(think=plan["think"], mix=plan["mix"], sequence=plan.get("sequence"), stages=plan["stages"],
                  windows=plan["windows"], markers=plan["markers"], abort=plan["abort"], units=plan["units"],
                  warmup_s=WARMUP, processes=processes),
        planned_seconds=seconds)
    (out_dir / "run.json").write_text(json.dumps(meta, indent=2))

    if args.type == "replace":
        threading.Timer(REPLACE_KILL_AT_S, lambda: print(
            "\n=========== NOW: kill one unit (aws_capture.py kill ...) ===========\n", flush=True)).start()
    print(f"\nStarting at {datetime.now(timezone.utc):%H:%M:%S} UTC. Output: {out_dir}\n", flush=True)
    started = time.time()
    code = subprocess.run(command, env={**os.environ, "LOAD_CONFIG": json.dumps(config)}, cwd=HERE).returncode

    timing = json.loads((out_dir / "timing.json").read_text()) if (out_dir / "timing.json").exists() else {}
    abort = json.loads((out_dir / "abort.json").read_text()) if (out_dir / "abort.json").exists() else None
    meta.update(started_utc=timing.get("start_utc"), ended_utc=timing.get("end_utc"), exit_code=code,
                aborted=bool(abort), abort_reason=abort["reason"] if abort else None,
                wall_seconds=round(time.time() - started, 1))
    (out_dir / "run.json").write_text(json.dumps(meta, indent=2))
    print(f"\nFinished with exit code {code}{' (ABORTED: ' + abort['reason'] + ')' if abort else ''}. Output in {out_dir}")
    print("Next: copy the folder to the laptop (see README), then aws_capture.py export, then analyze.py.")
    sys.exit(code)


if __name__ == "__main__":
    main()
