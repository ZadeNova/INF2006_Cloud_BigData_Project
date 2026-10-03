"""Locust workload for the 42Factors shop (docs/plans/load-harness.md).

One virtual user is one visitor slot: it runs visits back to back, each with an empty cookie jar and fresh connections.
Three kinds of visit (the mix is configured by run.py):
  shopper    browse only                                   5 page actions
  abandoner  browse, log in, add to cart, view cart        6 page actions
  buyer      the abandoner steps, then check out           8 page actions
Pacing is constant: page action k of a visit starts THINK seconds after action k-1 started (a late start is logged and
the schedule slips, it never catches up in a burst). Every HTTP request is written to requests-<pid>.csv, which is what
analyze.py reads; Locust's own CSV/HTML are kept as raw evidence too.

Run it through run.py, which builds the LOAD_CONFIG this file reads. Direct use: see README.md.
"""
import csv
import itertools
import json
import os
import random
import re
import time
from collections import deque
from datetime import datetime, timezone

import gevent
import psutil
from locust import HttpUser, LoadTestShape, constant, events, task
from locust.runners import WorkerRunner

import common

CFG = json.loads(os.environ.get("LOAD_CONFIG") or "{}")
OUT_DIR = CFG.get("out_dir") or os.path.join("out", "adhoc")
SEED = CFG.get("seed", 42)
THINK = float(CFG.get("think", 36))
MIX = CFG.get("mix") or {"shopper": 0.90, "abandoner": 0.075, "buyer": 0.025}
SEQUENCE = CFG.get("sequence")  # smoke runs: fixed cycle of visit kinds so every flow is exercised
PROCESSES = int(CFG.get("processes", 1))
POOL = int(CFG.get("pool", 1100))
PREFIX = os.environ.get("LOADTEST_PREFIX", "loadtest")
PASSWORD = os.environ.get("LOADTEST_PASSWORD", "")
CART_CAP = 10  # an abandoner's cart is emptied (untimed) once it holds more lines than this, so drift stays bounded
LATE_TOLERANCE = 1.0  # seconds

OK, STOCK, ERR, CLEAN, LATE = "ok", "stock_conflict", "error", "cleanup", "late"
HEADER = ["ts_epoch", "ts_utc", "user", "visit", "kind", "action", "seq", "method", "name", "status", "latency_ms",
          "bytes", "outcome", "account", "detail"]

STEPS = {
    "shopper": ["home", "detail", "list", "detail", "detail"],
    "abandoner": ["home", "detail", "login_form", "login", "cart_add", "cart"],
    "buyer": ["home", "detail", "login_form", "login", "cart_add", "cart", "checkout_review", "checkout_place"],
}


# --- per-request log (one file per Locust process, so no locking) ------------------------------------------

class RequestLog:
    def __init__(self):
        self.pid = None
        self.handle = None
        self.writer = None

    def row(self, **fields):
        if self.pid != os.getpid():
            os.makedirs(OUT_DIR, exist_ok=True)
            self.pid = os.getpid()
            self.handle = open(os.path.join(OUT_DIR, f"requests-{self.pid}.csv"), "a", newline="")
            self.writer = csv.DictWriter(self.handle, fieldnames=HEADER)
            if self.handle.tell() == 0:
                self.writer.writeheader()
        ts = fields.pop("ts")
        fields["ts_epoch"] = f"{ts:.3f}"
        fields["ts_utc"] = datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self.writer.writerow(fields)
        self.handle.flush()


LOG = RequestLog()
_SPAWNED = itertools.count()


class Result:
    def __init__(self, resp, outcome, detail):
        self.resp, self.outcome, self.detail = resp, outcome, detail


# --- response validators: content, not just status (a 200 error page is a failure) -------------------------

