"""
config.py — Central configuration for the Realisieren Pulse desktop app.

HOW API_URL IS RESOLVED (in priority order):
  1. Environment variable:   set API_URL=https://... before running
  2. Config file:            config.ini next to the .exe  (users can override)
  3. Hard-coded default:     the staging server URL below

This means:
  - When YOU build the EXE, the staging URL is baked in.
  - Users can drop a config.ini next to the EXE to point to a different server.
  - You can override with an env var for local testing.
"""

import os
import sys
import configparser
from pathlib import Path


# ── Where the EXE (or script) lives ────────────────────────
# sys.frozen is True when running as a PyInstaller EXE.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent        # folder containing Realisieren Pulse.exe
else:
    APP_DIR = Path(__file__).parent              # folder containing app.py


# ── Defaults ────────────────────────────────────────────────
STAGING_API_URL     = "http://69.62.76.202:8000"  # production server
STAGING_WEBSITE_URL = "https://desktrack-five.vercel.app"  # production website
SCREENSHOT_INTERVAL = 180                          # seconds (3 minutes)


def _load_config_file() -> dict:
    """
    Read optional config.ini that can sit next to the EXE.

    Example config.ini content:
        [realisieren-pulse]
        api_url = https://my-other-server.com:8000
        screenshot_interval = 30
    """
    config_path = APP_DIR / "config.ini"
    if not config_path.exists():
        return {}

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    section = "realisieren-pulse"
    result = {}

    if parser.has_option(section, "api_url"):
        result["api_url"] = parser.get(section, "api_url").rstrip("/")
    if parser.has_option(section, "website_url"):
        result["website_url"] = parser.get(section, "website_url").rstrip("/")
    if parser.has_option(section, "screenshot_interval"):
        result["screenshot_interval"] = int(parser.get(section, "screenshot_interval"))

    return result


def _resolve() -> dict:
    file_cfg = _load_config_file()

    api_url = (
        os.environ.get("API_URL")                 # 1. env var
        or file_cfg.get("api_url")                # 2. config.ini
        or STAGING_API_URL                        # 3. hard-coded default
    ).rstrip("/")

    screenshot_interval = int(
        os.environ.get("SCREENSHOT_INTERVAL")
        or file_cfg.get("screenshot_interval")
        or SCREENSHOT_INTERVAL
    )

    return {
        "api_url":             api_url,
        "screenshot_interval": screenshot_interval,
    }


# ── Public constants ─────────────────────────────────────────
_cfg = _resolve()

API_URL             = _cfg["api_url"]
SCREENSHOT_INTERVAL = _cfg["screenshot_interval"]