# JARVIS 2 - PROFITABLE TRADING RULES

**Core Principle: Quality Over Quantity**
- 2 profitable trades > 10 mediocre trades
- Focus on profit per trade, NOT trade volume
- Book profits early, cut losses tight

---

## Entry Rules (Pre-Trade Profitability Check)

### Requirement 1: Win Probability >= 75%
```
Before ANY trade, calculate probability of profit
- Only enter if odds are 75%+ in our favor
- Use technical factors to estimate probability
- Skip trades that don't meet this threshold
```

### Requirement 2: Risk/Reward Ratio >= 2:1
```
Reward must be at least 2x the Risk
Example:
  Entry: ₹1000
  Stop Loss: ₹970 (Risk = 30)
  Take Profit: ₹1060 (Reward = 60)
  Ratio: 60/30 = 2.0:1 ✓ GOOD

If ratio < 2:1 → DO NOT TRADE
```

### Requirement 3: Positive Expected Value
```
Expected Profit % = (Win% × Avg Win) - (Loss% × Avg Loss)

Example with 75% win rate:
  (0.75 × 60) - (0.25 × 30) = 45 - 7.5 = +37.5% ✓ PROFITABLE

If Expected Value < 0 → DO NOT TRADE
```

---

## Stop Loss & Take Profit Rules

### Stop Loss (TIGHT)
```
BUY:  Entry × 0.97   (3% below entry)
SELL: Entry × 1.03   (3% above entry)

Why tight? Protects capital, cuts losses fast
```

### Take Profit (AGGRESSIVE BOOKING)
```
PRIMARY: Entry × 1.04 (4% profit) - 33% quantity
SECONDARY: Entry × 1.06 (6% profit) - 33% quantity
TERTIARY: Entry × 1.08 (8% profit) - 34% quantity

Book profits in thirds:
  - 1st third at 4%
  - 2nd third at 6%
  - 3rd third at 8%

Why? Secures profit early, avoids greedy reversals
```

---

## Daily Trade Metrics (Track These)

### Must Calculate
```
Win Rate %          = Wins / Total Trades
Profit Factor       = Total Profit / Total Loss  (Goal: 3.0+)
Avg Win             = Total Profit / Number of Wins
Avg Loss            = Total Loss / Number of Losses
Win/Loss Ratio      = Avg Win / Avg Loss  (Goal: 2.0+)
Net Profit          = Total Profit - Total Loss
```

### Decision Framework
```
EXCELLENT (Keep Strategy):
  Win Rate >= 80% + Profit Factor >= 1.5 + Net Profit > 0

GOOD (Monitor):
  Win Rate >= 70% + Net Profit > 0

OKAY (Tighten Filters):
  Win Rate >= 60% + Net Profit > 0
  → Increase entry thresholds, be MORE selective

POOR (Change Strategy):
  Win Rate < 50% OR Net Profit < 0
  → Complete strategy overhaul needed
```

---

## Agent-Specific Rules

### XAUUSD (EMA Crossover)
```
Entry Conditions:
  ✓ EMA12 > EMA26 + Close > EMA12 (BUY)
  ✓ EMA12 < EMA26 + Close < EMA12 (SELL)
  ✓ Volume > 10,000 contracts
  ✓ Profit probability >= 75%

Skip if:
  - Very choppy market (no clear trend)
  - Low volume
  - Expected profit < 0
```

### STOCKS (Momentum)
```
Entry Conditions:
  ✓ Intraday change > 0.8% (was 1.5%, reduced for quality)
  ✓ Volume > 20-day average
  ✓ RSI between 30-70 (avoid extremes)
  ✓ Profit probability >= 75%

Skip if:
  - Early morning gap opens (too volatile)
  - Before economic news
  - Volume declining
```

### SENSEX (Range Position)
```
Entry Conditions:
  ✓ Close > 60% of day's range (BUY)
  ✓ Close < 40% of day's range (SELL)
  ✓ Daily range > 1.5% (sufficient movement)
  ✓ Profit probability >= 75%

Skip if:
  - Market choppy (tight range)
  - Strong trend (don't fight trends)
  - News/events pending
```

