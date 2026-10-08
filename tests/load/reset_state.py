#!/usr/bin/env python3
"""Put the shop's data back to how it was before the load tests: remove the load-test orders, return their stock.

  reset_state.py --target ec2     [--apply]  the AWS database, through the running variant A instance (over SSM)
  reset_state.py --target fargate [--apply]  the AWS database, through a one-off task of variant B's stack
  reset_state.py --target local   [--apply]  the Docker Compose database, for testing this script

Without --apply it is a DRY RUN: it only prints what it would do. The database is shared by both variants, so either
target resets the same data: use ec2 while A is up, fargate while B is up (for example after B's campaign, when A has
been taken down). Run it from the laptop with lab credentials. It runs the app image's own `manage.py shell`, so nothing
here edits the application.

What a checkout writes is only: an Order, its OrderItems, a lower Product.stock, and the emptied cart lines. So the
reset, in ONE transaction, adds each product's ordered units back to its stock, deletes those order lines and orders,
and empties the carts of the load-test accounts. It touches only accounts named <prefix>-... and only orders made by
the web checkout (no imported external id, an idempotency key present). The accounts stay: both variants use them.
"""
import argparse
import base64
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Runs inside the application's own `manage.py shell` (Django ORM). __APPLY__ and __PREFIX__ are filled in below.
RESET_CODE = r'''
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from cart.models import CartItem
from catalogue.models import Product
from orders.models import Order, OrderItem

APPLY, PREFIX = __APPLY__, "__PREFIX__"
users = get_user_model().objects.filter(username__startswith=PREFIX + "-")
orders = Order.objects.filter(owner__in=users, external_id__isnull=True, idempotency_key__isnull=False)
items = OrderItem.objects.filter(order__in=orders)
back = {r["product"]: r["units"] for r in items.values("product").annotate(units=Sum("quantity"))}
cart_lines = CartItem.objects.filter(cart__owner__in=users)
print("accounts:", users.count(), "| load orders:", orders.count(), "| order lines:", items.count(),
      "| units to put back:", sum(back.values()), "| products:", len(back), "| cart lines:", cart_lines.count())
for pid, units in sorted(back.items(), key=lambda kv: -kv[1])[:5]:
    p = Product.objects.get(pk=pid)
    print("  most ordered:", p.display_name, "| stock", p.stock, "->", p.stock + units)
if not APPLY:
    print("DRY RUN: nothing was changed. Run again with --apply to do it.")
else:
    with transaction.atomic():
        for pid, units in back.items():
            Product.objects.filter(pk=pid).update(stock=F("stock") + units)
        items.delete()
        orders.delete()
        cart_lines.delete()
    print("APPLIED. Left: load orders", orders.count(), "| order lines", items.count(), "| cart lines", cart_lines.count())
'''


def build_code(prefix, apply):
    """The shell code with its two settings filled in. The prefix is checked so it can never carry code."""
    if not re.fullmatch(r"[a-z0-9]+", prefix):
        sys.exit(f"STOP: prefix {prefix!r} must be lowercase letters and digits only (the accounts are <prefix>-a-0001)")
    return RESET_CODE.replace("__APPLY__", "True" if apply else "False").replace("__PREFIX__", prefix)


def shell_argument(code):
    """One shell-safe argument for `manage.py shell -c`: the code travels base64-encoded, so quoting cannot break it."""
    b64 = base64.b64encode(code.encode()).decode()
    return f"exec(__import__('base64').b64decode('{b64}').decode(), {{}})"


def run_local(code):
    result = subprocess.run(["docker", "compose", "exec", "-T", "web", "python", "manage.py", "shell", "-c", shell_argument(code)],
                            cwd=REPO / "src", capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode:
        sys.exit(f"STOP: the local shell failed:\n{result.stderr[-1500:]}")


def instance_id(autoscaling, asg_name):
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])["AutoScalingGroups"]
    live = [i["InstanceId"] for g in groups for i in g["Instances"] if i["LifecycleState"] == "InService"]
    if not live:
        sys.exit(f"STOP: no InService instance in {asg_name}. Bring variant A up first (the reset runs through it).")
    return live[0]


def run_ec2(code, asg_name):
    import aws_capture
    clients = aws_capture.Clients(REGION)
    asg_name = asg_name or aws_capture.stack_outputs("ec2", {}).get("asg_name")
    if not asg_name:
        sys.exit("STOP: no asg_name (terraform output in src/infrastructure/ec2 failed); give it with --asg-name")
    instance = instance_id(clients.get("autoscaling"), asg_name)
    ssm = clients.get("ssm")
    script = (f"export HOME=/root AWS_DEFAULT_REGION={REGION}; set -euo pipefail; "
              f"/usr/local/bin/app-job web python manage.py shell -c \"{shell_argument(code)}\"")
    print(f"Running on {instance} through Systems Manager ...")
    command_id = ssm.send_command(InstanceIds=[instance], DocumentName="AWS-RunShellScript",
                                  Parameters={"commands": [script], "executionTimeout": ["600"]})["Command"]["CommandId"]
    status, inv = "Pending", None
    for _ in range(120):
        time.sleep(3)
        try:
            inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        status = inv["Status"]
        if status in ("Success", "Failed", "Cancelled", "TimedOut"):
            break
    if inv is None:
        sys.exit("STOP: no result from Systems Manager within 6 minutes; check the command in the console")
    print(inv["StandardOutputContent"], end="")
    if inv["StandardErrorContent"]:
        print("--- stderr ---\n" + inv["StandardErrorContent"][-1500:])
    if status != "Success":
        sys.exit(f"STOP: the reset command ended as {status}")


def run_fargate(code, clients=None, outputs=None):
    """A one-off task from variant B's task definition (the web container's own settings), as jobs.sh does for its jobs."""
    import aws_capture
    outputs = outputs or aws_capture.stack_outputs("fargate", {})
    missing = [k for k in ("cluster_name", "task_definition_arn", "subnet_ids", "security_group_ids", "log_group_name") if not outputs.get(k)]
    if missing:
        sys.exit(f"STOP: the fargate stack outputs {missing} are not available (is the fargate stack up, and are you in a shell with lab credentials?)")
    print(f"Running a one-off task in cluster {outputs['cluster_name']} (a minute or two) ...")
    log = aws_capture.run_in_task(clients or aws_capture.Clients(REGION), outputs,
                                  f'python manage.py shell -c "{shell_argument(code)}"', timeout_s=600)
    print(log)
    if "DRY RUN" not in log and "APPLIED" not in log:
        sys.exit("STOP: the task stopped without printing the DRY RUN or APPLIED line; read its log in CloudWatch before trusting the result")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=["ec2", "fargate", "local"], required=True)
    ap.add_argument("--apply", action="store_true", help="really change the database (default: dry run)")
    ap.add_argument("--prefix", default=os.environ.get("LOADTEST_PREFIX", "loadtest"), help="account name prefix (default loadtest)")
    ap.add_argument("--asg-name", help="ec2 only: if terraform output cannot be read")
    args = ap.parse_args()
    code = build_code(args.prefix, args.apply)
    print(("APPLYING" if args.apply else "DRY RUN") + f" on {args.target}, accounts '{args.prefix}-*'\n")
    {"local": lambda: run_local(code), "ec2": lambda: run_ec2(code, args.asg_name), "fargate": lambda: run_fargate(code)}[args.target]()


if __name__ == "__main__":
    main()
