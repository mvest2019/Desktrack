#!/bin/bash
# =============================================================
# deploy/deploy_frontend.sh
# =============================================================
# Self-hosted option: builds and serves Next.js on the same VPS.
# (Use this ONLY if you are NOT using Vercel.)
#
# If you use Vercel (recommended for simplicity), you do NOT
# need this script. See DEPLOYMENT.md → Part 4.
#
# HOW TO USE:
#   ssh root@69.62.76.202
#   cd /opt/realisieren-pulse
#   ./deploy/deploy_frontend.sh
#
# First run:
#   apt-get install -y nodejs npm
#   npm install -g pm2
# =============================================================

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

echo ""
echo "============================================"
echo "  Deploying Realisieren Pulse Frontend (Self-hosted)"
echo "============================================"
echo "  Frontend dir: $FRONTEND_DIR"
echo ""

# ── Step 1: Pull latest code ─────────────────────────────────
echo "[1/4] Pulling latest code..."
cd "$REPO_ROOT"
git pull origin main
echo "      Done."

# ── Step 2: Set staging API URL ──────────────────────────────
# Next.js rewrites (next.config.js) read BACKEND_URL at startup.
echo "[2/4] Setting staging environment..."
cd "$FRONTEND_DIR"
export BACKEND_URL="http://69.62.76.202:8000"
echo "      BACKEND_URL=$BACKEND_URL"

# ── Step 3: Install npm packages and build ───────────────────
echo "[3/4] Installing packages and building..."
npm install --silent
npm run build
echo "      Build complete."

# ── Step 4: Restart with PM2 (keeps it running after you log out) ─
# PM2 is a process manager for Node.js apps (like systemd for Python).
# Install once:  npm install -g pm2
echo "[4/4] Restarting frontend with PM2..."
if pm2 describe realisieren-pulse-frontend > /dev/null 2>&1; then
    pm2 restart realisieren-pulse-frontend
else
    # First time: start and save the process list
    pm2 start npm --name "realisieren-pulse-frontend" -- start
    pm2 save
    pm2 startup   # prints a command — run that command to auto-start on reboot
fi
echo "      Frontend running on port 3000."

echo ""
echo "============================================"
echo "  FRONTEND DEPLOYMENT COMPLETE"
echo "  Running at: http://69.62.76.202:3000"
echo "============================================"
echo ""
echo "IMPORTANT: Add a /etc/nginx/sites-available/realisieren-pulse-frontend"
echo "to proxy port 80 → port 3000 so users can access it without :3000"
echo "See DEPLOYMENT.md Part 4B for the nginx config."
echo ""
