#!/usr/bin/env python3
"""Turn raw run folders into summary tables. Deterministic, standard library only, reads nothing but the raw files.

  analyze.py [--raw evidence/raw] [--out FILE] [--operational operational.json] [--prices prices.json]

--raw          folder holding LOAD-* and RES-03-* run folders (default evidence/raw; use tests/load/out for local runs)
--operational  {"ec2": 12, "fargate": 9}: operational-burden figures, lower is better (not measured by this harness)
Rerunning on the same raw folders gives byte-identical output.
"""
import argparse
import csv
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
P95_LIMIT_MS, ERR_LIMIT = 800.0, 0.01          # thresholds accepted for the plan (section 3)
CPU_LIMIT, CPU_WINDOW_S, CLOCK_LIMIT_MS = 70.0, 30, 50.0
OVERLOAD_RATIO, RDS_LIMIT = 0.95, 80.0
CREDIT_EMPTY = 1.0  # burstable RDS: a balance under one CPU credit counts as exhausted
WEIGHTS = {"operational burden": 25, "replacement time and error window": 25, "steady-state latency": 20,
           "cost": 15, "scale-out time": 10, "capacity per unit": 5}


def epoch(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


# --- loading ------------------------------------------------------------------------------------------------

def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def read_csv(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def load_run(folder):
    meta = read_json(os.path.join(folder, "run.json"))
    if not meta:
        return None
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "requests-*.csv"))):
        for r in read_csv(path):
            r["ts"] = float(r["ts_epoch"])
            r["lat"] = float(r["latency_ms"]) if r["latency_ms"] else None
            rows.append(r)
    rows.sort(key=lambda r: (r["ts"], int(r["user"]), int(r["seq"])))
    cpu = [(float(r["ts_epoch"]), float(r["cpu_percent"])) for r in read_csv(os.path.join(folder, "generator_cpu.csv"))]
    metrics = {}
    for path in sorted(glob.glob(os.path.join(folder, "cloudwatch", "*.csv"))):
        metrics[Path(path).stem] = [(float(r["ts_epoch"]), float(r["value"])) for r in read_csv(path)]
    targets = []
    try:
        with open(os.path.join(folder, "targets.jsonl")) as f:
            targets = [json.loads(line) for line in f if line.strip()]
    except OSError:
        pass
    return dict(meta=meta, rows=rows, cpu=cpu, metrics=metrics, targets=targets,
                timing=read_json(os.path.join(folder, "timing.json"), {}), kill=read_json(os.path.join(folder, "kill.json")),
                alarms=read_json(os.path.join(folder, "alarm_history.json"), []),
                activities=read_json(os.path.join(folder, "scaling_activities.json"), []),
                ecs_events=read_json(os.path.join(folder, "ecs_events.json"), []))


# --- statistics for one window ------------------------------------------------------------------------------

def window_stats(rows, t0, t1, users, think, label):
    span = t1 - t0
    sel = [r for r in rows if t0 <= r["ts"] < t1]
    reqs = [r for r in sel if r["outcome"] in ("ok", "stock_conflict", "error")]
    dyn = [r for r in reqs if r["name"] != "GET static" and r["lat"] is not None]
    lat = [r["lat"] for r in dyn]
    checkout = [r["lat"] for r in dyn if r["name"] == "POST /checkout/"]
    errors = sum(1 for r in reqs if r["outcome"] == "error")
    actions = sum(1 for r in sel if r["seq"] == "1" and r["outcome"] != "late")
    intended = users / think if think else None
    return dict(label=label, users=users, seconds=span, n_req=len(reqs), n_dyn=len(dyn),
                p50=common.percentile(lat, 50), p95=common.percentile(lat, 95) if len(lat) >= 100 else None,
                p99=common.percentile(lat, 99) if len(lat) >= 1000 else None,
                checkout_p95=common.percentile(checkout, 95) if len(checkout) >= 20 else None,
                error_rate=errors / len(reqs) if reqs else None, errors=errors,
                stock_conflicts=sum(1 for r in reqs if r["outcome"] == "stock_conflict"),
                orders=sum(1 for r in reqs if r["name"] == "POST /checkout/" and r["status"] == "302"),
                req_s=len(reqs) / span, actions_s=actions / span, intended_actions_s=intended,
                late_starts=sum(1 for r in sel if r["outcome"] == "late"))


