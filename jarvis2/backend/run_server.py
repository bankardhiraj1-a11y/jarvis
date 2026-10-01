#!/usr/bin/env python3
"""Start Jarvis 2 API Server with proper environment loading"""
import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Verify credentials
client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()

print(f"[OK] DHAN_CLIENT_ID: {'SET' if client_id else 'MISSING'}")
print(f"[OK] DHAN_ACCESS_TOKEN: {'SET' if access_token else 'MISSING'}")

if not client_id or not access_token:
    print("[WARN] DhanHQ credentials not set - NSE agents (STOCKS/SENSEX/OPTIONS) will skip. XAUUSD (OANDA) will trade.")
    print("[WARN] To enable NSE agents, set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env")

# Start server
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
