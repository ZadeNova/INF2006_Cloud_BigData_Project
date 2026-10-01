#!/usr/bin/env bash
# One command from a clean base/ to a working, checked stack (ADR-010).
#
#   scripts/up.sh ec2 [--yes]
#
# Order: saved plan (shown to you) -> you type yes -> apply that plan -> secrets (idempotent) -> every database and
# data job still needed (jobs.sh all; idempotent) -> smoke test. Stops at the first failure.
# Needs: lab credentials; base/ applied; the image already pushed and tagged (scripts/push-image.sh <sha>, which writes
# <stack>/image.auto.tfvars); a clean committed tree (tf.sh enforces it).
set -euo pipefail
INFRA="$(cd "$(dirname "$0")/.." && pwd)"
VARIANT="${1:-}"; YES="${2:-}"
[ "$VARIANT" = ec2 ] || { echo "usage: $0 ec2 [--yes]  (fargate comes with the fargate/ stack)" >&2; exit 2; }
[ -s "$INFRA/base/terraform.tfstate" ] || { echo "STOP: base/ is not applied yet" >&2; exit 1; }
[ -f "$INFRA/$VARIANT/image.auto.tfvars" ] || { echo "STOP: no image selected; run scripts/push-image.sh <sha> first" >&2; exit 1; }

"$INFRA/scripts/tf.sh" "$VARIANT" plan
if [ "$YES" != "--yes" ]; then
  read -r -p "Apply this plan? Type yes: " answer
  [ "$answer" = yes ] || { echo "STOP: not confirmed; nothing applied" >&2; exit 1; }
fi
"$INFRA/scripts/tf.sh" "$VARIANT" apply
"$INFRA/scripts/secrets.sh" fill
"$INFRA/scripts/jobs.sh" "$VARIANT" all
"$INFRA/scripts/smoke.sh" "$VARIANT"
