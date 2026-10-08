#!/usr/bin/env python3
"""Checks for the harness's own logic, with no network and no Locust. Run:  python selftest.py

Covers the target allow-list, HTML parsing, redaction, percentiles, the fixed schedules in run.py, and analyze.py on
synthetic run folders whose scale-out, replacement, capacity and score values are known in advance. It does not (and
cannot) test anything that needs AWS; the README lists what stays untested until the first cloud session.
Named selftest.py, not test_*.py, so the CI pytest run over tests/ does not collect it.
"""
import csv
import json
import random
import subprocess
import sys
import tempfile
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import analyze
import common
import run

HERE = Path(__file__).resolve().parent
T0 = 1_790_000_000.0  # fixed start so the expected values are exact


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# --- unit checks --------------------------------------------------------------------------------------------

def test_allow_list():
    assert common.check_base_url("https://shop-ec2.fourtytwofactors.me/") == "https://shop-ec2.fourtytwofactors.me"
    assert common.check_base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    for bad in ("https://example.com", "http://shop-ec2.fourtytwofactors.me", "https://fonts.googleapis.com",
                "https://shop-ec2.fourtytwofactors.me.evil.com"):
        try:
            common.check_base_url(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should have been refused")


def test_parsing():
    page = ('<form method="post" action="/cart/items/"><input type="hidden" name="csrfmiddlewaretoken" value="tok123">'
            '<select name="product_id"><option value="" selected disabled>Choose a size</option>'
            '<option value="7">US 7</option><option value="8">US 8 · only 3 left</option>'
            '<option value="9" disabled>US 9 · sold out</option></select></form>'
            '<a href="/products/4/">x</a><a href="/products/4/">x</a><a href="/products/9/">y</a>'
            '<link href="/static/css/site.abc.css"><script src="/static/js/site.def.js"></script>'
            '<use href="/static/img/icons.1.svg#i-sun"/><model-viewer src="/static/models/a.b.glb">')
    assert common.csrf_token(page) == "tok123"
    assert common.product_ids(page) == ["4", "9"]
    assert common.static_assets(page) == ["/static/css/site.abc.css", "/static/js/site.def.js", "/static/img/icons.1.svg"]
    opts = common.size_options(page)
    assert [o[0] for o in opts] == ["7", "8", "9"] and [o[2] for o in opts] == [True, True, False]
    assert common.pick_size(opts, random.Random(1)) == "7"  # the roomy size beats 'only 3 left' and the disabled one
    assert common.pick_size([("8", "US 8 · only 3 left", True)], random.Random(1)) == "8"  # falls back to a low one
    assert common.review_value('name="review" value="' + "a" * 64 + '"') == "a" * 64
    assert common.review_value('name="review" value="short"') is None
    assert common.is_stock_message('Only 2 of "Air Max" in stock (indicative).')
    assert common.is_stock_message('Only 0 of "Air Max" left in stock.')
    assert not common.is_stock_message("This checkout no longer matches your cart.")
    assert common.order_id_from_location("/orders/42/") == "42"
    assert common.order_id_from_location("/cart/") is None


def test_redaction():
    text = "arn:aws:iam::123456789012:role/x from 54.12.200.7 and 10.0.1.5 and 127.0.0.1 v2.46.6 1790000000123"
    out = common.redact(text)
    assert "123456789012" not in out and "<ACCOUNT>" in out
    assert "54.12.200.7" not in out and "<PUBLIC-IP>" in out
    assert "10.0.1.5" in out and "127.0.0.1" in out and "2.46.6" in out and "1790000000123" in out


def test_percentiles():
    assert common.percentile(list(range(1, 101)), 95) == 95
    assert common.percentile(list(range(1, 101)), 99) == 99
    assert common.percentile([5], 99) == 5 and common.percentile([], 50) is None
    assert common.median([3, 1, 2]) == 2 and common.median([1, 2, 3, 4]) == 2.5


def test_schedules():
    def plan(t, **kw):
        return run.plan_for(Namespace(type=t, level=kw.get("level", 0), users_high=kw.get("users_high", 200)))
    p = plan("ladder", level=100)  # 100 users at 2/s: 50 s ramp, then 120 s warm-up, then 300 s measured
    assert p["windows"][0]["start"] == 170 and p["windows"][0]["end"] == 470 and p["stages"][0]["duration"] == 470
    assert plan("pilot")["windows"][0]["users"] == 1000 and plan("singapore")["windows"][0]["users"] == 10
    s = plan("saturation")
    assert [w["users"] for w in s["windows"]] == run.SATURATION_STEPS and s["windows"][1]["start"] == 150
    assert sum(x["duration"] for x in s["stages"]) == 7 * 120 and s["think"] == 0
    assert sum(x["duration"] for x in plan("scaleout")["stages"]) == 1380 and plan("scaleout")["markers"]["step_up"] == 180
    assert plan("replace")["markers"]["kill_at"] == 300 and plan("smoke")["sequence"] == ["buyer", "abandoner", "shopper"]
    assert abs(sum(run.MIX.values()) - 1.0) < 1e-9
    visit_actions = 0.90 * 5 + 0.075 * 6 + 0.025 * 8  # plan section 4: mean 5.15 actions per visit
    assert abs(visit_actions - 5.15) < 1e-9


# --- analysis on synthetic runs -----------------------------------------------------------------------------

HEADER = ["ts_epoch", "ts_utc", "user", "visit", "kind", "action", "seq", "method", "name", "status", "latency_ms", "bytes",
          "outcome", "account", "detail"]


def make_run(root, run_id, variant, rtype, level, windows, think, rows, markers=None, planned=600, cpu=20.0, extra=None):
    d = Path(root) / run_id
    d.mkdir(parents=True)
    meta = dict(run_id=run_id, type=rtype, variant=variant, level=level, repeat=1, planned_seconds=planned, aborted=False,
                generator=dict(clock_offset_ms=1.0),
                plan=dict(think=think, windows=windows, markers=markers or {}, stages=[], abort={}, units=1))
    (d / "run.json").write_text(json.dumps(meta))
    (d / "timing.json").write_text(json.dumps(dict(start_epoch=T0, start_utc=iso(T0))))
    with open(d / "requests-1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for off, name, status, lat, outcome, action, seq in rows:
            w.writerow([f"{T0 + off:.3f}", iso(T0 + off), 0, 1, "shopper", action, seq, "GET", name, status, lat, 0, outcome, "", ""])
    with open(d / "generator_cpu.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_epoch", "ts_utc", "cpu_percent"])
        for i in range(int(planned)):
            w.writerow([f"{T0 + i:.3f}", iso(T0 + i), cpu])
    for name, payload in (extra or {}).items():
        (d / name).write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return d


def steady_rows(seconds, base, jitter, name="GET /products/", errors_at=()):
    """One request per second: latency base + (i % 10) * 10 + jitter."""
    return [(i, name, 200 if i not in errors_at else 500, base + (i % 10) * 10 + jitter,
             "ok" if i not in errors_at else "error", "list", 1) for i in range(seconds)]


def build_fixture(root):
    win = [dict(label="u100", start=0, end=300, users=1)]
    for variant, base in (("ec2", 100), ("fargate", 200)):
        for rep in (1, 2, 3):
            for level in (10, 100):
                make_run(root, f"LOAD-{variant}-ladder-u{level}-r{rep}_x", variant, "ladder", level, win, 1,
                         steady_rows(300, base, rep), planned=300)
    # saturation (A only): u1 and u2 pass, u4 breaks the p95 limit
    sat_windows = [dict(label=f"u{u}", start=i * 100, end=(i + 1) * 100, users=u) for i, u in enumerate((1, 2, 4))]
    sat_rows = steady_rows(100, 100, 0) + [(100 + o, n, s, l, oc, a, q) for o, n, s, l, oc, a, q in steady_rows(100, 120, 0)] \
        + [(200 + o, n, s, l + 900, oc, a, q) for o, n, s, l, oc, a, q in steady_rows(100, 100, 0)]
    make_run(root, "LOAD-ec2-saturation-r1_x", "ec2", "saturation", None, sat_windows, 0, sat_rows, planned=300)
    # scale-out: load step at 100 s, alarm 150 s later, launch 10 s after that, healthy at +400 s
    make_run(root, "RES-03-ec2-scaleout-r1_x", "ec2", "scaleout", None, [dict(label="all", start=0, end=600, users=200)], 36,
             steady_rows(600, 100, 0), markers={"step_up": 100}, planned=600, extra={
                 "alarm_history.json": [dict(Timestamp=iso(T0 + 250), AlarmName="TargetTracking-asg-AlarmHigh-1",
                                             HistorySummary="Alarm updated from OK to ALARM")],
                 "scaling_activities.json": [dict(Description="Launching a new EC2 instance: i-1", StartTime=iso(T0 + 260))],
                 "targets.jsonl": "\n".join(json.dumps(x) for x in (dict(ts_utc=iso(T0 + 50), healthy=1),
                                                                    dict(ts_utc=iso(T0 + 500), healthy=2)))})
    # replacement: kill at 300 s, one target missing from +30 s, back to two healthy at +250 s; errors from +5 s to +30 s
    errs = tuple(range(305, 331))
    make_run(root, "RES-03-ec2-replace-r1_x", "ec2", "replace", None, [dict(label="all", start=0, end=600, users=100)], 36,
             steady_rows(600, 100, 0, errors_at=errs), markers={"kill_at": 300}, planned=600, extra={
                 "kill.json": dict(ts_utc=iso(T0 + 300), unit_id="i-1"),
                 "targets.jsonl": "\n".join(json.dumps(x) for x in (dict(ts_utc=iso(T0 + 100), healthy=2),
                                                                    dict(ts_utc=iso(T0 + 330), healthy=1),
                                                                    dict(ts_utc=iso(T0 + 550), healthy=2)))})
    # an invalid run: generator CPU too high
    make_run(root, "LOAD-ec2-ladder-u100-r9_x", "ec2", "ladder", 100, win, 1, steady_rows(300, 100, 0), planned=300, cpu=85.0)


def test_analysis():
    with tempfile.TemporaryDirectory() as tmp:
        build_fixture(tmp)
        by_id = {}
        for folder in sorted(Path(tmp).iterdir()):
            r = analyze.load_run(folder)
            by_id[r["meta"]["run_id"]] = analyze.analyse_run(r)
        scale = by_id["RES-03-ec2-scaleout-r1_x"]["timings"]
        assert scale["detection_s"] == 150.0 and scale["provisioning_s"] == 10.0, scale
        assert scale["scale_out_s"] == 250.0 and scale["total_from_load_s"] == 400.0, scale
        rep = by_id["RES-03-ec2-replace-r1_x"]["timings"]
        assert rep["detected_s"] == 30.0 and rep["replacement_s"] == 250.0, rep
        assert rep["error_window_s"] == 25.0 and rep["errors_after_kill"] == 26, rep
        assert by_id["LOAD-ec2-ladder-u100-r9_x"]["invalid"], "85% generator CPU must invalidate a run"
        assert not by_id["LOAD-ec2-ladder-u100-r1_x"]["invalid"]
        w = by_id["LOAD-ec2-ladder-u100-r1_x"]["windows"][0]
        assert w["n_dyn"] == 300 and w["errors"] == 0 and abs(w["actions_s"] - 1.0) < 1e-9, w
        assert w["p99"] is None  # fewer than 1,000 samples: not quoted
        cap = analyze.capacity_step(by_id["LOAD-ec2-saturation-r1_x"]["windows"])
        assert cap["users"] == 2, cap  # u4 has p95 over the limit, so the last passing step is 2 users
        ops = Path(tmp) / "ops.json"
        ops.write_text(json.dumps({"ec2": 12, "fargate": 9}))
        out = subprocess.run([sys.executable, str(HERE / "analyze.py"), "--raw", tmp, "--operational", str(ops)],
                             capture_output=True, text=True, check=True).stdout
        again = subprocess.run([sys.executable, str(HERE / "analyze.py"), "--raw", tmp, "--operational", str(ops)],
                               capture_output=True, text=True, check=True).stdout
        assert out == again, "analysis must be deterministic"
        assert "INVALID: generator CPU 85%" in out and "Weighted score" in out
        # A is faster at ladder levels 10 and 100 with non-overlapping ranges: A scores 10, B scores less
        row = next(line for line in out.splitlines() if line.startswith("| steady-state latency"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert cells[2] == "10.0" and float(cells[3]) < 10.0, row
        assert "not measured yet" in next(line for line in out.splitlines() if line.startswith("| capacity per unit"))


def test_credit_flag():
    def series(folder, name, values):
        (folder / "cloudwatch").mkdir(exist_ok=True)
        with open(folder / "cloudwatch" / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts_epoch", "ts_utc", "value"])
            for i, v in enumerate(values):
                w.writerow([f"{T0 + 60 * i:.3f}", iso(T0 + 60 * i), v])
    windows = [dict(label="u10", start=0, end=300, users=1)]
    with tempfile.TemporaryDirectory() as tmp:
        results = {}
        for name, balance, surplus, charged in (("ok", [80, 70, 60], [0, 0, 0], [0, 0, 0]),
                                                 ("empty", [20, 0.2, 0], [0, 0, 0], [0, 0, 0]),
                                                 ("unlimited", [0, 0, 0], [0, 4, 9], [0, 0, 3])):
            d = make_run(tmp, f"LOAD-ec2-ladder-u10-{name}_x", "ec2", "ladder", 10, windows, 1, steady_rows(300, 100, 0), planned=300)
            series(d, "rds_cpu_credit_balance", balance)
            series(d, "rds_cpu_surplus_credit_balance", surplus)
            series(d, "rds_cpu_surplus_credits_charged", charged)
            results[name] = analyze.analyse_run(analyze.load_run(d))
        assert not any("credit" in f for f in results["ok"]["flags"]) and results["ok"]["rds_credit_min"] == 60
        assert any(f.startswith("credit-limited: RDS CPU credit balance") for f in results["empty"]["flags"]), results["empty"]["flags"]
        flags = results["unlimited"]["flags"]
        assert any(f.startswith("credit-limited:") and "surplus credits used up to 9.0" in f for f in flags), flags
        assert any("charged: 3.0" in f for f in flags), flags
        assert not any("credit" in f for f in analyze.analyse_run(analyze.load_run(make_run(
            tmp, "LOAD-ec2-ladder-u10-none_x", "ec2", "ladder", 10, windows, 1, steady_rows(300, 100, 0), planned=300)))["flags"])


def test_reset_code():
    import base64
    import reset_state
    for apply, word in ((False, "False"), (True, "True")):
        code = reset_state.build_code("loadtest", apply)
        compile(code, "reset", "exec")
        assert f'APPLY, PREFIX = {word}, "loadtest"' in code and "__APPLY__" not in code and "__PREFIX__" not in code
    arg = reset_state.shell_argument(code)
    encoded = arg.split("b64decode('")[1].split("')")[0]
    assert base64.b64decode(encoded).decode() == code, "the code must survive the shell argument unchanged"
    assert "'" not in encoded and '"' not in arg
    try:
        reset_state.build_code("x'); import os", False)
        raise AssertionError("a prefix with quotes must be refused")
    except SystemExit:
        pass
    # Fargate: a one-off task whose command carries the code; its log must show the DRY RUN or APPLIED line
    import aws_capture
    outputs = dict(cluster_name="c", task_definition_arn="arn:aws:ecs:us-east-1:123456789012:task-definition/t:1",
                   subnet_ids=["subnet-a"], security_group_ids={"app": "sg-2"}, log_group_name="/g/app")
    task = "arn:aws:ecs:us-east-1:123456789012:task/c/abc"
    real_sleep, aws_capture.time.sleep = aws_capture.time.sleep, lambda s: None
    try:
        for log, ok in (("accounts: 8 | load orders: 2\nDRY RUN: nothing was changed.", True), ("Traceback ...", False)):
            kf = stubbed_clients()
            kf.stub("ecs").add_response("run_task", {"tasks": [{"taskArn": task}], "failures": []}, expected_params={
                "cluster": "c", "taskDefinition": outputs["task_definition_arn"], "launchType": "FARGATE", "count": 1,
                "networkConfiguration": {"awsvpcConfiguration": {"subnets": ["subnet-a"], "securityGroups": ["sg-2"], "assignPublicIp": "ENABLED"}},
                "overrides": {"containerOverrides": [{"name": "web", "command": ["sh", "-c", f'python manage.py shell -c "{arg}"']}]}})
            kf.stub("ecs").add_response("describe_tasks", {"tasks": [{"lastStatus": "STOPPED", "containers": [{"exitCode": 0}]}], "failures": []})
            kf.stub("logs").add_response("get_log_events", {"events": [{"timestamp": 1, "message": log, "ingestionTime": 1}]},
                                         expected_params={"logGroupName": "/g/app", "logStreamName": "web/web/abc"})
            for stubber in kf.stubs.values():
                stubber.activate()
            try:
                reset_state.run_fargate(code, kf, outputs)
                assert ok
            except SystemExit:
                assert not ok, "a task that printed neither DRY RUN nor APPLIED must stop the command"
            for stubber in kf.stubs.values():
                stubber.assert_no_pending_responses()
    finally:
        aws_capture.time.sleep = real_sleep


def test_score_pair():
    assert analyze.score_pair([100, 110], [105, 120], False) == (10.0, 10.0)  # ranges overlap: a tie
    a, b = analyze.score_pair([100, 101], [200, 202], False)
    assert a == 10.0 and abs(b - 10 * 101 / 201) < 0.6
    a, b = analyze.score_pair([50, 51], [25, 26], True)  # higher is better
    assert a == 10.0 and b < 6
    assert analyze.score_pair([], [1], False) is None



# --- aws_capture against botocore Stubber: no network, but every call's parameters are validated by the real
# --- AWS service models, so a misspelt parameter or a wrong type fails here instead of during a paid cloud run ----

def stubbed_clients():
    import boto3
    from botocore.stub import Stubber
    import aws_capture

    class StubbedClients(aws_capture.Clients):
        def __init__(self):
            super().__init__("us-east-1")
            self.stubs = {}

        def get(self, service):
            if service not in self._clients:
                client = boto3.client(service, region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")
                self._clients[service] = client
                self.stubs[service] = Stubber(client)
            return self._clients[service]

        def stub(self, service):
            self.get(service)
            return self.stubs[service]

    return StubbedClients()


def test_aws_capture_export_and_kill():
    try:
        import boto3  # noqa: F401
    except ImportError:
        print("SKIP  test_aws_capture_export_and_kill (boto3 not installed)")
        return
    import aws_capture
    outputs = dict(target_group_arn="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-app/abc123",
                   asg_name="inf2006-grp21-ec2-asg", web_acl_name="inf2006-grp21-ec2-waf", hostname="shop-ec2.fourtytwofactors.me",
                   image_digest="sha256:dead")
    at = datetime.fromtimestamp(T0 + 250, timezone.utc)
    clients = stubbed_clients()
    clients.stub("elbv2").add_response("describe_target_groups", {"TargetGroups": [{"LoadBalancerArns": [
        "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/inf2006-grp21-ec2-alb/f00"]}]})
    clients.stub("rds").add_response("describe_db_instances", {"DBInstances": [dict(
        DBInstanceIdentifier="inf2006-grp21-db", DBInstanceClass="db.t4g.small", EngineVersion="17.4", MultiAZ=False)]})
    queries = aws_capture.metric_queries("ec2", outputs, "app/inf2006-grp21-ec2-alb/f00", "targetgroup/tg-app/abc123", "inf2006-grp21-db")
    assert len({q[0] for q in queries}) == len(queries)
    cw = clients.stub("cloudwatch")
    cw.add_response("get_metric_data", {"MetricDataResults": [dict(Id=f"m{i}", Label=q[0], Timestamps=[at], Values=[12.5], StatusCode="Complete")
                                                              for i, q in enumerate(queries)]})
    cw.add_response("describe_alarms", {"MetricAlarms": [{"AlarmName": "TargetTracking-inf2006-grp21-ec2-asg-AlarmHigh-1"}]})
    cw.add_response("describe_alarms", {"MetricAlarms": []})
    cw.add_response("describe_alarm_history", {"AlarmHistoryItems": [dict(
        AlarmName="TargetTracking-inf2006-grp21-ec2-asg-AlarmHigh-1", Timestamp=at, HistoryItemType="StateUpdate",
        HistorySummary="Alarm updated from OK to ALARM by arn:aws:iam::123456789012:role/LabRole")]})
    clients.stub("autoscaling").add_response("describe_scaling_activities", {"Activities": [
        dict(ActivityId="a1", AutoScalingGroupName="x", Description="Launching a new EC2 instance: i-9", Cause="c", StartTime=at,
             EndTime=at, StatusCode="Successful", Progress=100),
        dict(ActivityId="a0", AutoScalingGroupName="x", Description="Launching long before the run", Cause="c",
             StartTime=datetime.fromtimestamp(T0 - 86400, timezone.utc), StatusCode="Successful", Progress=100)]})
    clients.stub("autoscaling").add_response("describe_auto_scaling_groups", {"AutoScalingGroups": [dict(
        AutoScalingGroupName="x", MinSize=1, MaxSize=2, DesiredCapacity=1, DefaultCooldown=300, AvailabilityZones=["us-east-1a"],
        HealthCheckType="ELB", CreatedTime=at, LaunchTemplate=dict(LaunchTemplateId="lt-1", Version="3"), Instances=[])]})
    clients.stub("ec2").add_response("describe_launch_template_versions", {"LaunchTemplateVersions": [
        dict(LaunchTemplateData=dict(InstanceType="c5.large"))]})
    clients.stub("wafv2").add_response("list_web_acls", {"WebACLs": [dict(Name="inf2006-grp21-ec2-waf", Id="id-1", ARN="arn:aws:wafv2:us-east-1:123456789012:regional/webacl/n/id-1", LockToken="tok")]})
    clients.stub("wafv2").add_response("get_web_acl", {"WebACL": dict(
        Name="n", Id="i", ARN="arn:aws:wafv2:us-east-1:123456789012:regional/webacl/n/id-1", DefaultAction={"Allow": {}}, VisibilityConfig=dict(
            SampledRequestsEnabled=True, CloudWatchMetricsEnabled=True, MetricName="m"),
        Rules=[dict(Name="login-rate-limit", Priority=1, Action={"Count": {}}, VisibilityConfig=dict(
            SampledRequestsEnabled=True, CloudWatchMetricsEnabled=True, MetricName="m"),
            Statement={"RateBasedStatement": {"Limit": 20, "AggregateKeyType": "IP"}})])})
    for stubber in clients.stubs.values():
        stubber.activate()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = make_run(Path(tmp) / "out", "LOAD-ec2-ladder-u10-r1_x", "ec2", "ladder", 10,
                           [dict(label="u10", start=0, end=300, users=1)], 1, steady_rows(300, 100, 0), planned=300)
        dest, warnings = aws_capture.export(clients, "ec2", outputs, run_dir, Path(tmp) / "evidence")
        assert not warnings, warnings
        for stubber in clients.stubs.values():
            stubber.assert_no_pending_responses()
        assert (dest / "cloudwatch" / "rds_cpu.csv").read_text().splitlines()[1].endswith(",12.5")
        history = json.loads((dest / "alarm_history.json").read_text())
        assert len(history) == 1 and "to ALARM" in history[0]["HistorySummary"]
        acts = json.loads((dest / "scaling_activities.json").read_text())
        assert [a["Description"] for a in acts] == ["Launching a new EC2 instance: i-9"], acts  # the old one is outside the window
        stack = json.loads((dest / "stack.json").read_text())
        assert stack["instance_type"] == "c5.large" and stack["rds_class"] == "db.t4g.small", stack
        assert stack["waf_login_action"] == "Count" and stack["waf_login_limit"] == 20 and stack["max"] == 2, stack
        assert all("123456789012" not in p.read_text() for p in dest.rglob("*") if p.is_file()), "account id leaked"
        assert "<ACCOUNT>" in (dest / "alarm_history.json").read_text()
        try:
            aws_capture.export(clients, "ec2", outputs, run_dir, Path(tmp) / "evidence")
        except SystemExit:
            pass
        else:
            raise AssertionError("export must refuse to overwrite existing evidence")

        # kill: picks the lowest in-service instance, logs the time, and refuses when only one unit is running
        kc = stubbed_clients()
        two = {"AutoScalingGroups": [dict(AutoScalingGroupName="x", MinSize=2, MaxSize=2, DesiredCapacity=2, DefaultCooldown=300,
                                          AvailabilityZones=["a"], HealthCheckType="ELB", CreatedTime=datetime.now(timezone.utc),
                                          Instances=[dict(InstanceId=i, AvailabilityZone="a", LifecycleState="InService",
                                                          HealthStatus="Healthy", ProtectedFromScaleIn=False) for i in ("i-b", "i-a")])]}
        kc.stub("autoscaling").add_response("describe_auto_scaling_groups", two)
        # graceful: through the Auto Scaling group (drains from the load balancer first), and the group replaces it
        kc.stub("autoscaling").add_response("terminate_instance_in_auto_scaling_group", {"Activity": dict(
            ActivityId="a-1", AutoScalingGroupName="x", Cause="load test", StartTime=datetime.now(timezone.utc), StatusCode="InProgress")},
            expected_params={"InstanceId": "i-a", "ShouldDecrementDesiredCapacity": False})
        for stubber in kc.stubs.values():
            stubber.activate()
        path = Path(tmp) / "kill.json"
        aws_capture.kill(kc, "ec2", outputs, path, True)
        killed = json.loads(path.read_text())
        assert killed["unit_id"] == "i-a" and killed["units_before"] == 2 and killed["ts_utc"].endswith("Z")
        assert killed["mode"] == "graceful"
        for stubber in kc.stubs.values():
            stubber.assert_no_pending_responses()
        one = stubbed_clients()
        one.stub("autoscaling").add_response("describe_auto_scaling_groups", {"AutoScalingGroups": [dict(
            AutoScalingGroupName="x", MinSize=1, MaxSize=1, DesiredCapacity=1, DefaultCooldown=300, AvailabilityZones=["a"],
            HealthCheckType="ELB", CreatedTime=datetime.now(timezone.utc),
            Instances=[dict(InstanceId="i-a", AvailabilityZone="a", LifecycleState="InService", HealthStatus="Healthy",
                            ProtectedFromScaleIn=False)])]})
        one.stub("autoscaling").activate()
        try:
            aws_capture.kill(one, "ec2", outputs, Path(tmp) / "k2.json", True)
        except SystemExit as exc:
            assert "needs two" in str(exc)
        else:
            raise AssertionError("kill must refuse with a single unit")

        states = stubbed_clients()
        states.stub("elbv2").add_response("describe_target_health", {"TargetHealthDescriptions": [
            dict(Target=dict(Id="i-a", Port=8000), TargetHealth=dict(State="healthy")),
            dict(Target=dict(Id="i-b", Port=8000), TargetHealth=dict(State="initial"))]},
            expected_params={"TargetGroupArn": outputs["target_group_arn"]})
        states.stub("elbv2").activate()
        assert aws_capture.target_states(states, outputs["target_group_arn"]) == {"i-a:8000": "healthy", "i-b:8000": "initial"}



def test_aws_capture_export_fargate():
    try:
        import boto3  # noqa: F401
    except ImportError:
        print("SKIP  test_aws_capture_export_fargate (boto3 not installed)")
        return
    import aws_capture
    outputs = dict(target_group_arn="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-f/abc123",
                   cluster_name="inf2006-grp21-fargate", service_name="inf2006-grp21-fargate-app",
                   web_acl_name="inf2006-grp21-fargate-waf", hostname="shop-fargate.fourtytwofactors.me")
    at = datetime.fromtimestamp(T0 + 250, timezone.utc)
    clients = stubbed_clients()
    clients.stub("elbv2").add_response("describe_target_groups", {"TargetGroups": [{"LoadBalancerArns": [
        "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/inf2006-grp21-fargate-alb/f00"]}]})
    clients.stub("rds").add_response("describe_db_instances", {"DBInstances": [dict(
        DBInstanceIdentifier="inf2006-grp21-db", DBInstanceClass="db.t4g.small", EngineVersion="17.4", MultiAZ=False)]})
    queries = aws_capture.metric_queries("fargate", outputs, "app/x/f00", "targetgroup/tg-f/abc123", "inf2006-grp21-db")
    cw = clients.stub("cloudwatch")
    cw.add_response("get_metric_data", {"MetricDataResults": [dict(Id=f"m{i}", Label=q[0], Timestamps=[at], Values=[1.0], StatusCode="Complete")
                                                              for i, q in enumerate(queries)]})
    cw.add_response("describe_alarms", {"MetricAlarms": []})
    cw.add_response("describe_alarms", {"MetricAlarms": []})
    event = dict(id="e1", createdAt=at, message="(service s) has started 1 tasks: (task t).")
    service = dict(serviceName="s", desiredCount=1, runningCount=1, taskDefinition="arn:aws:ecs:us-east-1:123456789012:task-definition/t:1",
                   events=[event, dict(id="e0", createdAt=datetime.fromtimestamp(T0 - 86400, timezone.utc), message="old")])
    ecs = clients.stub("ecs")
    ecs.add_response("describe_services", {"services": [service]})
    ecs.add_response("describe_services", {"services": [service]})
    ecs.add_response("describe_task_definition", {"taskDefinition": {"cpu": "2048", "memory": "4096"}})
    clients.stub("application-autoscaling").add_response("describe_scalable_targets", {"ScalableTargets": [dict(
        ServiceNamespace="ecs", ResourceId="service/c/s", ScalableDimension="ecs:service:DesiredCount", MinCapacity=1, MaxCapacity=2,
        RoleARN="arn:aws:iam::123456789012:role/r", CreationTime=at)]})
    arn = "arn:aws:wafv2:us-east-1:123456789012:regional/webacl/n/id-1"
    clients.stub("wafv2").add_response("list_web_acls", {"WebACLs": [dict(Name="inf2006-grp21-fargate-waf", Id="id-1", ARN=arn, LockToken="tok")]})
    clients.stub("wafv2").add_response("get_web_acl", {"WebACL": dict(
        Name="n", Id="i", ARN=arn, DefaultAction={"Allow": {}}, VisibilityConfig=dict(
            SampledRequestsEnabled=True, CloudWatchMetricsEnabled=True, MetricName="m"),
        Rules=[dict(Name="login-rate-limit", Priority=1, Action={"Count": {}}, VisibilityConfig=dict(
            SampledRequestsEnabled=True, CloudWatchMetricsEnabled=True, MetricName="m"),
            Statement={"RateBasedStatement": {"Limit": 20, "AggregateKeyType": "IP"}})])})
    for stubber in clients.stubs.values():
        stubber.activate()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = make_run(Path(tmp) / "out", "LOAD-fargate-ladder-u10-r1_x", "fargate", "ladder", 10,
                           [dict(label="u10", start=0, end=300, users=1)], 1, steady_rows(300, 100, 0), planned=300)
        dest, warnings = aws_capture.export(clients, "fargate", outputs, run_dir, Path(tmp) / "evidence")
        assert not warnings, warnings
        for stubber in clients.stubs.values():
            stubber.assert_no_pending_responses()
        events = json.loads((dest / "ecs_events.json").read_text())
        assert [e["message"] for e in events] == ["(service s) has started 1 tasks: (task t)."], events
        stack = json.loads((dest / "stack.json").read_text())
        assert stack["task_cpu"] == "2048" and stack["task_memory_mb"] == "4096" and stack["max"] == 2, stack
        assert (dest / "cloudwatch" / "ecs_cpu.csv").exists() and not (dest / "scaling_activities.json").exists()

        # kill on Fargate: lists the service's running tasks, stops the first one (sorted), logs the time
        kc = stubbed_clients()
        tasks = ["arn:aws:ecs:us-east-1:123456789012:task/c/bbb", "arn:aws:ecs:us-east-1:123456789012:task/c/aaa"]
        kc.stub("ecs").add_response("list_tasks", {"taskArns": tasks}, expected_params={
            "cluster": outputs["cluster_name"], "serviceName": outputs["service_name"], "desiredStatus": "RUNNING"})
        kc.stub("ecs").add_response("stop_task", {}, expected_params={
            "cluster": outputs["cluster_name"], "task": tasks[1], "reason": "load test: replacement"})
        kc.stub("ecs").activate()
        path = Path(tmp) / "kill-f.json"
        aws_capture.kill(kc, "fargate", outputs, path, True)
        assert json.loads(path.read_text())["unit_id"] == tasks[1]
        kc.stub("ecs").assert_no_pending_responses()


# --- run validity from stack.json, the bounded error window, per-step database figures, CPU model ----------------------

def write_series(folder, name, values, step=60, offset=0):
    (folder / "cloudwatch").mkdir(exist_ok=True)
    with open(folder / "cloudwatch" / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_epoch", "ts_utc", "value"])
        for i, v in enumerate(values):
            w.writerow([f"{T0 + offset + step * i:.3f}", iso(T0 + offset + step * i), v])


def good_stack(variant="ec2", **over):
    stack = dict(variant=variant, image_digest="sha256:" + "a" * 64, rds_class="db.t4g.small", waf_login_action="count", min=1, max=1, desired=1)
    stack.update(over)
    return stack


def test_stack_validity():
    win = [dict(label="u10", start=0, end=300, users=1)]

    def run(tmp, name, rtype="ladder", stack=None, healthy=1.0, windows=win, markers=None, targets=None):
        extra = {"stack.json": stack} if stack is not None else {}
        if targets is not None:   # the watcher's exact record: (seconds from the run start, healthy count)
            extra["targets.jsonl"] = "\n".join(json.dumps(dict(ts_utc=iso(T0 + t), healthy=h)) for t, h in targets)
        d = make_run(tmp, f"LOAD-ec2-{rtype}-{name}_x", "ec2", rtype, 10, windows, 1, steady_rows(300, 100, 0), markers=markers,
                     planned=300, extra=extra)
        if healthy is not None:
            write_series(d, "alb_healthy_hosts", [healthy, healthy], offset=-60)
        return d

    with tempfile.TemporaryDirectory() as tmp:
        runs = {
            "ok1": run(tmp, "ok1", stack=good_stack()), "ok2": run(tmp, "ok2", stack=good_stack()),
            "ok3": run(tmp, "ok3", stack=good_stack()),
            "digest": run(tmp, "digest", stack=good_stack(image_digest="sha256:" + "b" * 64)),
            "cap": run(tmp, "cap", stack=good_stack(max=2)),
            "waf": run(tmp, "waf", stack=good_stack(waf_login_action="block")),
            "healthy": run(tmp, "healthy", stack=good_stack(), healthy=0.0),
            "nostack": run(tmp, "nostack"),
            "nohealth": run(tmp, "nohealth", stack=good_stack(), healthy=None),
            "scale": run(tmp, "scale", rtype="scaleout", stack=good_stack(min=1, max=2), markers={"step_up": 100}, targets=[(-30, 1)]),
            # replacement: the exact watcher count decides, so a CloudWatch series that reads 1 (per zone, say) changes nothing
            "replace": run(tmp, "replace", rtype="replace", stack=good_stack(min=2, max=2), healthy=1.0, markers={"kill_at": 100},
                           targets=[(-60, 1), (-30, 2)]),
            "replace1": run(tmp, "replace1", rtype="replace", stack=good_stack(min=1, max=2), markers={"kill_at": 100}, targets=[(-30, 2)]),
            "replace_bad": run(tmp, "replace_bad", rtype="replace", stack=good_stack(min=2, max=2), markers={"kill_at": 100}, targets=[(-30, 1)]),
            "replace_nowatch": run(tmp, "replace_nowatch", rtype="replace", stack=good_stack(min=2, max=2), markers={"kill_at": 100}),
        }
        loaded = {k: analyze.load_run(d) for k, d in runs.items()}
        ref = analyze.campaign_reference(loaded.values())
        assert ref["image_digest"] == "sha256:" + "a" * 64 and ref["waf_login_action"] == "count", ref
        out = {k: analyze.analyse_run(r, ref) for k, r in loaded.items()}
        for good in ("ok1", "ok2", "ok3", "scale", "replace"):
            assert not out[good]["invalid"], (good, out[good]["invalid"])
        assert any("image digest" in x for x in out["digest"]["invalid"]), out["digest"]
        assert any("capacity min 1 max 2" in x for x in out["cap"]["invalid"]), out["cap"]
        assert any("WAF mode" in x for x in out["waf"]["invalid"]), out["waf"]
        assert any("0 healthy targets" in x for x in out["healthy"]["invalid"]), out["healthy"]
        assert any("needs min 2 max 2" in x for x in out["replace1"]["invalid"]), out["replace1"]
        assert any("1 healthy targets at the start" in x and "expected 2" in x for x in out["replace_bad"]["invalid"]), out["replace_bad"]
        assert not out["replace_nowatch"]["invalid"] and any("no watcher record" in f for f in out["replace_nowatch"]["flags"]), out["replace_nowatch"]
        assert not any("not verified" in f for f in out["replace"]["flags"] + out["scale"]["flags"]), (out["replace"], out["scale"])
        assert not out["nostack"]["invalid"] and any("stack.json missing" in f for f in out["nostack"]["flags"])
        assert not out["nohealth"]["invalid"] and any("not verified" in f for f in out["nohealth"]["flags"])
        # a stack.json for the other variant is a mislabelled run
        mis = analyze.analyse_run(analyze.load_run(run(tmp, "mis", stack=good_stack(variant="fargate"))), ref)
        assert any("labelled ec2" in x for x in mis["invalid"]), mis


def test_reference_and_cpu_age():
    win = [dict(label="u10", start=0, end=300, users=1)]
    with tempfile.TemporaryDirectory() as tmp:
        old, new = "sha256:" + "a" * 64, "sha256:" + "c" * 64
        folders = [make_run(tmp, f"LOAD-ec2-ladder-u10-o{i}_x", "ec2", "ladder", 10, win, 1, steady_rows(300, 100, 0), planned=300,
                            extra={"stack.json": good_stack(image_digest=old, rds_class="db.t4g.small")}) for i in range(3)]
        folders += [make_run(tmp, f"LOAD-ec2-ladder-u10-n{i}_x", "ec2", "ladder", 10, win, 1, steady_rows(300, 100, 0), planned=300,
                             extra={"stack.json": good_stack(image_digest=new, rds_class="db.t4g.medium"),
                                    "cpu.json": dict(variant="ec2", model="Intel X", vcpus=2, ts_utc=iso(T0 - 30 * 3600))}) for i in range(4)]
        loaded = [analyze.load_run(d) for d in folders]
        values = analyze.campaign_values(loaded)
        assert values["image_digest"] == {old: 3, new: 4} and values["rds_class"] == {"db.t4g.medium": 4, "db.t4g.small": 3}, values
        # by majority the newer runs (the user's intended campaign after a resize) are the reference ...
        assert analyze.campaign_reference(loaded)["rds_class"] == "db.t4g.medium"
        # ... and the user can state the reference instead, which then wins over the majority
        ref = analyze.campaign_reference(loaded, {"rds_class": "db.t4g.small", "image_digest": old})
        assert ref["rds_class"] == "db.t4g.small" and ref["image_digest"] == old and ref["waf_login_action"] == "count"
        stated = [analyze.analyse_run(r, ref) for r in loaded]
        assert all(not x["invalid"] for x in stated[:3]) and all(any("RDS class" in i for i in x["invalid"]) for x in stated[3:])
        # a CPU model recorded 30 hours before the run is flagged as possibly another session's
        assert any("CPU model was recorded 30 h from this run" in f for f in stated[3]["flags"]), stated[3]["flags"]
        # the report lists the disagreement and uses the stated file
        refile = Path(tmp) / "reference.json"
        refile.write_text(json.dumps({"rds_class": "db.t4g.small", "image_digest": old}))
        out = subprocess.run([sys.executable, str(HERE / "analyze.py"), "--raw", tmp, "--reference", str(refile)],
                             capture_output=True, text=True, check=True).stdout
        assert "WARNING: runs disagree on the RDS class" in out and "stated by the user in reference.json" in out, out[:600]


def test_replace_error_window_is_bounded():
    errs = tuple(range(305, 331)) + (590,)  # the kill's errors, and one unrelated error long after recovery (550 s)
    with tempfile.TemporaryDirectory() as tmp:
        d = make_run(tmp, "RES-03-ec2-replace-r1_x", "ec2", "replace", None, [dict(label="all", start=0, end=600, users=100)], 36,
                     steady_rows(600, 100, 0, errors_at=errs), markers={"kill_at": 300}, planned=600, extra={
                         "kill.json": dict(ts_utc=iso(T0 + 300), unit_id="i-1"),
                         "targets.jsonl": "\n".join(json.dumps(x) for x in (dict(ts_utc=iso(T0 + 100), healthy=2),
                                                                           dict(ts_utc=iso(T0 + 330), healthy=1),
                                                                           dict(ts_utc=iso(T0 + 550), healthy=2)))})
        rep = analyze.analyse_run(analyze.load_run(d))["timings"]
        assert rep["error_window_s"] == 25.0 and rep["errors_after_kill"] == 26 and rep["errors_later"] == 1, rep
        # never recovered: every error up to the end of the run belongs to the window
        d2 = make_run(tmp, "RES-03-ec2-replace-r2_x", "ec2", "replace", None, [dict(label="all", start=0, end=600, users=100)], 36,
                      steady_rows(600, 100, 0, errors_at=errs), markers={"kill_at": 300}, planned=600, extra={
                          "kill.json": dict(ts_utc=iso(T0 + 300), unit_id="i-1"),
                          "targets.jsonl": "\n".join(json.dumps(x) for x in (dict(ts_utc=iso(T0 + 100), healthy=2),
                                                                            dict(ts_utc=iso(T0 + 330), healthy=1)))})
        rep2 = analyze.analyse_run(analyze.load_run(d2))["timings"]
        assert rep2["replacement_s"] is None and rep2["errors_after_kill"] == 27 and rep2["errors_later"] == 0, rep2


def test_database_figures_per_step():
    windows = [dict(label=f"u{u}", start=i * 100, end=(i + 1) * 100, users=u) for i, u in enumerate((1, 2, 4))]
    with tempfile.TemporaryDirectory() as tmp:
        d = make_run(tmp, "LOAD-ec2-saturation-r1_x", "ec2", "saturation", None, windows, 0, steady_rows(300, 100, 0), planned=300)
        write_series(d, "rds_cpu", [10, 12, 30, 35, 50])
        write_series(d, "rds_cpu_credit_balance", [90, 80, 70, 60, 50])
        out = analyze.analyse_run(analyze.load_run(d))
        assert [w["rds_cpu_max"] for w in out["windows"]] == [12, 35, 50], [w["rds_cpu_max"] for w in out["windows"]]
        assert [w["rds_credit_min"] for w in out["windows"]] == [80, 60, 50]


def test_cpu_model_record():
    import aws_capture
    assert aws_capture.parse_cpu("model name\t: Intel(R) Xeon(R) Platinum 8124M CPU @ 3.00GHz\n2\n") == ("Intel(R) Xeon(R) Platinum 8124M CPU @ 3.00GHz", 2)
    try:
        aws_capture.parse_cpu("nothing useful")
    except ValueError:
        pass
    else:
        raise AssertionError("a missing model line must be an error")
    real_sleep, aws_capture.time.sleep = aws_capture.time.sleep, lambda s: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # EC2: SSM Run Command on the lowest in-service instance
            kc = stubbed_clients()
            asg = {"AutoScalingGroups": [dict(AutoScalingGroupName="x", MinSize=1, MaxSize=1, DesiredCapacity=1, DefaultCooldown=300,
                                              AvailabilityZones=["a"], HealthCheckType="ELB", CreatedTime=datetime.now(timezone.utc),
                                              Instances=[dict(InstanceId="i-a", AvailabilityZone="a", LifecycleState="InService",
                                                              HealthStatus="Healthy", ProtectedFromScaleIn=False)])]}
            kc.stub("autoscaling").add_response("describe_auto_scaling_groups", asg)
            kc.stub("ssm").add_response("send_command", {"Command": {"CommandId": "11111111-2222-3333-4444-555555555555"}}, expected_params={
                "InstanceIds": ["i-a"], "DocumentName": "AWS-RunShellScript", "Parameters": {"commands": [aws_capture.CPU_COMMAND]}})
            kc.stub("ssm").add_response("get_command_invocation", {"Status": "Success", "StandardOutputContent": "model name\t: Intel X\n2\n"},
                                        expected_params={"CommandId": "11111111-2222-3333-4444-555555555555", "InstanceId": "i-a"})
            for stubber in kc.stubs.values():
                stubber.activate()
            path = Path(tmp) / "cpu-ec2.json"
            aws_capture.record_cpu(kc, "ec2", {"asg_name": "x"}, path)
            assert json.loads(path.read_text())["model"] == "Intel X" and json.loads(path.read_text())["vcpus"] == 2
            for stubber in kc.stubs.values():
                stubber.assert_no_pending_responses()
            # Fargate: a one-off task from the service's task definition, read back from its log stream
            outputs = dict(cluster_name="c", task_definition_arn="arn:aws:ecs:us-east-1:123456789012:task-definition/t:1",
                           subnet_ids=["subnet-a", "subnet-b"], security_group_ids={"alb": "sg-1", "app": "sg-2"}, log_group_name="/g/app")
            task = "arn:aws:ecs:us-east-1:123456789012:task/c/abc"
            kf = stubbed_clients()
            kf.stub("ecs").add_response("run_task", {"tasks": [{"taskArn": task}], "failures": []}, expected_params={
                "cluster": "c", "taskDefinition": outputs["task_definition_arn"], "launchType": "FARGATE", "count": 1,
                "networkConfiguration": {"awsvpcConfiguration": {"subnets": ["subnet-a", "subnet-b"], "securityGroups": ["sg-2"], "assignPublicIp": "ENABLED"}},
                "overrides": {"containerOverrides": [{"name": "web", "command": ["sh", "-c", aws_capture.CPU_COMMAND]}]}})
            kf.stub("ecs").add_response("describe_tasks", {"tasks": [{"lastStatus": "STOPPED", "containers": [{"exitCode": 0}]}], "failures": []},
                                        expected_params={"cluster": "c", "tasks": [task]})
            kf.stub("logs").add_response("get_log_events", {"events": [{"timestamp": 1, "message": "model name\t: AMD EPYC Y", "ingestionTime": 1},
                                                                       {"timestamp": 2, "message": "2", "ingestionTime": 2}]},
                                         expected_params={"logGroupName": "/g/app", "logStreamName": "web/web/abc"})
            for stubber in kf.stubs.values():
                stubber.activate()
            path = Path(tmp) / "cpu-fargate.json"
            aws_capture.record_cpu(kf, "fargate", outputs, path)
            assert json.loads(path.read_text())["model"] == "AMD EPYC Y"
            for stubber in kf.stubs.values():
                stubber.assert_no_pending_responses()
            # a task that could not start (image pull, permissions) names its reason instead of a parse error
            kb = stubbed_clients()
            kb.stub("ecs").add_response("run_task", {"tasks": [{"taskArn": task}], "failures": []})
            kb.stub("ecs").add_response("describe_tasks", {"tasks": [{"lastStatus": "STOPPED", "stoppedReason": "CannotPullContainerError"}], "failures": []})
            for stubber in kb.stubs.values():
                stubber.activate()
            try:
                aws_capture.record_cpu(kb, "fargate", outputs, Path(tmp) / "cpu-bad.json")
            except SystemExit as exc:
                assert "CannotPullContainerError" in str(exc), exc
            else:
                raise AssertionError("a task that did not run must stop the command with its reason")
            # the model reaches the report
            d = make_run(tmp, "LOAD-ec2-ladder-u10-m_x", "ec2", "ladder", 10, [dict(label="u10", start=0, end=300, users=1)], 1,
                         steady_rows(300, 100, 0), planned=300, extra={"cpu.json": dict(variant="ec2", model="Intel X", vcpus=2)})
            assert analyze.analyse_run(analyze.load_run(d))["cpu_model"]["model"] == "Intel X"
    finally:
        aws_capture.time.sleep = real_sleep


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    sys.exit(1 if failed else 0)
