#!/bin/bash
# =============================================================
# deploy/deploy_backend.sh
# =============================================================
# Your whole project is ONE repo. On the server it lives at:
#   /opt/realisieren-pulse/               ← the git repo root
#   /opt/realisieren-pulse/backend/       ← FastAPI code (backend/ subfolder)
#   /opt/realisieren-pulse/frontend/      ← Next.js code
#   /opt/realisieren-pulse/desktop/       ← Windows app code
#   /opt/realisieren-pulse/deploy/        ← these scripts
#
# Run this every time you push new backend code:
#   ssh root@YOUR_SERVER_IP
#   cd /opt/realisieren-pulse
#   ./deploy/deploy_backend.sh
#
# What it does:
#   1. git pull — gets your latest code
#   2. pip install — updates Python packages if requirements changed
#   3. Restarts the backend service
# =============================================================

set -e

# The repo root = one folder above this script (deploy/ is inside the repo)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"   # backend/ is already here — no copying needed
VENV="/opt/realisieren-pulse/venv"

echo ""
echo "============================================"
echo "  Deploying Realisieren Pulse Backend"
echo "============================================"
echo "  Repo root:  $REPO_ROOT"
echo "  Backend:    $BACKEND_DIR"
echo ""

# ── Step 1: Pull latest code ────────────────────────────────
# This updates ALL folders (backend/, frontend/, desktop/) in one shot
# because they all live in the same repo.
echo "[1/3] Pulling latest code..."
cd "$REPO_ROOT"
git pull origin main
echo "      Done."

# ── Step 2: Install/update Python dependencies ──────────────
# Only re-installs if requirements.txt changed
echo "[2/3] Installing Python packages..."
"$VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q
echo "      Done."

# ── Step 3: Restart the backend service ─────────────────────
echo "[3/3] Restarting realisieren-pulse-backend service..."
systemctl restart realisieren-pulse-backend
sleep 2

if systemctl is-active --quiet realisieren-pulse-backend; then
    echo "      Service is running."
else
    echo "      ERROR: Service failed to start!"
    echo "      Run: journalctl -u realisieren-pulse-backend -n 50"
    exit 1
fi

echo ""
echo "============================================"
echo "  DEPLOYMENT COMPLETE"
echo "  API is live at: http://$(hostname -I | awk '{print $1}'):8000"
echo "  Health check:   http://$(hostname -I | awk '{print $1}'):8000/api/health"
echo "============================================"
echo ""
