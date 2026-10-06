#!/usr/bin/env bash
# One command to build something, with the checks that matter (ADR-010, ADR-017).
#
#   scripts/up.sh base            first-time setup of the shared part (asks two questions, creates the bucket, applies)
#   scripts/up.sh ec2 [--yes]     variant A: EC2 + Auto Scaling group, ready and checked
#   scripts/up.sh fargate [--yes] variant B: ECS on Fargate, ready and checked
#   scripts/up.sh loadgen [--yes] the load-test machine
#
# Every target shows the Terraform plan and waits for you to type yes (--yes skips that). A stack's steps:
#   ec2      image (pushed if none chosen) -> plan -> apply -> secrets -> every database job still needed -> smoke test
#   fargate  image -> plan -> apply -> database check as a one-off task -> smoke test
#   loadgen  plan -> apply -> prints how to open a shell on it
# Stops at the first failure. Safe to run again. Needs: lab credentials (run labcreds first), a clean committed tree.
# fargate shares the database that variant A set up; on a brand-new database run `up.sh ec2` once first.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
TARGET="${1:-}"; YES="${2:-}"
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
case "$TARGET" in base|ec2|fargate|loadgen) ;; *) die "usage: $0 <base|ec2|fargate|loadgen> [--yes]   (run scripts/status.sh to see where you are)" ;; esac
[ -z "$YES" ] || [ "$YES" = --yes ] || die "unknown option '$YES' (only --yes)"

aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"

# plan_and_apply <folder>: the saved plan is shown, you confirm, exactly that plan is applied.
plan_and_apply() {
  "$INFRA/scripts/tf.sh" "$1" plan
  if [ "$YES" != "--yes" ]; then
    read -r -p "Apply this plan? Type yes: " answer
    [ "$answer" = yes ] || die "not confirmed; nothing applied"
  fi
  "$INFRA/scripts/tf.sh" "$1" apply
}

# ---------------------------------------------------------------------------------------------------- base
up_base() {
  local tfvars="$INFRA/base/terraform.tfvars" bucket email domain
  for t in terraform aws jq openssl; do command -v "$t" >/dev/null || die "$t is required"; done

  if [ ! -f "$tfvars" ]; then
    echo "First-time setup. Two questions (they go into base/terraform.tfvars, which git ignores):"
    email="${ALARM_EMAIL:-}"; domain="${DOMAIN_NAME:-}"
    if [ -z "$email" ]; then [ -t 0 ] || die "no terminal to ask on: set ALARM_EMAIL (and DOMAIN_NAME) and run again"; read -r -p "  Email address for alarm notifications: " email; fi
    if [ -z "$domain" ]; then
      if [ -t 0 ]; then read -r -p "  Domain you control, registered anywhere [fourtytwofactors.me]: " domain; fi
      domain="${domain:-fourtytwofactors.me}"
    fi
    [ -n "$email" ] || die "an email address is needed"
    # The lab denies a read that Terraform's bucket resource makes, so the bucket is created with the CLI; Terraform
    # then manages every setting on it (base/storage.tf).
    bucket="inf2006-grp21-data-$(openssl rand -hex 8)"
    echo "  Creating the S3 bucket $bucket ..."
    aws s3api create-bucket --bucket "$bucket" --region "$REGION" >/dev/null
    aws s3api put-bucket-tagging --bucket "$bucket" --tagging \
      'TagSet=[{Key=Name,Value=inf2006-grp21-data},{Key=Project,Value=inf2006-grp21},{Key=Env,Value=evidence},{Key=ManagedBy,Value=cli}]'
    umask 077
    { echo "alarm_email    = \"$email\""; echo "s3_bucket_name = \"$bucket\""; echo "domain_name    = \"$domain\""; } > "$tfvars"
    echo "  Wrote base/terraform.tfvars"
  else
    bucket="$(sed -n 's/^s3_bucket_name *= *"\(.*\)".*/\1/p' "$tfvars")"
    aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1 \
      || die "base/terraform.tfvars names the bucket $bucket, which does not exist in this account. Fix or delete base/terraform.tfvars and run again"
  fi
  domain="$(sed -n 's/^domain_name *= *"\(.*\)".*/\1/p' "$tfvars")"
  [ -n "$domain" ] || domain="$(awk '/variable "domain_name"/{f=1} f&&/default/{gsub(/.*= *"|".*/,""); print; exit}' "$INFRA/base/variables.tf")"

  "$INFRA/scripts/tf.sh" base plan
  if [ "$YES" != "--yes" ]; then read -r -p "Apply this plan? Type yes: " a; [ "$a" = yes ] || die "not confirmed; nothing applied"; fi

  # The certificate is validated through DNS, so the apply waits until the domain's name servers are the zone's. While
  # it waits, this loop prints the four name servers once, so you can set them at your registrar.
  "$INFRA/scripts/tf.sh" base apply &
  local apply_pid=$! shown=0 zone ns
  while kill -0 "$apply_pid" 2>/dev/null; do
    if [ "$shown" = 0 ]; then
      zone="$(aws route53 list-hosted-zones-by-name --dns-name "$domain." --max-items 1 --query "HostedZones[?Name=='$domain.'].Id|[0]" --output text 2>/dev/null || true)"
      if [ -n "$zone" ] && [ "$zone" != None ]; then
        shown=1
        if command -v dig >/dev/null && dig +short NS "$domain" 2>/dev/null | grep -q awsdns; then :; else
          ns="$(aws route53 get-hosted-zone --id "$zone" --query 'DelegationSet.NameServers' --output text)"
          printf '\n>>> ACTION NEEDED NOW: at your domain registrar, set the name servers of %s to (custom DNS):\n' "$domain"
          printf '      %s\n' $ns
          printf '    The apply is waiting for this and carries on by itself within minutes of the change.\n    Namecheap: Domain List, Manage, Nameservers, Custom DNS, enter the four, click the green tick.\n\n'
        fi
      fi
    fi
    sleep 10
  done
  wait "$apply_pid" || die "the base apply failed (read the error above; a re-run is safe)"
  echo
  echo "base is up. Two things left:"
  echo "  - Click the confirmation link in the email AWS sent to your alarm address (check spam), or alarms reach no one."
  echo "  - Start a variant:  scripts/up.sh ec2   or   scripts/up.sh fargate"
}

