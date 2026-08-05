#!/bin/bash
# =============================================================================
# telegent VPS root setup — run as root, ONCE.
# The host is assumed already provisioned by the invintiry setup (uv, git,
# deploy user, swap, firewall, Caddy). This only adds the telegent-specific
# root step: a sudoers grant so the deploy user can manage the telegent services.
#
# Usage (as root):  bash /home/deploy/telegent/deploy/setup.sh
# =============================================================================
set -euo pipefail

SUDOERS_SRC="/home/deploy/telegent/deploy/telegent.sudoers"

echo "=== telegent root setup ==="
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root (e.g. 'sudo bash $0' from a sudo-capable account, or as root)."; exit 1; }
[ -f "$SUDOERS_SRC" ] || { echo "ERROR: $SUDOERS_SRC not found — clone the telegent repo into /home/deploy first."; exit 1; }

echo "[1/1] Installing sudoers grant for the deploy user..."
cp "$SUDOERS_SRC" /etc/sudoers.d/deploy-telegent
chmod 440 /etc/sudoers.d/deploy-telegent
visudo -cf /etc/sudoers.d/deploy-telegent

echo ""
echo "=== Root setup complete ==="
echo "Now, as the deploy user:"
echo "  ~/universal-chat-agent/deploy/setup-app.sh   # brain first"
echo "  ~/telegent/deploy/setup-app.sh               # then bridge"
