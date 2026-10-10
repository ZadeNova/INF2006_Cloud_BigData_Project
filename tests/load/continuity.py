#!/usr/bin/env python3
"""RES-04: session and cart continuity across the removal of one unit, from a recorded RES-03b run.

    python tests/load/continuity.py evidence/raw/RES-03-fargate-replace-r1_2026-10-09

Reads kill.json and requests-*.csv from a replacement run folder. No network, no AWS, standard library only.

What the log can show. Every visit starts with an empty cookie jar, and the harness only marks `cart` as ok if the
cart page lists its lines, `checkout_review` if the review form is present and `checkout_place` if the order page
says it is confirmed. So an authenticated visit that is still ok after the removal kept its session and its cart.

What it cannot show. The request log does not record which unit served a request, so it cannot say which requests
were on the removed unit. It is also a graceful removal (the unit is drained first), not a crash.
"""
import collections
import csv
import datetime as dt
import glob
import json
import os
import sys

AUTH_ONLY = ("cart", "checkout_review", "checkout_place")


def parse_utc(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def load(folder):
    kill = json.load(open(os.path.join(folder, "kill.json"), encoding="utf-8"))
    t_kill = parse_utc(kill["ts_utc"])
    rows = []
    for f in sorted(glob.glob(os.path.join(folder, "requests-*.csv"))):
        with open(f, encoding="utf-8", newline="") as fh:
            rows += list(csv.DictReader(fh))
    for r in rows:
        r["t"] = float(r["ts_epoch"])
    return kill, t_kill, rows


def analyse(folder, window_s=120):
    kill, t_kill, rows = load(folder)
    visits = collections.defaultdict(list)
    for r in rows:
        visits[(r["user"], r["visit"])].append(r)
    out = collections.OrderedDict()
    out["folder"] = folder
    out["variant"] = kill.get("variant")
    out["mode"] = kill.get("mode")
    out["kill_utc"] = kill["ts_utc"]
    out["requests_total"] = len(rows)
    spanning = {k: v for k, v in visits.items() if min(r["t"] for r in v) < t_kill < max(r["t"] for r in v)}
    out["visits_total"] = len(visits)
    out["visits_spanning_kill"] = len(spanning)
    by_kind = collections.Counter(v[0]["kind"] for v in spanning.values())
    out["spanning_by_kind"] = dict(by_kind)
    authed = {k: v for k, v in spanning.items()
              if any(r["action"] == "login" and r["outcome"] == "ok" and r["t"] < t_kill for r in v)}
    out["authenticated_spanning_visits"] = len(authed)
    post = [r for v in authed.values() for r in v if r["t"] >= t_kill]
    out["post_kill_requests_in_authenticated_visits"] = len(post)
    out["post_kill_outcomes"] = dict(collections.Counter(r["outcome"] for r in post))
    out["post_kill_auth_only_actions"] = dict(collections.Counter((r["action"], r["outcome"]) for r in post if r["action"] in AUTH_ONLY))
    # The login action is logged as two rows (the POST and its redirect), so count the POSTs only.
    relog = [k for k, v in authed.items() if sum(1 for r in v if r["action"] == "login" and r["method"] == "POST") > 1]
    out["visits_that_needed_a_second_login"] = len(relog)
    out["orders_confirmed_after_kill"] = sum(1 for r in post if r["action"] == "checkout_place" and r["outcome"] == "ok")
    # Requests inside the drain window for every visit, authenticated or not.
    near = [r for r in rows if t_kill <= r["t"] <= t_kill + window_s]
    out[f"requests_in_{window_s}s_after_kill"] = len(near)
    out[f"non_ok_in_{window_s}s_after_kill"] = sum(1 for r in near if r["outcome"] != "ok")
    out["status_5xx_all_run"] = sum(1 for r in rows if r["status"].startswith("5"))
    out["non_ok_all_run"] = sum(1 for r in rows if r["outcome"] != "ok")
    return out


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    for folder in argv[1:]:
        res = analyse(folder.rstrip("/\\"))
        print(f"== {os.path.basename(res['folder'])}")
        for k, v in res.items():
            if k != "folder":
                print(f"  {k}: {v}")
        ok = (res["visits_that_needed_a_second_login"] == 0 and res["non_ok_all_run"] == 0
              and res["authenticated_spanning_visits"] > 0)
        print(f"  RESULT: {'continuity held' if ok else 'NOT held or not testable: read the figures above'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
