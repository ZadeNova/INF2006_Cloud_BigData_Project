#!/usr/bin/env python3
"""AWS side of a load run. Runs on the laptop with lab credentials; the load generator never needs them.

  aws_capture.py watch  --variant ec2|fargate --run-id ID            while a scale-out or replacement run is going
  aws_capture.py kill   --variant ec2|fargate --run-id ID [--yes]    replacement run: replace ONE unit, gracefully
  aws_capture.py cpu    --variant ec2|fargate                        once per variant per session: record the CPU model
  aws_capture.py export --variant ec2|fargate --run-id ID --run-dir out/ID   after the run, before any teardown

watch  polls target health every few seconds and logs every change with a UTC timestamp (aws-out/<ID>/targets.jsonl).
kill   is the only command here that stops anything of the stack's. It asks first, logs the UTC time to aws-out/<ID>/kill.json, then
       replaces one unit the same graceful way on both variants (ADR-017): A asks the Auto Scaling group to terminate an
       in-service instance (it is taken out of the load balancer and drained first, then replaced); B stops one running
       task (ECS drains it, then sends SIGTERM). The user runs it; no session does. A sudden crash is not tested.
cpu    reads the processor model on one instance (through SSM: one read-only command) or in a one-off Fargate task (a few
       seconds of billed compute and a log stream), and saves it to aws-out/cpu-<variant>.json; export adds it to each run's folder, so the report can state the hardware.
export copies the run folder into evidence/raw/<ID>/, adds the CloudWatch metrics for the run's window, alarm history,
       scaling activities (A) or ECS service events (B), and a stack.json describing what was tested, then redacts
       account IDs and public IPs in every text file. Refuses to overwrite an existing evidence folder.

Stack names come from `terraform output -json` in src/infrastructure/<variant> (ec2 today; fargate once its stack
exists). Any missing output can be given on the command line. Needs: boto3 (requirements.txt), terraform, lab credentials.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
NAME_PREFIX = "inf2006-grp21"
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".html", ".txt", ".md"}


def utc(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_utc():
    return datetime.now(timezone.utc)


class Clients:
    """boto3 clients on demand. The self-test swaps in clients wrapped by botocore's Stubber."""

    def __init__(self, region=REGION):
        self.region, self._clients = region, {}

    def get(self, service):
        if service not in self._clients:
            import boto3
            self._clients[service] = boto3.client(service, region_name=self.region)
        return self._clients[service]


def stack_outputs(variant, overrides):
    """Terraform outputs of the variant's stack, with command-line overrides on top."""
    outputs = {}
    try:
        raw = subprocess.run(["terraform", f"-chdir={REPO / 'src' / 'infrastructure' / variant}", "output", "-json"],
                             capture_output=True, text=True, check=True, timeout=60).stdout
        outputs = {k: v["value"] for k, v in json.loads(raw).items()}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"note: could not read terraform outputs for {variant} ({exc.__class__.__name__}); using command-line values only")
    outputs.update({k: v for k, v in overrides.items() if v})
    return outputs


def need(outputs, *keys):
    missing = [k for k in keys if not outputs.get(k)]
    if missing:
        sys.exit(f"STOP: stack output(s) {missing} not available; give them with the matching --option "
                 f"(a Fargate stack must output them; see the harness plan, section 10)")


def aws_out(run_id):
    path = HERE / "aws-out" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- watch -----------------------------------------------------------------------------------------------

def target_states(clients, tg_arn):
    resp = clients.get("elbv2").describe_target_health(TargetGroupArn=tg_arn)
    return {f"{d['Target']['Id']}:{d['Target'].get('Port', '')}": d["TargetHealth"]["State"]
            for d in resp["TargetHealthDescriptions"]}


def watch(clients, tg_arn, path, interval, stop_after=None):
    last, started = None, time.monotonic()
    with open(path, "a") as f:
        while stop_after is None or time.monotonic() - started < stop_after:
            states = target_states(clients, tg_arn)
            snapshot = dict(sorted(states.items()))
            if snapshot != last:
                healthy = sum(1 for s in snapshot.values() if s == "healthy")
                f.write(json.dumps(dict(ts_utc=utc(now_utc()), healthy=healthy, total=len(snapshot), states=snapshot)) + "\n")
                f.flush()
                print(f"{utc(now_utc())}  healthy {healthy}/{len(snapshot)}  {snapshot}", flush=True)
                last = snapshot
            time.sleep(interval)


