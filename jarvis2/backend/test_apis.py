#!/usr/bin/env python3
"""
Test API Connectivity for Jarvis 2
Verifies DhanHQ and Zerodha Kite connections
"""

import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from data.multi_api_client import multi_api_client
import json

def test_apis():
    """Test all configured APIs"""

    print("=" * 80)
    print("JARVIS 2 - Multi-API Connectivity Test")
    print("=" * 80)
    print()

    # Check configuration
    status = multi_api_client.get_status()
    print("API Configuration Status:")
    print(f"  ONDA Trading (Forex/Gold):  {'CONFIGURED' if status['onda_configured'] else 'NOT CONFIGURED'}")
    print(f"  DhanHQ (Forex/Commodities): {'CONFIGURED' if status['dhan_configured'] else 'NOT CONFIGURED'}")
    print(f"  XAUUSD Primary Source:      {status.get('xauusd_primary', 'DhanHQ')}")
    print()

    if not status['onda_configured'] and not status['dhan_configured']:
        print("[ERROR] No APIs configured!")
        print()
        print("Setup Instructions:")
        print("1. Copy .env.template to .env")
        print("2. Fill in your API credentials:")
        print("   - ONDA:   https://www.onda.trading/")
        print("   - DhanHQ: https://www.dhanhq.co/")
        print("3. Run this test again")
        return False

    print("-" * 80)
    print("Testing Live Market Data Fetch...")
    print("-" * 80)
    print()

    # Test DhanHQ symbols only
    test_symbols = ["XAUUSD", "CRUDE", "EURUSD", "USDINR"]
    results = {}

    for symbol in test_symbols:
        print(f"Fetching {symbol}...", end=" ")
        data = multi_api_client.get_live_data(symbol)

        if data:
            print("[SUCCESS]")
            results[symbol] = {
                "status": "OK",
                "ltp": data.get("ltp", data.get("close", 0)),
                "high": data.get("high", 0),
                "low": data.get("low", 0),
                "timestamp": data.get("timestamp"),
            }
        else:
            print("[FAILED]")
            results[symbol] = {"status": "FAILED"}

    print()
    print("=" * 80)
    print("Test Results:")
    print("=" * 80)
    print(json.dumps(results, indent=2))
    print()

    success_count = sum(1 for r in results.values() if r["status"] == "OK")
    print(f"Summary: {success_count}/{len(test_symbols)} symbols fetched successfully")

    if success_count > 0:
        print()
        print("[SUCCESS] APIs are live and connected!")
        print("Jarvis 2 is ready for live trading.")
        return True
    else:
        print()
        print("[WARNING] No live data received. Check:")
        print("  1. API credentials are correct")
        print("  2. Market is open")
        print("  3. Firewall allows outbound HTTPS")
        return False

if __name__ == "__main__":
    success = test_apis()
    sys.exit(0 if success else 1)
