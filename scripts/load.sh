#!/usr/bin/env bash
# Generate steady traffic against checkout-api so the metrics/logs have signal.
# Ctrl-C to stop.
set -euo pipefail
URL="${1:-http://localhost:8080/checkout}"
echo "sending traffic to $URL (Ctrl-C to stop)..."
while true; do
  items=$(( (RANDOM % 5) + 1 ))
  code=$(curl -s -o /dev/null -w "%{http_code}" "${URL}?items=${items}")
  echo "$(date +%H:%M:%S) items=${items} -> HTTP ${code}"
  sleep 0.5
done