# ---------------------------------------------------------------------------------------------- stacks
need_base() { [ -s "$INFRA/base/terraform.tfstate" ] || die "base/ is not applied yet. Run: scripts/up.sh base"; }

# An image must be chosen for the stack (image.auto.tfvars, written by push-image.sh); push one if not.
need_image() {
  if [ ! -f "$INFRA/$1/image.auto.tfvars" ]; then
    echo "No image chosen for $1 yet: running push-image.sh (builds and pushes the app image; needs Docker)."
    "$INFRA/scripts/push-image.sh"
  fi
  [ -f "$INFRA/$1/image.auto.tfvars" ] || die "no image.auto.tfvars in $1/ after push-image.sh"
  echo "Image for $1: $(sed -n 's/^image_tag *= *"\(.*\)".*/\1/p' "$INFRA/$1/image.auto.tfvars")"
}

up_ec2() {
  need_base; need_image ec2
  plan_and_apply ec2
  "$INFRA/scripts/secrets.sh" fill
  "$INFRA/scripts/jobs.sh" ec2 all
  "$INFRA/scripts/smoke.sh" ec2
}

up_fargate() {
  need_base; need_image fargate
  # The tasks read the shared secrets and database. If variant A never set them up, the tasks would fail to start.
  local web
  web="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id inf2006-grp21/web --query SecretString --output text 2>/dev/null || echo '{}')"
  printf '%s' "$web" | jq -e 'has("POSTGRES_PASSWORD") and has("DJANGO_SECRET_KEY")' >/dev/null 2>&1 \
    || die "the shared secrets are empty: the database was never set up. Run scripts/up.sh ec2 once first (it fills the secrets and seeds the database), then fargate"
  plan_and_apply fargate
  "$INFRA/scripts/jobs.sh" fargate check
  "$INFRA/scripts/smoke.sh" fargate
}

up_loadgen() {
  need_base
  plan_and_apply loadgen
  local id; id="$(terraform -chdir="$INFRA/loadgen" output -raw instance_id)"
  echo
  echo "The load generator is up: $id (about 2 minutes until its tools are installed)."
  echo "  Open a shell:  aws ssm start-session --target $id"
  echo "  Ready when:    ls /var/lib/loadgen-ready   (on the instance)"
  echo "  Remember to run scripts/down.sh loadgen when the test session ends."
}

case "$TARGET" in
  base) up_base ;;
  ec2) up_ec2 ;;
  fargate) up_fargate ;;
  loadgen) up_loadgen ;;
esac