def _error_text(html):
    m = re.search(r'message--error[^>]*>.*?<p>(.*?)</p>', html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""


def _path(resp):
    return re.sub(r"^https?://[^/]+", "", resp.headers.get("Location", ""))


def v_home(resp):
    return (OK, "") if resp.status_code == 302 and _path(resp) == "/products/" else (ERR, f"/ gave {resp.status_code}")


def v_list(resp):
    if resp.status_code != 200:
        return ERR, f"status {resp.status_code}"
    n = len(common.product_ids(resp.text))
    return (OK, "") if n >= 5 else (ERR, f"only {n} product links")


def v_detail(resp):
    if resp.status_code != 200:
        return ERR, f"status {resp.status_code}"
    body = resp.text
    if 'name="product_id"' in body:  # logged in: the add-to-cart form must offer a size and carry a CSRF token
        if not common.csrf_token(body):
            return ERR, "detail form has no csrf token"
        if not any(o[2] for o in common.size_options(body)):
            return STOCK, "no size in stock"
        return OK, ""
    return (OK, "") if "/login/?next=" in body else (ERR, "detail page has neither form nor login link")


def v_login_form(resp):
    return (OK, "") if resp.status_code == 200 and common.csrf_token(resp.text) else (ERR, f"login form: {resp.status_code}")


def v_cart(resp):
    if resp.status_code != 200:
        return ERR, f"status {resp.status_code}"
    return (OK, "") if common.cart_line_ids(resp.text) else (ERR, "cart has no lines")


def v_checkout_review(resp):
    if resp.status_code != 200:
        return ERR, f"status {resp.status_code} (cart empty?)"
    return (OK, "") if common.review_value(resp.text) and common.csrf_token(resp.text) else (ERR, "no review value")


def v_order(resp):
    return (OK, "") if resp.status_code == 200 and "is confirmed" in resp.text else (ERR, f"order page {resp.status_code}")


def v_static(resp):
    return (OK, "") if resp.status_code == 200 else (ERR, f"static {resp.status_code}")


# --- the virtual user ---------------------------------------------------------------------------------------

class Visitor(HttpUser):
    wait_time = constant(0)

    def on_start(self):
        self.origin = common.check_base_url(self.host)
        runner = self.environment.runner
        worker = max(getattr(runner, "worker_index", 0) or 0, 0)
        self.idx = next(_SPAWNED) * PROCESSES + worker  # unique across processes
        self.acct_n = self.idx % POOL + 1
        self.rng = random.Random(f"{SEED}:{self.idx}")
        self.visit_no = 0
        self.next_at = time.monotonic() + (self.rng.uniform(0, THINK) if THINK else 0)
        self.client.headers["User-Agent"] = f"42factors-loadtest/{common.HARNESS_VERSION}"

    # pacing -----------------------------------------------------------------------------------------------
    def begin_action(self, action):
        self.action, self.seq = action, 0
        if not THINK:
            return
        now = time.monotonic()
        wait = self.next_at - now
        if wait > 0:
            gevent.sleep(wait)
            start = self.next_at
        else:
            start = now
            if -wait > LATE_TOLERANCE:
                self.write(ts=time.time(), method="-", name="late_start", status="", latency_ms=f"{-wait * 1000:.0f}",
                           bytes="", outcome=LATE, detail="")
        self.next_at = start + THINK

    def write(self, **f):
        LOG.row(user=self.idx, visit=self.visit_no, kind=getattr(self, "kind", ""), action=getattr(self, "action", "-"),
                seq=getattr(self, "seq", 0), account=getattr(self, "account", ""), **f)

    # one HTTP request ---------------------------------------------------------------------------------------
    def call(self, method, path, name, validate, data=None, referer=None, cleanup=False):
        self.seq += 1
        headers = {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
        if method == "POST":
            headers["Origin"] = self.origin
            headers["Referer"] = self.origin + (referer or path)
        elif referer:
            headers["Referer"] = self.origin + referer
        ts, t0 = time.time(), time.perf_counter()
        with self.client.request(method, path, name=name, data=data, headers=headers, allow_redirects=False,
                                 catch_response=True) as resp:
            own_ms = (time.perf_counter() - t0) * 1000
            if resp.status_code == 0:
                outcome, detail = ERR, f"no response: {getattr(resp, 'error', '')}"[:120]
            else:
                try:
                    outcome, detail = validate(resp)
                except Exception as exc:  # a parsing bug must show up as an error, not kill the user
                    outcome, detail = ERR, f"validator: {exc!r}"[:120]
            if cleanup:
                outcome = CLEAN
            if outcome == ERR:
                resp.failure(detail or "error")
            else:
                resp.success()
        ms = (getattr(resp, "request_meta", None) or {}).get("response_time", own_ms)
        self.write(ts=ts, method=method, name=name, status=resp.status_code, latency_ms=f"{ms:.1f}",
                   bytes=len(resp.content or b""), outcome=outcome, detail=detail)
        return Result(resp, outcome, detail)

    def fetch_statics(self, html):
        for path in common.static_assets(html):  # D1: the first page of a visit, as a cold browser would
            self.call("GET", path, "GET static", v_static, referer="/products/")

    def clean_cart(self, html=None):
        """Empty the cart through the app. Logged as cleanup, excluded from every statistic."""
        if html is None:
            html = self.call("GET", "/cart/", "GET /cart/ (cleanup)", lambda r: (OK, ""), cleanup=True).resp.text
        for item in common.cart_delete_ids(html):
            self.call("POST", f"/cart/items/{item}/delete/", "POST /cart/items/[id]/delete/ (cleanup)",
                      lambda r: (OK, ""), data={"csrfmiddlewaretoken": common.csrf_token(html) or ""},
                      referer="/cart/", cleanup=True)

    # page actions: each returns True to carry on with the visit ---------------------------------------------
    def a_home(self):
        self.begin_action("home")
        if self.call("GET", "/", "GET /", v_home).outcome != OK:
            return False
        r = self.call("GET", "/products/", "GET /products/", v_list)
        if r.outcome != OK:
            return False
        self.pids = common.product_ids(r.resp.text)
        self.fetch_statics(r.resp.text)
        return True

    def a_list(self):
        self.begin_action("list")
        r = self.call("GET", "/products/", "GET /products/", v_list)
        if r.outcome == OK:
            self.pids = common.product_ids(r.resp.text)
        return r.outcome == OK

    def a_detail(self):
        self.begin_action("detail")
        self.detail_id = self.rng.choice(self.pids)
        return self.call("GET", f"/products/{self.detail_id}/", "GET /products/[id]/", v_detail).outcome == OK

    def a_login_form(self):
        self.begin_action("login_form")
        self.login_next = f"/products/{self.detail_id}/"
        r = self.call("GET", f"/login/?next={self.login_next}", "GET /login/", v_login_form, referer=self.login_next)
        self.csrf = common.csrf_token(r.resp.text) if r.outcome == OK else None
        return r.outcome == OK

    def a_login(self):
        self.begin_action("login")
        username = f"{PREFIX}-{'a' if self.kind == 'abandoner' else 'b'}-{self.acct_n:04d}"
        data = {"csrfmiddlewaretoken": self.csrf, "username": username, "password": PASSWORD, "next": self.login_next}
        nxt = self.login_next
        r = self.call("POST", "/login/", "POST /login/",
                      lambda resp: (OK, "") if resp.status_code == 302 and _path(resp) == nxt
                      else (ERR, f"login failed: {resp.status_code}"), data=data, referer=f"/login/?next={nxt}")
        if r.outcome != OK:
            return False
        self.account = username
        r = self.call("GET", nxt, "GET /products/[id]/", v_detail)  # the redirect target; now carries the form
        if r.outcome != OK or 'name="product_id"' not in r.resp.text:
            return False
        self.form = (common.csrf_token(r.resp.text), common.size_options(r.resp.text))
        return True

    def a_cart_add(self):
        self.begin_action("cart_add")
        token, options = self.form
        data = {"csrfmiddlewaretoken": token, "next": self.login_next, "product_id": common.pick_size(options, self.rng),
                "quantity": "1"}
        nxt = self.login_next
        r = self.call("POST", "/cart/items/", "POST /cart/items/",
                      lambda resp: (OK, "") if resp.status_code == 302 and _path(resp) == nxt
                      else (ERR, f"add gave {resp.status_code}"), data=data, referer=nxt)
        if r.outcome != OK:
            return False

        def added(resp):
            if resp.status_code != 200:
                return ERR, f"status {resp.status_code}"
            if "added to your cart" in resp.text:
                return OK, ""
            return (STOCK, "refused for stock") if common.is_stock_message(resp.text) else (ERR, _error_text(resp.text) or "no confirmation")

        return self.call("GET", nxt, "GET /products/[id]/", added).outcome == OK

    def a_cart(self):
        self.begin_action("cart")
        r = self.call("GET", "/cart/", "GET /cart/", v_cart)
        if r.outcome == OK and len(common.cart_delete_ids(r.resp.text)) > CART_CAP:
            self.clean_cart(r.resp.text)
        return r.outcome == OK

    def a_checkout_review(self):
        self.begin_action("checkout_review")
        r = self.call("GET", "/checkout/", "GET /checkout/", v_checkout_review, referer="/cart/")
        if r.outcome != OK:
            return False
        self.checkout = (common.csrf_token(r.resp.text), common.review_value(r.resp.text))
        return True

    def a_checkout_place(self):
        self.begin_action("checkout_place")
        token, review = self.checkout

        def placed(resp):
            if resp.status_code == 302 and common.order_id_from_location(_path(resp)):
                return OK, f"order {common.order_id_from_location(_path(resp))}"
            if resp.status_code == 409 and common.is_stock_message(resp.text):
                return STOCK, "refused for stock"
            return ERR, f"checkout gave {resp.status_code}: {_error_text(resp.text)}"

        r = self.call("POST", "/checkout/", "POST /checkout/", placed,
                      data={"csrfmiddlewaretoken": token, "review": review}, referer="/checkout/")
        if r.outcome == STOCK:
            self.clean_cart()  # otherwise the sold-out line blocks this account's next checkout
            return False
        if r.outcome != OK:
            return False
        order_path = _path(r.resp)
        return self.call("GET", order_path, "GET /orders/[id]/", v_order).outcome == OK

    # a visit ------------------------------------------------------------------------------------------------
    def choose_kind(self):
        if SEQUENCE:
            return SEQUENCE[(self.idx + self.visit_no) % len(SEQUENCE)]
        x, acc = self.rng.random(), 0.0
        for kind, share in MIX.items():
            acc += share
            if x < acc:
                return kind
        return "shopper"

    @task
    def visit(self):
        self.kind = self.choose_kind()
        self.visit_no += 1
        self.account = ""
        self.client.cookies.clear()  # a new visitor: no cookies, new TLS connections
        self.client.close()
        try:
            for step in STEPS[self.kind]:
                if not getattr(self, f"a_{step}")():
                    break
        except Exception as exc:
            self.write(ts=time.time(), method="-", name="visit_exception", status="", latency_ms="", bytes="",
                       outcome=ERR, detail=repr(exc)[:120])
            events.request.fire(request_type="VISIT", name="visit_exception", response_time=0, response_length=0,
                                exception=exc, context={})


# --- load shape: the stages come from run.py ----------------------------------------------------------------

_STAGES = CFG.get("stages") or []
if _STAGES:
    _ENDS = list(itertools.accumulate(s["duration"] for s in _STAGES))

    class StagedShape(LoadTestShape):
        def tick(self):
            t = self.get_run_time()
            for end, stage in zip(_ENDS, _STAGES):
                if t < end:
                    return stage["users"], stage["spawn_rate"]
            return None


# --- generator CPU, automatic abort, timing (master / local runner only) ------------------------------------

def _write_json(name, payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w") as f:
        json.dump(payload, f, indent=2)


def _utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _cpu_sampler():
    os.makedirs(OUT_DIR, exist_ok=True)
    psutil.cpu_percent(interval=None)
    with open(os.path.join(OUT_DIR, "generator_cpu.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_epoch", "ts_utc", "cpu_percent"])
        while True:
            gevent.sleep(1)
            now = time.time()
            w.writerow([f"{now:.3f}", _utc(now), psutil.cpu_percent(interval=None)])
            f.flush()


def _abort_monitor(environment):
    rule = CFG.get("abort") or {}
    if not rule:
        return
    started, step = time.monotonic(), 5
    samples, prev = deque(), (0, 0)
    while True:
        gevent.sleep(step)
        total = environment.runner.stats.total
        now = time.monotonic()
        samples.append((now, total.num_requests - prev[0], total.num_failures - prev[1],
                        total.get_current_response_time_percentile(0.95)))
        prev = (total.num_requests, total.num_failures)
        while samples and samples[0][0] < now - rule["window"]:
            samples.popleft()
        if now - started < rule["after"] or len(samples) < rule["window"] / step * 0.9:
            continue
        reqs, fails = sum(s[1] for s in samples), sum(s[2] for s in samples)
        reason = None
        if reqs >= 20 and fails / reqs > rule["err"]:
            reason = f"error rate {fails / reqs:.0%} over the last {rule['window']} s exceeds {rule['err']:.0%}"
        elif rule.get("p95_ms") and all(s[3] and s[3] > rule["p95_ms"] for s in samples):
            reason = f"p95 above {rule['p95_ms']} ms for {rule['window']} s"
        if reason:
            _write_json("abort.json", {"reason": reason, "at_utc": _utc(time.time())})
            environment.process_exit_code = 3
            environment.runner.quit()
            return


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    now = time.time()
    _write_json("timing.json", {"start_epoch": now, "start_utc": _utc(now)})
    gevent.spawn(_cpu_sampler)
    gevent.spawn(_abort_monitor, environment)


@events.quitting.add_listener
def _on_quitting(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    path = os.path.join(OUT_DIR, "timing.json")
    try:
        with open(path) as f:
            timing = json.load(f)
    except (OSError, ValueError):
        return
    now = time.time()
    timing.update(end_epoch=now, end_utc=_utc(now), exit_code=environment.process_exit_code)
    _write_json("timing.json", timing)