# --- kill --------------------------------------------------------------------------------------------------

def pick_unit(clients, variant, outputs):
    if variant == "ec2":
        asg = clients.get("autoscaling").describe_auto_scaling_groups(AutoScalingGroupNames=[outputs["asg_name"]])["AutoScalingGroups"][0]
        live = sorted(i["InstanceId"] for i in asg["Instances"] if i["LifecycleState"] == "InService")
        return (live[0], len(live)) if live else (None, 0)
    tasks = clients.get("ecs").list_tasks(cluster=outputs["cluster_name"], serviceName=outputs["service_name"],
                                          desiredStatus="RUNNING")["taskArns"]
    tasks = sorted(tasks)
    return (tasks[0], len(tasks)) if tasks else (None, 0)


def kill(clients, variant, outputs, path, assume_yes):
    unit, count = pick_unit(clients, variant, outputs)
    if not unit:
        sys.exit("STOP: no running unit found")
    if count < 2:
        sys.exit(f"STOP: only {count} unit running; a replacement test needs two (pin min = max = 2 first)")
    print(f"About to {'terminate (gracefully, through the Auto Scaling group) EC2 instance' if variant == 'ec2' else 'stop ECS task'} {unit} ({count} running).")
    if not assume_yes and input("Type kill to go ahead: ").strip() != "kill":
        sys.exit("Not killed.")
    t0 = now_utc()
    if variant == "ec2":
        # Through the group, not EC2 directly: the group deregisters the instance from the target group and waits for the
        # deregistration delay before terminating, as ECS does for a stopped task. The group then launches a replacement.
        clients.get("autoscaling").terminate_instance_in_auto_scaling_group(InstanceId=unit, ShouldDecrementDesiredCapacity=False)
    else:
        clients.get("ecs").stop_task(cluster=outputs["cluster_name"], task=unit, reason="load test: replacement")
    t1 = now_utc()
    path.write_text(json.dumps(dict(ts_utc=utc(t0), api_returned_utc=utc(t1), variant=variant, unit_id=unit, units_before=count,
                                    mode="graceful"), indent=2))
    print(f"Killed at {utc(t0)} UTC. Keep `watch` running until two units are healthy again.")


# --- cpu ---------------------------------------------------------------------------------------------------

CPU_COMMAND = "grep -m1 'model name' /proc/cpuinfo; nproc"


def parse_cpu(text):
    """('Intel(R) ...', 2) from the output of CPU_COMMAND."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    model = next((ln.split(":", 1)[1].strip() for ln in lines if ln.startswith("model name")), None)
    vcpus = next((int(ln) for ln in reversed(lines) if ln.isdigit()), None)
    if not model:
        raise ValueError(f"no 'model name' line in: {text!r}")
    return model, vcpus


def run_on_instance(clients, instance_id, command, timeout_s=90):
    ssm = clients.get("ssm")
    cid = ssm.send_command(InstanceIds=[instance_id], DocumentName="AWS-RunShellScript",
                           Parameters={"commands": [command]})["Command"]["CommandId"]
    deadline = time.time() + timeout_s
    while True:
        inv = ssm.get_command_invocation(CommandId=cid, InstanceId=instance_id)
        if inv["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            break
        if time.time() > deadline:
            sys.exit(f"STOP: the command on {instance_id} did not finish in {timeout_s} s")
        time.sleep(3)
    if inv["Status"] != "Success":
        sys.exit(f"STOP: the command on {instance_id} ended {inv['Status']}")
    return inv["StandardOutputContent"]


def run_in_task(clients, outputs, command, timeout_s=300):
    """Run a one-off Fargate task from the stack's task definition with its own command; return what it logged."""
    ecs = clients.get("ecs")
    resp = ecs.run_task(cluster=outputs["cluster_name"], taskDefinition=outputs["task_definition_arn"], launchType="FARGATE", count=1,
                        networkConfiguration={"awsvpcConfiguration": {"subnets": list(outputs["subnet_ids"]),
                                                                     "securityGroups": [outputs["security_group_ids"]["app"]],
                                                                     "assignPublicIp": "ENABLED"}},
                        overrides={"containerOverrides": [{"name": "web", "command": ["sh", "-c", command]}]})
    if not resp.get("tasks"):
        sys.exit(f"STOP: ECS did not start a task: {resp.get('failures')}")
    arn = resp["tasks"][0]["taskArn"]
    deadline = time.time() + timeout_s
    while True:
        task = ecs.describe_tasks(cluster=outputs["cluster_name"], tasks=[arn])["tasks"][0]
        if task["lastStatus"] == "STOPPED":
            break
        if time.time() > deadline:
            sys.exit(f"STOP: the task {arn.rsplit('/', 1)[-1]} did not stop in {timeout_s} s")
        time.sleep(5)
    # An image-pull or permission failure ends the task with no exit code: say why instead of failing later on empty output.
    code = (task.get("containers") or [{}])[0].get("exitCode")
    if code != 0:
        sys.exit(f"STOP: the one-off task ended with exit code {code} ({task.get('stoppedReason', 'no reason given')})")
    time.sleep(5)  # log lines arrive a few seconds after the task stops
    events = clients.get("logs").get_log_events(logGroupName=outputs["log_group_name"],
                                                logStreamName=f"web/web/{arn.rsplit('/', 1)[-1]}")["events"]
    return "\n".join(e["message"] for e in events)


