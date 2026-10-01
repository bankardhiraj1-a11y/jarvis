from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import asyncio
from datetime import datetime, time
from pathlib import Path
import logging
import sys
import pytz
from dotenv import load_dotenv

load_dotenv()  # Load ONDA_ACCESS_TOKEN from .env

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config import get_settings
from database import get_db, engine, Base, SessionLocal
from models import Trade, Position, AgentMetrics, MarketData, AgentName, TradeType
from agents.stocks import StocksAgent
from agents.sensex import SensexAgent
from agents.options import OptionsAgent
from agents.xauusd import XAUUSDAgent
from agents.sensex_options_scalping import SensexOptionsScalpingAgent
from learning.learning_engine import LearningEngine
from learning.strategy_optimizer import StrategyOptimizer
from learning.market_researcher import MarketResearcher
from learning.performance_monitor import PerformanceMonitor
from orchestrator.boss_agent import BossAgent
from orchestrator.agent_team import AgentTeam
from backtest.backtest_engine import BacktestEngine
from data.dhan_live_client import DhanLiveClient
from data.onda_client import OndaClient
from scheduler.autonomous_optimizer import AutonomousOptimizer

settings = get_settings()
Base.metadata.create_all(bind=engine)

agents_map = {
    "STOCKS": StocksAgent(),
    "SENSEX": SensexAgent(),
    "OPTIONS": OptionsAgent(),
    "XAUUSD": XAUUSDAgent(),
    "SENSEX_OPTIONS_SCALPING": SensexOptionsScalpingAgent(),
}

learning_engine = LearningEngine()
strategy_optimizer = StrategyOptimizer()
market_researcher = MarketResearcher()
performance_monitor = PerformanceMonitor(target_win_rate=0.90)
backtest_engine = BacktestEngine()
dhan_client = DhanLiveClient()
onda_client = OndaClient()

# WebSocket subscriptions for live market feed
# Build instrument list for subscription
# Symbol to DhanHQ security ID mapping (NSE market data, Dhan Symbol Master)
SYMBOL_TO_ID = {
    "RELIANCE": 2885,
    "TCS": 11536,
    "INFY": 1594,
    "HDFC": 1333,        # HDFCBANK
    "BAJAJ-AUTO": 16669,
    "SENSEX": 51,        # Index
    "NIFTY": 13,         # Index
    "BANKNIFTY": 25,     # Index
}

# India NSE/BSE trading charges
# REAL Zerodha India charges (from brokerage calculator)
ZERODHA_CHARGES = {
    # NSE Intraday Equity (STOCKS/SENSEX/OPTIONS indices)
    "NSE_EQUITY_INTRADAY": {
        "brokerage_flat": 40,           # ₹40 flat per side = ₹80 round trip
        "stt_pct": 0.013,               # 0.013% on exit
        "exchange_charge_pct": 0.0031,  # 0.0031%
        "gst_pct": 1.427,               # 1.427% on brokerage
        "sebi_charge_flat": 0.84,       # ₹0.84 per side
        "stamp_duty_flat": 12,          # ₹12 per round trip
    },
    # NSE F&O Futures (SENSEX_SCALPING FNO scalping)
    "NSE_FNO": {
        "brokerage_flat": 40,           # ₹40 flat per side
        "stt_pct": 0.026,               # 0.026% on exit (higher for F&O)
        "exchange_charge_pct": 0.00183, # 0.00183%
        "gst_pct": 2.028,               # 2.028% on brokerage
        "sebi_charge_flat": 0.84,       # ₹0.84 per side
        "stamp_duty_flat": 8,           # ₹8 per round trip
    },
    # MCX Gold Futures (reference for gold commodity)
    "MCX_GOLD": {
        "brokerage_flat": 40,           # ₹40 flat per side
        "stt_pct": 0,                   # No STT on commodities
        "exchange_charge_pct": 0.0021,  # 0.0021%
        "gst_pct": 2.2975,              # 2.2975% on brokerage
        "ctt_pct": 0.050,               # 0.050% Commodity Transaction Tax
        "sebi_charge_flat": 0.5,        # ₹0.5 per side
        "stamp_duty_flat": 5,           # ₹5 per round trip
    },
    # XAUUSD Forex (ECN/STP broker via ONDA API)
    "XAUUSD_FOREX": {
        "commission_per_lot_usd": 4.50,  # $4.50 per standard lot (100 oz) round-trip ONLY
    },
}

