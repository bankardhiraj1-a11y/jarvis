"""
DhanHQ Live Market Feed Client using WebSocket.
Uses the official dhanhq library MarketFeed for real-time data.

The installed dhanhq package's MarketFeed takes instruments as
(exchange_segment_int, security_id_str, request_code_int) tuples - NOT the
{"ExchangeSegment": "NSE_EQ", ...} dict shape documented on the REST API pages.
Segment ints match the library's own constants (MarketFeed.NSE, .IDX, etc.),
which line up 1:1 with the REST API's string segment names.

Callbacks are invoked by the library as on_x(self, feed_instance, ...) -
i.e. they always receive the MarketFeed instance as an extra first argument.
"""
import os
from typing import Dict, Optional
from datetime import datetime
from threading import Thread, Lock

try:
    from dhanhq import DhanContext, MarketFeed
except ImportError as exc:
    # The upstream DhanHQ SDK has changed these exports between releases.
    # Keep the local paper-trading dashboard usable without broker credentials.
    DhanContext = None
    MarketFeed = None
    DHAN_SDK_IMPORT_ERROR = str(exc)
else:
    DHAN_SDK_IMPORT_ERROR = None

# REST API segment name -> MarketFeed's numeric segment constant
SEGMENT_MAP = (
    {
        "IDX_I": MarketFeed.IDX,
        "NSE_EQ": MarketFeed.NSE,
        "NSE_FNO": MarketFeed.NSE_FNO,
        "NSE_FO": MarketFeed.NSE_FNO,
        "NSE_CURRENCY": MarketFeed.NSE_CURR,
        "BSE_EQ": MarketFeed.BSE,
        "MCX_COMM": MarketFeed.MCX,
        "BSE_CURRENCY": MarketFeed.BSE_CURR,
        "BSE_FNO": MarketFeed.BSE_FNO,
    }
    if MarketFeed is not None
    else {}
)


class DhanLiveClient:
    """
    DhanHQ WebSocket-based live market feed client.
    Subscribes to instruments and streams live price updates via WebSocket.
    """

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        self.price_lock = Lock()
        self.latest_prices: Dict[str, Dict] = {}  # security_id -> price data
        self.market_feed = None
        self.context = None
        self.subscribed = False
        self.last_error: Optional[str] = None
        self.last_traceback: Optional[str] = None

        if not self.access_token or not self.client_id:
            print("[WARN] DhanHQ credentials not set")
            return

        if DhanContext is None or MarketFeed is None:
            self.last_error = (
                "Installed DhanHQ SDK does not provide the legacy MarketFeed API"
            )
            print(f"[WARN] {self.last_error}: {DHAN_SDK_IMPORT_ERROR}")
            return

        self.context = DhanContext(self.client_id, self.access_token)

    def on_connect(self, instance):
        """Callback when WebSocket connects"""
        print("[INFO] DhanHQ WebSocket connected")

    def on_message(self, instance, message):
        """Callback for incoming WebSocket ticks (already parsed by MarketFeed into a dict)"""
        try:
            if not isinstance(message, dict):
                return

            # DEBUG: Log message structure once
            if not hasattr(self, '_logged_msg_keys'):
                print(f"[DEBUG] Message keys: {list(message.keys())}")
                self._logged_msg_keys = True

            security_id = str(message.get("security_id") or message.get("SecurityId") or message.get("securityId") or "")
            if not security_id:
                return

            def _f(key, alt_key=None, default=0.0):
                val = message.get(key) or (message.get(alt_key) if alt_key else None)
                if val is None:
                    return default
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            with self.price_lock:
                existing = self.latest_prices.get(security_id, {})
                # Try multiple field name variations
                ltp = _f("LTP", "ltp", existing.get("close", 0))
                if ltp == 0:
                    ltp = _f("close", None, existing.get("close", 0))

                self.latest_prices[security_id] = {
                    "close": ltp,
                    "open": _f("open", "Open", existing.get("open", ltp)),
                    "high": _f("high", "High", existing.get("high", ltp)),
                    "low": _f("low", "Low", existing.get("low", ltp)),
                    "volume": int(_f("volume", "Volume", existing.get("volume", 0))),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                if ltp > 0:
                    print(f"[TICK] SecurityID {security_id}: ${ltp:.2f}")
        except Exception as e:
            print(f"[ERROR] WebSocket message parsing: {e}")

    def on_close(self, instance):
        """Callback when WebSocket closes"""
        print("[WARN] DhanHQ WebSocket disconnected")
        self.subscribed = False

    def on_error(self, instance, error):
        """Callback on WebSocket error"""
        print(f"[ERROR] DhanHQ WebSocket error: {error}")
        self.last_error = str(error)

    def subscribe(self, instruments: list):
        """
        Subscribe to live market feed for given instruments.

        Args:
            instruments: List of dicts: [{"ExchangeSegment": "NSE_EQ", "SecurityId": "500325"}, ...]
                         ExchangeSegment must be one of SEGMENT_MAP's keys.
        """
        self.last_error = None

        if not self.context or not self.access_token:
            self.last_error = "Credentials not set (DHAN_CLIENT_ID/DHAN_ACCESS_TOKEN missing)"
            return False

        try:
            # MarketFeed wants (segment_int, security_id_str, request_code) tuples.
            # Full (21) gives OHLCV; indices have no volume/depth so they only
            # publish Ticker (15) packets - Full/Quote silently produce nothing for them.
            instrument_tuples = [
                (
                    SEGMENT_MAP.get(inst.get("ExchangeSegment", "NSE_EQ"), MarketFeed.NSE),
                    str(inst.get("SecurityId", "")),
                    MarketFeed.Ticker if inst.get("ExchangeSegment") == "IDX_I" else MarketFeed.Full,
                )
                for inst in instruments
                if inst.get("SecurityId")
            ]

            self.market_feed = MarketFeed(
                self.context,
                instrument_tuples,
                on_connect=self.on_connect,
                on_message=self.on_message,
                on_close=self.on_close,
                on_error=self.on_error,
            )

            print(f"[INFO] Subscribing to {len(instrument_tuples)} instruments via WebSocket...")
            feed_thread = Thread(target=self.market_feed.run, daemon=True)
            feed_thread.start()

            self.subscribed = True
            return True
        except Exception as e:
            import traceback
            self.last_error = f"{type(e).__name__}: {e}"
            self.last_traceback = traceback.format_exc()
            return False

    def get_live_data(self, security_id: str, symbol: str = "", segment: str = "NSE_EQ") -> Dict:
        """
        Get latest live price for a security.

        Args:
            security_id: DhanHQ security ID (as string)
            symbol: Symbol name (for reference only)
            segment: ExchangeSegment code (NSE_EQ, NSE_FO, MCX, etc.)

        Returns:
            Dict with latest OHLCV data or empty dict if no data yet
        """
        with self.price_lock:
            data = self.latest_prices.get(str(security_id), {})

        if data:
            return {
                "symbol": symbol,
                "segment": segment,
                **data
            }

        # Return template with zeros if no data yet (caller checks close value)
        return {
            "symbol": symbol,
            "segment": segment,
            "timestamp": datetime.utcnow().isoformat(),
            "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0,
        }

    def close(self):
        """Close WebSocket connection"""
        if self.market_feed:
            self.market_feed.close()
            self.subscribed = False
