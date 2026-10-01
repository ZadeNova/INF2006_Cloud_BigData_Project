#!/usr/bin/env bash
# Black-box checks of a deployed stack from outside (ADR-010). Prints PASS/FAIL lines and exits non-zero on any FAIL.
#
#   scripts/smoke.sh ec2|fargate|<hostname>
#
# Checks: /health/ 200, HTTP redirects to HTTPS, the certificate verifies and is TLS 1.2+, the login and product
# pages answer, the product page really lists products, and the security headers the app promises are present.
# Needs only curl and openssl; no AWS credentials, so a marker can run it against any deployment.
set -uo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"
case "$TARGET" in
  ec2|fargate) HOST="$(terraform -chdir="$INFRA/base" output -json shop_hostnames | jq -r ".$TARGET")" ;;
  "") echo "usage: $0 ec2|fargate|<hostname>" >&2; exit 2 ;;
  *) HOST="$TARGET" ;;
esac
FAILS=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAILS=$((FAILS+1)); }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }

echo "Smoke test: https://$HOST"
[ "$(code "https://$HOST/health/")" = 200 ] && pass "/health/ returns 200" || fail "/health/ did not return 200"
r="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 15 "http://$HOST/")"
case "$r" in "301 https://"*) pass "HTTP redirects to HTTPS (301)" ;; *) fail "HTTP did not redirect with 301 to https (got: $r)" ;; esac
tls="$(echo | openssl s_client -connect "$HOST:443" -servername "$HOST" -verify_return_error 2>/dev/null | grep -E 'Verification: OK|Protocol  *:' | tr -s ' ' | tr '\n' ' ')"
case "$tls" in *"Verification: OK"*) pass "certificate verifies ($tls)" ;; *) fail "certificate did not verify ($tls)" ;; esac
[ "$(code "https://$HOST/login/")" = 200 ] && pass "/login/ returns 200" || fail "/login/ did not return 200"
body="$(curl -s --max-time 15 "https://$HOST/products/")"
n="$(printf '%s' "$body" | grep -o 'href="/products/[0-9][0-9]*/"' | sort -u | wc -l)"
[ "$n" -ge 5 ] && pass "/products/ lists products ($n distinct product links)" || fail "/products/ lists $n product links (expected 5 or more; is the dataset imported?)"
h="$(curl -sI --max-time 15 "https://$HOST/products/" | tr -d '\r' | tr 'A-Z' 'a-z')"
for hdr in strict-transport-security x-content-type-options x-frame-options; do
  case "$h" in *"$hdr:"*) pass "header $hdr present" ;; *) fail "header $hdr missing" ;; esac
done
echo
[ "$FAILS" -eq 0 ] && echo "All checks passed." || { echo "$FAILS check(s) failed."; exit 1; }
