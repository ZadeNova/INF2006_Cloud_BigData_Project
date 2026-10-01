#!/usr/bin/env bash
# Lab probe for the EC2 vs Fargate comparison (plan step 1): docs/plans/aws-ecs-comparison.md.
#
# Answers, with PASS / FAIL / UNKNOWN lines and no account IDs or ARNs, whether this Learner Lab lets us:
#   1. use LabRole as an ECS task and execution role
#   2. run a Fargate task that pulls our ECR image and logs to CloudWatch
#   3. launch the EC2 type used for the matched comparison
#   4. create the RDS classes and Multi-AZ we may need
#
# Needs: lab credentials exported in this shell, the AWS CLI, jq, terraform (state already applied).
# Creates one throwaway ECS cluster, task definition and task, and removes them on exit.
#
# Usage: scripts/probe-lab-comparison.sh [terraform-dir]     (default: the directory above this script)
set -uo pipefail

REGION="${AWS_REGION:-us-east-1}"
TF_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PROBE="inf2006-grp21-probe"
EC2_TYPE="${EC2_TYPE:-c5.large}"
RDS_CLASSES="${RDS_CLASSES:-db.t4g.small db.t4g.medium}"

pass() { printf 'PASS    %s\n' "$*"; }
fail() { printf 'FAIL    %s\n' "$*"; }
unknown() { printf 'UNKNOWN %s\n' "$*"; }

command -v jq >/dev/null || { echo "jq is required"; exit 2; }
aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || { echo "No working lab credentials in this shell. Export them first."; exit 2; }

tf_out() { terraform -chdir="$TF_DIR" output -json "$1"; }
SUBNET=$(tf_out public_subnet_ids | jq -r '.a')
SG_APP=$(tf_out security_group_ids | jq -r '.app')
LOG_GROUP=$(tf_out log_group_name | jq -r '.')
REPO_URL=$(tf_out ecr_repository_url | jq -r '.')
IMAGE_TAG=$(sed -n 's/^image_tag[[:space:]]*=[[:space:]]*"\(.*\)".*/\1/p' "$TF_DIR/terraform.tfvars")
[ -n "$SUBNET" ] && [ -n "$SG_APP" ] && [ -n "$LOG_GROUP" ] && [ -n "$REPO_URL" ] && [ -n "$IMAGE_TAG" ] \
  || { echo "Could not read subnet, security group, log group, repository or image_tag from $TF_DIR"; exit 2; }

echo "== 1. LabRole as ECS task and execution role =="
if aws iam get-role --role-name LabRole --query 'Role.AssumeRolePolicyDocument' --output json 2>/dev/null \
    | grep -q 'ecs-tasks.amazonaws.com'; then
  pass "LabRole trust policy names ecs-tasks.amazonaws.com"
else
  unknown "LabRole trust policy not readable or lacks ecs-tasks; the task run in step 2 is the real test"
fi
if aws iam get-role --role-name AWSServiceRoleForECS >/dev/null 2>&1; then
  pass "ECS service-linked role exists"
else
  unknown "ECS service-linked role not visible; creating the cluster in step 2 creates it if allowed"
fi

echo "== 2. Fargate task: image pull, LabRole, CloudWatch logs =="
ROLE_ARN=$(aws iam get-role --role-name LabRole --query 'Role.Arn' --output text 2>/dev/null)
TASK_DEF=""
cleanup() {
  [ -n "$TASK_DEF" ] && aws ecs deregister-task-definition --task-definition "$TASK_DEF" >/dev/null 2>&1
  aws ecs delete-cluster --cluster "$PROBE" >/dev/null 2>&1
}
trap cleanup EXIT

if aws ecs create-cluster --cluster-name "$PROBE" >/dev/null 2>&1; then
  pass "cluster created"
else
  fail "cluster creation refused (ECS may be unavailable, or the service-linked role cannot be created)"
fi

TASK_DEF=$(aws ecs register-task-definition --family "$PROBE" --requires-compatibilities FARGATE \
  --network-mode awsvpc --cpu 256 --memory 512 --task-role-arn "$ROLE_ARN" --execution-role-arn "$ROLE_ARN" \
  --container-definitions "$(jq -nc --arg image "$REPO_URL:$IMAGE_TAG" --arg group "$LOG_GROUP" --arg region "$REGION" '[{
      name: "probe", image: $image, essential: true,
      command: ["python", "-c", "print(\"ecs probe ok\")"],
      logConfiguration: {logDriver: "awslogs", options: {"awslogs-group": $group, "awslogs-region": $region, "awslogs-stream-prefix": "ecs-probe"}}
    }]')" --query 'taskDefinition.taskDefinitionArn' --output text 2>/dev/null)
if [ -n "$TASK_DEF" ] && [ "$TASK_DEF" != "None" ]; then
  pass "task definition registered with LabRole as task and execution role"
else
  TASK_DEF=""
  fail "task definition refused (LabRole may not be usable as an ECS role)"
fi

if [ -n "$TASK_DEF" ]; then
  TASK=$(aws ecs run-task --cluster "$PROBE" --launch-type FARGATE --task-definition "$TASK_DEF" \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG_APP],assignPublicIp=ENABLED}" \
    --query 'tasks[0].taskArn' --output text 2>/dev/null)
  if [ -z "$TASK" ] || [ "$TASK" = "None" ]; then
    fail "run-task refused"
  else
    pass "task started"
    aws ecs wait tasks-stopped --cluster "$PROBE" --tasks "$TASK" 2>/dev/null
    EXIT_CODE=$(aws ecs describe-tasks --cluster "$PROBE" --tasks "$TASK" --query 'tasks[0].containers[0].exitCode' --output text 2>/dev/null)
    REASON=$(aws ecs describe-tasks --cluster "$PROBE" --tasks "$TASK" --query 'tasks[0].stoppedReason' --output text 2>/dev/null)
    if [ "$EXIT_CODE" = "0" ]; then
      pass "container ran to exit code 0: the image was pulled from ECR with LabRole"
    else
      fail "container did not succeed (exit code: $EXIT_CODE; reason: $REASON)"
    fi
  fi
fi

echo "== 3. EC2 type for the matched comparison: $EC2_TYPE =="
AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query 'Parameter.Value' --output text 2>/dev/null)
DRY=$(aws ec2 run-instances --dry-run --image-id "$AMI" --instance-type "$EC2_TYPE" --subnet-id "$SUBNET" 2>&1)
if grep -q 'DryRunOperation' <<<"$DRY"; then
  pass "$EC2_TYPE can be launched"
else
  fail "$EC2_TYPE refused: $(grep -o '(\(UnauthorizedOperation\|InvalidParameterValue\|Unsupported\|[A-Za-z]*\))' <<<"$DRY" | head -1)"
fi

echo "== 4. RDS classes (PostgreSQL 17) and Multi-AZ =="
for class in $RDS_CLASSES; do
  ROW=$(aws rds describe-orderable-db-instance-options --engine postgres --db-instance-class "$class" \
    --query "OrderableDBInstanceOptions[?starts_with(EngineVersion, '17')] | [0].MultiAZCapable" --output text 2>/dev/null)
  case "$ROW" in
    True)  pass "$class orderable on PostgreSQL 17, Multi-AZ capable" ;;
    False) pass "$class orderable on PostgreSQL 17, NOT Multi-AZ capable" ;;
    *)     fail "$class not orderable on PostgreSQL 17 here" ;;
  esac
done

echo "Probe finished; the task definition and cluster are removed on exit."
