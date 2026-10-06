#!/usr/bin/env bash
# What is installed, what is running and what to do next. Read-only: it creates, changes and deletes nothing.
#
#   scripts/status.sh
#
# Start here. It checks the tools, whether your lab credentials work, what each Terraform folder has built
# (from its state file), and, when credentials work, whether AWS agrees. The last lines say what to run next.
set -uo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PREFIX="inf2006-grp21"
NEXT=()
ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  WARN  %s\n' "$*"; }
bad()  { printf '  MISSING  %s\n' "$*"; }

echo "Tools"
missing=0
for t in terraform aws jq curl openssl git python3; do
  if command -v "$t" >/dev/null; then ok "$t"; else bad "$t is not installed"; missing=1; fi
done
if command -v terraform >/dev/null; then
  tv="$(terraform version -json 2>/dev/null | jq -r .terraform_version 2>/dev/null)"
  if [ -n "$tv" ] && [ "$(printf '%s\n1.10.0\n' "$tv" | sort -V | head -1)" = 1.10.0 ]; then ok "terraform $tv (1.10 or newer needed)"
  else bad "terraform ${tv:-?} is older than 1.10"; missing=1; fi
fi
command -v docker >/dev/null && ok "docker (needed only to build the app image)" || warn "docker not installed: needed only to build the app image"
[ "$missing" = 1 ] && NEXT+=("Install the missing tools (see 'Tools and credentials' in src/infrastructure/README.md).")

echo; echo "Lab credentials"
CREDS=0
if command -v aws >/dev/null; then
  acct="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" && [ -n "$acct" ] && CREDS=1
fi
if [ "$CREDS" = 1 ]; then ok "working (account ending ${acct: -4}, region $REGION)"
else bad "no working credentials in this shell (they expire after about 4 hours)"; NEXT+=("Run labcreds and paste the AWS Details block, then run this again.")
fi

# resources recorded in a folder's state file (0 if there is none)
count_state() {
  local f="$INFRA/$1/terraform.tfstate"
  [ -s "$f" ] && jq '[.resources[]? | select(.mode=="managed") | (.instances | length)] | add // 0' "$f" 2>/dev/null || echo 0
}
live_alb() {   # prints the state of a stack's load balancer, or nothing
  aws elbv2 describe-load-balancers --region "$REGION" --names "$PREFIX-$1-alb" --query 'LoadBalancers[0].State.Code' --output text 2>/dev/null
}
live_loadgen() {
  aws ec2 describe-instances --region "$REGION" --filters "Name=tag:Stack,Values=loadgen" "Name=instance-state-name,Values=pending,running" \
    --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null
}

echo; echo "Shared base (database, DNS, certificate, registry, secrets)"
BASE_N="$(count_state base)"
if [ "$BASE_N" -gt 0 ]; then ok "applied ($BASE_N resources in state)"; else bad "not applied"; NEXT+=("First-time setup: scripts/up.sh base"); fi
[ -f "$INFRA/base/terraform.tfvars" ] && ok "base/terraform.tfvars present" || warn "base/terraform.tfvars missing (scripts/up.sh base creates it)"

echo; echo "Stacks"
UP_ANY=0
for s in ec2 fargate loadgen; do
  n="$(count_state "$s")"; line="$(printf '%-8s' "$s")"
  if [ "$n" -gt 0 ]; then
    UP_ANY=1; msg="UP    $n resources in state"
    if [ "$CREDS" = 1 ]; then
      if [ "$s" = loadgen ]; then [ -n "$(live_loadgen)" ] && msg="$msg; instance running" || msg="$msg; WARNING no running instance found"
      else a="$(live_alb "$s")"; [ -n "$a" ] && [ "$a" != None ] && msg="$msg; load balancer $a" || msg="$msg; WARNING no load balancer found"; fi
    fi
    printf '  %s %s\n' "$line" "$msg"
    [ "$s" != loadgen ] && NEXT+=("$s is up and costs money: when you stop, run scripts/down.sh $s")
    [ "$s" = loadgen ] && NEXT+=("loadgen is up and costs money: when the test session ends, run scripts/down.sh loadgen")
  else
    msg="DOWN"
    if [ "$CREDS" = 1 ]; then
      if [ "$s" = loadgen ]; then [ -n "$(live_loadgen)" ] && msg="DOWN in state, BUT an instance is running: it is billing and Terraform does not know it"
      else a="$(live_alb "$s")"; [ -n "$a" ] && [ "$a" != None ] && msg="DOWN in state, BUT a load balancer exists: it is billing and Terraform does not know it"; fi
    fi
    printf '  %s %s\n' "$line" "$msg"
  fi
done

echo; echo "App image"
for s in ec2 fargate; do
  f="$INFRA/$s/image.auto.tfvars"
  if [ -f "$f" ]; then ok "$s runs $(sed -n 's/^image_tag *= *"\(.*\)".*/\1/p' "$f")"; else warn "$s has no image selected (scripts/up.sh $s pushes one)"; fi
done

echo; echo "Next"
if [ "$BASE_N" -gt 0 ] && [ "$CREDS" = 1 ] && [ "$missing" = 0 ] && [ "$UP_ANY" = 0 ]; then
  NEXT+=("Start variant A: scripts/up.sh ec2     Start variant B: scripts/up.sh fargate")
fi
if [ "${#NEXT[@]}" -eq 0 ]; then echo "  Nothing to do. Check a running shop with scripts/smoke.sh ec2 (or fargate)."
else for n in "${NEXT[@]}"; do echo "  - $n"; done; fi
