#!/usr/bin/env bash
# The one-off database and data jobs, one command each (ADR-009, ADR-017).
#
#   scripts/jobs.sh ec2 <bootstrap|migrate|trainer-sql|restart|check|import|operator|refresh|all>
#   scripts/jobs.sh fargate <bootstrap|migrate|check|import|operator|refresh|all>
#   all = everything a fresh database needs, in order: bootstrap, migrate, [ec2 only: trainer-sql, restart], import,
#   operator, refresh. Safe to repeat: bootstrap is skipped when check_database already passes, and every other job
#   skips or changes nothing the second time.
#
# ec2: runs through SSM Run Command (aws ssm send-command) on the stack's instance: no interactive session, output
# printed here. If the lab denies SendCommand it says so; the manual Session Manager commands in
# evidence/aws-build-runbook.md (Procedures) still work.
# fargate: each job is a one-off ECS task (aws ecs run-task) from the stack's task definition, with the job's command
# and secret name overriding the web container's; the script waits for it to stop, prints its log and fails on a
# non-zero exit code. The frozen image has no psql, AWS CLI or data folder, so import and operator run as small Python
# programs (boto3 and psycopg are in requirements.txt): import downloads the dataset from the bucket, operator stores
# the password with boto3. trainer-sql and restart are offered on variant A only: the trainer login serves the offline
# ML training, which is not part of running the shop. Needs the fargate/ stack to exist (zero tasks is enough).
# bootstrap copies the RDS master login into the bootstrap secret for the run only, and puts the placeholder
# back on exit even if the job fails (RDS rotates that password every 7 days; it must not sit in the secret).
# import builds data/derived/shoes if missing, checks it against checksums.txt, uploads it to the bucket, then loads it
# from there. Run it once per fresh database.
# operator creates the demo-operator login with a random password generated ON the instance (a password passed
# through SSM parameters would sit in the command history) and stores it in the operator secret; read it with
#   aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator --query SecretString --output text
# Needs: lab credentials, aws, jq, terraform.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$INFRA/../.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
NAMESPACE="synthetic/shoes/revision-a/demo/v1"
PREFIX="inf2006-grp21"
AS_OF="2026-01-02"   # the cutoff the local README uses; the dataset ends here
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

VARIANT="${1:-}"; JOB="${2:-}"
case "$VARIANT" in
  ec2) JOBS="bootstrap|migrate|trainer-sql|restart|check|import|operator|refresh|all" ;;
  fargate) JOBS="bootstrap|migrate|check|import|operator|refresh|all" ;;
  *) die "usage: $0 <ec2|fargate> <job>   (ec2: bootstrap|migrate|trainer-sql|restart|check|import|operator|refresh|all; fargate: bootstrap|migrate|check|import|operator|refresh|all)" ;;
esac
case "$JOB" in
  bootstrap|migrate|check|import|operator|refresh|all) ;;
  trainer-sql|restart)
    [ "$VARIANT" = ec2 ] || die "'$JOB' is only offered on variant A (it needs psql or the instance's Docker; the trainer login serves the offline ML training). Offered on fargate: $JOBS" ;;
  *) die "unknown job '$JOB' (for $VARIANT: $JOBS)" ;;
esac
for t in aws jq terraform; do command -v "$t" >/dev/null || die "$t is required"; done
aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"

tfout() { terraform -chdir="$INFRA/$1" output -raw "$2"; }
BUCKET="$(tfout base s3_bucket_name)"
MASTER_ARN="$(tfout base db_master_secret_arn)"

if [ "$VARIANT" = ec2 ]; then
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
else
  CLUSTER="$(tfout fargate cluster_name)"
  TASK_DEF="$(tfout fargate task_definition_arn)"
  LOG_GROUP="$(tfout fargate log_group_name)"
  SUBNETS="$(terraform -chdir="$INFRA/fargate" output -json subnet_ids | jq -r 'join(",")')"
  APP_SG="$(terraform -chdir="$INFRA/fargate" output -json security_group_ids | jq -r .app)"
  echo "Cluster: $CLUSTER"
