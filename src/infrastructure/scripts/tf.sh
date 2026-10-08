#!/usr/bin/env bash
# The one way to plan and apply a Terraform folder (aws-ecs-comparison.md section 8, ADR-005).
#
#   scripts/tf.sh <base|ec2|fargate|loadgen> plan     fmt check, init, validate, saved plan; records the commit it was made from
#   scripts/tf.sh <base|ec2|fargate|loadgen> apply    applies that saved plan only if HEAD is still that commit; then backs up the state
#
# Refuses a dirty working tree under src/infrastructure, so the code that ran is always a recorded commit.
# Needs: lab credentials exported in this shell (it checks), terraform, git.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
FOLDER="${1:-}"; ACTION="${2:-}"
case "$FOLDER" in base|ec2|fargate|loadgen) ;; *) echo "usage: $0 <base|ec2|fargate|loadgen> <plan|apply>" >&2; exit 2 ;; esac
case "$ACTION" in plan|apply) ;; *) echo "usage: $0 <base|ec2|fargate|loadgen> <plan|apply>" >&2; exit 2 ;; esac
DIR="$INFRA/$FOLDER"
[ -d "$DIR" ] || { echo "STOP: $DIR does not exist yet" >&2; exit 1; }

die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"
[ -z "$(git -C "$INFRA" status --porcelain -- .)" ] || die "uncommitted changes in src/infrastructure; commit first"
SHA="$(git -C "$INFRA" rev-parse --short HEAD)"

# ADR-017: the two variants are compared on the same image. Release tags are immutable, so equal tags are the same bytes.
# A deliberate difference (for example timing a rollout) needs ALLOW_IMAGE_MISMATCH=1.
if { [ "$FOLDER" = ec2 ] || [ "$FOLDER" = fargate ]; } && [ "$ACTION" = plan ] && [ -z "${ALLOW_IMAGE_MISMATCH:-}" ]; then
  tag_of() { sed -n 's/^image_tag *= *"\(.*\)".*/\1/p' "$INFRA/$1/image.auto.tfvars" 2>/dev/null || true; }   # a stack with no image yet is not an error
  a="$(tag_of ec2)"; b="$(tag_of fargate)"
  [ -z "$a" ] || [ -z "$b" ] || [ "$a" = "$b" ] \
    || die "ec2 runs $a but fargate runs $b: the comparison needs the same image. Make them equal (copy one image.auto.tfvars over the other), or set ALLOW_IMAGE_MISMATCH=1 for a deliberate difference"
fi

# ADR-016: the Fargate task starts the image's own command from a copy in fargate/ecs.tf. If src/Dockerfile's CMD has
# changed and the copy has not, the two variants would run different server settings without anyone deciding so.
if [ "$FOLDER" = fargate ] && [ "$ACTION" = plan ]; then
  cmd="$(python3 -c 'import json, sys
line = [l for l in open(sys.argv[1]) if l.startswith("CMD ")][0]
print(" ".join(json.loads(line[4:])))' "$INFRA/../Dockerfile")" || die "could not read the CMD line of src/Dockerfile"
  grep -qF "exec $cmd" "$DIR/ecs.tf" \
    || die "src/Dockerfile's CMD is not the command in fargate/ecs.tf (web_command). Make them the same (ADR-016): $cmd"
fi
PLAN="$FOLDER.tfplan"

if [ "$ACTION" = plan ]; then
  terraform -chdir="$DIR" fmt -check -recursive || die "terraform fmt would change files; run terraform fmt and commit"
  terraform -chdir="$DIR" init -input=false >/dev/null
  terraform -chdir="$DIR" validate
  terraform -chdir="$DIR" plan -input=false -out="$PLAN"
  echo "$SHA" > "$DIR/.plan-commit"
  echo; echo "Plan saved from commit $SHA. Review it, then: scripts/tf.sh $FOLDER apply"
else
  [ -f "$DIR/$PLAN" ] || die "no saved plan; run: scripts/tf.sh $FOLDER plan"
  [ "$(cat "$DIR/.plan-commit" 2>/dev/null)" = "$SHA" ] \
    || die "the plan was made from commit $(cat "$DIR/.plan-commit" 2>/dev/null || echo '?'), HEAD is $SHA; plan again"
  terraform -chdir="$DIR" apply -input=false "$PLAN"
  rm -f "$DIR/$PLAN" "$DIR/.plan-commit"
  if [ -f "$DIR/terraform.tfstate" ]; then
    BAK="terraform.tfstate.$(date +%Y-%m-%d-%H%M).$SHA.bak"
    cp -p "$DIR/terraform.tfstate" "$DIR/$BAK"
    echo "State backed up as $FOLDER/$BAK. Copy it off this laptop (it holds resource IDs and may hold sensitive values)."
  fi
  echo "Applied from commit $SHA. Record it in evidence/aws-build-runbook.md."
fi
