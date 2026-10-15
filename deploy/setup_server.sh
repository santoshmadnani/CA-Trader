#!/usr/bin/env bash
# One-time bootstrap for a fresh Ubuntu host (run as the `ubuntu` user with sudo rights).
# Mirrors the layout .github/workflows/deploy_to_oracle.yml expects:
#   repo  -> /home/ubuntu/CA-Trader   (branch CA-Trader-Bifurcated)
#   venv  -> /home/ubuntu/venv
#   unit  -> catrader.service (uvicorn on 127.0.0.1:8000), public traffic via a Cloudflare tunnel.
#
# Moving to a new server:
#   1. Run this script on the new host.
#   2. Copy .env and ca_trader.sqlite3 (+ catrader_telegram.session) from the old host into /home/ubuntu/CA-Trader.
#   3. Install the tunnel: `sudo cloudflared service install <TUNNEL_TOKEN>` (token from the Cloudflare dashboard).
#   4. Update GitHub repo secrets ORACLE_HOST and ORACLE_SSH_KEY; the next push deploys there.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/santoshmadnani/CA-Trader.git}"
APP_DIR=/home/ubuntu/CA-Trader

sudo apt-get update -y
sudo apt-get install -y git python3 python3-venv sqlite3 curl

[ -d "$APP_DIR/.git" ] || git clone -b CA-Trader-Bifurcated "$REPO_URL" "$APP_DIR"
[ -d /home/ubuntu/venv ] || python3 -m venv /home/ubuntu/venv
/home/ubuntu/venv/bin/pip install --upgrade pip
/home/ubuntu/venv/bin/pip install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/data" "$APP_DIR/backups"
sudo cp "$APP_DIR/deploy/catrader.service" /etc/systemd/system/catrader.service
sudo systemctl daemon-reload
sudo systemctl enable catrader

if ! command -v cloudflared >/dev/null; then
  curl -fsSL -o /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  sudo dpkg -i /tmp/cloudflared.deb
fi

echo "Bootstrap done. Add .env + database, then: sudo systemctl start catrader && curl -s http://127.0.0.1:8000/health"