def record_cpu(clients, variant, outputs, path):
    if variant == "ec2":
        unit, _ = pick_unit(clients, "ec2", outputs)
        if not unit:
            sys.exit("STOP: no in-service instance to read the CPU model from")
        text = run_on_instance(clients, unit, CPU_COMMAND)
    else:
        text = run_in_task(clients, outputs, CPU_COMMAND)
    model, vcpus = parse_cpu(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(variant=variant, model=model, vcpus=vcpus, ts_utc=utc(now_utc())), indent=2))
    print(f"{variant}: {model} ({vcpus} vCPU). Saved to {path}")


# --- export ------------------------------------------------------------------------------------------------

def dim(name, value):
    return {"Name": name, "Value": value}


def metric_queries(variant, outputs, lb, tg, rds_id):
    """(file name, namespace, metric, dimensions, statistic) for every series the plan asks for."""
    alb, tgd = [dim("LoadBalancer", lb)], [dim("TargetGroup", tg), dim("LoadBalancer", lb)]
    q = [("alb_request_count", "AWS/ApplicationELB", "RequestCount", alb, "Sum"),
         ("alb_request_count_per_target", "AWS/ApplicationELB", "RequestCountPerTarget", tgd, "Sum"),
         ("alb_target_response_time_avg", "AWS/ApplicationELB", "TargetResponseTime", alb, "Average"),
         ("alb_target_response_time_p95", "AWS/ApplicationELB", "TargetResponseTime", alb, "p95"),
         ("alb_target_5xx", "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", alb, "Sum"),
         ("alb_target_4xx", "AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", alb, "Sum"),
         ("alb_healthy_hosts", "AWS/ApplicationELB", "HealthyHostCount", tgd, "Average"),
         ("alb_unhealthy_hosts", "AWS/ApplicationELB", "UnHealthyHostCount", tgd, "Average")]
    if variant == "ec2":
        asg = [dim("AutoScalingGroupName", outputs["asg_name"])]
        q += [("asg_desired", "AWS/AutoScaling", "GroupDesiredCapacity", asg, "Average"),
              ("asg_in_service", "AWS/AutoScaling", "GroupInServiceInstances", asg, "Average"),
              ("asg_pending", "AWS/AutoScaling", "GroupPendingInstances", asg, "Average"),
              ("asg_terminating", "AWS/AutoScaling", "GroupTerminatingInstances", asg, "Average"),
              ("ec2_cpu", "AWS/EC2", "CPUUtilization", asg, "Average"),
              ("ec2_cpu_max", "AWS/EC2", "CPUUtilization", asg, "Maximum")]
    else:
        svc = [dim("ClusterName", outputs["cluster_name"]), dim("ServiceName", outputs["service_name"])]
        q += [("ecs_cpu", "AWS/ECS", "CPUUtilization", svc, "Average"),
              ("ecs_cpu_max", "AWS/ECS", "CPUUtilization", svc, "Maximum"),
              ("ecs_memory", "AWS/ECS", "MemoryUtilization", svc, "Average")]  # no RunningTaskCount: Container Insights is off (ADR-015)
    if rds_id:
        db = [dim("DBInstanceIdentifier", rds_id)]
        q += [("rds_cpu", "AWS/RDS", "CPUUtilization", db, "Average"),
              ("rds_cpu_max_stat", "AWS/RDS", "CPUUtilization", db, "Maximum"),
              ("rds_connections", "AWS/RDS", "DatabaseConnections", db, "Average"),
              ("rds_freeable_memory", "AWS/RDS", "FreeableMemory", db, "Average"),
              ("rds_cpu_credit_balance", "AWS/RDS", "CPUCreditBalance", db, "Average"),
              ("rds_cpu_surplus_credit_balance", "AWS/RDS", "CPUSurplusCreditBalance", db, "Average"),
              ("rds_cpu_surplus_credits_charged", "AWS/RDS", "CPUSurplusCreditsCharged", db, "Sum")]
    acl = outputs.get("web_acl_name")
    if acl:
        waf = [dim("WebACL", acl), dim("Rule", acl.removesuffix("-waf") + "-login-rate"), dim("Region", REGION)]
        q += [("waf_login_counted", "AWS/WAFV2", "CountedRequests", waf, "Sum"),
              ("waf_login_blocked", "AWS/WAFV2", "BlockedRequests", waf, "Sum")]
    return q