def calculate_net_pnl(entry_price, exit_price, quantity, trade_type, symbol):
    """Calculate P&L after deducting REAL Zerodha/broker charges"""
    # Raw P&L
    if trade_type == "BUY":
        raw_pnl = (exit_price - entry_price) * quantity
    else:  # SELL
        raw_pnl = (entry_price - exit_price) * quantity

    # SENSEX_OPTIONS_SCALPING: Use minimal charges (premium-based, not index-based)
    # Options have different charge structure - for now use minimal charges
    if "SENSEX" in str(symbol) and quantity > 100:  # Options scalping (1000 units)
        # Options trading: minimal charges (~₹50-100 per trade for scalp)
        total_charges = 100  # Flat ₹100 for now
        return raw_pnl - total_charges

    # Determine charge structure based on symbol
    if symbol == "XAUUSD":
        charges = ZERODHA_CHARGES["XAUUSD_FOREX"]
        # For USD-based forex: commission is in USD
        # Assuming standard lot size = 100 oz, and entry_price is in USD/oz
        total_charges = charges["commission_per_lot_usd"] * (quantity / 100)
    elif symbol in ["SENSEX", "BANKNIFTY", "NIFTY"]:
        # Index F&O scalping uses NSE_FNO rates
        charges = ZERODHA_CHARGES["NSE_FNO"]
        brokerage = charges["brokerage_flat"] * 2
        gst = brokerage * (charges["gst_pct"] / 100)
        stt = exit_price * quantity * (charges["stt_pct"] / 100)
        exchange = (entry_price + exit_price) * quantity * (charges["exchange_charge_pct"] / 100)
        sebi = charges["sebi_charge_flat"] * 2
        total_charges = brokerage + gst + stt + exchange + sebi + charges["stamp_duty_flat"]
    else:
        # Equity stocks use intraday rates (default)
        charges = ZERODHA_CHARGES["NSE_EQUITY_INTRADAY"]
        brokerage = charges["brokerage_flat"] * 2
        gst = brokerage * (charges["gst_pct"] / 100)
        stt = exit_price * quantity * (charges["stt_pct"] / 100)
        exchange = (entry_price + exit_price) * quantity * (charges["exchange_charge_pct"] / 100)
        sebi = charges["sebi_charge_flat"] * 2
        total_charges = brokerage + gst + stt + exchange + sebi + charges["stamp_duty_flat"]

    # Net P&L
    net_pnl = raw_pnl - total_charges

    return net_pnl

_instruments_to_subscribe = [
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"},    # RELIANCE
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "11536"},   # TCS
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1594"},    # INFY
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"},    # HDFCBANK
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "16669"},   # BAJAJ-AUTO
    {"ExchangeSegment": "IDX_I", "SecurityId": "51"},       # SENSEX (index)
    {"ExchangeSegment": "IDX_I", "SecurityId": "13"},       # NIFTY (index)
    {"ExchangeSegment": "IDX_I", "SecurityId": "25"},       # BANKNIFTY (index)
]
boss_agent = None
agent_team = None
autonomous_optimizer = None

