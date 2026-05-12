#!/bin/bash
# =============================================================
# deploy/setup_server.sh
# =============================================================
# Run this ONCE on a fresh Ubuntu 22.04 VPS to set up:
#   - Python + pip
#   - PostgreSQL
#   - MongoDB
#   - Nginx (reverse proxy)
#   - Your FastAPI backend as a systemd service
#
# USAGE (on your server via SSH):
#   ssh root@YOUR_SERVER_IP
#
#   # Clone the WHOLE project repo into /opt/realisieren-pulse
#   # (backend/, frontend/, desktop/, deploy/ will all be inside it)
#   git clone https://github.com/YOUR_USERNAME/ai-assistant.git /opt/realisieren-pulse
#
#   cd /opt/realisieren-pulse
#   chmod +x deploy/setup_server.sh
#   ./deploy/setup_server.sh
#
# After this script, create the .env file, then run:
#   ./deploy/deploy_backend.sh    (to start/update the backend)
# =============================================================

set -e   # stop on any error

echo ""
echo "============================================"
echo "  Realisieren Pulse Server Setup"
echo "============================================"
echo ""

# ── Step 1: System updates ────────────────────────────────
echo "[1/7] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ── Step 2: Python 3.11 ───────────────────────────────────
echo "[2/7] Installing Python 3.11..."
apt-get install -y -qq python3.11 python3.11-venv python3-pip python3.11-dev

# ── Step 3: Nginx (reverse proxy) ─────────────────────────
# Nginx sits in front of uvicorn and handles:
# - Port 80 → forward to uvicorn on port 8000
# - SSL termination (when you add HTTPS later)
echo "[3/7] Installing Nginx..."
apt-get install -y -qq nginx

# ── Step 4: PostgreSQL ────────────────────────────────────
echo "[4/7] Installing PostgreSQL..."
apt-get install -y -qq postgresql postgresql-contrib

# Start PostgreSQL and enable it on reboot
systemctl start postgresql
systemctl enable postgresql

# ── Step 5: MongoDB ───────────────────────────────────────
echo "[5/7] Installing MongoDB..."
apt-get install -y -qq gnupg curl
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc \
    | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
    https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
    | tee /etc/apt/sources.list.d/mongodb-org-7.0.list
apt-get update -qq
apt-get install -y -qq mongodb-org
systemctl start mongod
systemctl enable mongod

# ── Step 6: Create virtual environment ───────────────────
# The repo is already cloned to /opt/realisieren-pulse/ (see USAGE above).
# We just create a Python virtualenv next to it.
# backend/ frontend/ desktop/ are already inside /opt/realisieren-pulse/
echo "[6/7] Setting up Python virtual environment..."
if [ ! -d "/opt/realisieren-pulse" ]; then
    echo "ERROR: /opt/realisieren-pulse does not exist."
    echo "Please clone your repo first:"
    echo "  git clone https://github.com/YOUR_USERNAME/ai-assistant.git /opt/realisieren-pulse"
    exit 1
fi
python3.11 -m venv /opt/realisieren-pulse/venv
/opt/realisieren-pulse/venv/bin/pip install --upgrade pip -q

# ── Step 7: Firewall ──────────────────────────────────────
echo "[7/7] Configuring firewall..."
apt-get install -y -qq ufw
ufw allow OpenSSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS (for later)
ufw allow 8000/tcp  # FastAPI direct access (for staging testing)
ufw --force enable

echo ""
echo "============================================"
echo "  SERVER SETUP COMPLETE"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Create the PostgreSQL database and user:"
echo "     sudo -u postgres psql"
echo "     CREATE USER realisieren_pulse_user WITH PASSWORD 'choose_a_password';"
echo "     CREATE DATABASE realisieren_pulse_staging OWNER realisieren_pulse_user;"
echo "     \\q"
echo ""
echo "  2. Create /opt/realisieren-pulse/backend/.env with your settings"
     echo "     cp /opt/realisieren-pulse/backend/.env.example /opt/realisieren-pulse/backend/.env"
     echo "     nano /opt/realisieren-pulse/backend/.env"
echo ""
echo "  3. Run: ./deploy/deploy_backend.sh"
echo ""
