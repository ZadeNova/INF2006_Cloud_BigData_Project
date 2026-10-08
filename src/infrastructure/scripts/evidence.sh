#!/usr/bin/env bash
# Records the cloud evidence that the load harness does not (review EVD-001 to EVD-015, docs/plans/evidence-session.md).
# Every step runs the same way on both variants and saves a dated, redacted file in evidence/raw/:
#   <CASE>_<UTC date>_<variant>_<step>.txt   (a second run of the same step gets _rerun, _rerun2, ...; nothing is overwritten)
# Each file starts with the UTC time, the git commit and the command, and ends with the exit code and end time. Account IDs,
# public IPs and email addresses are replaced before the file is written; the unredacted copy stays outside the
# repository in $EVIDENCE_SCRATCH (default ~/evidence-scratch).
#
#   scripts/evidence.sh preflight                    PRE: image in ECR, LabRole trust, service-linked roles, Fargate quota, alarm email
#   scripts/evidence.sh <ec2|fargate> up             up.sh, recorded with start and end time (OPS)
#   scripts/evidence.sh <ec2|fargate> security       stack IDs; SEC-10 smoke and listeners; SEC-09 RDS, security groups, S3; SEC-11 secrets
#   scripts/evidence.sh <ec2|fargate> func           FUNC-03: the harness's smoke visit (register, login, cart, checkout) from this laptop, exported
#   scripts/evidence.sh <ec2|fargate> pin MIN MAX DESIRED count|block
#                                                    capacity and WAF mode for the next runs: plan, confirm, apply, wait until healthy
#   scripts/evidence.sh <ec2|fargate> alarm          MON-03: force the 5xx alarm to ALARM, wait for OK, save the history
#   scripts/evidence.sh <ec2|fargate> waf            SEC-17: login burst against block mode (pin ... block first; the last test on a variant)
#   scripts/evidence.sh <ec2|fargate> logs           MON-01 sample, MON-02 saved queries, SEC-18 secrets-in-logs; before down
#   scripts/evidence.sh <ec2|fargate> down           down.sh, recorded; removes the session's pin file
#   scripts/evidence.sh rec NAME COMMAND...          record any other command the same way (NAME without .txt)
#
# Needs: lab credentials, aws, jq, terraform, curl, python3 (and tests/load set up for `func`). Run from anywhere.
set -uo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$INFRA/../.." && pwd)"
RAW="${EVIDENCE_RAW:-$REPO/evidence/raw}"   # override only to test this script
SCRATCH="${EVIDENCE_SCRATCH:-$HOME/evidence-scratch}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$REGION" AWS_PAGER=""
PREFIX="inf2006-grp21"
D="$(date -u +%F)"

die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }   # show each command inside the saved file, then run it

