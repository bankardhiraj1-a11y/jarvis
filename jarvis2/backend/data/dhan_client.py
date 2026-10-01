"""
DhanHQ market-data client for NSE stocks and indices - READ ONLY.

Adapted from gold-agent's proven working pattern.
Security IDs from Dhan Symbol Master: https://images.dhan.co/api-data/api-scrip-master.csv

Endpoints verified against https://dhanhq.co/docs/v2/:
  POST /v2/marketfeed/ltp           -> last traded price

Auth headers: `access-token` (JWT) and `client-id`.
Rate limits: marketfeed 1 req/sec minimum interval.

Segments:
  E = Equity (NSE stocks)
  I = Index (NIFTY, SENSEX, BANKNIFTY, etc.)
  D = Derivatives/Options
"""
import os
import time as _time
from typing import Dict, List
from datetime import datetime

import requests

BASE_URL = "https://api.dhan.co"
TIMEOUT = 15
_MIN_INTERVAL = 1.05  # DhanHQ rate limit: 1 req/sec


class DhanClient:
    """
    DhanHQ integration for NSE live market data.
    Requires: DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN environment variables
    """

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        self.base_url = BASE_URL

        if not self.access_token or not self.client_id:
            print("[WARN] DhanHQ credentials not set. Set DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID")

        self._session = requests.Session()
        self._last_call = 0.0

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _throttle(self) -> None:
        """Enforce 1 req/sec rate limit"""
        elapsed = _time.monotonic() - self._last_call
        if elapsed < _MIN_INTERVAL:
            _time.sleep(_MIN_INTERVAL - elapsed)
        self._last_call = _time.monotonic()

    def _post(self, path: str, payload: Dict) -> Dict:
        """POST request with rate limiting and error handling"""
        self._throttle()
        url = f"{self.base_url}{path}"
        try:
            r = self._session.post(
                url, json=payload, headers=self._headers, timeout=TIMEOUT
            )
        except requests.RequestException as e:
            print(f"[ERROR] DhanHQ {path} request failed: {e}")
            return {"status": "error", "data": {}}

        if r.status_code != 200:
            print(f"[ERROR] DhanHQ {path} returned HTTP {r.status_code}: {r.text[:200]}")
            return {"status": "error", "data": {}}

        try:
            body = r.json()
        except ValueError as e:
            print(f"[ERROR] DhanHQ {path} returned non-JSON: {r.text[:100]}")
            return {"status": "error", "data": {}}

        # Check for application-level failure
        if isinstance(body, dict) and body.get("status") == "failure":
            print(f"[ERROR] DhanHQ {path} application error: {body.get('message', 'unknown')}")
            return {"status": "error", "data": {}}

        return body

    def get_live_data(
        self, symbol: str, security_id: int, segment: str = "E"
    ) -> Dict:
        """
        Fetch LIVE LTP data from DhanHQ API.

        Args:
            symbol: Symbol name (e.g., "RELIANCE")
            security_id: Numeric DhanHQ security ID from Symbol Master (e.g., 500325 for RELIANCE)
            segment: Exchange segment code:
                     "E" = Equity (NSE stocks)
                     "I" = Index (SENSEX, NIFTY, BANKNIFTY)
                     "D" = Derivatives/Options

        Returns:
            Dict with OHLCV data: {symbol, segment, close, open, high, low, volume, timestamp}
            Empty dict on error
        """
        if not self.access_token or not self.client_id or not security_id:
            return {
                "symbol": symbol,
                "segment": segment,
                "timestamp": datetime.utcnow().isoformat(),
                "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0,
            }

        try:
            # Payload format: {segment: [security_id]}
            body = self._post(
                "/v2/marketfeed/ltp",
                {segment: [int(security_id)]}
            )

            if body.get("status") == "success" and body.get("data"):
                # Response format: {"data": {segment: {str(security_id): {last_price, open, high, low, volume, ...}}}}
                segment_data = body.get("data", {}).get(segment, {})
                tick = segment_data.get(str(security_id), {})

                if isinstance(tick, dict) and tick.get("last_price", 0) > 0:
                    return {
                        "symbol": symbol,
                        "segment": segment,
                        "timestamp": datetime.utcnow().isoformat(),
                        "open": float(tick.get("open", 0) or 0),
                        "high": float(tick.get("high", 0) or 0),
                        "low": float(tick.get("low", 0) or 0),
                        "close": float(tick.get("last_price", 0) or 0),
                        "volume": int(tick.get("volume", 0) or 0),
                    }

            return {
                "symbol": symbol,
                "segment": segment,
                "timestamp": datetime.utcnow().isoformat(),
                "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0,
            }
        except Exception as e:
            print(f"[ERROR] get_live_data {symbol}: {e}")
            return {
                "symbol": symbol,
                "segment": segment,
                "timestamp": datetime.utcnow().isoformat(),
                "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0,
            }

    def get_historical_data(
        self, symbol: str, security_id: int, segment: str = "E",
        duration: int = 1, interval: str = "1D"
    ) -> List[Dict]:
        """Fetch historical OHLC data"""
        # TODO: Implement if needed for backtesting
        return []
