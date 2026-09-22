#!/usr/bin/env python3
"""
run_server.py
Reliable local server entrypoint for Windows.
Enforces WindowsSelectorEventLoopPolicy BEFORE uvicorn initializes,
preventing IOCP [WinError 64] socket crash when headless browsers disconnect.
"""

import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import uvicorn
import uvicorn.loops.asyncio

if sys.platform == "win32":
    # Patch uvicorn's internal loop factory which otherwise forces ProactorEventLoop in Python 3.12+
    uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop

if __name__ == "__main__":
    port = 8000
    host = "127.0.0.1"
    print(f"Starting CA Trader on http://{host}:{port} with SelectorEventLoop...", flush=True)
    uvicorn.run("app:app", host=host, port=port, log_level="info")