# Account IDs and public IPs (the harness's own rule, tests/load/common.py), plus email addresses.
redact() {
  python3 -c '
import re, sys
sys.path.insert(0, sys.argv[1])
import common
text = common.redact(sys.stdin.read())
sys.stdout.write(re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", "<EMAIL>", text))' "$REPO/tests/load"
}

# rec NAME COMMAND...: live output on the terminal (prompts still work), unredacted copy in $SCRATCH, redacted copy in evidence/raw.
rec() {
  local name="$1"; shift
  mkdir -p "$SCRATCH" "$RAW"; chmod 700 "$SCRATCH"
  local base="$name" n=1
  while [ -e "$RAW/$base.txt" ]; do
    if [ "$n" = 1 ]; then base="${name}_rerun"; else base="${name}_rerun$n"; fi
    n=$((n + 1))
  done
  local tmp="$SCRATCH/$base.txt" rc
  { echo "# file: evidence/raw/$base.txt"; echo "# date_utc: $(date -u +%FT%TZ)"
    echo "# commit: $(git -C "$REPO" rev-parse --short HEAD)"; echo "# command: $*"; } > "$tmp"
  "$@" 2>&1 | tee -a "$tmp"; rc=${PIPESTATUS[0]}
  echo "# exit: $rc  end_utc: $(date -u +%FT%TZ)" >> "$tmp"
  redact < "$tmp" > "$RAW/$base.txt" || die "redaction failed; nothing saved for $base (unredacted copy: $tmp)"
  echo ">> saved evidence/raw/$base.txt (exit $rc)"
  return "$rc"
}

need_creds() { aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 || die "no working lab credentials (run labcreds)"; }
base_out() { terraform -chdir="$INFRA/base" output -raw "$1" 2>/dev/null; }
tfo() { terraform -chdir="$INFRA/$V" output -raw "$1" 2>/dev/null; }

load_stack() {
  STACK="$PREFIX-$V"
  HOST="$(tfo hostname)" || true
  [ -n "${HOST:-}" ] || die "the $V stack is not up (no outputs in $V/). Run: scripts/evidence.sh $V up"
  TG="$(tfo target_group_arn)"; LG="$(tfo log_group_name)"; ACL="$(tfo web_acl_name)"
}

# healthy targets right now
healthy_count() {
  aws elbv2 describe-target-health --target-group-arn "$TG" \
    --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' --output text
}

# --- preflight ------------------------------------------------------------------------------------------------

pre_image() {
  local repo tag_a tag_b
  repo="$(base_out ecr_repository_name)"
  tag_a="$(sed -n 's/^image_tag *= *"\(.*\)".*/\1/p' "$INFRA/ec2/image.auto.tfvars" 2>/dev/null)"
  tag_b="$(sed -n 's/^image_tag *= *"\(.*\)".*/\1/p' "$INFRA/fargate/image.auto.tfvars" 2>/dev/null)"
  echo "image_tag in ec2/: ${tag_a:-none}   in fargate/: ${tag_b:-none, up.sh fargate copies the ec2 tag}"
  [ -n "$tag_a" ] || { echo "VERDICT: no image selected for ec2 (up.sh ec2 will push one)"; return 1; }
  run aws ecr describe-images --repository-name "$repo" --image-ids "imageTag=$tag_a" \
    --query 'imageDetails[0].{tags:imageTags,digest:imageDigest,pushed:imagePushedAt}' \
    && echo "VERDICT: $tag_a is in ECR" || { echo "VERDICT: $tag_a is NOT in ECR (push-image.sh builds a new digest; record it)"; return 1; }
}

pre_labrole() {
  local p
  echo "\$ aws iam get-role --role-name LabRole --query Role.AssumeRolePolicyDocument.Statement[].Principal"
  p="$(aws iam get-role --role-name LabRole --query 'Role.AssumeRolePolicyDocument.Statement[].Principal' --output json)" || return 1
  echo "$p"
  if grep -q 'ecs-tasks.amazonaws.com' <<<"$p"; then echo "VERDICT: LabRole trusts ecs-tasks.amazonaws.com (variant B can run)"
  else echo "VERDICT: LabRole does NOT trust ecs-tasks.amazonaws.com: do not apply fargate/ (B is 'designed, blocked by lab IAM')"; return 1; fi
}

pre_slr() {
  local r
  for r in AWSServiceRoleForECS AWSServiceRoleForApplicationAutoScaling_ECSService; do
    if run aws iam get-role --role-name "$r" --query 'Role.{name:RoleName,created:CreateDate}' --output json; then echo "VERDICT: $r exists"
    else echo "VERDICT: $r missing. AWS normally creates it on first use; if the fargate apply fails on it, try: aws iam create-service-linked-role --aws-service-name $( [ "$r" = AWSServiceRoleForECS ] && echo ecs.amazonaws.com || echo ecs.application-autoscaling.amazonaws.com)"; fi
  done
}

pre_quota() {
  run aws service-quotas get-service-quota --service-code fargate --quota-code L-3032A538 \
    --query 'Quota.{name:QuotaName,value:Value}' --output json \
    && echo "VERDICT: B needs 4 vCPU for two tasks (6 while a one-off job task runs)" \
    || echo "VERDICT: quota not readable in the lab; the first pin to 2 tasks is the test"
}

pre_sns() {
  local t subs
  t="$(base_out sns_topic_arn)"
  echo "\$ aws sns list-subscriptions-by-topic --topic-arn $t"
  subs="$(aws sns list-subscriptions-by-topic --topic-arn "$t" --query 'Subscriptions[].{protocol:Protocol,endpoint:Endpoint,arn:SubscriptionArn}' --output json)" || return 1
  echo "$subs"
  if jq -e 'map(select(.protocol=="email" and .arn!="PendingConfirmation")) | length > 0' <<<"$subs" >/dev/null; then
    echo "VERDICT: an email subscription is confirmed (MON-03 will send email)"
  else echo "VERDICT: NO confirmed email subscription: click the link in the 'AWS Notification - Subscription Confirmation' email before MON-03"; return 1; fi
}

pre_pins() {
  local s f
  for s in ec2 fargate; do
    f="$INFRA/$s/session.auto.tfvars"
    if [ -f "$f" ]; then echo "$s/session.auto.tfvars exists (left from an earlier session):"; cat "$f"; echo "VERDICT: up.sh would apply these values; 'evidence.sh $s up' removes it first"
    else echo "$s: no session pin file (defaults: 1/2/1, WAF count)"; fi
  done
}

preflight() {
  need_creds
  terraform -chdir="$INFRA/base" output -raw s3_bucket_name >/dev/null 2>&1 || die "base/ has no outputs here; run scripts/status.sh"
  local c fail=0
  for c in image labrole slr quota sns pins; do
    say "PRE $c"; rec "PRE_${D}_$c" "pre_$c" || fail=1
  done
  say "Preflight done"; grep -h '^VERDICT' "$RAW"/PRE_"${D}"_*.txt | sort -u
  [ "$fail" = 0 ] || echo "At least one check needs attention (see the VERDICT lines above and docs/plans/evidence-session.md, 'Stop rules')."
}

# --- up / down ------------------------------------------------------------------------------------------------

do_up() {
  if [ -f "$INFRA/$V/session.auto.tfvars" ]; then
    echo "Removing $V/session.auto.tfvars from an earlier session, so up.sh applies the defaults (1/2/1, WAF count):"
    cat "$INFRA/$V/session.auto.tfvars"; rm -f "$INFRA/$V/session.auto.tfvars"
  fi
  rec "OPS_${D}_${V}_up" "$INFRA/scripts/up.sh" "$V"
}

do_down() {
  rec "OPS_${D}_${V}_down" "$INFRA/scripts/down.sh" "$V"
  local rc=$?
  if [ "$rc" = 0 ] && [ -f "$INFRA/$V/session.auto.tfvars" ]; then rm -f "$INFRA/$V/session.auto.tfvars"; echo "Removed $V/session.auto.tfvars."; fi
  return "$rc"
}

# --- security -------------------------------------------------------------------------------------------------

ids() {
  # Kept so CloudWatch metrics stay reachable by hand after down.sh (review EVD-009): 1-minute data lasts about 15 days.
  run terraform -chdir="$INFRA/$V" output
  run aws elbv2 describe-target-groups --target-group-arns "$TG" --query 'TargetGroups[0].{target_group:TargetGroupArn,load_balancers:LoadBalancerArns}'
}

sec10_listeners() {
  local alb
  alb="$(aws elbv2 describe-load-balancers --names "$STACK-alb" --query 'LoadBalancers[0].LoadBalancerArn' --output text)"
  run aws elbv2 describe-listeners --load-balancer-arn "$alb" \
    --query 'Listeners[].{port:Port,protocol:Protocol,tls_policy:SslPolicy,action:DefaultActions[0].Type,redirect:DefaultActions[0].RedirectConfig}'
}

sec09_rds() {
  run aws rds describe-db-instances \
    --query "DBInstances[?starts_with(DBInstanceIdentifier, '$PREFIX')].{id:DBInstanceIdentifier,publicly_accessible:PubliclyAccessible,encrypted:StorageEncrypted,multi_az:MultiAZ,class:DBInstanceClass,engine:EngineVersion,security_groups:VpcSecurityGroups[].VpcSecurityGroupId}"
}

sec09_security_groups() {
  local alb app db
  alb="$(terraform -chdir="$INFRA/$V" output -json security_group_ids | jq -r .alb)"
  app="$(terraform -chdir="$INFRA/$V" output -json security_group_ids | jq -r .app)"
  db="$(base_out sg_db_id)"
  echo "alb=$alb  app=$app  db=$db"
  run aws ec2 describe-security-groups --group-ids "$alb" "$app" "$db" \
    --query 'SecurityGroups[].{name:GroupName,id:GroupId,inbound:IpPermissions[].{from_port:FromPort,to_port:ToPort,protocol:IpProtocol,cidr:IpRanges[].CidrIp,from_groups:UserIdGroupPairs[].GroupId}}'
}

sec09_s3() {
  local b
  b="$(base_out s3_bucket_name)"
  run aws s3api get-public-access-block --bucket "$b"
  run aws s3api get-bucket-policy-status --bucket "$b" || echo "(no bucket policy: nothing in a policy can make the bucket public)"
  echo "anonymous list request:"; run curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 15 "https://$b.s3.amazonaws.com/"
  echo "anonymous object request:"; run curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 15 "https://$b.s3.amazonaws.com/imports/anything.csv"
}

sec11_runtime() {
  if [ "$V" = ec2 ]; then
    run aws ec2 describe-launch-template-versions --launch-template-name "$STACK-lt" --versions '$Latest' \
      --query 'LaunchTemplateVersions[0].LaunchTemplateData.IamInstanceProfile'
    echo "\$ (user data, decoded) lines naming a secret, password or key:"
    aws ec2 describe-launch-template-versions --launch-template-name "$STACK-lt" --versions '$Latest' \
      --query 'LaunchTemplateVersions[0].LaunchTemplateData.UserData' --output text | base64 -d | grep -niE 'secret|password|key' \
      || echo "(none)"
  else
    run aws ecs describe-task-definition --task-definition "$STACK-app" \
      --query 'taskDefinition.{task_role:taskRoleArn,execution_role:executionRoleArn,environment:containerDefinitions[0].environment,secrets:containerDefinitions[0].secrets}'
  fi
}

security() {
  need_creds; load_stack
  say "Stack IDs"; rec "SESSION_${D}_${V}_ids" ids
  say "SEC-10 smoke"; rec "SEC-10_${D}_${V}_smoke" "$INFRA/scripts/smoke.sh" "$V"
  say "SEC-10 listeners"; rec "SEC-10_${D}_${V}_listeners" sec10_listeners
  say "SEC-09 RDS"; rec "SEC-09_${D}_${V}_rds" sec09_rds
  say "SEC-09 security groups"; rec "SEC-09_${D}_${V}_security-groups" sec09_security_groups
  say "SEC-09 S3"; rec "SEC-09_${D}_${V}_s3" sec09_s3
  say "SEC-11 runtime identity and secret references"; rec "SEC-11_${D}_${V}_runtime" sec11_runtime
  say "SEC-11 secrets match the database"; rec "SEC-11_${D}_${V}_secrets-check" "$INFRA/scripts/secrets.sh" check
  say "SEC-11 the app reads them"; rec "SEC-11_${D}_${V}_app-check" "$INFRA/scripts/jobs.sh" "$V" check
}

# --- FUNC-03 --------------------------------------------------------------------------------------------------

func_summary() {
  python3 - "$1" <<'PYEOF'
import collections, csv, glob, os, sys
rows = []
for path in glob.glob(os.path.join(sys.argv[1], "requests-*.csv")):
    with open(path, newline="") as f:
        rows += list(csv.DictReader(f))
by = collections.Counter((r.get("visit", ""), r.get("action", ""), r.get("outcome", "")) for r in rows)
print(f"{len(rows)} requests in {sys.argv[1].rsplit('/', 1)[-1]}")
print(f"{'visit':<12} {'action':<22} {'outcome':<15} count")
for (visit, action, outcome), n in sorted(by.items()):
    print(f"{visit:<12} {action:<22} {outcome:<15} {n}")
errors = sum(n for (_, _, o), n in by.items() if o == "error")
print(f"errors: {errors}")
PYEOF
}

func() {
  need_creds; load_stack
  local load="$REPO/tests/load" py n id url="https://$HOST"
  py="$load/.venv/bin/python"; [ -x "$py" ] || die "tests/load/.venv is missing (tests/load/README.md, 'One-time setup')"
  if [ -z "${LOADTEST_PASSWORD:-}" ] && [ -f "$load/.env" ]; then set -a; . "$load/.env"; set +a; fi
  [ -n "${LOADTEST_PASSWORD:-}" ] || die "LOADTEST_PASSWORD is not set (tests/load/.env, see tests/load/README.md)"
  n=1; while [ -e "$load/out/LOAD-$V-smoke-r${n}_$D" ] || [ -e "$RAW/LOAD-$V-smoke-r${n}_$D" ]; do n=$((n + 1)); done
  id="LOAD-$V-smoke-r${n}_$D"
  say "FUNC-03 test accounts (idempotent)"
  (cd "$load" && "$py" accounts.py create --base-url "$url" --count 4) || die "account creation failed"
  say "FUNC-03 visit run $id (about 75 s)"
  (cd "$load" && "$py" run.py smoke --variant "$V" --base-url "$url" --repeat "$n" --location laptop --yes) || echo "WARNING: run.py exited non-zero; recorded anyway"
  say "FUNC-03 export"
  (cd "$load" && "$py" aws_capture.py export --variant "$V" --run-id "$id" --run-dir "out/$id") || die "export failed; the run stays in tests/load/out/$id"
  rec "FUNC-03_${D}_${V}_summary" func_summary "$RAW/$id"
}

# --- pin ------------------------------------------------------------------------------------------------------

pin() {
  need_creds; load_stack
  local mn="${1:-}" mx="${2:-}" de="${3:-}" mode="${4:-}" a t0 h
  [[ "$mn" =~ ^[0-9]+$ && "$mx" =~ ^[0-9]+$ && "$de" =~ ^[0-9]+$ ]] || die "usage: evidence.sh $V pin MIN MAX DESIRED count|block"
  case "$mode" in count|block) ;; *) die "usage: evidence.sh $V pin MIN MAX DESIRED count|block" ;; esac
  [ "$mn" -le "$de" ] && [ "$de" -le "$mx" ] || die "need MIN <= DESIRED <= MAX"
  cat > "$INFRA/$V/session.auto.tfvars" <<EOF