fi

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

# ecs_task <label> <secret> <command...>: one-off task from the fargate stack's task definition. The command replaces
# the web container's start command and AWS_SECRET_ID names the secret the job may read. EXTRA_ENV (a JSON list of
# {name,value}) adds plain settings the job needs, never secrets.
EXTRA_ENV='[]'
ecs_task() {
  local label="$1" secret="$2"; shift 2
  local task id exit_code reason result
  printf '\n== %s ==\n' "$label"
  # The command goes in as a JSON list built from NUL-separated words, so words that look like options
  # (--noinput, --as-of) are not mistaken for options by jq.
  jq -n --arg secret "$PREFIX/$secret" --argjson extra "$EXTRA_ENV" \
    --argjson cmd "$(printf '%s\0' "$@" | jq -Rsc 'split("\u0000")[:-1]')" \
    '{containerOverrides: [{name: "web", command: $cmd, environment: ([{name: "AWS_SECRET_ID", value: $secret}] + $extra)}]}' > "$TMP"
  task="$(aws ecs run-task --region "$REGION" --cluster "$CLUSTER" --task-definition "$TASK_DEF" --launch-type FARGATE --count 1 \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$APP_SG],assignPublicIp=ENABLED}" \
    --overrides "file://$TMP" --query 'tasks[0].taskArn' --output text)" \
    || die "run-task was refused (see the error above)"
  { [ -n "$task" ] && [ "$task" != None ]; } || die "$label: ECS did not start a task (capacity or permissions); see: aws ecs run-task failures"
  id="${task##*/}"
  echo "Task $id started; waiting for it to finish (a minute or two) ..."
  aws ecs wait tasks-stopped --region "$REGION" --cluster "$CLUSTER" --tasks "$task" || die "$label: the task did not stop within the wait; check the cluster in the console"
  result="$(aws ecs describe-tasks --region "$REGION" --cluster "$CLUSTER" --tasks "$task" \
    --query 'tasks[0].[containers[0].exitCode, stoppedReason]' --output text)" \
    || die "$label: could not read the task result (credentials expired?). The task may still have run: see the cluster $CLUSTER in the console"
  read -r exit_code reason <<<"$result"
  sleep 5   # log lines arrive a few seconds after the task stops
  aws logs get-log-events --region "$REGION" --log-group-name "$LOG_GROUP" --log-stream-name "web/web/$id" \
    --query 'events[].message' --output text 2>/dev/null | tr '\t' '\n' || echo "(no log lines found in $LOG_GROUP, stream web/web/$id)"
  [ "$exit_code" = 0 ] || die "$label: exit code ${exit_code:-none} ($reason)"
  EXTRA_ENV='[]'   # the settings belong to this job only
  echo "$label: ok"
}

# run_app <label> <web|migration|bootstrap> <command...>: the same app job on either variant.
run_app() {
  local label="$1" secret="$2"; shift 2
  if [ "$VARIANT" = ec2 ]; then remote "$label" "/usr/local/bin/app-job $secret $*"
  else ecs_task "$label" "$secret" "$@"; fi
}

# Puts the placeholder back in the bootstrap secret. If that fails (credentials expired during the job), say exactly what
# to run, because the RDS master login would otherwise stay in the secret.
bootstrap_cleanup() {
  "$INFRA/scripts/secrets.sh" master-out \
    || echo "STOP: could NOT put the placeholder back in the bootstrap secret. Run labcreds, then: $INFRA/scripts/secrets.sh master-out" >&2
}

job_bootstrap() {
  # Master login in for this run only; the placeholder goes back on any exit.
  ( trap 'bootstrap_cleanup' EXIT
    "$INFRA/scripts/secrets.sh" master-in
    run_app "bootstrap" bootstrap python tools/db_bootstrap.py )
}

job_migrate() {
  run_app "migrate" migration python manage.py migrate --noinput
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
  run_app "check_database" web python manage.py check_database
}

