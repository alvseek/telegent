#!/bin/bash
# =============================================================================
# telegent bridge — redeploy after code changes
# Run as the deploy user.
#
# Usage: ~/telegent/deploy/redeploy.sh
# =============================================================================
set -euo pipefail

# Monorepo: git lives at the repo root; the bridge app lives in application/bridge/.
REPO_DIR="/home/deploy/telegent"
APP_DIR="$REPO_DIR/application/bridge"
UV="$HOME/.local/bin/uv"

echo "=== telegent-bridge redeploy ==="

echo "[1/3] pull (repo root)..."
cd "$REPO_DIR"
git pull origin main

echo "[2/3] deps (bridge app)..."
cd "$APP_DIR"
"$UV" pip install --python .venv/bin/python --no-cache -r requirements.txt

echo "[3/3] restart..."
sudo systemctl restart telegent-bridge
sleep 2
echo "bridge: $(systemctl is-active telegent-bridge)"