# Written by scripts/evidence.sh pin at $(date -u +%FT%TZ). Gitignored. Overrides the defaults (1/2/1, count);
# 'evidence.sh $V down' or 'evidence.sh $V up' removes it.
min_capacity     = $mn
max_capacity     = $mx
desired_capacity = $de
waf_login_action = "$mode"
EOF
  say "Pin $V to min $mn, max $mx, desired $de, WAF $mode"
  rec "OPS_${D}_${V}_pin-$mn-$mx-$de-${mode}_plan" "$INFRA/scripts/tf.sh" "$V" plan || die "plan failed"
  read -r -p "Apply this plan? Type yes: " a; [ "$a" = yes ] || die "not applied (session.auto.tfvars is written; pin again or remove it)"
  t0="$(date +%s)"
  rec "OPS_${D}_${V}_pin-$mn-$mx-$de-${mode}_apply" "$INFRA/scripts/tf.sh" "$V" apply || die "apply failed"
  say "Waiting for $de healthy target(s) (up to 15 minutes)"
  while :; do
    h="$(healthy_count)"
    printf '%s  healthy %s of %s wanted\n' "$(date -u +%T)" "$h" "$de"
    [ "$h" = "$de" ] && break
    [ $(( $(date +%s) - t0 )) -gt 900 ] && die "not $de healthy after 15 minutes: check the target group and the stop rules"
    sleep 15
  done
  echo "Healthy at $(date -u +%T) UTC. Settle rule (EVD-010): start the next run at or after $(date -u -d '+3 min' +%T) UTC."
}

