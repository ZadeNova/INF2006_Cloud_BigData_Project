#!/usr/bin/env bash
# Delegate a subdomain of a domain YOU own to someone else's Route 53 zone (so their ACM certificate can validate).
#
#   scripts/delegate-subdomain.sh <subdomain> <ns1> <ns2> <ns3> <ns4> [--apply]
#   e.g. scripts/delegate-subdomain.sh mine.fourtytwofactors.me ns-1.awsdns-01.org ns-2.awsdns-02.com ns-3.awsdns-03.net ns-4.awsdns-04.co.uk --apply
#
# Run it with lab credentials in the AWS account that holds the PARENT domain's Route 53 hosted zone (for the team, the
# account that ran `up.sh base`). Without --apply it only shows the record it would create. The four name servers are the
# ones the other person's `up.sh base` printed ("ACTION NEEDED NOW"). It creates one NS record in the parent zone and
# changes nothing else. Remove it later with the same command and DELETE instead of UPSERT (aws route53 console).
set -euo pipefail
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[ "$#" -ge 5 ] || die "usage: $0 <subdomain> <ns1> <ns2> <ns3> <ns4> [--apply]"
SUB="${1%.}"; shift
APPLY=no; NS=()
for a in "$@"; do [ "$a" = "--apply" ] && APPLY=yes || NS+=("${a%.}."); done
[ "${#NS[@]}" -eq 4 ] || die "give exactly four name servers (got ${#NS[@]})"
for n in "${NS[@]}"; do case "$n" in ns-*.awsdns-*) ;; *) die "'$n' does not look like a Route 53 name server (ns-NNN.awsdns-NN.xxx)";; esac; done
case "$SUB" in *.*.*) ;; *) die "'$SUB' must be a subdomain (for example mine.example.com), not the apex";; esac
PARENT="${SUB#*.}"
command -v aws >/dev/null && command -v jq >/dev/null || die "aws and jq are required"
aws sts get-caller-identity >/dev/null 2>&1 || die "no working lab credentials in this shell (run labcreds first)"

# The parent zone in THIS account whose servers are the ones the internet uses for the parent (an account can hold stale zones).
want=""; command -v dig >/dev/null && want="$(dig +short NS "$PARENT" | sed 's/\.$//' | tr 'A-Z' 'a-z' | sort | tr '\n' ' ')"
ZONE=""
for id in $(aws route53 list-hosted-zones-by-name --dns-name "$PARENT." --query "HostedZones[?Name=='$PARENT.'].Id" --output text); do
  have="$(aws route53 get-hosted-zone --id "$id" --query 'DelegationSet.NameServers' --output text | tr '\t' '\n' | sed 's/\.$//' | tr 'A-Z' 'a-z' | sort | tr '\n' ' ')"
  if [ -z "$want" ] || [ "$have" = "$want" ]; then ZONE="$id"; break; fi
done
[ -n "$ZONE" ] || die "no hosted zone for $PARENT in this account matches the name servers the internet uses for it ($want). Are you in the account that owns $PARENT's DNS?"
BATCH="$(jq -n --arg n "$SUB." --argjson v "$(printf '%s\n' "${NS[@]}" | jq -R '{Value: .}' | jq -s .)" \
  '{Comment:"delegate subdomain for a reproduction", Changes:[{Action:"UPSERT", ResourceRecordSet:{Name:$n, Type:"NS", TTL:300, ResourceRecords:$v}}]}')"
echo "Parent zone: $ZONE ($PARENT)"; echo "Record to create:"; echo "$BATCH" | jq -c '.Changes[0].ResourceRecordSet'
if [ "$APPLY" != yes ]; then echo "Dry run. Add --apply to create it."; exit 0; fi
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE" --change-batch "$BATCH" --query 'ChangeInfo.[Id,Status]' --output text
echo "Done. The other person's certificate should validate within a few minutes."
