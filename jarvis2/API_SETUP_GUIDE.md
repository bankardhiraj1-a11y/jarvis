# Jarvis 2 - Multi-API Setup Guide

## Overview
Jarvis 2 integrates **THREE market data APIs** for complete trading coverage:

| API | Purpose | Symbols | Status |
|---|---|---|---|
| **ONDA Trading** | Forex & Gold (Primary) | XAUUSD | ✅ Integrated |
| **DhanHQ** | Forex & Commodities (Fallback) | XAUUSD, Crude Oil | ✅ Integrated |
| **Zerodha Kite** | Equities & Options | RELIANCE, TCS, NIFTY, BANKNIFTY, SENSEX | ✅ Integrated |

---

## Quick Start (5 minutes)

### 1️⃣ Copy Environment Template
```bash
cp .env.template .env
```

### 2️⃣ Add Your API Credentials to `.env`

#### For ONDA Trading (Forex/Gold - Primary)
1. Go to: https://www.onda.trading/
2. Login → Settings → API Credentials
3. Copy your credentials:
```
ONDA_API_KEY=xxx
ONDA_ACCESS_TOKEN=xxx
```

#### For DhanHQ (Forex/Gold - Fallback)
1. Go to: https://www.dhanhq.co/
2. Login → Settings → API Credentials
3. Copy your credentials:
```
DHAN_CLIENT_ID=xxx
DHAN_ACCESS_TOKEN=xxx
```

#### For Zerodha Kite (Stocks/Options)
1. Go to: https://kite.trade/
2. Login → Settings → API Credentials
3. Generate access token via: https://kite.trade/docs/connect/v3/
4. Copy your credentials:
```
KITE_API_KEY=xxx
KITE_ACCESS_TOKEN=xxx
```

### 3️⃣ Test the Connection
```bash
cd backend
python test_apis.py
```

Expected output:
```
API Configuration Status:
  DhanHQ (Forex/Commodities): CONFIGURED
  Kite/Zerodha (Equities):    CONFIGURED

Testing Live Market Data Fetch...
Fetching XAUUSD... [SUCCESS]
Fetching RELIANCE... [SUCCESS]
...
Summary: 4/4 symbols fetched successfully

[SUCCESS] APIs are live and connected!
```

### 4️⃣ Start the Backend
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5️⃣ Start the Frontend
```bash
cd ../frontend
python -m http.server 8001 --directory dist
```

### 6️⃣ Open Dashboard
- Go to: http://localhost:8001
- See **LIVE trades** from real market data

---

## API Details

### ONDA Trading API Endpoints
- **LTP (Last Traded Price)**: Real-time forex prices
- **Quote**: Full bid/ask spreads and market depth
- **Support**: Focus on XAUUSD (Gold Forex)

**Rate Limit:** 1 request/second per endpoint

### DhanHQ API Endpoints
- **LTP (Last Traded Price)**: Real-time price updates
- **Quote**: Full bid/ask spreads and market depth
- **Candles**: Intraday OHLCV data
- **Option Chain**: Greeks and implied volatility

**Symbols:**
- XAUUSD (Gold)
- CRUDE (Oil)
- Other forex pairs

**Rate Limit:** 1 request/second per endpoint

### Zerodha Kite API Endpoints  
- **Quote**: Real-time stock/index quotes
- **Historical**: OHLCV candle data
- **Orders**: Paper-trading order placement (configured for paper-only)

**Symbols:**
- NSE:RELIANCE, NSE:TCS, NSE:INFOSY (Stocks)
- NSE:NIFTY 50, NSE:NIFTY BANK (Indices)
- BSE:SENSEX (Sensex)

**Rate Limit:** 10 requests/second

---

## Agent Trading Symbols

| Agent | Symbols | API | Fallback | Strategy |
|---|---|---|---|---|
| **STOCKS** | RELIANCE, TCS, INFY, WIPRO, ICICIBANK | Kite | — | Volume + Price Change |
| **SENSEX** | SENSEX | Kite | — | Support/Resistance Range |
| **OPTIONS** | NIFTY, BANKNIFTY, FINNIFTY | Kite | — | Candle Body Ratio |
| **CANDLE** | RELIANCE, TCS, INFY, NIFTY, BANKNIFTY | Kite | — | Close Pattern + Trend |
| **XAUUSD** | XAUUSD | ONDA | DhanHQ | EMA(12) Crossover |

---

## Troubleshooting

### ❌ "DhanHQ not configured"
- Check `.env` has `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN`
- Verify credentials at https://www.dhanhq.co/

### ❌ "Kite not configured"  
- Check `.env` has `KITE_API_KEY` and `KITE_ACCESS_TOKEN`
- Generate new token at https://kite.trade/docs/connect/v3/

### ❌ No live data received
- **Market Hours?** NSE: 9:15 AM - 3:30 PM IST, Mon-Fri
- **Credentials Valid?** Run `test_apis.py` to verify
- **Firewall?** Ensure HTTPS outbound is allowed
- **Rate Limit?** Wait a few seconds between requests

### ❌ "API Status: FAILED"
- Check internet connection
- Verify API endpoint URLs (may have changed)
- Check API documentation for authentication format changes

---

## Paper Trading Verification

All trades are **PAPER ONLY**:
```python
# From config.py
PAPER_TRADING_ENABLED = True  # ✅ No real money
```

Each agent has:
- ✅ Separate paper account (no real execution)
- ✅ Live market data (real prices)
- ✅ Simulated position management
- ✅ Real-time P&L calculation

---

## Dashboard Live Feed

Once APIs are connected, your dashboard will show:

**Live Positions Tab:**
- Real-time trades from live market signals
- Entry/Exit prices from actual market data
- Running P&L based on current prices
- Agent status (WORKING when analyzing)

**Agent Performance Panel:**
- Profit/Loss trade counts
- Win rate calculation
- Real-time confidence scores

**Portfolio Summary:**
- Total P&L (live updates every tick)
- Win rate from closed trades
- Net worth based on current prices

---

## Monitoring Live Trading

**Terminal Output:**
```
🎯 STOCKS BUY: RELIANCE @ ₹2500.50
🎯 XAUUSD SELL: XAUUSD @ ₹2505.25
🎯 OPTIONS BUY: NIFTY @ ₹23450.00
```

**Dashboard:**
- Active Trades count increases
- Agent status shows WORKING
- P&L updates in real-time
- Positions appear instantly

---

## API Limits & Best Practices

### DhanHQ
- Max 1 request/second (enforced with throttling)
- Batch multiple symbols in single request
- Cache quotes for 1-2 seconds when possible

### Zerodha Kite
- Max 10 requests/second
- Use market hours for live data (9:15-3:30 IST)
- Indices update every 1 second

### Rate Limiting
✅ Already built into multi_api_client.py:
```python
def _throttle(self):
    """Enforces rate limits automatically"""
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
```

---

## Getting Help

**API Documentation:**
- DhanHQ: https://dhanhq.co/docs/v2/
- Kite: https://kite.trade/docs/connect/v3/

**Support:**
- DhanHQ: support@dhanhq.co
- Zerodha: support@zerodha.com

---

## Next Steps

1. ✅ Copy `.env.template` → `.env`
2. ✅ Fill in API credentials
3. ✅ Run `python test_apis.py`
4. ✅ Restart backend
5. ✅ View dashboard at localhost:8001
6. ✅ Monitor live trades

**Status: READY FOR LIVE TRADING! 🚀**
