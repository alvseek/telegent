#!/bin/bash
# =============================================================================
# telegent bridge — one-time app setup
# Run as the deploy user AFTER: repo cloned, .env filled, and the telegent
# sudoers drop-in installed by root (see SETUP.md). The brain should be set up
# first (universal-chat-agent).
#
# Usage: ~/telegent/deploy/setup-app.sh
# =============================================================================
set -euo pipefail

# Monorepo: the repo root holds deploy/; the bridge app lives in application/bridge/.
REPO_DIR="/home/deploy/telegent"
APP_DIR="$REPO_DIR/application/bridge"
UV="$HOME/.local/bin/uv"

echo "=== telegent-bridge setup ==="
[ -f "$APP_DIR/.env" ] || { echo "ERROR: $APP_DIR/.env missing — cp .env.example .env and fill TELEGRAM_BOT_TOKEN + BRAIN_URL"; exit 1; }

echo "[1/3] venv + deps (uv)..."
cd "$APP_DIR"
[ -d .venv ] || "$UV" venv .venv
"$UV" pip install --python .venv/bin/python --no-cache -r requirements.txt

echo "[2/3] install systemd unit..."
sudo cp "$REPO_DIR/deploy/telegent-bridge.service" /etc/systemd/system/
sudo systemctl daemon-reload

echo "[3/3] enable + start..."
sudo systemctl enable telegent-bridge
sudo systemctl restart telegent-bridge
sleep 2
echo "bridge: $(systemctl is-active telegent-bridge)"
