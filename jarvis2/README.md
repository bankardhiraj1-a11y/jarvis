# Jarvis 2 - AI Trading Platform

A self-learning, multi-agent trading platform targeting 90%+ win rate across all segments.

## Architecture

### Backend (FastAPI + Python)
- **Agents:** Stocks, SENSEX, Options, Candle, XAUUSD
- **Learning Engine:** Analyzes daily performance, suggests adjustments
- **Strategy Optimizer:** Auto-tunes parameters based on market conditions
- **Market Researcher:** Analyzes trends, liquidity, volatility
- **Performance Monitor:** Tracks toward 90% success ratio

### Frontend (React + Tailwind)
- Futuristic sci-fi HUD dashboard (Kite Zerodha-inspired)
- Live charting with Recharts
- Agent performance heatmap
- Real-time trade execution panel
- WebSocket live data updates

### Database (PostgreSQL)
- Trade history & execution logs
- Agent metrics & performance tracking
- Market data cache
- Strategy optimization history

## Quick Start

### Local Development

```bash
# Clone repo
cd jarvis-2

# Start with Docker Compose
docker-compose up

# Or manually:
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

### Railway Deployment

```bash
# Create Railway services
# 1. Backend: Deploy backend/ folder
# 2. Frontend: Deploy frontend/ folder
# 3. PostgreSQL: Use Railway's managed DB

# Set environment variables:
DATABASE_URL=postgresql://...
API_HOST=0.0.0.0
API_PORT=8000
```

## Learning System

### Daily Cycle
1. **Market Analysis** (before session)
   - Analyze volatility, trends, liquidity
   - Identify opportunities per agent

2. **Trading** (during session)
   - Agents execute trades based on signals
   - Real-time performance tracking

3. **Performance Review** (after session)
   - Calculate win rates, profit factors
   - Identify losing patterns
   - Generate adjustment recommendations

4. **Strategy Optimization** (overnight)
   - Test new parameters via backtesting
   - Adjust thresholds based on performance
   - Prepare improved strategy for next day

### Success Metrics

- **Target:** 90%+ win rate per agent per week
- **Tracked:** Win rate, profit factor, Sharpe ratio, max drawdown
- **Triggers:** Auto-adjustments when performance dips below 70%

## Agent Specifications

| Agent | Symbols | Strategy | Win Rate Target |
|-------|---------|----------|-----------------|
| **STOCKS** | RELIANCE, TCS, INFY, WIPRO, ICICIBANK | Price action, volume | 90%+ |
| **SENSEX** | SENSEX | Index momentum, reversal | 90%+ |
| **OPTIONS** | NIFTY, BANKNIFTY, FINNIFTY | Volatility, Greeks | 90%+ |
| **CANDLE** | Multi-symbol | Candlestick patterns, trend | 90%+ |
| **XAUUSD** | XAUUSD | EMA crossover, trend | 90%+ |

## API Endpoints

```
GET  /health                    - Health check
GET  /portfolio                 - Portfolio summary (P&L, positions, net worth)
GET  /agents/performance        - All agents' metrics
POST /market-data               - Ingest market data
GET  /trades                    - Get trades by agent
WS   /ws/live                   - WebSocket for live updates
```

## Self-Learning Features

1. **LearningEngine**
   - Daily performance analysis
   - Win rate tracking
   - Confidence scoring

2. **StrategyOptimizer**
   - Parameter optimization
   - Market condition adaptation
   - Backtesting framework

3. **MarketResearcher**
   - Trend detection
   - Volatility analysis
   - Opportunity identification

4. **PerformanceMonitor**
   - 90% target tracking
   - Improvement plan generation
   - Auto-alerting system

## Development

### Backend Structure
```
backend/
├── main.py              # FastAPI app
├── config.py            # Settings
├── database.py          # SQLAlchemy setup
├── models.py            # DB models
├── agents/
│   ├── base.py          # Base agent class
│   ├── stocks.py        # Stocks agent
│   ├── sensex.py        # SENSEX agent
│   ├── options.py       # Options agent
│   ├── candle.py        # Candle agent
│   └── xauusd.py        # XAUUSD agent
└── learning/
    ├── learning_engine.py       # Learning core
    ├── strategy_optimizer.py    # Parameter optimization
    ├── market_researcher.py     # Market analysis
    └── performance_monitor.py   # Success tracking
```

### Frontend Components
```
frontend/
├── src/
│   ├── App.jsx                 # Main dashboard
│   ├── components/
│   │   ├── Dashboard.jsx       # Charts & indicators
│   │   ├── TradePanel.jsx      # Recent trades
│   │   └── AgentMetrics.jsx    # Agent performance
│   └── index.css               # Tailwind + theme
└── index.html
```

## Paper Trading Only

**Standing Rule:** All trades are paper-simulated. No live broker connections.

## License

Proprietary - AccentrixAI
