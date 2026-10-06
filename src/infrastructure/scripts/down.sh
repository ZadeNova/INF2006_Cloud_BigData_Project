#!/usr/bin/env bash
# Take a stack down and confirm nothing billing is left behind it (ADR-010). base/ (database, zone, certificate,
# registry, secrets) stays up; destroy it only at final teardown (README, "Final teardown").
#
#   scripts/down.sh <ec2|fargate|loadgen>
#
# Terraform lists everything it will destroy and asks you to type yes. Afterwards the script lists any load balancer,
# instance, ECS cluster or NAT gateway still left; every list should be empty. Needs: lab credentials, aws, terraform.
set -euo pipefail
INFRA="$(cd "$(dirname "$0")/.." && pwd)"
STACK="${1:-}"; REGION="${AWS_DEFAULT_REGION:-us-east-1}"
case "$STACK" in ec2|fargate|loadgen) ;; *) echo "usage: $0 <ec2|fargate|loadgen>   (scripts/status.sh shows what is up)" >&2; exit 2 ;; esac
aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 || { echo "STOP: no working lab credentials (run labcreds)" >&2; exit 1; }

terraform -chdir="$INFRA/$STACK" destroy -input=true
echo; echo "== Leftovers (each list should be empty) =="
echo "load balancers:"; aws elbv2 describe-load-balancers --region "$REGION" --query "LoadBalancers[?contains(LoadBalancerName,'inf2006-grp21-$STACK')].LoadBalancerName" --output text
echo "instances:"; aws ec2 describe-instances --region "$REGION" --filters "Name=tag:Stack,Values=$STACK" "Name=instance-state-name,Values=pending,running,stopping,stopped" --query 'Reservations[].Instances[].InstanceId' --output text
if [ "$STACK" = fargate ]; then
  echo "ECS clusters:"; aws ecs list-clusters --region "$REGION" --query "clusterArns[?contains(@,'inf2006-grp21-fargate')]" --output text
fi
echo "NAT gateways:"; aws ec2 describe-nat-gateways --region "$REGION" --filter "Name=state,Values=available,pending" --query 'NatGateways[].NatGatewayId' --output text
echo "Done. Still running by design: the database, hosted zone, certificate, registry and secrets (base/)."