# --- MON-03 ---------------------------------------------------------------------------------------------------

alarm_wait_ok() {
  local name="$1" s i
  for i in $(seq 1 40); do
    s="$(aws cloudwatch describe-alarms --alarm-names "$name" --query 'MetricAlarms[0].StateValue' --output text)"
    printf '%s  %s\n' "$(date -u +%T)" "$s"
    [ "$s" = OK ] && return 0
    sleep 15
  done
  echo "did not return to OK within 10 minutes"; return 1
}

alarm() {
  need_creds; load_stack
  local name="$STACK-target-5xx" t0
  t0="$(date -u -d '-1 min' +%FT%TZ)"
  say "MON-03 force $name to ALARM (tests the notification path, not detection)"
  rec "MON-03_${D}_${V}_force" run aws cloudwatch set-alarm-state --alarm-name "$name" --state-value ALARM \
    --state-reason "Evidence session: forced to test the alarm-to-email path"
  say "MON-03 waiting for the next evaluation to return it to OK"
  rec "MON-03_${D}_${V}_return-to-ok" alarm_wait_ok "$name"
  sleep 20   # the OK notification's history item lands a few seconds after the state change
  say "MON-03 history (state changes and the SNS actions)"
  rec "MON-03_${D}_${V}_history" run aws cloudwatch describe-alarm-history --alarm-name "$name" --start-date "$t0" \
    --query 'AlarmHistoryItems[].{time:Timestamp,type:HistoryItemType,summary:HistorySummary}'
  echo
  echo "Now save the two emails (ALARM and OK) as screenshots: evidence/raw/MON-03_${D}_${V}_email-alarm.png and _email-ok.png."
  echo "Crop or blur the recipient address, the account number and the unsubscribe link before saving."
}

