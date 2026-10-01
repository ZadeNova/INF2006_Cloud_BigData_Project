#!/usr/bin/env bash
# The one-off database and data jobs, run on the stack's compute from the laptop, one command each (ADR-009).
#
#   scripts/jobs.sh ec2 <job>
#   jobs: bootstrap | migrate | trainer-sql | restart | check | import | all
#   all = bootstrap, migrate, trainer-sql, restart (restart ends with check_database)
#
# Runs through SSM Run Command (aws ssm send-command): no interactive session, no typing on the instance, output
# printed here. If the lab denies SendCommand it says so; the manual Session Manager commands in
# evidence/aws-build-runbook.md (Procedures) still work.
# bootstrap copies the RDS master login into the bootstrap secret for the run only, and puts the placeholder
# back on exit even if the job fails (RDS rotates that password every 7 days; it must not sit in the secret).
# import builds data/derived/shoes if missing, checks it against checksums.txt, uploads it to the bucket, then loads it
# from there. Run it once per fresh database.
# Every job is safe to repeat except import, which refuses a namespace that already has demo products.
# Needs: lab credentials, aws, jq, terraform. The `fargate` variant is added with the fargate/ stack.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$INFRA/../.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
NAMESPACE="synthetic/shoes/revision-a/demo/v1"
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

VARIANT="${1:-}"; JOB="${2:-}"
[ "$VARIANT" = ec2 ] || die "usage: $0 ec2 <bootstrap|migrate|trainer-sql|restart|check|import|all>  (fargate comes with the fargate/ stack)"
case "$JOB" in bootstrap|migrate|trainer-sql|restart|check|import|all) ;; *) die "unknown job '$JOB'" ;; esac
for t in aws jq terraform; do command -v "$t" >/dev/null || die "$t is required"; done
aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"

tfout() { terraform -chdir="$INFRA/$1" output -raw "$2"; }
BUCKET="$(tfout base s3_bucket_name)"
MASTER_ARN="$(tfout base db_master_secret_arn)"
ASG="$(tfout ec2 asg_name)"

INSTANCE="$(aws autoscaling describe-auto-scaling-groups --region "$REGION" --auto-scaling-group-names "$ASG" \
  --query "AutoScalingGroups[0].Instances[?LifecycleState=='InService']|[0].InstanceId" --output text)"
{ [ -n "$INSTANCE" ] && [ "$INSTANCE" != None ]; } || die "no InService instance in $ASG yet"
echo "Instance: $INSTANCE"