### OPTIONS (Candle Body)
```
Entry Conditions:
  ✓ Body ratio > 50% of range (was 70%, reduced for more setups)
  ✓ Volume > 500,000 contracts
  ✓ Trading hours first 2 hours only
  ✓ Profit probability >= 75%

Skip if:
  - Late afternoon (avoid surprises)
  - Low volatility
  - Expiry week (time decay issues)
```

---

## Daily Analysis (3:30 PM IST)

Run: `python daily_profitability.py`

**Reports Generated:**
- `daily_profitability/2026-09-22_XAUUSD.json`
- `daily_profitability/2026-09-22_STOCKS.json`
- `daily_profitability/2026-09-22_SENSEX.json`
- `daily_profitability/2026-09-22_OPTIONS.json`

**Each Report Shows:**
```
Total Trades | Wins | Losses
Win Rate | Profit Factor | Net Profit
Avg Win | Avg Loss | Win/Loss Ratio
Largest Win | Largest Loss
Recommendation: Keep / Monitor / Tweak / Change
```

---

## Typical Daily Target

**Instead of:** "Take 50 trades, hope for 45+ wins"

**Now:** "Take 3-5 PROFITABLE trades per agent"

Example Perfect Day:
```
XAUUSD:  3 trades → 3 wins (+420 profit) ✓
STOCKS:  2 trades → 2 wins (+280 profit) ✓
SENSEX:  2 trades → 2 wins (+310 profit) ✓
OPTIONS: 4 trades → 3 wins (+630 profit) ✓
─────────────────────────────────────
TOTAL:  11 trades → 10 wins → 91% win rate + 1,640 profit
```

vs. Old Way:
```
217 trades → 164 wins (75.6% win rate) but quality unknown
Could have more losses hidden in volume
```

---

## What Changes After Profitability Filter

### Before:
- Took ALL signals (low thresholds)
- 200+ trades/month
- Mixed quality (some winners, some losers)
- Win rate around 75%

### After:
- Only PROFITABLE signals (high thresholds)
- 30-50 trades/month (more selective)
- High quality ALL trades
- Win rate 80-100%
- Profit factor 3.0-10.0+

---

## The Math (Why This Works)

**Example: Old System**
```
100 trades @ 75% win rate
75 wins × ₹500 avg  = +₹37,500
25 losses × ₹500    = -₹12,500
Net = +₹25,000 (not great for capital risk)
```

**Example: New System**
```
20 trades @ 90% win rate
18 wins × ₹1,500 avg = +₹27,000
2 losses × ₹300      = -₹600
Net = +₹26,400 (better with less capital at risk!)
```

---

## Golden Rules (NEVER Break)

1. ✓ **NEVER trade without profitability check**
   - Calculate win probability FIRST
   - Skip if < 75%

2. ✓ **NEVER violate 3% stop loss**
   - Protects capital from large losses
   - One trade shouldn't hurt too much

3. ✓ **ALWAYS book profits in thirds**
   - 33% at 4%, 33% at 6%, 34% at 8%
   - Take profits OFF THE TABLE

4. ✓ **NEVER override daily metrics**
   - If win rate < 80%, don't add capital
   - If profit factor < 1.5, review strategy
   - If net profit < 0, CHANGE approach

5. ✓ **ALWAYS check for volume**
   - No volume = no liquidity = no profit
   - Skip low volume setups

---

## Expected Performance

**Daily:** 2-5 profitable trades per agent
**Weekly:** 10-25 total profitable trades
**Monthly:** 40-100 total profitable trades
**Win Rate:** 80-95%+
**Profit Factor:** 3.0-8.0+
**Average Profit:** ₹200-500 per trade

**NOT Expected:**
- ❌ 50+ trades per day
- ❌ 70-75% win rate (too low quality)
- ❌ Huge single trades
- ❌ Martingale or revenge trading

---

**REMEMBER: Profitability is the goal. Volume is the distraction.**

Trade smart, book profits, live another day to trade again.