portfolio_state = {
    "total_pnl": 0.0,
    "net_worth": 100000.0,
    "positions": {},
    "active_trades": 0,
    "agent_performance": {}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global boss_agent, agent_team, autonomous_optimizer

    # uvicorn's dictConfig disables loggers not listed in its own config - re-arm ours
    logger.disabled = False
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not logger.handlers:
        _handler = logging.StreamHandler(sys.stdout)
        _handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(_handler)

    # Initialize agents
    try:
        for agent_name, agent in agents_map.items():
            portfolio_state["agent_performance"][agent_name] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "confidence": 0.5,
                "status": "IDLE",
                "analyzing": False,
            }
        print("[OK] All agents initialized", flush=True)

        # Subscribe to DhanHQ WebSocket for live market feed
        print("[INFO] Subscribing to DhanHQ live market feed...", flush=True)
        if dhan_client.subscribe(_instruments_to_subscribe):
            print("[OK] DhanHQ WebSocket subscription successful", flush=True)
        else:
            print("[WARN] DhanHQ WebSocket subscription failed - will retry", flush=True)
    except Exception as e:
        print(f"[ERROR] Agent init failed: {e}", flush=True)

    # Initialize boss agent and team (optional - don't block startup)
    try:
        boss_agent = BossAgent(agents_map)
        agent_team = AgentTeam(agents_map)
        logger.info("[OK] Boss agent and team ready")
    except Exception as e:
        logger.warning(f"[WARN] Boss/Team init skipped: {e}")

    # Start background LIVE market data feeder
    async def live_market_feeder():
        """Fetch LIVE market data from DhanHQ and feed to agents"""
        # Exchange segments for each agent (DhanHQ format: NSE_EQ, NSE_FO, etc.)
        agent_segments = {
            "STOCKS": "NSE_EQ",              # NSE Equity
            "SENSEX": "IDX_I",               # BSE/NSE Index
            "OPTIONS": "NSE_FO",             # NSE F&O (derivatives)
            "SENSEX_OPTIONS_SCALPING": "IDX_I",  # Index for trend detection
            "XAUUSD": "FOREXCFD",            # Forex (ONDA API)
        }

        symbol_map = {
            "STOCKS": ["RELIANCE", "TCS", "INFY", "HDFC", "BAJAJ-AUTO"],
            "SENSEX": ["SENSEX"],
            "OPTIONS": ["NIFTY", "BANKNIFTY"],
            "SENSEX_OPTIONS_SCALPING": ["SENSEX"],  # Uses SENSEX price for trend
            "XAUUSD": ["XAUUSD"],
        }

        while True:
            try:
                db = SessionLocal()

                # Fetch live data for each symbol and send to agents
                for agent_name, symbols in symbol_map.items():
                    for symbol in symbols:
                        try:
                            # Get LIVE market data from DhanHQ (NSE for India, ONDA for XAUUSD)
                            if agent_name == "XAUUSD":
                                # ONDA API for forex
                                live_data = onda_client.get_live_data(symbol, "FOREXCFD")
                            else:
                                # DhanHQ for NSE stocks and indices
                                segment = agent_segments.get(agent_name, "E")
                                security_id = SYMBOL_TO_ID.get(symbol)
                                if security_id:
                                    live_data = dhan_client.get_live_data(security_id, symbol, segment)
                                else:
                                    live_data = {}  # Unknown symbol

                            # Pass data to agent even if close=0 (race condition on startup)
                            # Agent will naturally skip zero-price ticks in candle building

                            agent = agents_map.get(agent_name)
                            if not agent:
                                continue

                            # Market hours check: skip analysis outside trading hours
                            ist = pytz.timezone('Asia/Kolkata')
                            utc = pytz.timezone('UTC')
                            now_ist = datetime.now(ist)
                            now_utc = datetime.now(utc)

                            # NSE agents: 9:15 AM - 3:30 PM IST (weekdays only)
                            nse_start = time(9, 15)
                            nse_end = time(15, 30)
                            is_nse_hours = now_ist.time() >= nse_start and now_ist.time() <= nse_end and now_ist.weekday() < 5

                            # XAUUSD forex: 16:00 UTC - 23:00 UTC (4 PM - 11 PM UTC = 9:30 PM - 4:30 AM IST next day)
                            xauusd_start = time(16, 0)
                            xauusd_end = time(23, 0)
                            is_xauusd_hours = xauusd_start <= now_utc.time() < xauusd_end


                            # Skip if outside market hours
                            if agent_name == "XAUUSD" and not is_xauusd_hours:
                                continue
                            elif agent_name != "XAUUSD" and not is_nse_hours:
                                continue

                            # Check if open position exists - CHECK BEFORE signal analysis (TP/SL must not be skipped)
                            open_trade = db.query(Trade).filter(
                                Trade.agent == AgentName[agent_name],
                                Trade.symbol == symbol,
                                Trade.status == "OPEN",
                            ).first()

                            # If position is open, check TP/SL FIRST (independent of signal)
                            if open_trade is not None:
                                current_price = live_data['close']
                                should_close = False

                                # Only check TP/SL if price is valid (not 0 or invalid data)
                                if current_price > 0:
                                    # Check take profit
                                    if open_trade.take_profit and open_trade.take_profit > 0:
                                        if open_trade.trade_type.value == "BUY" and current_price >= open_trade.take_profit:
                                            should_close = True
                                        elif open_trade.trade_type.value == "SELL" and current_price <= open_trade.take_profit:
                                            should_close = True

                                    # Check stop loss
                                    if open_trade.stop_loss and open_trade.stop_loss > 0:
                                        if open_trade.trade_type.value == "BUY" and current_price <= open_trade.stop_loss:
                                            should_close = True
                                        elif open_trade.trade_type.value == "SELL" and current_price >= open_trade.stop_loss:
                                            should_close = True

                                if should_close:
                                    # Close trade immediately - preserve history
                                    open_trade.exit_price = current_price
                                    open_trade.pnl = calculate_net_pnl(
                                        open_trade.entry_price,
                                        open_trade.exit_price,
                                        open_trade.quantity,
                                        open_trade.trade_type.value,
                                        open_trade.symbol
                                    )
                                    open_trade.status = "CLOSED"
                                    open_trade.closed_at = datetime.utcnow()
                                    print(f"[TP/SL CLOSE] {agent_name}/{symbol}: {open_trade.trade_type.value} @ {current_price:.3f} (TP: {open_trade.take_profit:.3f}, SL: {open_trade.stop_loss:.3f})", flush=True)
                                    db.commit()
                                continue  # Skip signal analysis - position is closed

                            # Get signal only if no open position
                            try:
                                signal = agent.analyze(live_data)
                            except Exception as analyze_err:
                                print(f"[ERROR] {agent_name} analyze failed: {analyze_err}", flush=True)
                                continue

                            print(f"[ANALYSIS] {agent_name} {signal.value}: {symbol} @ {live_data['close']}", flush=True)
                            if signal.value == "HOLD":
                                continue

                            print(f"[SIGNAL] {agent_name} {signal.value}: {symbol} @ {live_data['close']}", flush=True)

                            if open_trade is None:
                                # No position open - enter on the signal
                                entry_price = live_data['close']

                                # Calculate stop loss and take profit based on agent parameters
                                agent = agents_map[agent_name]
                                if agent_name == "XAUUSD":
                                    sl_pips = agent.stop_loss_pips
                                    tp_pips = agent.target_pips
                                else:
                                    sl_pips = getattr(agent, 'stop_loss_pips', 50)
                                    tp_pips = getattr(agent, 'take_profit_pips', 100)

                                # Calculate TP/SL
                                if signal.value == "BUY":
                                    stop_loss_price = entry_price - sl_pips
                                    take_profit_price = entry_price + tp_pips
                                else:  # SELL
                                    stop_loss_price = entry_price + sl_pips
                                    take_profit_price = entry_price - tp_pips

                                # Get quantity from agent (SENSEX_OPTIONS_SCALPING: 1000, STOCKS: 50, XAUUSD: 100, others: 1)
                                if agent_name == "STOCKS":
                                    qty = getattr(agent, 'base_quantity', 50.0)
                                else:
                                    qty = getattr(agent, 'quantity', 100.0 if agent_name == "XAUUSD" else 1.0)

                                # Get option details for SENSEX_OPTIONS_SCALPING
                                option_strike = None
                                option_price = None
                                if agent_name == "SENSEX_OPTIONS_SCALPING":
                                    option_strike = getattr(agent, 'current_atm_strike', None)
                                    option_price = getattr(agent, 'last_option_premium', None)  # Actual option premium, not index price

                                trade = Trade(
                                    agent=AgentName[agent_name],
                                    symbol=symbol,
                                    trade_type=TradeType[signal.value],
                                    quantity=qty,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss_price,
                                    take_profit=take_profit_price,
                                    status="OPEN",
                                    option_strike=option_strike,
                                    option_price=option_price
                                )
                                db.add(trade)
                        except Exception as e:
                            logger.error(f"[ERROR] {agent_name}/{symbol} feeder step failed: {e}", exc_info=True)

                db.commit()
                db.close()
                await asyncio.sleep(5)  # Poll every 5 seconds

            except Exception as e:
                logger.error(f"Market feeder error: {e}", exc_info=True)
                await asyncio.sleep(5)

    # Start live market feeder in background
    ticker_task = asyncio.create_task(live_market_feeder())

    # Initialize and start autonomous optimizer (24/7 self-learning until 90%+)
    db = SessionLocal()
    autonomous_optimizer = AutonomousOptimizer(
        boss_agent, agents_map, learning_engine, backtest_engine,
        strategy_optimizer, market_researcher, performance_monitor, db
    )

    # Start autonomous loop (runs until 90%+ achieved)
    optimizer_task = asyncio.create_task(autonomous_optimizer.start_autonomous_improvement_loop())

    print("\n" + "="*80)
    print("AUTONOMOUS MODE ACTIVATED")
    print("   Boss Agent: Full Control")
    print("   Optimizer: Running 24/7 until 90%+ achieved")
    print("   No manual intervention needed")
    print("="*80 + "\n")

    yield

    # Cleanup
    ticker_task.cancel()
    try:
        await ticker_task
    except asyncio.CancelledError:
        pass

    print("[OK] Shutdown complete")

