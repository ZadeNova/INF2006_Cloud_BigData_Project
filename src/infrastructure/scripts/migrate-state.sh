#!/usr/bin/env bash
# One-time state migration: the stage 1 single folder -> base/ (docs/plans/aws-ecs-comparison.md section 5, ADR-002).
# DONE on 1 October 2026 (runbook). Kept as the record of how it was done; the old folder's .tf files it needs were
# removed afterwards, so to rerun it, check out commit 308fb28 first.
#
#   scripts/migrate-state.sh check      read-only rehearsal on throwaway copies of the state (no AWS calls)
#   scripts/migrate-state.sh run        back up, destroy the resources that are recreated, move the rest, gate
#   scripts/migrate-state.sh rollback   put the state back as it was before the move (see "Recovery")
#
# What happens to the 38 resources Terraform manages (the 2 data sources are re-read, never moved):
#   MOVE      28  VPC, subnets, routes, default SG, sg-db, S3 settings, ECR, secrets, SNS    -> base/ state
#   RECREATE  10  sg-alb, sg-app, their 7 rules (incl. sg-db's rule from sg-app), app log group
#                 Each stack owns its own sg-alb, sg-app and log group, so these are destroyed here and created
#                 again in ec2/ and fargate/. Nothing is attached to them yet, so this costs nothing.
#
# Order of `run` (every step stops the script on failure):
#   1. backup           dated copy of terraform.tfstate
#   2. destroy          the 10 RECREATE resources (plan checked against the expected list, then you type yes)
#   3. backup           second copy, so a rollback matches what AWS really has
#   4. move             `terraform state mv` of the 28 into base/terraform.tfstate
#   5. GATE             `terraform plan` in base/ must show NO resource changes. Anything else: stop, nothing applied.
#
# Run it when base/ contains ONLY the moved resources (no zone, RDS or certificate yet), so "no changes" is
# literal. Needs: lab credentials exported, terraform, jq, git; a clean git tree for src/infrastructure
# (commit first, so the code that ran is recorded). The old folder's .tf files stay until the gate passes.
#
# Recovery. A failure before step 4 leaves the old state valid: re-run. A failure after it:
#   scripts/migrate-state.sh rollback       restores the post-destroy backup and removes base/terraform.tfstate;
#                                           then `terraform plan` in the old folder shows the 10 resources as
#                                           "to add" (they were destroyed on purpose): apply them or re-run `run`.
set -euo pipefail

OLD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_DIR="$OLD_DIR/base"
STAMP="$(date +%Y-%m-%d-%H%M)"

# Whole-resource addresses (every instance of a for_each/count resource moves together).
MOVE=(
  aws_vpc.main
  aws_internet_gateway.main
  aws_subnet.public
  aws_subnet.private
  aws_route_table.public
  aws_route_table.private
  aws_route_table_association.public
  aws_route_table_association.private
  aws_default_security_group.default
  aws_security_group.db
  aws_s3_bucket_public_access_block.main
  aws_s3_bucket_ownership_controls.main
  aws_s3_bucket_versioning.main
  aws_s3_bucket_server_side_encryption_configuration.main
  aws_s3_bucket_lifecycle_configuration.main
  aws_s3_bucket_policy.main
  aws_ecr_repository.app
  aws_ecr_lifecycle_policy.app
  aws_secretsmanager_secret.app
  aws_sns_topic.alarms
  aws_sns_topic_subscription.alarm_email
)
RECREATE=(
  aws_security_group.alb
  aws_security_group.app
  aws_vpc_security_group_ingress_rule.alb_https
  aws_vpc_security_group_ingress_rule.alb_http
  aws_vpc_security_group_egress_rule.alb_to_app
  aws_vpc_security_group_ingress_rule.app_from_alb
  aws_vpc_security_group_egress_rule.app_https
  aws_vpc_security_group_egress_rule.app_to_db
  aws_vpc_security_group_ingress_rule.db_from_app
  aws_cloudwatch_log_group.app
)

die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s ==\n' "$*"; }

managed() { terraform -chdir="$OLD_DIR" state list -state="$1" | grep -v '^data\.' || true; }   # one line per instance
top() { sed 's/\[.*$//' | sort -u; }                                           # strip ["a"] keys

need_tools() { for t in terraform jq git; do command -v "$t" >/dev/null || die "$t is required"; done; }

