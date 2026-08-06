#!/usr/bin/env bash
# Roll the checkout-api back to the last known-good revision (v1).
set -euo pipefail
cd "$(dirname "$0")"
echo "rolling back to last known-good revision v1..."
./deploy.sh v1