# --- SEC-17 ---------------------------------------------------------------------------------------------------

waf_mode() {
  local id
  id="$(aws wafv2 list-web-acls --scope REGIONAL --query "WebACLs[?Name=='$ACL'].Id | [0]" --output text)"
  aws wafv2 get-web-acl --scope REGIONAL --name "$ACL" --id "$id" \
    --query "WebACL.Rules[?Name=='login-rate-limit'].Action | [0]" --output json | jq -r 'keys[0] // "none"'
}

waf_burst() {
  local jar tok code server blocked=0 i
  jar="$(mktemp)"
  echo "POST /login/ with a valid CSRF token and a wrong password for user waf-probe, every 3 s, until 5 WAF blocks in a row or 80 attempts."
  echo "WAF block = status 403 with 'Server: awselb/2.0' (the load balancer). A Django refusal would carry 'Server: gunicorn'."
  for i in $(seq 1 80); do
    tok="$(curl -s -c "$jar" -b "$jar" --max-time 15 "https://$HOST/login/" | sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p' | head -1)"
    read -r code server < <(curl -s -o /dev/null -D - -b "$jar" -c "$jar" --max-time 15 \
      -e "https://$HOST/login/" -H "Origin: https://$HOST" \
      --data-urlencode "csrfmiddlewaretoken=$tok" --data-urlencode "username=waf-probe" --data-urlencode "password=wrong-$i" \
      "https://$HOST/login/" | tr -d '\r' | awk 'NR==1{c=$2} tolower($1)=="server:"{s=$2} END{print c, (s==""?"-":s)}')
    printf '%s  attempt %2d  HTTP %s  server %s\n' "$(date -u +%T)" "$i" "${code:-none}" "${server:--}"
    if [ "${code:-}" = 403 ] && [ "${server:-}" = awselb/2.0 ]; then blocked=$((blocked + 1)); else blocked=0; fi
    [ "$blocked" -ge 5 ] && break
    sleep 3
  done
  echo "browsing while the login is blocked: GET /products/ -> HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://$HOST/products/")"
  rm -f "$jar"
  [ "$blocked" -ge 5 ]
}

