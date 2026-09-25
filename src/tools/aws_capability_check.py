#!/usr/bin/env python3
"""Read-only AWS capability probe for the lab account (plan item B4).

Run it with lab credentials configured (``aws configure`` or the lab's exported
AWS_* variables). It calls only list/describe APIs and EC2 ``--dry-run`` checks,
so it creates no resources, and it writes a Markdown record of the calls
that succeeded. Read access is not deployment permission. Account numbers are redacted. It needs only the AWS CLI and
the standard library.

    python3 src/tools/aws_capability_check.py --region us-east-1 --output evidence/aws-capability-record.md
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys

CALL_TIMEOUT = 45  # seconds per AWS CLI call
DENIED = ("AccessDenied", "UnauthorizedOperation", "not authorized", "AuthorizationError")
FATAL = {
    "credentials": ("Unable to locate credentials", "NoCredentialProviders"),
    "expired": ("ExpiredToken", "RequestExpired", "token included in the request is expired"),
}


def classify(returncode, stderr):
    """Return allowed, denied, error, or a fatal reason (credentials, expired)."""
    for reason, needles in FATAL.items():
        if any(needle in stderr for needle in needles):
            return reason
    if "DryRunOperation" in stderr:
        return "allowed"  # an EC2 dry run that reports it would have succeeded
    if returncode == 0:
        return "allowed"
    if any(needle in stderr for needle in DENIED):
        return "denied"
    return "error"


# Error messages name the caller. In lab accounts the session name of an assumed role, the name of an IAM user
# and the email-like strings that often sit in them can identify a student, and this record is meant for evidence/.
SESSION_NAME = re.compile(r"(assumed-role/[^/\s]+/)[^\s:\"',]+")
IAM_USER_NAME = re.compile(r"(:user/)[^\s:\"',]+")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def redact(text):
    text = re.sub(r"\b\d{12}\b", "<account>", text)
    text = SESSION_NAME.sub(r"\1<session>", text)
    text = IAM_USER_NAME.sub(r"\1<user>", text)
    return EMAIL.sub("<email>", text)


def names(items, key, limit=8):
    found = [item[key] for item in items if key in item][:limit]
    return ", ".join(found) if found else "none"


# Each probe: (area, check, args builder taking ctx or None to skip, summariser taking data and ctx).
def _identity(data, ctx):
    ctx["account"] = data["Account"]
    tail = data["Arn"].split(":")[-1].split("/")
    principal = "/".join(tail[:2]) if tail[0] == "assumed-role" else tail[0]  # never print a personal user name
    return f"account ending {data['Account'][-4:]}, principal {principal}"


def _ami(data, ctx):
    ctx["ami"] = max(data["Images"], key=lambda image: image["CreationDate"])["ImageId"]
    return "found"


PROBES = [
    ("Identity", "sts get-caller-identity", lambda c: ["sts", "get-caller-identity"], _identity),
    ("Network", "availability zones (need 2)", lambda c: ["ec2", "describe-availability-zones"],
     lambda d, c: f"{len(d['AvailabilityZones'])} zones"),
    ("Network", "VPCs", lambda c: ["ec2", "describe-vpcs"],
     lambda d, c: f"{len(d['Vpcs'])} VPCs, default VPC {'present' if any(v.get('IsDefault') for v in d['Vpcs']) else 'absent'}"),
    ("Network", "create a VPC (dry run)", lambda c: ["ec2", "create-vpc", "--cidr-block", "10.250.0.0/16", "--dry-run"],
     lambda d, c: "permitted"),
    ("Compute", "instance types offered",
     lambda c: ["ec2", "describe-instance-type-offerings", "--location-type", "region", "--filters",
                "Name=instance-type,Values=t3.micro,t3.small,t3.medium"],
     lambda d, c: names(d["InstanceTypeOfferings"], "InstanceType")),
    ("Compute", "Amazon Linux 2023 AMI lookup (EC2 images)",
     lambda c: ["ec2", "describe-images", "--owners", "amazon", "--filters",
                "Name=name,Values=al2023-ami-2023.*-kernel-*-x86_64",
                "Name=state,Values=available", "Name=architecture,Values=x86_64"], _ami),
    ("Compute", "launch an instance (dry run)",
     lambda c: ["ec2", "run-instances", "--image-id", c["ami"], "--instance-type", "t3.micro", "--dry-run"] if "ami" in c else None,
     lambda d, c: "permitted"),
    ("Compute", "running on-demand standard vCPU quota",
     lambda c: ["service-quotas", "get-service-quota", "--service-code", "ec2", "--quota-code", "L-1216C47A"],
     lambda d, c: f"{d['Quota']['Value']:g} vCPUs"),
    ("Load balancing", "ALBs (list)", lambda c: ["elbv2", "describe-load-balancers"],
     lambda d, c: f"{len(d['LoadBalancers'])} existing"),
    ("Scaling", "Auto Scaling groups (list)", lambda c: ["autoscaling", "describe-auto-scaling-groups"],
     lambda d, c: f"{len(d['AutoScalingGroups'])} existing"),
    ("Database", "RDS instances (list)", lambda c: ["rds", "describe-db-instances"],
     lambda d, c: f"{len(d['DBInstances'])} existing"),
    ("Database", "default PostgreSQL engine version", lambda c: ["rds", "describe-db-engine-versions", "--engine", "postgres", "--default-only"],
     lambda d, c: names(d["DBEngineVersions"], "EngineVersion")),
    ("Storage", "S3 buckets (list)", lambda c: ["s3api", "list-buckets"],
     lambda d, c: f"{len(d.get('Buckets', []))} existing"),
    ("IAM", "instance profiles (list)", lambda c: ["iam", "list-instance-profiles"],
     lambda d, c: names(d["InstanceProfiles"], "InstanceProfileName")),
    ("IAM", "roles (list, service-linked hidden)", lambda c: ["iam", "list-roles"],
     lambda d, c: names([r for r in d["Roles"] if not r["Path"].startswith("/aws-service-role/")], "RoleName")),
    ("Secrets", "Secrets Manager (list)", lambda c: ["secretsmanager", "list-secrets"],
     lambda d, c: f"{len(d['SecretList'])} existing"),
    ("HTTPS", "ACM certificates (list)", lambda c: ["acm", "list-certificates"],
     lambda d, c: f"{len(d['CertificateSummaryList'])} existing"),
    ("HTTPS", "Route 53 hosted zones (list)", lambda c: ["route53", "list-hosted-zones"],
     lambda d, c: f"{len(d['HostedZones'])} existing"),
    ("Registry", "ECR repositories (list)", lambda c: ["ecr", "describe-repositories"],
     lambda d, c: f"{len(d['repositories'])} existing"),
    ("Audit", "CloudTrail trails (list)", lambda c: ["cloudtrail", "list-trails"],
     lambda d, c: f"{len(d['Trails'])} existing"),
    ("Protection", "regional WAF web ACLs (list)", lambda c: ["wafv2", "list-web-acls", "--scope", "REGIONAL"],
     lambda d, c: f"{len(d['WebACLs'])} existing"),
    ("Scheduling", "EventBridge Scheduler schedules (list)", lambda c: ["scheduler", "list-schedules"],
     lambda d, c: f"{len(d['Schedules'])} existing"),
    ("Inference", "Lambda functions (list)", lambda c: ["lambda", "list-functions"],
     lambda d, c: f"{len(d['Functions'])} existing"),
    ("Monitoring", "CloudWatch log groups (list)", lambda c: ["logs", "describe-log-groups", "--limit", "5"],
     lambda d, c: f"{len(d['logGroups'])} shown"),
    ("Monitoring", "CloudWatch alarms (list)", lambda c: ["cloudwatch", "describe-alarms", "--max-items", "5"],
     lambda d, c: f"{len(d['MetricAlarms'])} shown"),
    ("Monitoring", "SNS topics (list)", lambda c: ["sns", "list-topics"],
     lambda d, c: f"{len(d['Topics'])} existing"),
    ("Cost", "AWS Budgets (list)",
     lambda c: ["budgets", "describe-budgets", "--account-id", c["account"]] if "account" in c else None,
     lambda d, c: f"{len(d.get('Budgets', []))} existing"),
]


def run_probes(runner):
    """Run every probe through runner(args) -> (returncode, stdout, stderr). Return (results, fatal)."""
    ctx, results = {}, []
    for area, check, build, summarise in PROBES:
        args = build(ctx)
        if args is None:
            results.append((area, check, "skipped", "needs an earlier check that did not succeed"))
            continue
        returncode, stdout, stderr = runner(args)
        outcome = classify(returncode, stderr)
        if outcome in FATAL:
            return results, outcome
        detail = ""
        if outcome == "allowed":
            try:
                detail = summarise(json.loads(stdout) if stdout.strip() else {}, ctx)
            except (KeyError, IndexError, ValueError, TypeError):
                detail = "call succeeded; response not summarised"
        else:
            detail = redact(stderr.strip().splitlines()[-1])[:160] if stderr.strip() else ""
        results.append((area, check, outcome, redact(detail)))
    return results, None


def cell(text):
    """One table cell: no newline and no unescaped pipe, either of which would break the Markdown table."""
    return " ".join(str(text).split()).replace("|", "\\|")


def render(results, region, when):
    lines = [
        "# AWS capability record",
        "",
        f"Generated {when:%Y-%m-%d %H:%M} UTC. Region: `{region}`. Read-only probe: list/describe calls and EC2 dry runs only; nothing was created.",
        "",
        "| Area | Check | Result | Detail |",
        "|---|---|---|---|",
    ]
    lines += [f"| {area} | {check} | {outcome} | {cell(detail)} |" for area, check, outcome, detail in results]
    lines += [
        "",
        "## How to read this",
        "",
        "- **allowed** means the call succeeded (or the EC2 dry run said it would have). **denied** means the lab's policy refused it. **error** is anything else, so read the detail.",
        "- Listing a service proves its API is reachable, **not** that creating it is permitted. A Terraform plan also does not prove creation permission. Verify actual authorised console creation, then Terraform reproduction, and deployed behaviour; dry runs cover only the request tested.",
        "- Remaining balance is not available from the API. Read it from the lab page and record it here: `USD ____` on `____`.",
        "- Role names are discovery only: record the intended EC2 instance profile, Lambda execution role and Scheduler invocation role. Verify trust policies, least-privilege resource access and iam:PassRole for the deploying principal; listing roles proves none of these. Reference permitted lab roles where required.",
        "",
        "## Decisions this feeds",
        "",
        "- **HTTPS:** certificate listing is not issuance/import permission or hostname ownership. A test certificate needs permitted import, a matching hostname and explicit client trust; it is not a guaranteed fallback. See `docs/plans/cloud-independent-prep.md` (B4).",
        "- **Image source:** ECR is selected. Verify repository creation, image push and instance pull permissions separately; list success does not prove them. Resolve denied access before deployment.",
        "- **Secrets:** Secrets Manager is selected for database credentials and the shared `DJANGO_SECRET_KEY`, retrieved through least-privilege runtime roles. Unavailable secret storage or retrieval is a deployment blocker; never put plaintext secrets in user data or launch templates. List success does not prove retrieval permission.",
        "- **Management access:** Systems Manager (SSM) is not selected. Agree a secure lab-supported administration method with the infrastructure owner.",
        "- **Integration:** record ECR, SNS, CloudTrail, WAF, Scheduler and Lambda creation/configuration and role checks separately. Offline training exists; saved-model inference and scheduled Lambda integration are not implemented. Actual notifications, audit events, WAF enforcement and scheduled inference need deployed verification.",
        "",
    ]
    return "\n".join(lines)


def make_runner(base, timeout=CALL_TIMEOUT):
    """Return runner(args) -> (returncode, stdout, stderr). A call that times out is an error result, not a crash."""
    def runner(call):
        try:
            done = subprocess.run(base + call, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124, "", f"Timed out after {timeout} seconds"
        return done.returncode, done.stdout, done.stderr
    return runner


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", required=True, help="the lab's region, for example us-east-1")
    parser.add_argument("--profile", help="AWS CLI profile (optional)")
    parser.add_argument("--output", help="write the Markdown record here instead of standard output")
    args = parser.parse_args(argv)
    if shutil.which("aws") is None:
        sys.exit("The AWS CLI (aws) is not installed or not on PATH.")

    base = ["aws", "--region", args.region, "--output", "json", "--no-cli-pager"]
    if args.profile:
        base += ["--profile", args.profile]

    results, fatal = run_probes(make_runner(base))
    if fatal == "credentials":
        sys.exit("No AWS credentials found. Configure them (aws configure, or export the lab's AWS_* variables) and retry.")
    if fatal == "expired":
        sys.exit("The AWS session token has expired. Refresh the lab credentials and retry.")
    record = render(results, args.region, datetime.datetime.now(datetime.timezone.utc))
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(record)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(record)


if __name__ == "__main__":
    main()