# Wait up to 5 minutes for the SSM agent to register.
for _ in $(seq 1 30); do
  [ "$(aws ssm describe-instance-information --region "$REGION" --filters "Key=InstanceIds,Values=$INSTANCE" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = Online ] && break
  sleep 10
done
[ "$(aws ssm describe-instance-information --region "$REGION" --filters "Key=InstanceIds,Values=$INSTANCE" \
  --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = Online ] || die "$INSTANCE is not Online in Systems Manager"

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

# remote <label> <script>: run the script on the instance as root, wait, print its output, fail if it failed.
remote() {
  local label="$1" script="$2" id status
  printf '\n== %s ==\n' "$label"
  jq -n --arg s "export HOME=/root AWS_DEFAULT_REGION=$REGION; set -euo pipefail; $script" \
    '{commands: [$s], executionTimeout: ["900"]}' > "$TMP"
  id="$(aws ssm send-command --region "$REGION" --instance-ids "$INSTANCE" --document-name AWS-RunShellScript \
    --parameters "file://$TMP" --query Command.CommandId --output text)" \
    || die "SendCommand was refused (see the error above). Use the manual session commands in the runbook"
  for _ in $(seq 1 180); do
    sleep 5
    status="$(aws ssm get-command-invocation --region "$REGION" --command-id "$id" --instance-id "$INSTANCE" \
      --query Status --output text 2>/dev/null || echo Pending)"
    case "$status" in Success|Failed|Cancelled|TimedOut) break ;; esac
  done
  aws ssm get-command-invocation --region "$REGION" --command-id "$id" --instance-id "$INSTANCE" --output json \
    | jq -r '.StandardOutputContent, (if .StandardErrorContent != "" then "--- stderr ---\n" + .StandardErrorContent else empty end)'
  [ "$status" = Success ] || die "$label: $status"
  echo "$label: ok"
}

job_bootstrap() {
  # Master login in for this run only; the placeholder goes back on any exit.
  ( trap '"$INFRA/scripts/secrets.sh" master-out' EXIT
    "$INFRA/scripts/secrets.sh" master-in
    remote "bootstrap" '/usr/local/bin/app-job bootstrap python tools/db_bootstrap.py' )
}

job_migrate() {
  remote "migrate" '/usr/local/bin/app-job migration python manage.py migrate --noinput'
}

job_trainer_sql() {
  aws s3 cp "$INFRA/sql/" "s3://$BUCKET/ops/sql/" --recursive --region "$REGION" >/dev/null
  # Part 1 as the RDS master (creates the login), part 2 as the migration owner (grants). The app image has no
  # psql and no infrastructure files, so install the client and fetch the SQL from the bucket. jq -e makes a
  # missing key stop the job instead of becoming the text null.
  remote "trainer-sql" "BUCKET=$BUCKET; MASTER_ARN='$MASTER_ARN'; $(cat <<'EOS'
dnf install -y postgresql17 jq >/dev/null
docker run --rm --entrypoint cat "$(docker inspect --format '{{.Config.Image}}' web)" /app/certs/rds-global-bundle.pem > /tmp/rds-ca.pem
rm -rf /tmp/sql && aws s3 cp "s3://$BUCKET/ops/sql/" /tmp/sql/ --recursive >/dev/null
s() { aws secretsmanager get-secret-value --secret-id "$1" --query SecretString --output text; }
T=$(s inf2006-grp21/trainer); M=$(s inf2006-grp21/migration); R=$(s "$MASTER_ARN")
HOST=$(jq -er .POSTGRES_HOST <<<"$T"); DB=$(jq -er .POSTGRES_DB <<<"$T")
export TRAINER_USER=$(jq -er .POSTGRES_USER <<<"$T") TRAINER_PASSWORD=$(jq -er .POSTGRES_PASSWORD <<<"$T") APP_DB=$DB
PGPASSWORD=$(jq -er .password <<<"$R") psql "host=$HOST dbname=postgres user=$(jq -er .username <<<"$R") sslmode=verify-full sslrootcert=/tmp/rds-ca.pem" -v ON_ERROR_STOP=1 -f /tmp/sql/trainer_role_create.sql
PGPASSWORD=$(jq -er .POSTGRES_PASSWORD <<<"$M") psql "host=$HOST dbname=$DB user=$(jq -er .POSTGRES_USER <<<"$M") sslmode=verify-full sslrootcert=/tmp/rds-ca.pem" -v ON_ERROR_STOP=1 -f /tmp/sql/trainer_role_grant.sql
unset T M R TRAINER_PASSWORD
EOS
)"
}

job_restart() {
  remote "restart web and check_database" 'docker restart web >/dev/null; sleep 20; /usr/local/bin/app-job web python manage.py check_database'
}

job_check() {
  remote "check_database" '/usr/local/bin/app-job web python manage.py check_database'
}

job_import() {
  # Only checksums.txt and product_map.csv are committed; the rest is rebuilt from data/raw (deterministic), then
  # checked against the committed checksums, so the cloud gets exactly the inputs the local tests used.
  local dir="$REPO/data/derived/shoes"
  [ -f "$dir/customers.csv" ] || (cd "$REPO" && python3 analytics/build_shoe_dataset.py)
  (cd "$dir" && sha256sum -c checksums.txt >/dev/null) || die "$dir does not match checksums.txt; rebuild it with analytics/build_shoe_dataset.py"
  echo "Dataset checksums match."
  aws s3 sync "$REPO/data/derived/shoes" "s3://$BUCKET/data/derived/shoes/" --region "$REGION" --only-show-errors
  # The data is not in the image, so mount a copy read-only into a throwaway container (same settings as app-job).
  remote "import_dataset" "BUCKET=$BUCKET; NS='$NAMESPACE'; $(cat <<'EOS'
rm -rf /var/lib/inf2006-data && mkdir -p /var/lib/inf2006-data/derived/shoes
aws s3 sync "s3://$BUCKET/data/derived/shoes/" /var/lib/inf2006-data/derived/shoes/ --only-show-errors
IMAGE=$(docker inspect --format '{{.Config.Image}}' web)
docker run --rm --env-file /etc/inf2006/app.env -e AWS_SECRET_ID=inf2006-grp21/web \
  -v /var/lib/inf2006-data:/app/data:ro "$IMAGE" python manage.py import_dataset --source /app/data/derived/shoes --namespace "$NS"
EOS
)"
}

case "$JOB" in
  bootstrap) job_bootstrap ;;
  migrate) job_migrate ;;
  trainer-sql) job_trainer_sql ;;
  restart) job_restart ;;
  check) job_check ;;
  import) job_import ;;
  all) job_bootstrap; job_migrate; job_trainer_sql; job_restart ;;
esac
echo; echo "Done: $JOB"