waf_metrics() {
  local w
  for w in BlockedRequests CountedRequests; do
    run aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 --metric-name "$w" \
      --dimensions "Name=WebACL,Value=$ACL" "Name=Rule,Value=$STACK-login-rate" "Name=Region,Value=$REGION" \
      --start-time "$(date -u -d '-30 min' +%FT%TZ)" --end-time "$(date -u +%FT%TZ)" --period 60 --statistics Sum \
      --query 'sort_by(Datapoints,&Timestamp)[].{time:Timestamp,sum:Sum}'
  done
}

waf_samples() {
  # Request headers are removed: they carry the session and CSRF cookies (review EVD-012).
  local arn
  arn="$(aws wafv2 list-web-acls --scope REGIONAL --query "WebACLs[?Name=='$ACL'].ARN | [0]" --output text)"
  echo "\$ aws wafv2 get-sampled-requests --rule-metric-name $STACK-login-rate (last 30 min, headers removed)"
  aws wafv2 get-sampled-requests --web-acl-arn "$arn" --rule-metric-name "$STACK-login-rate" --scope REGIONAL \
    --time-window "StartTime=$(date -u -d '-30 min' +%FT%TZ),EndTime=$(date -u +%FT%TZ)" --max-items 100 --output json \
    | jq '{PopulationSize, SampledRequests: [.SampledRequests[] | {Timestamp, Action, RuleNameWithinRuleGroup, ClientIP: .Request.ClientIP, Method: .Request.Method, URI: .Request.URI}]}'
}