def rolling_cpu_peak(cpu):
    """Highest 30-second average of generator CPU, or None without samples."""
    vals = [v for _, v in cpu]
    if len(vals) < CPU_WINDOW_S:
        return max(vals) if vals else None
    return max(sum(vals[i:i + CPU_WINDOW_S]) / CPU_WINDOW_S for i in range(len(vals) - CPU_WINDOW_S + 1))


def credit_check(metrics, start, seconds, flags):
    """Lowest CPU credit balance in the run window; flags the run when a burstable database ran out of credits.

    Past the baseline a t4g database spends credits, and with none left it is throttled (standard mode) or
    keeps going on surplus credits that are billed (unlimited mode). Either way RDS CPU alone would not say so."""
    def inside(name):
        return [v for t, v in metrics.get(name, []) if start <= t <= start + seconds]
    balance = inside("rds_cpu_credit_balance")
    surplus = inside("rds_cpu_surplus_credit_balance")
    charged = inside("rds_cpu_surplus_credits_charged")
    empty = bool(balance) and min(balance) < CREDIT_EMPTY
    used = bool(surplus) and max(surplus) > 0
    if empty or used:
        flags.append("credit-limited: RDS CPU credit balance " + (f"fell to {min(balance):.1f}" if balance else "not recorded")
                     + (f", surplus credits used up to {max(surplus):.1f}" if used else ""))
    if charged and sum(charged) > 0:
        flags.append(f"RDS surplus credits charged: {sum(charged):.1f} (billed, not in the cost figures)")
    return min(balance) if balance else None


def analyse_run(run):
    meta, plan = run["meta"], run["meta"]["plan"]
    start = run["timing"].get("start_epoch")
    out = dict(meta=meta, windows=[], flags=[], invalid=[], timings=None)
    if start is None or not run["rows"]:
        out["invalid"].append("no timing or no requests recorded")
        return out
    for w in plan["windows"]:
        out["windows"].append(window_stats(run["rows"], start + w["start"], start + w["end"], w["users"], plan["think"], w["label"]))
    if run["meta"].get("aborted"):
        out["flags"].append("aborted: " + str(meta.get("abort_reason")))
    peak = rolling_cpu_peak(run["cpu"])
    out["generator_cpu_peak"] = peak
    if peak is None:
        out["invalid"].append("no generator CPU samples")
    elif peak > CPU_LIMIT:
        out["invalid"].append(f"generator CPU {peak:.0f}% over {CPU_WINDOW_S} s (limit {CPU_LIMIT:.0f}%)")
    offset = meta["generator"].get("clock_offset_ms")
    if offset is None:
        out["flags"].append("clock offset not recorded")
    elif abs(offset) > CLOCK_LIMIT_MS:
        out["invalid"].append(f"clock offset {offset} ms")
    if plan["think"] and meta["type"] in ("pilot", "ladder", "singapore"):
        for w in out["windows"]:
            if w["actions_s"] < OVERLOAD_RATIO * w["intended_actions_s"]:
                out["flags"].append(f"overloaded: {w['actions_s']:.2f} of {w['intended_actions_s']:.2f} actions/s")
    rds = run["metrics"].get("rds_cpu")
    if rds:
        window = [v for t, v in rds if start <= t <= start + meta["planned_seconds"]]
        if window and max(window) > RDS_LIMIT:
            out["flags"].append(f"database-limited: RDS CPU peaked at {max(window):.0f}%")
        out["rds_cpu_max"] = max(window) if window else None
    out["rds_credit_min"] = credit_check(run["metrics"], start, meta["planned_seconds"], out["flags"])
    if meta["type"] == "scaleout":
        out["timings"] = scaleout_timings(run, start)
    if meta["type"] == "replace":
        out["timings"] = replace_timings(run, start)
    return out


# --- scale-out and replacement timings (from AWS timestamps) --------------------------------------------------

def healthy_series(run):
    return [(epoch(t["ts_utc"]), t["healthy"]) for t in run["targets"]]