def fetch_metrics(cw, queries, start, end):
    defs = [{"Id": f"m{i}", "ReturnData": True, "MetricStat": {
        "Metric": {"Namespace": ns, "MetricName": metric, "Dimensions": dims}, "Period": 60, "Stat": stat}}
        for i, (_, ns, metric, dims, stat) in enumerate(queries)]
    series = {f"m{i}": [] for i in range(len(queries))}
    token = None
    while True:
        kwargs = dict(MetricDataQueries=defs, StartTime=start, EndTime=end, ScanBy="TimestampAscending")
        if token:
            kwargs["NextToken"] = token
        resp = cw.get_metric_data(**kwargs)
        for r in resp["MetricDataResults"]:
            series[r["Id"]] += list(zip(r["Timestamps"], r["Values"]))
        token = resp.get("NextToken")
        if not token:
            return {queries[int(i[1:])][0]: sorted(v) for i, v in series.items()}


def write_series(folder, name, points):
    path = Path(folder) / "cloudwatch"
    path.mkdir(exist_ok=True)
    with open(path / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_epoch", "ts_utc", "value"])
        for ts, value in points:
            w.writerow([f"{ts.timestamp():.3f}", utc(ts), value])


def alarm_history(cw, prefixes, start, end):
    names = []
    for prefix in prefixes:
        names += [a["AlarmName"] for a in cw.describe_alarms(AlarmNamePrefix=prefix, AlarmTypes=["MetricAlarm"])["MetricAlarms"]]
    items = []
    for name in sorted(set(names)):
        token = None
        while True:
            kwargs = dict(AlarmName=name, AlarmTypes=["MetricAlarm"], HistoryItemType="StateUpdate", StartDate=start,
                          EndDate=end, ScanBy="TimestampAscending")
            if token:
                kwargs["NextToken"] = token
            resp = cw.describe_alarm_history(**kwargs)
            items += [dict(Timestamp=utc(i["Timestamp"]), AlarmName=i["AlarmName"], HistorySummary=i["HistorySummary"])
                      for i in resp["AlarmHistoryItems"]]
            token = resp.get("NextToken")
            if not token:
                break
    return sorted(items, key=lambda i: (i["Timestamp"], i["AlarmName"]))


def describe_stack(clients, variant, outputs, rds):
    info = dict(variant=variant, hostname=outputs.get("hostname"), image_digest=outputs.get("image_digest"),
                rds_class=rds.get("DBInstanceClass") if rds else None, rds_engine_version=rds.get("EngineVersion") if rds else None,
                rds_multi_az=rds.get("MultiAZ") if rds else None)
    if variant == "ec2":
        asg = clients.get("autoscaling").describe_auto_scaling_groups(AutoScalingGroupNames=[outputs["asg_name"]])["AutoScalingGroups"][0]
        info.update(min=asg["MinSize"], max=asg["MaxSize"], desired=asg["DesiredCapacity"])
        lt = asg.get("LaunchTemplate")
        if lt:
            versions = clients.get("ec2").describe_launch_template_versions(LaunchTemplateId=lt["LaunchTemplateId"], Versions=[lt["Version"]])
            info["instance_type"] = versions["LaunchTemplateVersions"][0]["LaunchTemplateData"].get("InstanceType")
    else:
        svc = clients.get("ecs").describe_services(cluster=outputs["cluster_name"], services=[outputs["service_name"]])["services"][0]
        task = clients.get("ecs").describe_task_definition(taskDefinition=svc["taskDefinition"])["taskDefinition"]
        info.update(desired=svc["desiredCount"], task_cpu=task.get("cpu"), task_memory_mb=task.get("memory"))
        scalable = clients.get("application-autoscaling").describe_scalable_targets(
            ServiceNamespace="ecs", ResourceIds=[f"service/{outputs['cluster_name']}/{outputs['service_name']}"])["ScalableTargets"]
        if scalable:
            info.update(min=scalable[0]["MinCapacity"], max=scalable[0]["MaxCapacity"])
    acl_name = outputs.get("web_acl_name")
    if acl_name:
        waf = clients.get("wafv2")
        acl = next((a for a in waf.list_web_acls(Scope="REGIONAL")["WebACLs"] if a["Name"] == acl_name), None)
        if acl:
            rules = waf.get_web_acl(Name=acl["Name"], Scope="REGIONAL", Id=acl["Id"])["WebACL"]["Rules"]
            rule = next((r for r in rules if r["Name"] == "login-rate-limit"), None)
            if rule:
                info["waf_login_action"] = next(iter(rule.get("Action", {})), None)
                info["waf_login_limit"] = rule["Statement"].get("RateBasedStatement", {}).get("Limit")
    return info


def redact_tree(folder):
    for path in Path(folder).rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text(errors="replace")
            clean = common.redact(text)
            if clean != text:
                path.write_text(clean)


def export(clients, variant, outputs, run_dir, evidence_root, pad_s=300):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run.json").read_text())
    run_id = meta["run_id"]
    dest = Path(evidence_root) / run_id
    if dest.exists():
        sys.exit(f"STOP: {dest} exists; raw evidence is never overwritten")
    timing = json.loads((run_dir / "timing.json").read_text())
    start = datetime.fromtimestamp(timing["start_epoch"], timezone.utc) - timedelta(seconds=pad_s)
    end = datetime.fromtimestamp(timing.get("end_epoch") or timing["start_epoch"] + meta["planned_seconds"], timezone.utc) + timedelta(seconds=pad_s)
    shutil.copytree(run_dir, dest)
    local = HERE / "aws-out" / run_id
    for name in ("targets.jsonl", "kill.json"):
        if (local / name).exists():
            shutil.copy(local / name, dest / name)
    if (HERE / "aws-out" / f"cpu-{variant}.json").exists():
        shutil.copy(HERE / "aws-out" / f"cpu-{variant}.json", dest / "cpu.json")
    warnings = []

    def section(label, fn):
        try:
            return fn()
        except Exception as exc:  # keep going: a partial export is far better than none
            warnings.append(f"{label}: {exc.__class__.__name__}: {exc}")
            print(f"WARNING {label}: {exc}")

    tg_arn = outputs["target_group_arn"]
    lb = section("load balancer lookup", lambda: clients.get("elbv2").describe_target_groups(TargetGroupArns=[tg_arn])["TargetGroups"][0]["LoadBalancerArns"][0].split("loadbalancer/", 1)[1])
    rds = section("rds lookup", lambda: next((d for d in clients.get("rds").describe_db_instances()["DBInstances"]
                                              if d["DBInstanceIdentifier"].startswith(NAME_PREFIX)), None))
    if lb:
        queries = metric_queries(variant, outputs, lb, tg_arn.split(":", 5)[5], rds["DBInstanceIdentifier"] if rds else None)
        series = section("cloudwatch metrics", lambda: fetch_metrics(clients.get("cloudwatch"), queries, start, end))
        for name, points in (series or {}).items():
            write_series(dest, name, points)
    prefix = f"TargetTracking-{outputs['asg_name']}" if variant == "ec2" else \
        f"TargetTracking-service/{outputs.get('cluster_name')}/{outputs.get('service_name')}"
    history = section("alarm history", lambda: alarm_history(clients.get("cloudwatch"), [prefix, f"{NAME_PREFIX}-{variant}-"], start, end))
    (dest / "alarm_history.json").write_text(json.dumps(history or [], indent=2))
    if variant == "ec2":
        acts = section("scaling activities", lambda: clients.get("autoscaling").describe_scaling_activities(
            AutoScalingGroupName=outputs["asg_name"], MaxRecords=100)["Activities"]) or []
        (dest / "scaling_activities.json").write_text(json.dumps(sorted(
            [dict(Description=a["Description"], StartTime=utc(a["StartTime"]), EndTime=utc(a["EndTime"]) if a.get("EndTime") else None,
                  Cause=a.get("Cause"), StatusCode=a["StatusCode"]) for a in acts if start <= a["StartTime"] <= end],
            key=lambda a: a["StartTime"]), indent=2))
    else:
        svc = section("ecs service events", lambda: clients.get("ecs").describe_services(
            cluster=outputs["cluster_name"], services=[outputs["service_name"]])["services"][0])
        (dest / "ecs_events.json").write_text(json.dumps(sorted(
            [dict(createdAt=utc(e["createdAt"]), message=e["message"]) for e in (svc or {}).get("events", []) if start <= e["createdAt"] <= end],
            key=lambda e: e["createdAt"]), indent=2))
    stack = section("stack description", lambda: describe_stack(clients, variant, outputs, rds)) or {}
    stack.update(export_utc=utc(now_utc()), window_start_utc=utc(start), window_end_utc=utc(end), export_warnings=warnings)
    (dest / "stack.json").write_text(json.dumps(stack, indent=2))
    redact_tree(dest)
    print(f"Exported to {dest} ({len(warnings)} warning(s)). Review it, then run analyze.py.")
    return dest, warnings


# --- command line ------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["watch", "kill", "export", "cpu"])
    ap.add_argument("--variant", choices=["ec2", "fargate"], required=True)
    ap.add_argument("--run-id", help="run id, as printed by run.py (not needed for cpu)")
    ap.add_argument("--run-dir", help="export: the run folder copied back from the generator")
    ap.add_argument("--evidence-root", default=str(REPO / "evidence" / "raw"))
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--yes", action="store_true")
    for opt in ("target-group-arn", "asg-name", "web-acl-name", "cluster-name", "service-name", "image-digest", "hostname"):
        ap.add_argument(f"--{opt}")
    args = ap.parse_args()
    overrides = {k: getattr(args, k) for k in ("target_group_arn", "asg_name", "web_acl_name", "cluster_name", "service_name",
                                               "image_digest", "hostname")}
    outputs = stack_outputs(args.variant, overrides)
    clients = Clients()
    try:
        identity = clients.get("sts").get_caller_identity()["Arn"]  # fails early if the lab credentials expired
    except Exception as exc:
        sys.exit(f"STOP: no working AWS credentials ({exc.__class__.__name__}); refresh the lab credentials")
    print(f"AWS identity: {common.redact(identity)}")
    if args.command in ("watch", "kill", "export") and not args.run_id:
        sys.exit(f"STOP: {args.command} needs --run-id")
    if args.command == "cpu":
        need(outputs, *(["asg_name"] if args.variant == "ec2" else ["cluster_name", "task_definition_arn", "subnet_ids", "security_group_ids", "log_group_name"]))
        record_cpu(clients, args.variant, outputs, HERE / "aws-out" / f"cpu-{args.variant}.json")
    elif args.command == "watch":
        need(outputs, "target_group_arn")
        watch(clients, outputs["target_group_arn"], aws_out(args.run_id) / "targets.jsonl", args.interval)
    elif args.command == "kill":
        need(outputs, *(["asg_name"] if args.variant == "ec2" else ["cluster_name", "service_name"]))
        kill(clients, args.variant, outputs, aws_out(args.run_id) / "kill.json", args.yes)
    else:
        if not args.run_dir:
            sys.exit("STOP: export needs --run-dir")
        need(outputs, "target_group_arn", *(["asg_name"] if args.variant == "ec2" else ["cluster_name", "service_name"]))
        export(clients, args.variant, outputs, args.run_dir, args.evidence_root)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
