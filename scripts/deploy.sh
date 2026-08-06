#!/usr/bin/env bash
# Simulated deploy pipeline. Writes a revision's config to .env, records it in
# deploy-history.log, and recreates the checkout-api container.
#
#   ./scripts/deploy.sh v1   -> healthy revision  (MAX_CART_ITEMS=50)
#   ./scripts/deploy.sh v2    -> BAD deploy        (MAX_CART_ITEMS=unlimited)
set -euo pipefail
cd "$(dirname "$0")/.."

REV="${1:-}"
if [ -z "$REV" ]; then
  echo "usage: $0 <v1|v2>"
  exit 1
fi

case "$REV" in
  v1) MAX="50" ;;
  v2) MAX="unlimited" ;;
  *)  echo "unknown revision: $REV (expected v1 or v2)"; exit 1 ;;
esac

cat > .env <<EOF
APP_REVISION=$REV
MAX_CART_ITEMS=$MAX
EOF

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) deploy revision=$REV MAX_CART_ITEMS=$MAX" >> deploy-history.log

docker compose up -d --force-recreate checkout-api >/dev/null
echo "deployed revision=$REV (MAX_CART_ITEMS=$MAX)"
echo "recent deploy history:"
tail -n 5 deploy-history.log