waf() {
  need_creds; load_stack
  local m; m="$(waf_mode)"
  [ "$m" = Block ] || die "the login rule is in '$m' mode. First: scripts/evidence.sh $V pin <min> <max> <desired> block"
  say "SEC-17 login burst against block mode"; rec "SEC-17_${D}_${V}_burst" waf_burst
  echo "Waiting 3 minutes so the WAF metrics for the last minutes are published..."; sleep 180
  say "SEC-17 WAF metrics"; rec "SEC-17_${D}_${V}_metrics" waf_metrics
  say "SEC-17 sampled requests"; rec "SEC-17_${D}_${V}_samples" waf_samples
  echo
  echo "This laptop's IP stays blocked from POST /login/ on $V for about 5 minutes."
  echo "Run no further load test on $V in block mode: next is 'evidence.sh $V logs', then 'evidence.sh $V down'"
  echo "(down removes the pin file, so the next up.sh is back in count mode)."
}

# --- logs (MON-01, MON-02, SEC-18) ----------------------------------------------------------------------------

insights() {
  local q="$1" qid res st _
  echo "\$ aws logs start-query --log-group-name $LG (from $(date -u -d "@$SINCE" +%FT%TZ) to now)"
  echo "query: $q"
  qid="$(aws logs start-query --log-group-name "$LG" --start-time "$SINCE" --end-time "$(date +%s)" --query-string "$q" --query queryId --output text)" || return 1
  for _ in $(seq 1 60); do
    res="$(aws logs get-query-results --query-id "$qid" --output json)"; st="$(jq -r .status <<<"$res")"
    case "$st" in Complete|Failed|Cancelled|Timeout) break ;; esac
    sleep 2
  done
  jq '{status, statistics, results: [.results[] | map({(.field): .value}) | add]}' <<<"$res"
  [ "$st" = Complete ]
}

saved_query() {
  local q
  q="$(aws logs describe-query-definitions --query-definition-name-prefix "$STACK/$1" --query 'queryDefinitions[0].queryString' --output text)"
  [ -n "$q" ] && [ "$q" != None ] || { echo "saved query $STACK/$1 not found"; return 1; }
  echo "saved query: $STACK/$1"
  insights "$q"
}

logs() {
  need_creds; load_stack
  SINCE="$(date -d "-${SINCE_HOURS:-6} hours" +%s)"   # the window: the last 6 hours, or SINCE_HOURS
  say "MON-01 the latest 20 log lines"
  rec "MON-01_${D}_${V}_sample" insights 'fields @timestamp, @logStream, @message | sort @timestamp desc | limit 20'
  say "MON-01 requests by status per 5 minutes"
  rec "MON-01_${D}_${V}_status-per-5min" insights 'filter ispresent(status) | stats count(*) as requests by status, bin(5m) as window | sort window asc'
  say "MON-02 saved queries"
  rec "MON-02_${D}_${V}_recent-errors-and-security-warnings" saved_query recent-errors-and-security-warnings
  rec "MON-02_${D}_${V}_errors-and-warnings-per-minute" saved_query errors-and-warnings-per-minute
  say "SEC-18 secret-looking words in the CloudWatch logs"
  rec "SEC-18_${D}_${V}_count" insights 'filter @message like /(?i)(password|csrftoken|csrfmiddlewaretoken|sessionid|secret_key)/ | stats count(*) as matches'
  rec "SEC-18_${D}_${V}_matches" insights 'fields @timestamp, @message | filter @message like /(?i)(password|csrftoken|csrfmiddlewaretoken|sessionid|secret_key)/ | limit 20'
  echo
  echo "Every harness run on $V must be exported before 'evidence.sh $V down' (aws_capture.py export)."
}

# --- dispatch -------------------------------------------------------------------------------------------------

case "${1:-}" in
  preflight) preflight ;;
  rec) shift; [ $# -ge 2 ] || die "usage: evidence.sh rec NAME COMMAND..."; rec "$@" ;;
  ec2|fargate)
    V="$1"; STEP="${2:-}"; shift 2 2>/dev/null || true
    case "$STEP" in
      up) need_creds; do_up ;;
      down) need_creds; do_down ;;
      security) security ;;
      func) func ;;
      pin) pin "$@" ;;
      alarm) alarm ;;
      waf) waf ;;
      logs) logs ;;
      *) die "usage: evidence.sh $V up|security|func|pin|alarm|waf|logs|down" ;;
    esac ;;
  *) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
