"""The AWS capability probe classifies results, keeps personal identifiers out of its record and survives a slow call; it calls no AWS API here."""
import json
import subprocess
from types import SimpleNamespace

import pytest

from tools import aws_capability_check as probe

DENIED = "An error occurred (AccessDenied) when calling the ListRoles operation: User is not authorized"
DRY_RUN_OK = "An error occurred (DryRunOperation) when calling the RunInstances operation: Request would have succeeded"


@pytest.mark.parametrize("returncode, stderr, expected", [
    (0, "", "allowed"),
    (254, DRY_RUN_OK, "allowed"),
    (254, DENIED, "denied"),
    (254, "An error occurred (UnauthorizedOperation) when calling CreateVpc", "denied"),
    (255, "Could not connect to the endpoint URL", "error"),
    (255, "Unable to locate credentials. You can configure credentials by running aws configure", "credentials"),
    (254, "An error occurred (ExpiredToken) when calling GetCallerIdentity", "expired"),
])
def test_classify(returncode, stderr, expected):
    assert probe.classify(returncode, stderr) == expected


def fake_runner(calls, deny=()):
    """Answer each probe with canned data, or AccessDenied for the services named in deny."""
    def runner(args):
        calls.append(args)
        if args[0] in deny:
            return 254, "", DENIED
        if args[:2] == ["sts", "get-caller-identity"]:
            return 0, json.dumps({"Account": "123456789012", "Arn": "arn:aws:sts::123456789012:assumed-role/voclabs/someone@example.com"}), ""
        if args[:2] == ["ssm", "get-parameter"]:
            return 0, json.dumps({"Parameter": {"Value": "ami-0abc"}}), ""
        if "--dry-run" in args:
            return 254, "", DRY_RUN_OK
        return 254, "", "An error occurred (ValidationError) when calling Something: not summarised in this test"
    return runner


def test_identity_is_redacted_and_the_ami_feeds_the_launch_dry_run():
    calls = []
    results, fatal = probe.run_probes(fake_runner(calls))
    record = probe.render(results, "us-east-1", probe.datetime.datetime(2026, 9, 25, 9, 0))
    assert fatal is None
    assert "123456789012" not in record and "someone@example.com" not in record
    assert "account ending 9012, principal assumed-role/voclabs" in record
    launch = next(call for call in calls if call[:2] == ["ec2", "run-instances"])
    assert launch[launch.index("--image-id") + 1] == "ami-0abc"


def test_a_denied_service_is_reported_not_hidden():
    results, _ = probe.run_probes(fake_runner([], deny=("acm", "secretsmanager")))
    outcomes = {check: outcome for _, check, outcome, _ in results}
    assert outcomes["ACM certificates (list)"] == "denied"
    assert outcomes["Secrets Manager (list)"] == "denied"
    assert outcomes["create a VPC (dry run)"] == "allowed"


def test_the_launch_dry_run_is_skipped_when_the_ami_cannot_be_found():
    calls = []
    results, _ = probe.run_probes(fake_runner(calls, deny=("ssm",)))
    assert not any(call[:2] == ["ec2", "run-instances"] for call in calls)
    assert next(o for _, c, o, _ in results if c == "launch an instance (dry run)") == "skipped"


def test_probing_stops_on_expired_credentials():
    def expired(args):
        return 254, "", "An error occurred (ExpiredToken) when calling GetCallerIdentity"
    results, fatal = probe.run_probes(expired)
    assert fatal == "expired" and results == []


def test_no_probe_can_change_anything():
    """Every call is a list/describe/get, or an EC2 dry run; none may create, modify or delete."""
    verbs = ("get-", "describe-", "list-")
    for _, _, build, _ in probe.PROBES:
        args = build({"ami": "ami-0abc", "account": "123456789012"})
        assert args[1].startswith(verbs) or "--dry-run" in args, args


@pytest.mark.parametrize("text, secret", [
    ("arn:aws:iam::123456789012:root", "123456789012"),
    ("User: arn:aws:sts::1:assumed-role/voclabs/user2345678=Jane_Doe is not authorized", "Jane_Doe"),
    ("User: arn:aws:iam::1:user/JaneDoe is not authorized", "JaneDoe"),
    ("requested by someone@example.com", "someone@example.com"),
])
def test_redact_removes_each_kind_of_identifier(text, secret):
    assert secret not in probe.redact(text)


def test_an_error_is_redacted_before_it_is_cut_to_length():
    # The account number starts at column 149, so a 160-character cut leaves 11 digits: too few for the
    # account pattern, so cutting first would leak almost the whole number.
    line = "x" * 135 + " arn:aws:sts::123456789012:assumed-role/voclabs/user2345678=Jane_Doe is not authorized"

    def runner(args):
        return 254, "", f"An error occurred (AccessDenied)\n{line}"

    results, _ = probe.run_probes(runner)
    record = probe.render(results, "us-east-1", probe.datetime.datetime(2026, 9, 25, 9, 0))
    assert "1234567" not in record and "Jane_Doe" not in record and "user2345678" not in record


def test_a_pipe_or_newline_in_a_detail_cannot_break_the_table():
    record = probe.render([("Area2", "check", "error", "a | b\nc")], "us-east-1", probe.datetime.datetime(2026, 9, 25, 9, 0))
    row = next(line for line in record.splitlines() if line.startswith("| Area2"))
    assert row.replace("\\|", "").count("|") == 5      # four columns, five separators
    assert "a \\| b c" in row


def test_a_call_that_times_out_is_recorded_and_the_run_continues(monkeypatch):
    def slow_iam(command, **kwargs):
        if "iam" in command:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return SimpleNamespace(returncode=254, stdout="", stderr=DENIED)

    monkeypatch.setattr(probe.subprocess, "run", slow_iam)

    results, fatal = probe.run_probes(probe.make_runner(["aws"], timeout=45))

    assert fatal is None and len(results) == len(probe.PROBES)      # nothing after the timeouts was lost
    timed_out = [(outcome, detail) for area, _, outcome, detail in results if area == "IAM"]
    assert len(timed_out) == 2
    assert all(outcome == "error" and "Timed out after 45 seconds" in detail for outcome, detail in timed_out)