# Every managed resource in the state must be named in MOVE or RECREATE, and every name must exist.
check_inventory() {
  local state="$1" listed expected unknown missing
  listed="$(managed "$state" | top)"
  expected="$(printf '%s\n' "${MOVE[@]}" "${RECREATE[@]}" | sort -u)"
  unknown="$(comm -23 <(echo "$listed") <(echo "$expected"))"
  missing="$(comm -13 <(echo "$listed") <(echo "$expected"))"
  [ -z "$unknown" ] || die "state has resources this script does not know (decide where they go first):
$unknown"
  [ -z "$missing" ] || die "state lacks resources the script expects (already migrated, or stage 1 changed?):
$missing"
}

# Move MOVE from the state $1 into the state $2. Both files are changed in place; no automatic backups,
# because the script keeps its own dated ones.
move_all() {
  local src="$1" dst="$2" addr
  for addr in "${MOVE[@]}"; do
    terraform -chdir="$OLD_DIR" state mv -state="$src" -state-out="$dst" -backup=- -backup-out=- "$addr" "$addr" >/dev/null
  done
}

cmd_check() {
  need_tools
  [ -f "$OLD_DIR/terraform.tfstate" ] || die "no $OLD_DIR/terraform.tfstate (already migrated?)"
  say "Inventory of the old state"
  check_inventory "$OLD_DIR/terraform.tfstate"
  echo "OK: every managed resource is accounted for."

  say "Rehearsal of the move on throwaway copies"
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  cp "$OLD_DIR/terraform.tfstate" "$tmp/old.tfstate"
  move_all "$tmp/old.tfstate" "$tmp/base.tfstate"
  local moved left
  moved="$(managed "$tmp/base.tfstate" | wc -l)"
  left="$(managed "$tmp/old.tfstate" | wc -l)"
  echo "would move $moved resource instances; $left stay behind to be destroyed and recreated"
  managed "$tmp/old.tfstate" | sed 's/^/  destroy+recreate: /'
  [ "$left" -eq "${#RECREATE[@]}" ] || die "expected ${#RECREATE[@]} to stay behind, found $left"

  say "Preconditions for run"
  [ -d "$BASE_DIR" ] && ls "$BASE_DIR"/*.tf >/dev/null 2>&1 \
    && echo "OK: base/ has .tf files" || echo "NOT YET: base/ has no .tf files"
  [ ! -s "$BASE_DIR/terraform.tfstate" ] && echo "OK: base/ has no state yet" || echo "NOT YET: base/terraform.tfstate already exists"
  if [ -z "$(git -C "$OLD_DIR" status --porcelain -- .)" ]; then echo "OK: git tree clean"; else echo "NOT YET: uncommitted changes in src/infrastructure"; fi
  echo "Nothing was changed."
}

cmd_run() {
  need_tools
  aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
    || die "no working lab credentials in this shell (run labcreds first)"
  [ -f "$OLD_DIR/terraform.tfstate" ] || die "no old state to migrate"
  ls "$BASE_DIR"/*.tf >/dev/null 2>&1 || die "base/ has no .tf files yet"
  [ ! -s "$BASE_DIR/terraform.tfstate" ] || die "base/terraform.tfstate already exists; refusing to overwrite (use rollback)"
  [ -z "$(git -C "$OLD_DIR" status --porcelain -- .)" ] || die "uncommitted changes in src/infrastructure; commit first"
  check_inventory "$OLD_DIR/terraform.tfstate"
  echo "Applying code from commit $(git -C "$OLD_DIR" rev-parse --short HEAD)"

  say "1. Backup"
  cp -p "$OLD_DIR/terraform.tfstate" "$OLD_DIR/terraform.tfstate.$STAMP.pre-migration.bak"
  echo "saved terraform.tfstate.$STAMP.pre-migration.bak"

  say "2. Destroy the 10 resources that the stacks recreate"
  local targets=() r
  for r in "${RECREATE[@]}"; do targets+=("-target=$r"); done
  terraform -chdir="$OLD_DIR" plan -destroy -input=false -out=migrate-destroy.tfplan "${targets[@]}"
  local json deleted wanted others
  json="$(terraform -chdir="$OLD_DIR" show -json migrate-destroy.tfplan)"
  deleted="$(jq -r '.resource_changes[] | select(.change.actions == ["delete"]) | .address' <<<"$json" | sort)"
  wanted="$(managed "$OLD_DIR/terraform.tfstate" | grep -Fx -f <(printf '%s\n' "${RECREATE[@]}") | sort)"
  others="$(jq -r '.resource_changes[] | select(.change.actions != ["delete"] and .change.actions != ["no-op"]) | .address' <<<"$json")"
  [ -z "$others" ] || die "the destroy plan has changes other than deletes:
$others"
  [ "$deleted" = "$wanted" ] || die "the destroy plan does not match the expected list.
planned: $(echo "$deleted" | tr '\n' ' ')
expected: $(echo "$wanted" | tr '\n' ' ')"
  echo "The plan deletes exactly these $(echo "$deleted" | wc -l) resources and nothing else:"
  echo "$deleted" | sed 's/^/  /'
  read -r -p "Type yes to destroy them: " answer
  [ "$answer" = "yes" ] || die "not confirmed; nothing was destroyed"
  terraform -chdir="$OLD_DIR" apply -input=false migrate-destroy.tfplan
  rm -f "$OLD_DIR/migrate-destroy.tfplan"

  say "3. Backup after the destroy"
  cp -p "$OLD_DIR/terraform.tfstate" "$OLD_DIR/terraform.tfstate.$STAMP.post-destroy.bak"
  echo "saved terraform.tfstate.$STAMP.post-destroy.bak"

  say "4. Move the 28 resources into base/"
  move_all "$OLD_DIR/terraform.tfstate" "$BASE_DIR/terraform.tfstate"
  echo "base/ state now holds $(managed "$BASE_DIR/terraform.tfstate" | wc -l) resource instances"
  [ -z "$(managed "$OLD_DIR/terraform.tfstate")" ] || die "the old state still holds resources: $(managed "$OLD_DIR/terraform.tfstate")"

  say "5. Gate: terraform plan in base/ must show no resource changes"
  [ -f "$BASE_DIR/.terraform.lock.hcl" ] || cp "$OLD_DIR/.terraform.lock.hcl" "$BASE_DIR/"
  [ -f "$BASE_DIR/terraform.tfvars" ] || cp "$OLD_DIR/terraform.tfvars" "$BASE_DIR/"
  terraform -chdir="$BASE_DIR" init -input=false
  terraform -chdir="$BASE_DIR" plan -input=false -out=migration-gate.tfplan
  local gate bad noop
  gate="$(terraform -chdir="$BASE_DIR" show -json migration-gate.tfplan)"
  bad="$(jq -r '.resource_changes[] | select(.change.actions != ["no-op"]) | "\(.change.actions | join(",")) \(.address)"' <<<"$gate")"
  noop="$(jq '[.resource_changes[] | select(.change.actions == ["no-op"])] | length' <<<"$gate")"
  if [ -n "$bad" ] || [ "$noop" -ne "$(managed "$BASE_DIR/terraform.tfstate" | wc -l)" ]; then
    printf 'GATE FAILED: %s resources unchanged, and these differ:\n%s\n' "$noop" "$bad" >&2
    die "do not apply. Fix base/*.tf until the plan is clean, or run: scripts/migrate-state.sh rollback"
  fi
  mv "$OLD_DIR/terraform.tfstate" "$OLD_DIR/terraform.tfstate.migrated"
  echo "GATE PASSED: $noop resources, no changes."
  echo "The old state is renamed terraform.tfstate.migrated (empty of resources; keep it as a record)."
  echo "Next: copy the three .bak files off this laptop, then continue with the rest of base/."
}

cmd_rollback() {
  need_tools
  local bak; bak="$(ls -1t "$OLD_DIR"/terraform.tfstate.*.post-destroy.bak 2>/dev/null | head -1 || true)"
  [ -n "$bak" ] || die "no post-destroy backup found; if the destroy step never ran, the old state is already intact"
  echo "Restoring $bak"
  read -r -p "This overwrites terraform.tfstate and deletes base/terraform.tfstate. Type yes: " answer
  [ "$answer" = "yes" ] || die "not confirmed"
  cp -p "$bak" "$OLD_DIR/terraform.tfstate"
  rm -f "$BASE_DIR/terraform.tfstate" "$BASE_DIR/terraform.tfstate.backup" "$BASE_DIR/migration-gate.tfplan"
  rm -f "$OLD_DIR/terraform.tfstate.migrated"
  echo "Old state restored. In the old folder, terraform plan will show the 10 recreated resources as to add."
}

case "${1:-check}" in
  check) cmd_check ;;
  run) cmd_run ;;
  rollback) cmd_rollback ;;
  *) die "usage: $0 [check|run|rollback]" ;;
esac
