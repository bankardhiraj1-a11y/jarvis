---
name: Trading evidence boundaries
description: Dhan endpoint authentication and replay/provenance pitfalls found during genuine-data verification
---

Do not infer Dhan market-data authentication requirements from historical chart access. Token-only chart requests can succeed while live quotes require a client-ID header; the token-authenticated profile can resolve that ID privately.

**Why:** Direct verification returned historical bars without a client ID, but live quote requests returned 401 until profile-based identity resolution was used. Requiring the creator to supply a separate ID was unnecessary.

**How to apply:** Verify each endpoint independently using read-only requests. Keep profile-derived identity only in memory; never log or export credentials or profile content.

Resolve authenticated identity before concurrent market-data collectors can use a configured fallback.

**Why:** Simultaneous profile resolution and quote/chain startup allowed a rejected fallback request to clear the good identity after it had been discovered.

**How to apply:** Serialize identity resolution, make dashboard/cache reads network-free, and ensure a late rejection cannot invalidate a newer identity.

Historical OHLC bars must not be replayed as one close-price tick per bar. Preserve their open/high/low/close and make the completed bar available only at its closing time.

**Why:** Close-only replay turned genuine one-minute candles into dojis and falsely reported no scalping signals, while also altering options ATR and range conditions. Synthetic intrabar paths would be equally unsupported.

**How to apply:** Use an explicit completed-bar adapter with parity tests. Label bar-fill models and signal-only analysis separately from executable option-performance evidence.

An exchange last-trade timestamp is not a bid/ask depth-update timestamp.

**Why:** The provider returns observed market depth alongside the time of the last transaction, not the time each quoted side changed.

**How to apply:** Retain observation and trade times separately. Filter stale data conservatively, and never describe receipt time or last-trade time as verified depth-update provenance.