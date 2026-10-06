#!/usr/bin/env bash
# Fill, check and handle the four Secrets Manager secrets without a value ever appearing on a command line,
# in Terraform state or in output (ADR-005; field contract: src/config/secrets.py).
#
#   scripts/secrets.sh fill         add missing fields, never change an existing password or key; once, safe to rerun
#   scripts/secrets.sh check        prints match / DIFFER and key names only
#   scripts/secrets.sh master-in    copy the RDS master login into the bootstrap secret, immediately before db_bootstrap
#   scripts/secrets.sh master-out   put the placeholder back, immediately after db_bootstrap
#
# `fill` never regenerates: a password already stored is kept, because after db_bootstrap the database holds it.
# It always refreshes POSTGRES_HOST and POSTGRES_DB and re-derives the copies the contract demands
# (bootstrap's runtime and migration logins, migration's signing key), so they cannot drift.
# RDS rotates the master password every 7 days: run master-in only right before bootstrap, master-out right after.
# Needs: lab credentials, aws, jq, openssl, terraform. Reads the host and master secret from base/ outputs.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PREFIX="inf2006-grp21"
DBNAME="inf2006"
PLACEHOLDER="replace-before-bootstrap"   # the loader refuses values starting with "replace-" at runtime
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

for t in aws jq openssl terraform; do command -v "$t" >/dev/null || die "$t is required"; done
aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"

umask 077
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

# Only "no value yet" (ResourceNotFoundException, also an empty container) counts as {}; any other failure stops the script,
# so a hiccup can never look like an empty secret and lead to new passwords being generated and stored.
get() {
  local out
  if out="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$PREFIX/$1" --query SecretString --output text 2>&1)"; then
    printf '%s' "$out"
  elif printf '%s' "$out" | grep -q ResourceNotFoundException; then
    echo '{}'
  else
    die "could not read the $1 secret: $(printf '%s' "$out" | head -1)"
  fi
}
# put <name> <json in env var named by $2>: the value goes through a private temp file, not argv.
put() { printf '%s' "${!2}" > "$TMP"; aws secretsmanager put-secret-value --region "$REGION" --secret-id "$PREFIX/$1" \
  --secret-string "file://$TMP" >/dev/null && echo "$1: updated, keys: $(jq -r 'keys | join(",")' "$TMP")"; }
load() { export W M T B; W="$(get web)"; M="$(get migration)"; T="$(get trainer)"; B="$(get bootstrap)"; }