def scaleout_timings(run, start):
    plan = run["meta"]["plan"]
    t0 = start + plan["markers"]["step_up"]
    series = healthy_series(run)
    base = [h for t, h in series if t <= t0]
    alarms = sorted(epoch(a["Timestamp"]) for a in run["alarms"]
                    if "AlarmHigh" in a.get("AlarmName", "") and "to ALARM" in a.get("HistorySummary", "")
                    and epoch(a["Timestamp"]) >= t0 - 60)
    t1 = alarms[0] if alarms else None
    t2 = None
    if t1 is not None:
        launches = sorted(epoch(a["StartTime"]) for a in run["activities"] if a.get("Description", "").startswith("Launching")
                          and epoch(a["StartTime"]) >= t1 - 30)
        events = sorted(epoch(e["createdAt"]) for e in run["ecs_events"] if "has started" in e.get("message", "")
                        and epoch(e["createdAt"]) >= t1 - 30)
        t2 = (launches or events or [None])[0]
    t4 = None
    if t1 is not None and base:
        t4 = next((t for t, h in series if t >= t1 and h > base[-1]), None)
    d = lambda a, b: round(b - a, 1) if a is not None and b is not None else None  # noqa: E731
    return dict(detection_s=d(t0, t1), provisioning_s=d(t1, t2), scale_out_s=d(t1, t4), total_from_load_s=d(t0, t4))


def replace_timings(run, start):
    kill = run["kill"]
    if not kill:
        return dict(replacement_s=None, error_window_s=None, errors_after_kill=None)
    t_kill = epoch(kill["ts_utc"])
    series = [(t, h) for t, h in healthy_series(run) if t >= t_kill]
    dropped = next((t for t, h in series if h < 2), None)
    recovered = next((t for t, h in series if dropped is not None and t > dropped and h >= 2), None)
    errs = sorted(r["ts"] for r in run["rows"] if r["outcome"] == "error" and r["ts"] >= t_kill)
    return dict(replacement_s=round(recovered - t_kill, 1) if recovered else None,
                detected_s=round(dropped - t_kill, 1) if dropped else None,
                error_window_s=round(errs[-1] - errs[0], 1) if errs else 0.0, errors_after_kill=len(errs))


# --- aggregation --------------------------------------------------------------------------------------------

def spread(values):
    vals = [v for v in values if v is not None]
    return (common.median(vals), min(vals), max(vals), len(vals)) if vals else (None, None, None, 0)


def fmt(v, digits=0, unit=""):
    return "n/a" if v is None else f"{v:.{digits}f}{unit}"


def cell(values, digits=0, unit=""):
    med, lo, hi, n = spread(values)
    if med is None:
        return "n/a"
    return f"{med:.{digits}f}{unit}" if n == 1 else f"{med:.{digits}f}{unit} ({lo:.{digits}f}-{hi:.{digits}f})"


def capacity_step(windows):
    """Highest saturation step that still meets p95 and error limits, scanning up from the first step (contiguous)."""
    best = None
    for w in windows:
        if w["p95"] is None or w["p95"] >= P95_LIMIT_MS or (w["error_rate"] or 0) >= ERR_LIMIT:
            break
        best = w
    return best


def cost_per_1000(prices, variant, units, req_s):
    if not req_s:
        return None
    return (common.unit_hour(prices, variant) * units + common.fixed_hour(prices)) / (req_s * 3600) * 1000


def score_pair(a_vals, b_vals, higher_better):
    a, b = [v for v in a_vals if v is not None], [v for v in b_vals if v is not None]
    if not a or not b:
        return None
    if max(min(a), min(b)) <= min(max(a), max(b)):  # min-max ranges overlap: inside the noise, tie
        return 10.0, 10.0
    ma, mb = common.median(a), common.median(b)
    if higher_better:
        best = max(ma, mb)
        return 10 * ma / best, 10 * mb / best
    best = min(ma, mb)
    return 10 * best / ma, 10 * best / mb


