# Gold H4 / M15 / M3 forward-paper experiment

This replaces the automatic M1 RSI/Bollinger experiment only. Existing manual
parents, pending orders and trades are retained. There is no broker-order API.

## Frozen rule contract

- H4 completed midpoint close: EMA20 above EMA50, close above EMA20, and
  EMA20 rising over three bar intervals for BUY; inverse for SELL.
- M15 completed bars: matching EMA20/50 alignment and close on the matching
  side of EMA20. At least one of the latest three bars must touch its own EMA20.
- M3 completed bullish close above the previous high and EMA20 for BUY;
  completed bearish close below the previous low and EMA20 for SELL.
- All three directions must agree. Mixed, incomplete or unavailable data is HOLD.
- Startup suppresses the latest historical setup. Each later M3 close is checked
  at most once. Indicator updates continue outside entry hours and during holds.

The original detailed conversation specification was not available in repository
history. This contract preserves the staged implementation, rather than introducing
new indicators or optimizing rules. Deterministic fixtures verify software behavior,
not market accuracy or profitability.

## Provider and warmup contract

Only OANDA practice XAU_USD evidence is eligible for automatic paper entries.
Quotes require provider UTC timestamps, explicit tradeability and usable bid/ask.
M3 uses three contiguous complete M1 bid/ask candles, not an invented tick path.
M15/H4 use native completed candles. H4 is aligned to OANDA's 17:00
America/New_York convention with daylight saving, not UTC-hour modulo four.
Bar-open time and close-observation time remain separate.

Fetch an extra provider candle so an incomplete candle cannot remove required
warmup: 240 completed M1, 100 M15 and 100 H4 are requested as bounded windows.
Strategy minimums are 50 completed M3, 50 M15 and 100 H4. Rolling refreshes append
to bounded EMA state rather than reseeding from a moving window. Restart uses
a new deterministic provider warmup and suppresses its first historical setup.
Only higher-timeframe closes observable by the M3 decision are used.

## Risk and holding

- One lot = 100 troy ounces. Stop $1.50/oz and target $3.75/oz.
- Planned price risk $150 and target $375, before unknown costs/gaps.
  This is not a guaranteed maximum realized loss or net-profit amount.
- At most three accepted Gold entries per provider UTC day; persisted entries
  including manual parents remain authoritative across restarts.
- London 08:00–17:00 local entry window, with a complete 25-minute holding
  window required before session close and the New York rollover buffer.
- No overnight automatic holds; due exits wait for genuine fresh quotes instead
  of inventing an exit. Pending manual orders and existing positions block
  automatic entries. Manual Gold parents use their own stop/target/rollover policy
  without an elapsed-time cap, including resumed trades; the automatic 25-minute
  limit must never override that contract. Manual Indian trades keep their
  market-specific bounded intraday holds.

## Evidence boundaries

No multiframe performance validation, holdout replay or parameter search was
performed. Prior RSI/Bollinger session-study results remain historical evidence
for that experiment only, not results for this replacement. The final holdout
remains untouched. Reused development searches accumulate selection bias.
Any later evaluation must freeze its scope first and use genuinely new forward
observations or an appropriately preserved holdout, without retuning on it.

Dashboard Gold totals retain existing trades; they combine prior strategy and
manual activity and must not be described as isolated multiframe performance.