cmd_fill() {
  HOST="$(terraform -chdir="$INFRA/base" output -raw db_host)"; export HOST DBNAME
  export PW_WEB PW_MIG PW_TRN DJ
  PW_WEB="$(openssl rand -hex 24)"; PW_MIG="$(openssl rand -hex 24)"; PW_TRN="$(openssl rand -hex 24)"
  DJ="$(openssl rand -base64 48 | tr -d '\n')"; export PLACEHOLDER
  load
  # Existing values win over the generated ones; host and db are always refreshed.
  W2="$(jq -ecn '({POSTGRES_USER:"inf2006_web", POSTGRES_PASSWORD:$ENV.PW_WEB, DJANGO_SECRET_KEY:$ENV.DJ} + ($ENV.W|fromjson))
    + {POSTGRES_HOST:$ENV.HOST, POSTGRES_DB:$ENV.DBNAME}
    | with_entries(select(.key | IN("POSTGRES_DB","POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","DJANGO_SECRET_KEY","POSTGRES_PORT")))')"
  export W2
  M2="$(jq -ecn '({POSTGRES_USER:"inf2006_migration", POSTGRES_PASSWORD:$ENV.PW_MIG} + ($ENV.M|fromjson))
    + {POSTGRES_HOST:$ENV.HOST, POSTGRES_DB:$ENV.DBNAME, DJANGO_SECRET_KEY:($ENV.W2|fromjson|.DJANGO_SECRET_KEY)}
    | with_entries(select(.key | IN("POSTGRES_DB","POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","DJANGO_SECRET_KEY","POSTGRES_PORT")))')"
  T2="$(jq -ecn '({POSTGRES_USER:"inf2006_trainer", POSTGRES_PASSWORD:$ENV.PW_TRN} + ($ENV.T|fromjson))
    + {POSTGRES_HOST:$ENV.HOST, POSTGRES_DB:$ENV.DBNAME}
    | with_entries(select(.key | IN("POSTGRES_DB","POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_PORT")))')"
  export M2 T2
  B2="$(jq -ecn '({BOOTSTRAP_USER:$ENV.PLACEHOLDER, BOOTSTRAP_PASSWORD:$ENV.PLACEHOLDER} + ($ENV.B|fromjson))
    + {POSTGRES_HOST:$ENV.HOST, POSTGRES_DB:$ENV.DBNAME,
       POSTGRES_USER:($ENV.W2|fromjson|.POSTGRES_USER), POSTGRES_PASSWORD:($ENV.W2|fromjson|.POSTGRES_PASSWORD),
       MIGRATION_USER:($ENV.M2|fromjson|.POSTGRES_USER), MIGRATION_PASSWORD:($ENV.M2|fromjson|.POSTGRES_PASSWORD)}
    | with_entries(select(.key | IN("POSTGRES_DB","POSTGRES_HOST","POSTGRES_USER","POSTGRES_PASSWORD","MIGRATION_USER","MIGRATION_PASSWORD","BOOTSTRAP_USER","BOOTSTRAP_PASSWORD","POSTGRES_PORT")))')"
  export B2
  put web W2; put migration M2; put trainer T2; put bootstrap B2
  unset W M T B W2 M2 T2 B2 PW_WEB PW_MIG PW_TRN DJ
  cmd_check
}

cmd_check() {
  load
  jq -rn '($ENV.W|fromjson) as $w | ($ENV.M|fromjson) as $m | ($ENV.B|fromjson) as $b | ($ENV.T|fromjson) as $t |
    [["runtime login", $w.POSTGRES_USER == $b.POSTGRES_USER and $w.POSTGRES_PASSWORD == $b.POSTGRES_PASSWORD],
     ["migration login", $m.POSTGRES_USER == $b.MIGRATION_USER and $m.POSTGRES_PASSWORD == $b.MIGRATION_PASSWORD],
     ["signing key", $w.DJANGO_SECRET_KEY == $m.DJANGO_SECRET_KEY],
     ["host and db", ([$w,$m,$t,$b] | map(.POSTGRES_HOST, .POSTGRES_DB) | unique | length) == 2]]
    | .[] | "\(.[0]): \(if .[1] then "match" else "DIFFER" end)"'
  for n in W M T B; do jq -rn --arg n "$n" '"\($n): " + (($ENV[$n]|fromjson) | keys | join(","))'; done
  unset W M T B
}

cmd_master() {
  load
  if [ "$1" = in ]; then
    ARN="$(terraform -chdir="$INFRA/base" output -raw db_master_secret_arn)"
    export R; R="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$ARN" --query SecretString --output text)" \
      || die "could not read the RDS master secret"
    B2="$(jq -ecn '($ENV.B|fromjson) + {BOOTSTRAP_USER:($ENV.R|fromjson|.username), BOOTSTRAP_PASSWORD:($ENV.R|fromjson|.password)}')"
    unset R
    echo "Run db_bootstrap now, then: scripts/secrets.sh master-out"
  else
    export PLACEHOLDER
    B2="$(jq -ecn '($ENV.B|fromjson) + {BOOTSTRAP_USER:$ENV.PLACEHOLDER, BOOTSTRAP_PASSWORD:$ENV.PLACEHOLDER}')"
  fi
  export B2; put bootstrap B2; unset B2 W M T B
}

case "${1:-}" in
  fill) cmd_fill ;;
  check) cmd_check ;;
  master-in) cmd_master in ;;
  master-out) cmd_master out ;;
  *) die "usage: $0 <fill|check|master-in|master-out>" ;;
esac