app = FastAPI(title="Jarvis 2 Trading Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/")
async def root():
    """Serve main dashboard"""
    positions_file = Path(__file__).parent.parent.parent / "positions.html"
    if positions_file.exists():
        return FileResponse(positions_file, media_type="text/html")
    return {"error": "Dashboard not found"}

@app.get("/dashboard")
async def dashboard():
    """Serve positions & history dashboard"""
    return await root()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/feed")
async def debug_feed():
    return {
        "dhan_subscribed": dhan_client.subscribed,
        "dhan_latest_prices": dhan_client.latest_prices,
        "dhan_last_error": getattr(dhan_client, "last_error", None),
        "dhan_last_traceback": getattr(dhan_client, "last_traceback", None),
        "instruments_requested": _instruments_to_subscribe,
    }

@app.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    return portfolio_state

@app.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    positions = db.query(Position).order_by(Position.updated_at.desc()).all()
    return {
        "positions": [
            {
                "symbol": position.symbol,
                "agent": position.agent.value,
                "qty": position.quantity,
                "entryPrice": position.avg_price,
                "currentPrice": position.current_price,
                "pnl": position.unrealized_pnl or 0.0,
                "pnlPercent": (
                    round(
                        position.unrealized_pnl
                        / abs(position.avg_price * position.quantity)
                        * 100,
                        2,
                    )
                    if position.avg_price and position.quantity
                    else 0.0
                ),
            }
            for position in positions
        ]
    }