job_operator() {
  # Skips if the operator secret already holds a value, so a rerun never replaces a password the database does not have.
  if [ "$VARIANT" = fargate ]; then
    EXTRA_ENV="$(jq -nc --arg r "$REGION" '[{name:"JOB_REGION", value:$r}]')"
    ecs_task "operator" web python -c "$(cat "$INFRA/scripts/fargate_jobs/create_operator.py")"
    return
  fi
  remote "operator" "NS='$NAMESPACE'; $(cat <<'EOS'
if aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator >/dev/null 2>&1; then
  echo "operator secret already set; leaving the operator account as it is"; exit 0
fi
IMAGE=$(docker inspect --format '{{.Config.Image}}' web)
export DEMO_OPERATOR_PASSWORD="$(head -c 18 /dev/urandom | base64 | tr -d '/+=')"
docker run --rm --env-file /etc/inf2006/app.env -e AWS_SECRET_ID=inf2006-grp21/web -e DEMO_OPERATOR_PASSWORD \
  "$IMAGE" python manage.py seed_demo --no-products
# The password goes to the secret through a private file, not a command line (a command line is readable in /proc).
umask 077; F=$(mktemp); trap 'rm -f "$F"' EXIT   # removed even if the put fails
jq -cn --arg u demo-operator '{username:$u, password:$ENV.DEMO_OPERATOR_PASSWORD}' > "$F"
aws secretsmanager put-secret-value --secret-id inf2006-grp21/operator --secret-string "file://$F" >/dev/null
unset DEMO_OPERATOR_PASSWORD
echo "demo-operator created; the password is in the operator secret"
EOS
)"
}

job_refresh() {
  run_app "refresh_analytics" web python manage.py refresh_analytics --as-of "$AS_OF"
}

job_import() {
  # Only checksums.txt and product_map.csv are committed; the rest is rebuilt from data/raw (deterministic), then
  # checked against the committed checksums, so the cloud gets exactly the inputs the local tests used.
  local dir="$REPO/data/derived/shoes"
  [ -f "$dir/customers.csv" ] || (cd "$REPO" && python3 analytics/build_shoe_dataset.py)
  (cd "$dir" && sha256sum -c checksums.txt >/dev/null) || die "$dir does not match checksums.txt; rebuild it with analytics/build_shoe_dataset.py"
  echo "Dataset checksums match."
  aws s3 sync "$REPO/data/derived/shoes" "s3://$BUCKET/data/derived/shoes/" --region "$REGION" --only-show-errors --delete
  if [ "$VARIANT" = fargate ]; then
    EXTRA_ENV="$(jq -nc --arg r "$REGION" --arg b "$BUCKET" --arg n "$NAMESPACE" \
      '[{name:"JOB_REGION", value:$r}, {name:"JOB_BUCKET", value:$b}, {name:"JOB_NAMESPACE", value:$n}]')"
    ecs_task "import_dataset" web python -c "$(cat "$INFRA/scripts/fargate_jobs/import_dataset.py")"
    return
  fi
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

# Everything a fresh database needs. Bootstrap is not repeatable, so it runs only if the app cannot already use the
# database; the check runs in a subshell so its failure is an answer, not the end of the script.
job_all() {
  if (job_check) >/dev/null 2>&1; then
    echo "check_database passes: the database is already set up, so bootstrap is skipped."
  else
    job_bootstrap
  fi
  job_migrate
  if [ "$VARIANT" = ec2 ]; then job_trainer_sql; job_restart; fi
  job_import; job_operator; job_refresh
}

case "$JOB" in
  bootstrap) job_bootstrap ;;
  migrate) job_migrate ;;
  trainer-sql) job_trainer_sql ;;
  restart) job_restart ;;
  check) job_check ;;
  import) job_import ;;
  operator) job_operator ;;
  refresh) job_refresh ;;
  all) job_all ;;
esac
echo; echo "Done: $JOB"
