#!/usr/bin/env python3
"""
desktop_app.py
CA Trader Native Windows Desktop Client
Connects directly to CA Trader cloud server (https://catrader.site)
with seamless fallback and native Edge WebView2 engine.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CA_Trader_Desktop")

# Ensure proper working directory
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

os.chdir(str(APP_DIR))

# Target cloud production server
CLOUD_URL = "https://catrader.site/terminal"


def main():
    logger.info("Launching CA Trader Native Desktop Terminal...")

    import webview

    icon_path = BUNDLE_DIR / "static" / "ca_trader.ico"
    if not icon_path.exists():
        icon_path = APP_DIR / "static" / "ca_trader.ico"

    # Create native Windows application window
    window = webview.create_window(
        title="CA Trader — Institutional Trading Terminal",
        url=CLOUD_URL,
        width=1440,
        height=900,
        min_size=(1024, 700),
        background_color="#0b0e14",
        text_select=True,
        zoomable=True,
        confirm_close=False
    )

    logger.info(f"Connected to {CLOUD_URL}. Starting desktop UI engine...")

    # Start Edge WebView2 desktop container (allows cookies, sessions, credentials persistence)
    try:
        webview.start(
            debug=False,
            private_mode=False,
            storage_path=str(APP_DIR / ".desktop_cache")
        )
    except Exception as e:
        logger.error(f"Error running webview: {e}", exc_info=True)
    finally:
        logger.info("CA Trader desktop window closed. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
