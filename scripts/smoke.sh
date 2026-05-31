#!/usr/bin/env bash
# Curl-driven smoke test against a running JRDbooks API.
# Verifies the critical end-to-end flows that the e2e suite also covers,
# without needing Playwright or a browser.

set -euo pipefail

API="${API:-http://127.0.0.1:8000}"
EMAIL="${EMAIL:-demo@jrdbooks.io}"
PASSWORD="${PASSWORD:-demo}"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; exit 1; }

bold "1. Health"
curl -sf "${API}/health" >/dev/null && ok "/health returns 200" || fail "API not running at ${API}"

bold "2. Login"
TOKEN=$(curl -sf -X POST "${API}/auth/token" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
[ -n "${TOKEN}" ] && ok "Token issued" || fail "Could not log in"

bold "3. Entities"
ENT=$(curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/entities" \
  | python3 -c 'import sys,json;rows=json.load(sys.stdin);print(rows[0]["id"]);')
[ -n "${ENT}" ] && ok "Entities listed (using ${ENT:0:8}…)" || fail "No entities found"

bold "4. Trial balance ties"
curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/reports/trial-balance?entity_id=${ENT}" \
  | python3 -c '
import sys,json
rows = json.load(sys.stdin)
td = sum(float(r["debit"]) for r in rows)
tc = sum(float(r["credit"]) for r in rows)
assert abs(td - tc) < 0.01, f"Trial balance off by {td-tc:.4f}"
print(f"  total debit = ${td:,.2f} / total credit = ${tc:,.2f}")
' && ok "Trial balance ties" || fail "Trial balance is out of balance"

bold "5. Balance sheet balances"
curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/reports/balance-sheet?entity_id=${ENT}&as_of=$(date +%Y-%m-%d)" \
  | python3 -c '
import sys,json
bs = json.load(sys.stdin)
a = float(bs["assets_total"])
le = float(bs["liabilities_total"]) + float(bs["equity_total"])
delta = abs(a - le)
assert delta < 0.01, f"BS off by {delta:.4f}"
print(f"  A = ${a:,.2f} / L+E = ${le:,.2f}")
' && ok "Balance sheet balances" || fail "Balance sheet does not balance"

bold "6. Dashboard summary returns shape"
curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/dashboard/summary?entity_id=${ENT}" \
  | python3 -c '
import sys,json
b = json.load(sys.stdin)
for k in ("cash_balance","month_to_date","unreconciled_count","ar_outstanding","ap_outstanding","bank_accounts","revenue_trend"):
    assert k in b, "missing key: " + k
cash = b["cash_balance"]
net = b["month_to_date"]["net_income"]
unrec = b["unreconciled_count"]
print("  cash=${:,.2f} MTD net=${:,.2f} unrec={}".format(cash, net, unrec))
' && ok "Dashboard payload OK" || fail "Dashboard payload incomplete"

bold "7. Posting engine rejects unbalanced journal"
ACCT_CASH=$(curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/accounts?entity_id=${ENT}" \
  | python3 -c 'import sys,json;rows=json.load(sys.stdin);print(next(r["id"] for r in rows if r["code"]=="1010"))')
ACCT_REV=$(curl -sf -H "Authorization: Bearer ${TOKEN}" "${API}/accounts?entity_id=${ENT}" \
  | python3 -c 'import sys,json;rows=json.load(sys.stdin);print(next(r["id"] for r in rows if r["code"]=="4000"))')

STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API}/journals?post=true" \
  -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' \
  -d "{\"entity_id\":\"${ENT}\",\"posting_date\":\"$(date +%Y-%m-%d)\",\"memo\":\"smoke-bad\",\"lines\":[{\"line_no\":1,\"account_id\":\"${ACCT_CASH}\",\"debit\":\"10\",\"credit\":\"0\"},{\"line_no\":2,\"account_id\":\"${ACCT_REV}\",\"debit\":\"0\",\"credit\":\"5\"}]}")
[ "$STATUS" = "400" ] && ok "Unbalanced journal rejected (HTTP 400)" || fail "Got HTTP $STATUS, expected 400"

bold "8. Post and reverse a balanced journal"
JID=$(curl -sf -X POST "${API}/journals?post=true" \
  -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' \
  -d "{\"entity_id\":\"${ENT}\",\"posting_date\":\"$(date +%Y-%m-%d)\",\"memo\":\"smoke-ok\",\"lines\":[{\"line_no\":1,\"account_id\":\"${ACCT_CASH}\",\"debit\":\"100\",\"credit\":\"0\"},{\"line_no\":2,\"account_id\":\"${ACCT_REV}\",\"debit\":\"0\",\"credit\":\"100\"}]}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
ok "Posted journal ${JID:0:8}…"

curl -sf -X POST "${API}/journals/${JID}/reverse" -H "Authorization: Bearer ${TOKEN}" >/dev/null \
  && ok "Reversed journal" || fail "Reversal failed"

printf "\n\033[32mAll checks green.\033[0m\n"