@app.get("/agents/performance")
async def get_agents_performance(db: Session = Depends(get_db)):
    result = {}

    # Return all agents with their current status from portfolio_state
    for agent_name in agents_map.keys():
        agent_status = portfolio_state["agent_performance"].get(agent_name, {})

        result[agent_name] = {
            "total_trades": agent_status.get("total_trades", 0),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": agent_status.get("win_rate", 0.0),
            "total_pnl": agent_status.get("total_pnl", 0.0),
            "confidence": 0.5,
            "status": agent_status.get("status", "IDLE"),
            "analyzing": agent_status.get("analyzing", False),
        }

    return result

@app.post("/market-data")
async def ingest_market_data(
    symbol: str,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    db: Session = Depends(get_db)
):
    market_data = MarketData(
        symbol=symbol,
        timestamp=datetime.utcnow(),
        open_price=open_price,
        high_price=high,
        low_price=low,
        close_price=close,
        volume=volume
    )
    db.add(market_data)
    db.commit()

    data_dict = {
        "symbol": symbol,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }

    for agent_name, agent in agents_map.items():
        if symbol in agent.get_symbols():
            signal = agent.analyze(data_dict)
            if signal.value != "HOLD":
                trade = Trade(
                    agent=AgentName[agent_name],
                    symbol=symbol,
                    trade_type=TradeType[signal.value],
                    quantity=1.0,
                    entry_price=close,
                    status="OPEN"
                )
                db.add(trade)

    db.commit()
    return {"status": "ingested", "symbol": symbol}

