# JARVIS 2 - QUICK START (Live Trading Ready!)

## 🎯 Current Status: PRODUCTION READY ✅

**Everything is built and tested. You just need to add 2 API credentials.**

---

## ⚡ 5-Minute Setup

### 1. Create `.env` file
```bash
cp .env.template .env
```

### 2. Add API Credentials

**Get ONDA Trading Token (Primary for XAUUSD):**
1. Go to https://www.onda.trading/
2. Login → Settings → API → Copy your API Key and Access Token
3. Add to `.env`:
```
ONDA_API_KEY=your_onda_api_key
ONDA_ACCESS_TOKEN=your_onda_access_token
```

**Get DhanHQ Token (Fallback for XAUUSD):**
1. Go to https://www.dhanhq.co/
2. Login → Settings → API → Copy your Client ID and Access Token
3. Add to `.env`:
```
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

**Get Zerodha Kite Token (Stocks & Options):**
1. Go to https://kite.trade/
2. Login → Settings → API → Generate Access Token
3. Add to `.env`:
```
KITE_API_KEY=your_api_key
KITE_ACCESS_TOKEN=your_access_token
```

### 3. Test APIs
```bash
cd backend
python test_apis.py
```

**Expected Output:**
```
API Configuration Status:
  DhanHQ (Forex/Commodities): CONFIGURED
  Kite/Zerodha (Equities):    CONFIGURED

Testing Live Market Data Fetch...
Fetching XAUUSD... [SUCCESS]
Fetching RELIANCE... [SUCCESS]
Fetching NIFTY... [SUCCESS]
Fetching TCS... [SUCCESS]

Summary: 4/4 symbols fetched successfully
[SUCCESS] APIs are live and connected!
```

### 4. Start Services
```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn main:app --reload

# Terminal 2 - Frontend  
cd frontend
python -m http.server 8001 --directory dist
```

### 5. Open Dashboard
- Go to: **http://localhost:8001**
- Watch live trades appear in real-time

---

## 📊 What You'll See

### Live Trading Dashboard
```
HEADER (Updates Every Tick):
├─ Total PnL: +₹XXX.XX 📈
├─ Win Rate: XX.X%
├─ Active Trades: N
└─ Time: HH:MM:SS

AGENT PERFORMANCE (5 Agents):
├─ STOCKS   [WORKING] → Real-time trades on RELIANCE, TCS, INFY
├─ SENSEX  [IDLE]    → Monitoring SENSEX index
├─ OPTIONS [WORKING] → Trading NIFTY, BANKNIFTY
├─ CANDLE  [IDLE]    → Pattern-based entries
└─ XAUUSD  [ACTIVE]  → Gold forex trading 🌟

LIVE POSITIONS (Real-time P&L):
├─ RELIANCE Entry: ₹2500 | P&L: +₹125 (LIVE!)
├─ NIFTY    Entry: 23400 | P&L: +₹250 (LIVE!)
├─ XAUUSD   Entry: 2505  | P&L: +₹50  (LIVE!)
└─ More trades as they execute...
```

---

## 🔄 APIs Integrated

| API | Coverage | Priority | Status |
|---|---|---|---|
| **ONDA Trading** | XAUUSD (Gold Forex) | Primary | ✅ Ready |
| **DhanHQ** | XAUUSD (Gold Forex) | Fallback | ✅ Ready |
| **Zerodha Kite** | RELIANCE, TCS, INFY, NIFTY, BANKNIFTY, SENSEX | — | ✅ Ready |

---

## 🎯 How It Works

```
1. Market opens
   ↓
2. Backend polls APIs every 5 seconds
   ↓
3. Real market prices received
   ↓
4. Each agent analyzes with its strategy
   ↓
5. When signal found → CREATE TRADE
   ↓
6. Dashboard updates instantly
   ↓
7. P&L calculated on current price
   ↓
8. Repeat every 5 seconds
```

---

## 📋 Agents & Strategies

| Agent | Symbols | Strategy | Status |
|-------|---------|----------|--------|
| **STOCKS** | RELIANCE, TCS, INFY, WIPRO, ICICIBANK | Volume + Price Change (>1.5%) | 🟢 Ready |
| **SENSEX** | SENSEX | Support/Resistance Range | 🟢 Ready |
| **OPTIONS** | NIFTY, BANKNIFTY, FINNIFTY | Candle Body Ratio (>70%) | 🟢 Ready |
| **CANDLE** | RELIANCE, TCS, INFY, NIFTY, BANKNIFTY | Close Pattern + Trend | 🟢 Ready |
| **XAUUSD** | XAUUSD | EMA(12) Crossover | 🟢 Ready |

---

## ⚙️ Configuration

All settings in `backend/main.py`:

```python
# Paper Trading Enforced
PAPER_TRADING_ENABLED = True  # ✅ No real money

# Capital Allocation
INITIAL_CAPITAL = 500,000
per_agent = 100,000 each

# Risk Management
risk_per_trade = 3,500  # Per agent

# Live Update Frequency
Market Polling: 5 seconds
Dashboard Refresh: 1 second
```

---

## 🔒 Safety Features

✅ **Paper Trading Only** - No real broker orders  
✅ **Live Prices** - Real market data  
✅ **Simulated Execution** - Paper-only positions  
✅ **Real P&L** - Based on live market prices  
✅ **Rate Limited** - Respects API limits  
✅ **Timeout Protected** - 15s max per request  

---

## ❓ Troubleshooting

### No API data showing up?
1. Did you create `.env` file?
2. Did you add credentials?
3. Run `python test_apis.py` to diagnose

### "CONFIGURED" but no live trades?
1. Check if market is open (9:15-3:30 IST)
2. Verify credentials are correct
3. Check firewall allows HTTPS outbound

### Want to reset trades?
```bash
cd backend
python reset_trades.py
```
(This only clears test trades, not live ones)

---

## 📖 Full Documentation

- **Setup Guide**: `API_SETUP_GUIDE.md` - Detailed credential setup
- **Integration Status**: `INTEGRATION_STATUS.md` - Architecture overview
- **Code**: `backend/data/multi_api_client.py` - API router

---

## 🚀 YOU'RE READY!

### Next 3 Steps:
1. ✅ Add DhanHQ credentials
2. ✅ Add Zerodha Kite credentials  
3. ✅ Run `test_apis.py`

**Then watch LIVE TRADING happen! 🎯**

---

## 💡 Pro Tips

- **Market Hours**: NSE 9:15 AM - 3:30 PM IST, Mon-Fri
- **Forex**: XAUUSD trades 24/5 (Sun-Fri)
- **Best Time**: First hour (9:15-10:15) has highest volume
- **Monitor**: Watch dashboard for agent signals
- **Adjust**: If win rate drops, agents self-optimize

---

## 🎉 Ready to Launch!

```bash
# Terminal 1
cd backend && python -m uvicorn main:app --reload

# Terminal 2
cd frontend && python -m http.server 8001 --directory dist

# Open browser
http://localhost:8001
```

**LIVE TRADING STARTS NOW! 🚀**
