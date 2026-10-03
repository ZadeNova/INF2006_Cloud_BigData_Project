#!/usr/bin/env python3
"""Synthetic test accounts and cart resets for the load runs. Never timed, never part of a measurement.

  accounts.py create       --base-url URL [--count 1100] [--kinds ab] [--workers 8]
  accounts.py reset-carts  --base-url URL (--from-run RUN_DIR | --all [--count 1100]) [--kinds ab] [--workers 4]

Accounts are named <LOADTEST_PREFIX>-a-0001 (cart abandoners) and <prefix>-b-0001 (buyers) and share the password in
LOADTEST_PASSWORD. They are created through the normal /register/ form, because imported customers have unusable
passwords. `create` is idempotent: an existing account is checked by logging in. They live in the shared database,
so one `create` serves both variants.
"""
import argparse
import csv
import glob
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

import common

PREFIX = os.environ.get("LOADTEST_PREFIX", "loadtest")
PASSWORD = os.environ.get("LOADTEST_PASSWORD", "")


def names(kinds, count):
    return [f"{PREFIX}-{k}-{n:04d}" for k in kinds for n in range(1, count + 1)]


class Shop:
    """A browser-like session: fetch the form first, send its CSRF token with a same-origin Referer and Origin."""

    def __init__(self, origin):
        self.origin = origin
        self.http = requests.Session()
        self.http.headers["User-Agent"] = f"42factors-loadtest/{common.HARNESS_VERSION} (setup)"

    def get(self, path):
        return self.http.get(self.origin + path, timeout=30, allow_redirects=False)

    def post(self, path, data):
        return self.http.post(self.origin + path, data=data, timeout=30, allow_redirects=False,
                              headers={"Origin": self.origin, "Referer": self.origin + path})

    def form_token(self, path):
        page = self.get(path)
        token = common.csrf_token(page.text) if page.status_code == 200 else None
        if not token:
            raise RuntimeError(f"GET {path} gave {page.status_code} without a CSRF token")
        return token

    def login(self, username):
        r = self.post("/login/", {"csrfmiddlewaretoken": self.form_token("/login/"), "username": username,
                                  "password": PASSWORD, "next": "/cart/"})
        return r.status_code == 302


def create_one(origin, username):
    shop = Shop(origin)
    try:
        r = shop.post("/register/", {"csrfmiddlewaretoken": shop.form_token("/register/"), "username": username,
                                     "password1": PASSWORD, "password2": PASSWORD})
        if r.status_code == 302:
            return username, "created", ""
        if "already exists" in r.text:
            return (username, "existing", "") if Shop(origin).login(username) else \
                (username, "failed", "exists, but the password does not match LOADTEST_PASSWORD")
        return username, "failed", f"register gave {r.status_code}"
    except Exception as exc:
        return username, "failed", repr(exc)[:120]


def reset_one(origin, username):
    shop = Shop(origin)
    try:
        if not shop.login(username):
            return username, "failed", "login failed"
        page = shop.get("/cart/")
        items = common.cart_delete_ids(page.text)
        token = common.csrf_token(page.text)
        for item in items:
            r = shop.post(f"/cart/items/{item}/delete/", {"csrfmiddlewaretoken": token})
            if r.status_code not in (200, 302):
                return username, "failed", f"delete gave {r.status_code}"
        return username, "cleared" if items else "empty", str(len(items))
    except Exception as exc:
        return username, "failed", repr(exc)[:120]


def accounts_from_run(run_dir):
    """Accounts that added something to a cart during a run (they may have left it there)."""
    found = set()
    for path in glob.glob(os.path.join(run_dir, "requests-*.csv")):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row["action"] == "cart_add" and row["account"]:
                    found.add(row["account"])
    return sorted(found)


def run_all(fn, origin, usernames, workers):
    tally, failures = {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (user, result, detail) in enumerate(pool.map(lambda u: fn(origin, u), usernames), 1):
            tally[result] = tally.get(result, 0) + 1
            if result == "failed":
                failures.append(f"{user}: {detail}")
            if i % 100 == 0:
                print(f"  {i}/{len(usernames)} {tally}", flush=True)
    print(f"done: {tally}")
    for line in failures[:10]:
        print("  FAILED", line)
    return not failures


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["create", "reset-carts"])
    ap.add_argument("--base-url", default=os.environ.get("LOAD_BASE_URL", ""))
    ap.add_argument("--count", type=int, default=1100, help="accounts per kind")
    ap.add_argument("--kinds", default="ab", help="a = abandoners, b = buyers")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--from-run", help="reset only accounts that added to a cart in this run directory")
    ap.add_argument("--all", action="store_true", help="reset every account (logs in 2 x count times; slow)")
    args = ap.parse_args()
    if not PASSWORD:
        sys.exit("STOP: set LOADTEST_PASSWORD (see .env.example)")
    try:
        origin = common.check_base_url(args.base_url)
    except ValueError as exc:
        sys.exit(f"STOP: {exc}")

    if args.command == "create":
        users = names(args.kinds, args.count)
        print(f"Creating up to {len(users)} accounts on {origin} ...")
        ok = run_all(create_one, origin, users, args.workers or 8)
    else:
        if bool(args.from_run) == bool(args.all):
            sys.exit("STOP: give exactly one of --from-run or --all")
        users = names(args.kinds, args.count) if args.all else accounts_from_run(args.from_run)
        print(f"Checking {len(users)} carts on {origin} ...")
        ok = run_all(reset_one, origin, users, args.workers or 4)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