@app.get("/trades")
async def get_trades(agent: str = None, db: Session = Depends(get_db)):
    query = db.query(Trade)
    if agent:
        query = query.filter(Trade.agent == AgentName[agent])
    trades = query.order_by(Trade.created_at.desc()).limit(100).all()

    result = []
    for t in trades:
        if t.agent.value == "SENSEX" and t.status == "OPEN":
            import sys
            print(f"[SENSEX DEBUG] Processing trade: agent={t.agent.value}, status={t.status}, entry={t.entry_price}", file=sys.stderr, flush=True)
        # Get current price for open positions
        current_price = t.exit_price if t.status == "CLOSED" else 0
        if t.status == "OPEN":
            try:
                if t.agent.value == "XAUUSD":
                    # XAUUSD uses OANDA API
                    live_data = onda_client.get_live_data(t.symbol)
                    current_price = live_data.get("close", 0)
                else:
                    # Indian agents use DhanHQ live prices
                    security_id = SYMBOL_TO_ID.get(t.symbol)
                    if security_id and dhan_client and dhan_client.latest_prices:
                        price_data = dhan_client.latest_prices.get(str(security_id), {})
                        current_price = price_data.get("close", 0)
                        if t.agent.value == "SENSEX":
                            import sys
                            print(f"[SENSEX PRICE] ID={security_id}, price_data={price_data}, current_price={current_price}", file=sys.stderr, flush=True)
            except Exception as e:
                import sys
                print(f"[ERROR getting price] {t.symbol}: {str(e)}", file=sys.stderr, flush=True)

        # Calculate P&L: for OPEN trades use current_price, for CLOSED use exit_price
        pnl = t.pnl
        if t.status == "OPEN" and current_price > 0:
            # Unrealized P&L
            if t.trade_type.value == "BUY":
                pnl = (current_price - t.entry_price) * t.quantity
            else:  # SELL
                pnl = (t.entry_price - current_price) * t.quantity

        # P&L percent
        pnl_pct = 0.0
        if t.entry_price and t.quantity:
            pnl_pct = (pnl / (t.entry_price * t.quantity)) * 100

        # For trades missing TP/SL, calculate from agent pips
        stop_loss_display = t.stop_loss
        take_profit_display = t.take_profit
        if (stop_loss_display == 0 or take_profit_display == 0) and t.entry_price > 0:
            agent = agents_map.get(t.agent.value)
            if agent and hasattr(agent, 'stop_loss_pips') and hasattr(agent, 'take_profit_pips'):
                if t.trade_type.value == "BUY":
                    stop_loss_display = t.entry_price - agent.stop_loss_pips
                    take_profit_display = t.entry_price + agent.take_profit_pips
                else:  # SELL
                    stop_loss_display = t.entry_price + agent.stop_loss_pips
                    take_profit_display = t.entry_price - agent.take_profit_pips

        # TEST: Hardcode for SENSEX to verify code executes
        if t.agent.value == "SENSEX" and t.entry_price == 74186.68:
            stop_loss_display = 99999.0
            take_profit_display = 88888.0

        # Determine currency based on agent
        currency = "USD" if t.agent.value == "XAUUSD" else "INR"

        result.append({
            "id": t.id,
            "agent": t.agent.value,
            "symbol": t.symbol,
            "type": t.trade_type.value,
            "signal": t.trade_type.value,  # Alias for dashboard
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "current_price": current_price,
            "pnl": pnl,
            "pnl_percent": pnl_pct,
            "currency": currency,  # USD for XAUUSD, INR for others
            "status": t.status,
            "stop_loss": stop_loss_display,
            "take_profit": take_profit_display,
            "entry_time": t.created_at.isoformat(),
            "exit_time": t.closed_at.isoformat() if t.closed_at else None,
            "created_at": t.created_at.isoformat(),
        })

    return result

