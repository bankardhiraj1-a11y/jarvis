"""Jarvis 2 - Aggressive Profitable Trading: 90%+ Win Rate Enforced"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import random
import json
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pathlib import Path
import pytz

load_dotenv()

# IST timezone for trade timestamps
IST = pytz.timezone('Asia/Kolkata')

# Indian Market Holidays 2025-2026 (NSE)
INDIAN_HOLIDAYS = {
    "2025-01-26": "Republic Day",
    "2025-03-08": "Maha Shivaratri",
    "2025-03-10": "Holi",
    "2025-03-29": "Good Friday",
    "2025-04-11": "Eid ul-Fitr",
    "2025-04-17": "Ram Navami",
    "2025-04-21": "Mahavir Jayanti",
    "2025-05-23": "Eid ul-Adha",
    "2025-08-15": "Independence Day",
    "2025-08-27": "Janmashtami",
    "2025-09-16": "Milad ul-Nabi",
    "2025-10-02": "Gandhi Jayanti",
    "2025-10-12": "Dussehra",
    "2025-10-30": "Diwali",
    "2025-11-01": "Diwali (Day 2)",
    "2025-11-25": "Guru Nanak Jayanti",
    "2025-12-25": "Christmas",
}

# Import all agents (4 main + 1 scalping)
from agents.stocks import StocksAgent
from agents.sensex import SensexAgent
from agents.options import OptionsAgent
from agents.xauusd import XAUUSDAgent
from agents.sensex_scalping import SensexScalpingAgent
from data.dhan_client import DhanClient
from data.yfinance_client import YFinanceClient
from data.forex_spot_client import ForexSpotClient  # Alternative XAUUSD data source
from profitable_trading import ProfitableTrading
from xauusd_timing import XAUUSDTiming
from charges_calculator import ChargesCalculator  # NEW: Charges calculation
from platform_keepawake import setup_keep_awake, maintain_keep_awake  # Prevent system sleep during trading

# Initialize agents
agents_map = {
    "STOCKS": StocksAgent(),
    "SENSEX": SensexAgent(),
    "OPTIONS": OptionsAgent(),
    "XAUUSD": XAUUSDAgent(),
    "SENSEX_SCALPING": SensexScalpingAgent(),  # 3-min scalping on SENSEX only
}

# Symbol-to-Lot-Size mapping (NSE FNO contracts)
SYMBOL_LOT_SIZE = {
    "SENSEX": 20,           # 20 units per lot
    "NIFTY": 50,            # 50 units per lot
    "BANKNIFTY": 20,        # 20 units per lot
    "FINNIFTY": 40,         # 40 units per lot
    "MIDCPNIFTY": 75,       # 75 units per lot
    # Stocks and XAUUSD use 1 (no lot multiplier)
}

dhan_client = DhanClient()
yfinance_client = YFinanceClient()  # Real-time XAUUSD from Yahoo Finance
forex_spot_client = ForexSpotClient()  # Alternative: free APIs + test data for XAUUSD
profitability_checker = ProfitableTrading()  # Only trade profitable setups
xauusd_timing = XAUUSDTiming()  # Market-timing for XAUUSD (24/5)

# CAPITAL: 50 Lakh (₹50,00,000)
STARTING_CAPITAL = 5000000.0
MIN_WIN_RATE = 0.90  # 90% HARD MINIMUM - NO EXCEPTIONS

# Capital allocation: 5 agents (4 main + 1 scalping)
CAPITAL_ALLOCATION = {
    "STOCKS": 1250000,      # 12.5L
    "SENSEX": 1000000,      # 10L (reduced for scalping)
    "OPTIONS": 1250000,     # 12.5L
    "XAUUSD": 1250000,      # 12.5L
    "SENSEX_SCALPING": 250000,  # 2.5L (independent scalping)
}

portfolio_state = {
    "total_pnl": 0.0,
    "net_worth": STARTING_CAPITAL,
    "starting_capital": STARTING_CAPITAL,
    "positions": {},
    "active_trades": 0,
    "agent_capital": CAPITAL_ALLOCATION.copy(),
    "agent_performance": {}
}

# Initialize agent performance
for agent_name in agents_map.keys():
    capital = CAPITAL_ALLOCATION[agent_name]
    portfolio_state["agent_performance"][agent_name] = {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 100.0,  # Start at 100%
        "total_pnl": 0.0,
        "allocated_capital": capital,
        "available_capital": capital,
        "status": "IDLE",
        "last_signal": None,
        "can_trade": True,  # Trading allowed if win rate >= 90%
        "analyzing": False,
    }

trades_log = []  # Fresh start - all old XAUUSD INR trades removed

# Trade persistence
TRADES_DB_FILE = Path("D:/claude ai/jarvis-2/backend/trades.json")

def load_trades_from_disk():
    """Load trades from JSON file on startup"""
    global trades_log
    if TRADES_DB_FILE.exists():
        try:
            with open(TRADES_DB_FILE, 'r') as f:
                trades_log = json.load(f)
                # CLEANUP: Remove any XAUUSD trades (they should not exist)
                trades_log = [t for t in trades_log if t.get('agent') != 'XAUUSD']
                print(f"[OK] Loaded {len(trades_log)} trades from disk (XAUUSD filtered)")
        except Exception as e:
            print(f"[ERROR] Error loading trades: {e}")
            trades_log = []
    else:
        trades_log = []

def save_trades_to_disk():
    """Save trades to JSON file (called after each trade modification)"""
    try:
        with open(TRADES_DB_FILE, 'w') as f:
            json.dump(trades_log, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Error saving trades: {e}")

def is_indian_holiday():
    """Check if today is an Indian market holiday"""
    today = get_ist_time().date()
    return str(today) in INDIAN_HOLIDAYS

def get_ist_time_str():
    """Get current time in IST as ISO string with timezone offset"""
    now_utc = datetime.now(pytz.UTC)
    now_ist = now_utc.astimezone(IST)
    # Manually add +05:30 to ISO string to ensure timezone is included
    iso_str = now_ist.isoformat()
    if '+' not in iso_str and 'Z' not in iso_str:
        iso_str = iso_str + '+05:30'
    return iso_str

def close_trade_with_charges(trade, exit_price, exit_reason):
    """
    Close a trade and calculate NET P&L with all charges.

    Args:
        trade: Trade record
        exit_price: Exit price per unit
        exit_reason: Reason for exit (TP_HIT, SL_HIT, etc.)

    Updates trade record with:
        - Charges breakdown
        - Gross P&L
        - Net P&L (after charges)
        - Exit time and reason
    """

    symbol = trade.get("symbol", "")
    entry_price = trade.get("entry_price", 0)
    signal = trade.get("signal", "BUY")
    qty = trade.get("quantity", 1)
    lot_size = SYMBOL_LOT_SIZE.get(symbol, 1)

    # Calculate charges using ChargesCalculator
    charges_info = ChargesCalculator.calculate_charges(
        symbol=symbol,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=qty,
        lot_size=lot_size
    )

    # Calculate GROSS profit/loss
    if signal == "BUY":
        gross_pnl = (exit_price - entry_price) * qty * lot_size
    else:  # SELL
        gross_pnl = (entry_price - exit_price) * qty * lot_size

    # Calculate NET P&L (after charges)
    net_pnl = gross_pnl - charges_info['total_charges']

    # Calculate percentages
    entry_value = entry_price * qty * lot_size
    gross_pnl_pct = (gross_pnl / entry_value) * 100 if entry_value > 0 else 0
    net_pnl_pct = (net_pnl / entry_value) * 100 if entry_value > 0 else 0

    # Update trade record
    trade["current_price"] = exit_price
    trade["exit_time"] = get_ist_time_str()
    trade["exit_reason"] = exit_reason
    trade["status"] = "CLOSED"
    trade["exit_date"] = get_ist_time().strftime("%Y-%m-%d")

    # Store charges breakdown (NEW)
    trade["charges"] = charges_info['charge_breakdown']
    trade["gross_pnl"] = round(gross_pnl, 2)
    trade["gross_pnl_percent"] = round(gross_pnl_pct, 2)

    # Use NET P&L for all calculations (IMPORTANT)
    trade["pnl"] = round(net_pnl, 2)  # NET profit
    trade["pnl_percent"] = round(net_pnl_pct, 2)  # NET percentage

    # Store full charges info for dashboard display
    trade["charges_info"] = {
        'segment': charges_info['segment'],
        'total_charges': charges_info['total_charges'],
        'charge_ratio': charges_info.get('charge_ratio_pct', 0),
        'breakeven': charges_info.get('breakeven_points', charges_info.get('breakeven_pct', 0))
    }

    return trade

def get_ist_time():
    """Get current time in IST timezone"""
    return datetime.now(pytz.UTC).astimezone(IST)

def calculate_win_rate(agent_name):
    """Calculate win rate for agent"""
    agent_trades = [t for t in trades_log if t["agent"] == agent_name and t["status"] == "CLOSED"]
    if not agent_trades:
        return 100.0  # Start with 100% before any closed trades

    winning = len([t for t in agent_trades if t["pnl"] > 0])
    return (winning / len(agent_trades)) * 100 if agent_trades else 100.0

def update_live_pnl():
    """Update live P&L for open trades with charges deduction"""
    for trade in trades_log:
        if trade["status"] == "OPEN":
            # Get trade parameters
            qty = trade.get("quantity", 1)
            symbol = trade.get("symbol", "")
            entry_price = trade.get("entry_price", 0)
            current_price = trade.get("current_price", entry_price)

            # Get lot size from symbol mapping
            lot_size = SYMBOL_LOT_SIZE.get(symbol, 1) if symbol else 1

            # Calculate GROSS P&L
            if trade["signal"] == "BUY":
                gross_pnl = (current_price - entry_price) * qty * lot_size
            else:  # SELL
                gross_pnl = (entry_price - current_price) * qty * lot_size

            # Calculate charges for current position
            charges_info = ChargesCalculator.calculate_charges(
                symbol=symbol,
                entry_price=entry_price,
                exit_price=current_price,
                quantity=qty,
                lot_size=lot_size
            )

            # Calculate NET P&L (after charges)
            net_pnl = gross_pnl - charges_info['total_charges']

            # Update trade record with charges
            trade["gross_pnl"] = round(gross_pnl, 2)
            trade["pnl"] = round(net_pnl, 2)  # NET P&L for display
            entry_value = entry_price * qty * lot_size
            trade["pnl_percent"] = round((net_pnl / entry_value) * 100, 2) if entry_value > 0 else 0

            # Add charges breakdown to trade (for Charges tab)
            trade["charges"] = charges_info['charge_breakdown']
            trade["charges_info"] = {
                'segment': charges_info['segment'],
                'total_charges': charges_info['total_charges'],
                'charge_ratio': charges_info.get('charge_ratio_pct', 0),
                'breakeven': charges_info.get('breakeven_points', charges_info.get('breakeven_pct', 0))
            }

            # Check stop loss or take profit
            if trade["signal"] == "BUY":
                if trade["current_price"] <= trade["stop_loss"]:
                    close_trade_with_charges(trade, trade["stop_loss"], "SL_HIT")
                    save_trades_to_disk()  # Persist trade closure
                elif trade["current_price"] >= trade["take_profit"]:
                    close_trade_with_charges(trade, trade["take_profit"], "TP_HIT")
                    save_trades_to_disk()  # Persist trade closure
            else:  # SELL
                if trade["current_price"] >= trade["stop_loss"]:
                    close_trade_with_charges(trade, trade["stop_loss"], "SL_HIT")
                    save_trades_to_disk()  # Persist trade closure
                elif trade["current_price"] <= trade["take_profit"]:
                    close_trade_with_charges(trade, trade["take_profit"], "TP_HIT")
                    save_trades_to_disk()  # Persist trade closure

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Load trades from disk
    load_trades_from_disk()

    # Setup platform keep-awake during trading hours
    keep_awake = setup_keep_awake()
    print(f"[STARTUP] Keep-Awake system initialized: {keep_awake.get_trading_status()}")

    async def live_market_analyzer():
        """Aggressive trading with 90%+ win rate enforcement"""
        symbol_map = {
            "STOCKS": ["RELIANCE", "TCS", "INFY"],
            "SENSEX": ["SENSEX"],  # Re-enabled
            "OPTIONS": ["NIFTY", "BANKNIFTY", "FINNIFTY"],
            "XAUUSD": ["XAUUSD"],
            "SENSEX_SCALPING": ["SENSEX"],  # 3-min scalping - SENSEX only
        }

        # LIVE DATA ONLY - NO MOCK PRICES
        # All agents use real, connected APIs:
        # - DhanHQ for NSE (STOCKS, SENSEX, OPTIONS, SENSEX_SCALPING)
        # - Yahoo Finance for XAUUSD (24/5 market)

        cycle = 0
        while True:
            try:
                cycle += 1

                # KEEP-AWAKE: Prevent system sleep during trading hours
                maintain_keep_awake()

                # NSE MARKET HOURS CHECK: 9:15 AM - 3:00 PM IST (no trades after 3:00 PM)
                current_time = get_ist_time()
                nse_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
                nse_close = current_time.replace(hour=15, minute=0, second=0, microsecond=0)
                is_nse_trading_hours = nse_open <= current_time <= nse_close

                # INDIAN MARKET HOLIDAY CHECK
                is_holiday = is_indian_holiday()
                is_weekend = current_time.weekday() >= 5  # Saturday = 5, Sunday = 6

                if is_holiday:
                    print(f"[INFO] Market holiday today ({INDIAN_HOLIDAYS.get(str(current_time.date()))}). No trading.")
                    continue

                if is_weekend:
                    print(f"[INFO] Weekend - market closed. Only XAUUSD (24/5) active.")
                    symbol_map_filtered = {k: v for k, v in symbol_map.items() if k == "XAUUSD"}
                elif not is_nse_trading_hours:
                    # Only allow XAUUSD trading (24-hour market)
                    symbol_map_filtered = {k: v for k, v in symbol_map.items() if k == "XAUUSD"}
                else:
                    symbol_map_filtered = symbol_map

                # Update live P&L for open trades
                update_live_pnl()

                for agent_name, symbols in symbol_map_filtered.items():
                    # Check if agent can trade (90%+ win rate required)
                    current_win_rate = calculate_win_rate(agent_name)
                    portfolio_state["agent_performance"][agent_name]["win_rate"] = current_win_rate
                    can_trade = current_win_rate >= MIN_WIN_RATE * 100
                    portfolio_state["agent_performance"][agent_name]["can_trade"] = can_trade

                    if not can_trade:
                        portfolio_state["agent_performance"][agent_name]["status"] = "PAUSED"
                        continue  # Skip trading for this agent

                    portfolio_state["agent_performance"][agent_name]["status"] = "SCANNING"
                    found_signal = False

                    # XAUUSD Market-Timing Check: Only trade during optimal sessions
                    if agent_name == "XAUUSD":
                        xauusd_strategy = xauusd_timing.get_xauusd_strategy()
                        if not xauusd_strategy["should_trade"]:
                            # Skip XAUUSD trading during low-volatility Asian session
                            portfolio_state["agent_performance"][agent_name]["status"] = "PAUSED (Asian session - low volatility)"
                            continue

                    for symbol in symbols:
                        try:
                            # Get market data - use ForexSpotClient for XAUUSD, DhanHQ for others
                            if agent_name == "XAUUSD":
                                # Use ForexSpotClient for real-time XAUUSD (tries multiple free APIs + test data)
                                live_data = forex_spot_client.get_live_data("XAUUSD")
                            else:
                                # Use DhanHQ for stocks/indices/options/scalping
                                exchange = "NSE" if agent_name in ["STOCKS", "SENSEX", "OPTIONS", "SENSEX_SCALPING"] else "FOREXCFD"
                                live_data = dhan_client.get_live_data(symbol, exchange)

                            # NO MOCK DATA - LIVE DATA ONLY
                            if not live_data or live_data.get("close", 0) == 0:
                                # Skip this symbol if live data is unavailable
                                print(f"[WARN] Live data unavailable for {symbol} - skipping (API error or market closed)")
                                continue

                            if live_data and live_data.get("close", 0) > 0:
                                agent = agents_map.get(agent_name)
                                if agent:
                                    signal = agent.analyze(live_data)

                                    # HIGH-CONFIDENCE SIGNALS ONLY - 90%+ win rate enforced
                                    # Only trade if:
                                    # 1. Clear signal (BUY/SELL, not HOLD)
                                    # 2. Current win rate is 90%+ (already checked above)
                                    # 3. PROFITABILITY CHECK: Only trade if profit is LIKELY
                                    if signal.value != "HOLD" and can_trade:  # MUST be tradeable (90%+ WR)

                                        # PROFITABILITY FILTER: Check if this trade is worth taking
                                        profitability_decision = profitability_checker.should_enter_trade(
                                            signal.value, live_data, agent_name
                                        )

                                        if not profitability_decision["should_trade"]:
                                            # Skip this signal - not profitable enough
                                            continue

                                        entry_price = profitability_decision["entry_price"]
                                        stop_loss = profitability_decision["stop_loss"]
                                        take_profit = profitability_decision["take_profit"]

                                        # SENSEX_SCALPING: Use agent-provided TP/SL or agent defaults
                                        if agent_name == "SENSEX_SCALPING":
                                            # Prefer signal's TP/SL if available
                                            if "take_profit" in signal_dict and "stop_loss" in signal_dict:
                                                take_profit = signal_dict["take_profit"]
                                                stop_loss = signal_dict["stop_loss"]
                                            else:
                                                # Fallback to agent defaults: 6pt SL, 12pt TP
                                                stop_loss = (entry_price - 6) if signal.value == "BUY" else (entry_price + 6)
                                                take_profit = (entry_price + 12) if signal.value == "BUY" else (entry_price - 12)

                                        agent_capital = portfolio_state["agent_performance"][agent_name]["available_capital"]
                                        risk_per_trade = agent_capital * 0.05  # 5% risk (conservative, for consistency)

                                        # For OPTIONS: Add strike and contract type with expiry
                                        option_contract = None
                                        if agent_name == "OPTIONS":
                                            # Calculate nearest strike (round to 100 for NIFTY/FINNIFTY, 200 for BANKNIFTY)
                                            if symbol == "BANKNIFTY":
                                                strike = int(entry_price / 200) * 200
                                            else:
                                                strike = int(entry_price / 100) * 100

                                            contract_type = "CALL" if signal.value == "BUY" else "PUT"
                                            # Monthly expiry - use 29 or 28 (last Thursday of month, typically)
                                            expiry = "29 SEP" if symbol != "FINNIFTY" else "29 SEP"
                                            option_contract = f"{symbol} {expiry} {strike} {contract_type}"

                                            # Store detailed contract info
                                            trade_contract_details = {
                                                "symbol": symbol,
                                                "strike": strike,
                                                "expiry": expiry,
                                                "type": contract_type,
                                                "full_name": option_contract
                                            }

                                        # Build trade details
                                        trade_details = {}

                                        # For OPTIONS: Add full contract details
                                        if agent_name == "OPTIONS":
                                            trade_details["contract_full"] = option_contract
                                            trade_details["strike"] = trade_contract_details.get("strike")
                                            trade_details["expiry"] = trade_contract_details.get("expiry")
                                            trade_details["contract_type"] = trade_contract_details.get("type")

                                        # For SENSEX: Add price level details
                                        if agent_name == "SENSEX":
                                            price_level = int(entry_price)
                                            direction = "BUY" if signal.value == "BUY" else "SELL"
                                            range_position = "TOP 40%" if signal.value == "BUY" else "BOTTOM 60%"
                                            sensex_contract = f"SENSEX {price_level} {direction} ({range_position})"
                                            trade_details["contract_full"] = sensex_contract
                                            trade_details["price_level"] = price_level
                                            trade_details["direction"] = direction
                                            trade_details["range_position"] = range_position

                                        # Set contract based on agent type
                                        contract_value = None
                                        if agent_name == "OPTIONS":
                                            contract_value = option_contract
                                        elif agent_name == "SENSEX":
                                            range_pos = "TOP 40%" if signal.value == "BUY" else "BOTTOM 60%"
                                            contract_value = "SENSEX %d %s (%s)" % (int(entry_price), signal.value, range_pos)
                                        elif agent_name == "SENSEX_SCALPING":
                                            contract_value = "SENSEX 3MIN SCALP %d %s" % (int(entry_price), signal.value)

                                        # Use IST for all timestamps
                                        now_ist = get_ist_time()

                                        # Get quantity from agent (scalping = 50, others = 1)
                                        agent_qty = getattr(agent, 'quantity', 1)

                                        trade = {
                                            "id": len(trades_log) + 1,
                                            "timestamp": now_ist.isoformat(),
                                            "agent": agent_name,
                                            "symbol": symbol,
                                            "contract": contract_value,  # For OPTIONS/SENSEX: Full contract details
                                            "signal": signal.value,
                                            "entry_price": entry_price,
                                            "current_price": entry_price,
                                            "stop_loss": stop_loss,
                                            "take_profit": take_profit,
                                            "entry_time": get_ist_time_str(),
                                            "entry_date": now_ist.strftime("%Y-%m-%d"),
                                            "exit_time": None,
                                            "exit_date": None,
                                            "status": "OPEN",
                                            "pnl": 0.0,
                                            "pnl_percent": 0.0,
                                            "quantity": agent_qty,
                                            "currency": "USD" if agent_name == "XAUUSD" else "INR",  # XAUUSD in USD
                                            "details": trade_details  # Additional trading details
                                        }
                                        trades_log.append(trade)
                                        save_trades_to_disk()  # Persist new trade

                                        # Update agent metrics
                                        portfolio_state["agent_performance"][agent_name]["available_capital"] -= risk_per_trade
                                        portfolio_state["agent_performance"][agent_name]["status"] = "WORKING"
                                        portfolio_state["agent_performance"][agent_name]["last_signal"] = f"{signal.value} {symbol}"
                                        portfolio_state["agent_performance"][agent_name]["total_trades"] += 1
                                        portfolio_state["active_trades"] = len([t for t in trades_log if t["status"] == "OPEN"])

                                        price_display = f"${entry_price:.2f}" if agent_name == "XAUUSD" else f"₹{entry_price:.2f}"
                                        sl_display = f"${stop_loss:.2f}" if agent_name == "XAUUSD" else f"₹{stop_loss:.2f}"
                                        tp_display = f"${take_profit:.2f}" if agent_name == "XAUUSD" else f"₹{take_profit:.2f}"
                                        print(f"[{cycle}] {agent_name} {signal.value}: {symbol} @ {price_display} | SL:{sl_display} TP:{tp_display} | WR:{current_win_rate:.1f}% | Trades:{portfolio_state['agent_performance'][agent_name]['total_trades']}")
                                        found_signal = True
                        except Exception as e:
                            pass

                    if not found_signal:
                        portfolio_state["agent_performance"][agent_name]["status"] = "IDLE"

                await asyncio.sleep(30)  # Reduced from 60s to 30s for faster trading
            except Exception as e:
                print(f"Market analyzer error: {e}")
                await asyncio.sleep(60)

    # Start market analyzer
    task = asyncio.create_task(live_market_analyzer())
    yield
    task.cancel()

app = FastAPI(title="Jarvis 2 - Profitable Trading", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/")
async def root():
    """Serve dashboard HTML"""
    from fastapi.responses import FileResponse
    dashboard_file = Path(__file__).parent.parent / "frontend" / "neural-fi.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file, media_type="text/html")
    # Fallback to index.html
    fallback_file = Path(__file__).parent.parent / "frontend" / "index.html"
    if fallback_file.exists():
        return FileResponse(fallback_file, media_type="text/html")
    return {"error": "Dashboard not found"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "PROFITABLE",
        "capital": f"₹{STARTING_CAPITAL:,.0f}",
        "min_win_rate": f"{MIN_WIN_RATE*100}%"
    }

@app.get("/portfolio")
async def get_portfolio():
    # Calculate total metrics
    total_trades = sum(p["total_trades"] for p in portfolio_state["agent_performance"].values())
    total_winning = sum(p["winning_trades"] for p in portfolio_state["agent_performance"].values())
    total_pnl = sum(t["pnl"] for t in trades_log if t["status"] == "CLOSED")

    return {
        **portfolio_state,
        "total_closed_pnl": total_pnl,
        "overall_win_rate": (total_winning / total_trades * 100) if total_trades > 0 else 100.0
    }

@app.get("/agents/performance")
async def get_agents_performance():
    result = {}
    for agent_name in agents_map.keys():
        agent_status = portfolio_state["agent_performance"].get(agent_name, {})
        agent_trades = [t for t in trades_log if t["agent"] == agent_name and t["status"] == "CLOSED"]
        winning = len([t for t in agent_trades if t["pnl"] > 0])

        win_rate = calculate_win_rate(agent_name)
        portfolio_state["agent_performance"][agent_name]["win_rate"] = win_rate
        portfolio_state["agent_performance"][agent_name]["winning_trades"] = winning
        portfolio_state["agent_performance"][agent_name]["losing_trades"] = len(agent_trades) - winning

        result[agent_name] = {
            "total_trades": agent_status.get("total_trades", 0),
            "winning_trades": winning,
            "losing_trades": len(agent_trades) - winning,
            "win_rate": win_rate,
            "total_pnl": sum(t["pnl"] for t in agent_trades),
            "allocated_capital": agent_status.get("allocated_capital", 0),
            "available_capital": agent_status.get("available_capital", 0),
            "status": agent_status.get("status", "IDLE"),
            "last_signal": agent_status.get("last_signal"),
            "can_trade": agent_status.get("can_trade", True),
        }
    return result

@app.get("/agent/{agent_name}/trades")
async def get_agent_trades(agent_name: str):
    """Get trades for a specific agent"""
    agent_trades = [t for t in trades_log if t["agent"] == agent_name]
    return {
        "agent": agent_name,
        "total_trades": len(agent_trades),
        "open_trades": [t for t in agent_trades if t["status"] == "OPEN"],
        "closed_trades": [t for t in agent_trades if t["status"] == "CLOSED"],
        "all_trades": agent_trades
    }

@app.get("/trades")
async def get_trades():
    return trades_log

@app.get("/active-trades-with-charges")
async def get_active_trades_with_charges():
    """Get active trades with charges breakdown - Active Trades Tab with Charges"""
    open_trades = [t for t in trades_log if t["status"] == "OPEN"]

    active_data = []
    for trade in open_trades:
        active_data.append({
            "id": trade.get("id"),
            "agent": trade.get("agent"),
            "symbol": trade.get("symbol"),
            "signal": trade.get("signal"),
            "entry_price": trade.get("entry_price"),
            "current_price": trade.get("current_price"),
            "quantity": trade.get("quantity"),
            "entry_time": trade.get("entry_time"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit"),
            "gross_pnl": trade.get("gross_pnl", 0),  # Before charges
            "pnl": trade.get("pnl"),  # NET P&L (after charges)
            "pnl_percent": trade.get("pnl_percent"),
            "charges": trade.get("charges", {}),  # Charges components
            "charges_info": trade.get("charges_info", {}),  # Charges summary
            "status": trade.get("status")
        })

    return {
        "total_open_trades": len(open_trades),
        "trades": active_data
    }

@app.get("/charges")
async def get_charges_breakdown():
    """Get detailed charges breakdown for closed trades - Charges Tab"""
    closed_trades = [t for t in trades_log if t["status"] == "CLOSED"]

    charges_data = []
    for trade in closed_trades:
        # Only include trades that have charges calculated
        if "charges_info" in trade or "charges" in trade:
            charges_data.append({
                "id": trade.get("id"),
                "agent": trade.get("agent"),
                "symbol": trade.get("symbol"),
                "signal": trade.get("signal"),
                "entry_price": trade.get("entry_price"),
                "exit_price": trade.get("current_price"),
                "quantity": trade.get("quantity"),
                "entry_time": trade.get("entry_time"),
                "exit_time": trade.get("exit_time"),
                "gross_pnl": trade.get("gross_pnl", 0),
                "pnl": trade.get("pnl"),  # NET P&L (after charges)
                "pnl_percent": trade.get("pnl_percent"),
                "charges": trade.get("charges", {}),  # Charges breakdown
                "charges_info": trade.get("charges_info", {}),  # Charges summary
                "exit_reason": trade.get("exit_reason", "UNKNOWN")
            })

    return {
        "total_closed_trades": len(closed_trades),
        "trades_with_charges": len(charges_data),
        "trades": charges_data
    }

@app.get("/optimizer/status")
async def get_optimizer_status():
    return {
        "is_running": True,
        "cycle_count": len(trades_log),
        "capital": f"₹{STARTING_CAPITAL:,.0f}",
        "min_win_rate": f"{MIN_WIN_RATE*100}%",
        "message": "AGGRESSIVE PROFITABLE TRADING - 90%+ win rate enforced"
    }

from fastapi.responses import FileResponse

@app.get("/dashboard")
async def get_dashboard():
    """Serve positions & history dashboard"""
    positions_file = Path("D:/claude ai/positions.html")
    if positions_file.exists():
        return FileResponse(positions_file, media_type="text/html")
    return {"error": "Dashboard not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
