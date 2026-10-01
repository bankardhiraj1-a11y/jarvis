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

**How to apply:** Use an explicit completed-bar adapter with parity tests. Provider bar-open time must stay separate from close-price observation time, including session-boundary checks. Reject warmup bars that complete after the first sample opens. Label bar-fill models and signal-only analysis separately from executable option-performance evidence.

An exchange last-trade timestamp is not a bid/ask depth-update timestamp.

**Why:** The provider returns observed market depth alongside the time of the last transaction, not the time each quoted side changed.

**How to apply:** Retain observation and trade times separately. Filter stale data conservatively, and never describe receipt time or last-trade time as verified depth-update provenance.

OANDA practice and live API authorization must be verified separately. A successful practice pricing response is genuine provider evidence, but does not establish live-account authorization or validated paper performance.

**Why:** Verification succeeded for practice account/pricing endpoints while the live account endpoint rejected the same token. Silently dropping the environment label would misrepresent the source.

**How to apply:** Preserve practice/live environment with every observation, discover an account only when exactly one is authorized, and keep data collection separate from trade-entry approval.

Validate currency-conversion instruments independently from the traded instrument; successful gold pricing does not imply usable USD/INR pricing.

**Why:** Gold observations were current while the same provider returned an old, nontradeable USD/INR observation. Treating it as a live exchange rate would misstate INR portfolio P&L.

**How to apply:** Keep source-currency trade P&L unchanged. Consolidate only with a fresh, explicitly sourced FX observation or labeled daily reference; missing FX or market marks must leave totals unavailable.

Live and historical strategies must advance identical indicator state outside entry windows and while positions are open.

**Why:** A candidate search suppressed EMA updates during those periods, while its proposed runtime continued updating them. That made its reported outcomes unsuitable for evaluating the deployed strategy.

**How to apply:** Share a completed-bar reducer between replay and runtime. Entry eligibility may suppress orders, not indicator updates. Preserve the original strategy independently when evaluating replacements.