# --- report -------------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=str(HERE.parent.parent / "evidence" / "raw"))
    ap.add_argument("--out")
    ap.add_argument("--operational")
    ap.add_argument("--prices", default=str(HERE / "prices.json"))
    args = ap.parse_args()
    prices = json.loads(Path(args.prices).read_text())
    operational = read_json(args.operational, {}) if args.operational else {}

    runs = []
    for folder in sorted(glob.glob(os.path.join(args.raw, "LOAD-*")) + glob.glob(os.path.join(args.raw, "RES-03-*"))):
        run = load_run(folder)
        if run:
            analysed = analyse_run(run)
            analysed["id"] = run["meta"]["run_id"]
            runs.append(analysed)
    if not runs:
        sys.exit(f"No run folders with run.json under {args.raw}")

    L = []
    w = L.append
    w("# Load test summary (generated by tests/load/analyze.py from the raw run folders; do not edit)\n")
    w(f"Latency is per dynamic HTTP request (static files reported separately); p95 needs at least 100 samples and p99 "
      f"at least 1,000. Limits: p95 under {P95_LIMIT_MS:.0f} ms, errors under {ERR_LIMIT:.0%}. "
      f"Prices: {'verified by the user' if prices.get('verified_by_user') else 'NOT verified by the user'} ({prices['checked']}).\n")

    w("## Runs\n")
    w("| Run | Window | Requests | Errors | Stock conflicts | Orders | Actions/s (intended) | Generator CPU peak | Status |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in runs:
        status = "INVALID: " + "; ".join(r["invalid"]) if r["invalid"] else ("; ".join(r["flags"]) or "valid")
        for win in r["windows"] or [None]:
            if win is None:
                w(f"| {r['id']} | - | - | - | - | - | - | - | {status} |")
                continue
            inten = f" ({win['intended_actions_s']:.2f})" if win["intended_actions_s"] else ""
            w(f"| {r['id']} | {win['label']} | {win['n_req']} | {win['errors']} ({fmt((win['error_rate'] or 0) * 100, 2, '%')}) | "
              f"{win['stock_conflicts']} | {win['orders']} | {win['actions_s']:.2f}{inten} | "
              f"{fmt(r.get('generator_cpu_peak'), 0, '%')} | {status} |")

    valid = [r for r in runs if not r["invalid"]]
    groups = {}
    for r in valid:
        m = r["meta"]
        if m["type"] in ("ladder", "pilot", "singapore"):
            groups.setdefault((m["variant"], m["type"], m["level"]), []).append(r)

    w("\n## Ladder, pilot and Singapore runs (median, min-max over valid repeats)\n")
    w("| Variant | Type | Users | Repeats | p50 ms | p95 ms | p99 ms | Errors | Requests/s | Actions/s | Checkout p95 ms | Orders/run |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    summary = {}
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2] or 0)):
        ws = [g["windows"][0] for g in groups[key]]
        summary[key] = ws
        w(f"| {key[0]} | {key[1]} | {key[2]} | {len(ws)} | {cell([x['p50'] for x in ws])} | {cell([x['p95'] for x in ws])} | "
          f"{cell([x['p99'] for x in ws])} | {cell([(x['error_rate'] or 0) * 100 for x in ws], 2, '%')} | "
          f"{cell([x['req_s'] for x in ws], 2)} | {cell([x['actions_s'] for x in ws], 2)} | "
          f"{cell([x['checkout_p95'] for x in ws])} | {cell([x['orders'] for x in ws])} |")

    sat = {}
    w("\n## Saturation (no think time; first 30 s of each step discarded)\n")
    for variant in ("ec2", "fargate"):
        for r in [x for x in valid if x["meta"]["variant"] == variant and x["meta"]["type"] == "saturation"]:
            w(f"### {r['id']}\n")
            w("| Users | Requests/s | Actions/s | p50 ms | p95 ms | Errors | RDS CPU max | RDS credits min |")
            w("|---|---|---|---|---|---|---|---|")
            for win in r["windows"]:
                w(f"| {win['users']} | {win['req_s']:.1f} | {win['actions_s']:.2f} | {fmt(win['p50'])} | {fmt(win['p95'])} | "
                  f"{fmt((win['error_rate'] or 0) * 100, 2, '%')} | {fmt(r.get('rds_cpu_max'), 0, '%')} | {fmt(r.get('rds_credit_min'), 1)} |")
            cap = capacity_step(r["windows"])
            top = max(r["windows"], key=lambda x: x["req_s"])
            sat.setdefault(variant, []).append(dict(
                capacity_users=cap["users"] if cap else None, capacity_actions_s=cap["actions_s"] if cap else None,
                capacity_req_s=cap["req_s"] if cap else None, max_req_s=top["req_s"], max_users=top["users"],
                cost_1000=cost_per_1000(prices, variant, 1, cap["req_s"] if cap else None)))
            w(f"\nPractical capacity: {'step of ' + str(cap['users']) + ' users (' + format(cap['actions_s'], '.2f') + ' page actions/s)' if cap else 'no step met the limits'}; "
              f"maximum throughput {top['req_s']:.1f} requests/s at {top['users']} users.\n")

    timing_rows = [r for r in valid if r["timings"]]
    w("## Scale-out and replacement timings\n")
    if timing_rows:
        w("| Run | Detection s | Alarm to scaling action s | Scale-out s (alarm to healthy) | Load step to healthy s | Kill to detected s | Replacement s | Error window s | Errors after kill |")
        w("|---|---|---|---|---|---|---|---|---|")
        for r in timing_rows:
            t = r["timings"]
            w(f"| {r['id']} | {fmt(t.get('detection_s'))} | {fmt(t.get('provisioning_s'))} | {fmt(t.get('scale_out_s'))} | "
              f"{fmt(t.get('total_from_load_s'))} | {fmt(t.get('detected_s'))} | {fmt(t.get('replacement_s'))} | "
              f"{fmt(t.get('error_window_s'))} | {fmt(t.get('errors_after_kill'))} |")
    else:
        w("No scale-out or replacement runs with AWS data yet.")

    w("\n## Comparison, EC2 (A) and Fargate (B)\n")
    levels = sorted({k[2] for k in summary if k[1] == "ladder"})
    scores, missing = {}, []
    if any(k[0] == "ec2" for k in summary) and any(k[0] == "fargate" for k in summary):
        w("| Users | p95 A ms | p95 B ms | B/A | Errors A | Errors B | Cost A per 1,000 req | Cost B per 1,000 req |")
        w("|---|---|---|---|---|---|---|---|")
        for lv in levels:
            a, b = summary.get(("ec2", "ladder", lv)), summary.get(("fargate", "ladder", lv))
            if not (a and b):
                continue
            ma, mb = spread([x["p95"] for x in a])[0], spread([x["p95"] for x in b])[0]
            ca = cost_per_1000(prices, "ec2", 1, spread([x["req_s"] for x in a])[0])
            cb = cost_per_1000(prices, "fargate", 1, spread([x["req_s"] for x in b])[0])
            w(f"| {lv} | {fmt(ma)} | {fmt(mb)} | {fmt(mb / ma, 2) if ma and mb else 'n/a'} | "
              f"{cell([(x['error_rate'] or 0) * 100 for x in a], 2, '%')} | {cell([(x['error_rate'] or 0) * 100 for x in b], 2, '%')} | "
              f"{fmt(ca, 4)} | {fmt(cb, 4)} |")

        def by_variant(fn):
            return [fn("ec2"), fn("fargate")]

        def tvals(variant, kind, key):
            return [r["timings"].get(key) for r in valid if r["meta"]["variant"] == variant and r["meta"]["type"] == kind and r["timings"]]

        lat = []
        for lv in (10, 100):
            s = score_pair([x["p95"] for x in summary.get(("ec2", "ladder", lv), [])],
                           [x["p95"] for x in summary.get(("fargate", "ladder", lv), [])], False)
            if s:
                lat.append(s)
        scores["steady-state latency"] = tuple(sum(x[i] for x in lat) / len(lat) for i in (0, 1)) if lat else None
        scores["capacity per unit"] = score_pair(*by_variant(lambda v: [s["capacity_actions_s"] for s in sat.get(v, [])]), True)
        scores["scale-out time"] = score_pair(*by_variant(lambda v: tvals(v, "scaleout", "scale_out_s")), False)
        rep = [score_pair(*by_variant(lambda v: tvals(v, "replace", k)), False) for k in ("replacement_s", "error_window_s")]
        rep = [x for x in rep if x]
        scores["replacement time and error window"] = tuple(sum(x[i] for x in rep) / len(rep) for i in (0, 1)) if rep else None
        scores["cost"] = score_pair(*by_variant(lambda v: [s["cost_1000"] for s in sat.get(v, [])]), False)
        scores["operational burden"] = score_pair([operational.get("ec2")], [operational.get("fargate")], False) if operational else None

        w("\n### Weighted score (weights locked by the user on 3 October 2026; ranges that overlap count as a tie)\n")
        w("| Criterion | Weight | A | B |")
        w("|---|---|---|---|")
        tot_w = tot_a = tot_b = 0
        for name, weight in WEIGHTS.items():
            s = scores.get(name)
            if s is None:
                missing.append(name)
                w(f"| {name} | {weight} | not measured yet | not measured yet |")
                continue
            tot_w += weight
            tot_a += weight * s[0]
            tot_b += weight * s[1]
            w(f"| {name} | {weight} | {s[0]:.1f} | {s[1]:.1f} |")
        if tot_w:
            w(f"\nWeighted total over the criteria measured (weights {tot_w} of 100): A {tot_a / tot_w:.2f}, B {tot_b / tot_w:.2f} out of 10."
              + (f" Missing: {', '.join(missing)}." if missing else ""))
    else:
        w("Both variants are needed for a comparison; only one has valid ladder data so far.")
    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text)
        print(f"Wrote {args.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
