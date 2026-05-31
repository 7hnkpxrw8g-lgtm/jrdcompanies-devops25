#!/usr/bin/env bash
# One-shot prod deploy. Run this on the server that owns
# jrdbooks.jrdcompanies.com (after pointing the DNS A record at it).
#
# What it does:
#   - Verifies docker is installed and the DNS record points at this box.
#   - Generates .env.prod with strong defaults if it doesn't exist.
#   - Brings up postgres, redis, api (auto-migrates + seeds), web, and caddy.
#   - Caddy fetches a Let's Encrypt certificate automatically (ports 80 + 443
#     must be open and DOMAIN must resolve to this server).
#
# Usage:
#   sudo bash scripts/deploy.sh
#   sudo DOMAIN=jrdbooks.example.com bash scripts/deploy.sh

set -euo pipefail

cd "$(dirname "$0")/.."

DOMAIN="${DOMAIN:-jrdbooks.jrdcompanies.com}"
ENV_FILE="infra/.env.prod"

err() { printf "\033[31m%s\033[0m\n" "$*" >&2; }
ok()  { printf "\033[32m%s\033[0m\n" "$*"; }
info(){ printf "\033[36m%s\033[0m\n" "$*"; }

info "==> deploying JRDbooks at https://${DOMAIN}"

command -v docker >/dev/null || { err "docker not installed"; exit 1; }
docker compose version >/dev/null 2>&1 || { err "docker compose plugin missing"; exit 1; }

# DNS preflight (warn-only; cert fetch needs this to be right).
if command -v dig >/dev/null; then
  resolved=$(dig +short "$DOMAIN" | tail -1)
  myip=$(curl -s --max-time 5 https://api.ipify.org || true)
  if [ -n "$resolved" ] && [ -n "$myip" ] && [ "$resolved" != "$myip" ]; then
    err "WARNING: $DOMAIN resolves to $resolved but this server is $myip."
    err "Cert issuance will fail until DNS is corrected. Continuing anyway."
  fi
fi

# Generate .env.prod if missing.
if [ ! -f "$ENV_FILE" ]; then
  info "==> creating $ENV_FILE with generated secrets"
  jwt=$(openssl rand -base64 48 | tr -d '\n')
  pg=$(openssl rand -hex 24)
  cat > "$ENV_FILE" <<EOF
DOMAIN=${DOMAIN}
ACME_EMAIL=${ACME_EMAIL:-admin@${DOMAIN#*.}}
JWT_SECRET=${jwt}
POSTGRES_USER=jrd
POSTGRES_PASSWORD=${pg}
POSTGRES_DB=jrdbooks
SENTRY_DSN=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
PLAID_CLIENT_ID=
PLAID_SECRET=
OPENAI_API_KEY=
EOF
  chmod 600 "$ENV_FILE"
  ok "wrote $ENV_FILE (locked to 0600). Edit it to add integration keys later."
fi

info "==> docker compose up --build -d"
docker compose --env-file "$ENV_FILE" -f infra/docker-compose.prod.yml up --build -d

info "==> waiting for api to report healthy (max 60s)..."
for _ in $(seq 1 30); do
  if docker compose --env-file "$ENV_FILE" -f infra/docker-compose.prod.yml exec -T api \
      python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
    ok "api healthy"
    break
  fi
  sleep 2
done

info "==> checking https://${DOMAIN}/api/health (cert may take ~30s on first run)"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 5 "https://${DOMAIN}/api/health" >/dev/null 2>&1; then
    ok "live: https://${DOMAIN}"
    ok "login: demo@jrdbooks.io / demo"
    exit 0
  fi
  sleep 2
done

err "Site did not respond on HTTPS within 60s. Inspect logs with:"
err "  docker compose --env-file ${ENV_FILE} -f infra/docker-compose.prod.yml logs caddy api web --tail 100"
exit 1