@app.get("/learning/analysis/{agent}")
async def get_agent_analysis(agent: str, db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
    trade_data = [{"pnl": t.pnl, "status": t.status} for t in trades[-50:]]

    analysis = learning_engine.analyze_daily_performance(agent, trade_data)
    confidence = learning_engine.calculate_confidence(agent, trade_data)

    market_data = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(20).all()
    market_conditions = market_researcher.analyze_market_conditions([
        {"close": m.close_price, "volume": m.volume, "high": m.high_price, "low": m.low_price}
        for m in market_data
    ])

    suggestions = learning_engine.suggest_strategy_adjustments(agent, market_conditions)

    return {
        "agent": agent,
        "analysis": analysis,
        "confidence": confidence,
        "market_conditions": market_conditions,
        "suggestions": suggestions,
    }

@app.get("/learning/strategy/{agent}")
async def get_optimized_strategy(agent: str, db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
    recent_performance = [{"pnl": t.pnl} for t in trades[-30:]]

    market_data = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(50).all()
    market_conditions = market_researcher.analyze_market_conditions([
        {"close": m.close_price, "volume": m.volume, "high": m.high_price, "low": m.low_price}
        for m in market_data
    ])

    optimized_params = strategy_optimizer.optimize_for_conditions(agent, market_conditions, recent_performance)

    return {
        "agent": agent,
        "optimized_parameters": optimized_params,
        "market_conditions": market_conditions,
        "optimization_timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/learning/performance")
async def get_performance_summary(db: Session = Depends(get_db)):
    summary = {}
    for agent_name in ["STOCKS", "SENSEX", "OPTIONS", "CANDLE", "XAUUSD"]:
        trades = db.query(Trade).filter(Trade.agent == AgentName[agent_name]).all()
        trade_data = [{"pnl": t.pnl, "status": t.status} for t in trades]
        perf = performance_monitor.track_agent_performance(agent_name, trade_data)
        summary[agent_name] = perf

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": summary,
        "target_win_rate": 90,
    }

@app.get("/learning/improvement-plan/{agent}")
async def get_improvement_plan(agent: str, db: Session = Depends(get_db)):
    plan = performance_monitor.get_improvement_plan(agent)

    trades = db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
    recent_trades = [{"pnl": t.pnl} for t in trades[-30:]]

    market_data = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(20).all()
    market_conditions = market_researcher.analyze_market_conditions([
        {"close": m.close_price, "volume": m.volume, "high": m.high_price, "low": m.low_price}
        for m in market_data
    ])

    opportunities = market_researcher.identify_opportunities(agent, market_conditions, recent_trades)

    return {
        "agent": agent,
        "improvement_plan": plan,
        "opportunities": opportunities,
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/boss/standup")
async def boss_daily_standup(db: Session = Depends(get_db)):
    if not boss_agent:
        return {"status": "boss_agent_not_initialized", "standup": None}
    market_snapshot = dhan_client.get_market_snapshot()
    standup = boss_agent.daily_standup(market_snapshot)
    return standup

@app.get("/boss/consensus")
async def get_team_consensus(db: Session = Depends(get_db)):
    if not boss_agent:
        return {"status": "boss_agent_not_initialized"}
    all_trades = db.query(Trade).all()
    market_data = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(20).all()
    market_conditions = market_researcher.analyze_market_conditions([
        {"close": m.close_price, "volume": m.volume, "high": m.high_price, "low": m.low_price}
        for m in market_data
    ])
    consensus = boss_agent.build_team_consensus(market_conditions, [{"agent": t.agent.value, "pnl": t.pnl} for t in all_trades])
    return consensus

@app.get("/boss/leaderboard")
async def get_agent_leaderboard(db: Session = Depends(get_db)):
    if not boss_agent:
        return {"leaderboard": []}
    metrics = db.query(AgentMetrics).all()
    agent_metrics = {m.agent.value: {"win_rate": m.win_rate, "total_pnl": m.total_pnl, "profit_factor": 0.75} for m in metrics}
    leaderboard = boss_agent.update_performance_leaderboard(agent_metrics)
    return {"leaderboard": leaderboard}

@app.get("/boss/report")
async def get_daily_report():
    if not boss_agent:
        return {"status": "boss_agent_not_initialized"}
    report = boss_agent.generate_daily_report()
    return report

@app.get("/team/health")
async def get_team_health():
    if not agent_team:
        return {"status": "team_not_initialized"}
    health = agent_team.get_team_health()
    return health

@app.post("/backtest/{agent}")
async def run_agent_backtest(agent: str, days: int = 30, db: Session = Depends(get_db)):
    if agent not in agents_map:
        return {"error": f"Agent {agent} not found"}
    market_data = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(days * 20).all()
    data = [{"close": m.close_price, "high": m.high_price, "low": m.low_price, "volume": m.volume} for m in reversed(market_data)]
    if not data:
        return {"status": "insufficient_data"}
    result = backtest_engine.run_backtest(agents_map[agent], data)
    return {
        "agent": agent,
        "backtest_period": f"last_{days}_days",
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "total_pnl": result.total_pnl,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown,
    }

@app.get("/data/market-snapshot")
async def get_market_snapshot():
    return dhan_client.get_market_snapshot()

@app.get("/optimizer/status")
async def get_optimizer_status():
    if not autonomous_optimizer:
        return {"status": "optimizer_not_initialized"}
    return autonomous_optimizer.get_status()

@app.get("/optimizer/log")
async def get_optimizer_log(limit: int = 50):
    if not autonomous_optimizer:
        return {"logs": []}
    logs = autonomous_optimizer.get_improvement_log()
    return {"logs": logs[-limit:], "total_cycles": len(logs)}

@app.get("/optimizer/progress")
async def get_optimizer_progress():
    if not autonomous_optimizer:
        return {"progress": None}

    return {
        "is_running": autonomous_optimizer.is_running,
        "cycle_count": autonomous_optimizer.cycle_count,
        "target_hit": autonomous_optimizer.target_hit,
        "target_percent": 90,
        "message": "Running 24/7 until 90%+ achieved" if not autonomous_optimizer.target_hit else "[OK] TARGET ACHIEVED!"
    }

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({
                "type": "message",
                "data": json.loads(data),
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
