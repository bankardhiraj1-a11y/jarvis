from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import asyncio
from datetime import datetime, time, timezone
from pathlib import Path
import logging
import sys
import pytz
from dotenv import load_dotenv

load_dotenv()  # Provider credentials are read only from environment variables.

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# OANDA URLs contain private account identifiers. Do not log HTTP request paths.
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
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
from backtest.live_capture import LiveObservationRecorder
from data.dhan_live_client import DhanLiveClient
from data.onda_client import OndaClient
from scheduler.autonomous_optimizer import AutonomousOptimizer
from trading.live_paper import (
    build_long_option_paper_entry,
    ensure_trade_provenance_columns,
    is_verified_closed_trade,
    option_entry_and_exit_prices,
    parse_option_contract,
    provider_side_price,
    quote_has_timestamp,
    quote_is_fresh,
    verified_closed_trade_metrics,
)

settings = get_settings()
Base.metadata.create_all(bind=engine)
ensure_trade_provenance_columns(engine)

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
evidence_dir = Path(__file__).resolve().parents[1] / "evidence"
live_observation_recorder = LiveObservationRecorder(evidence_dir / "live_observations.sqlite")
xau_observation_recorder = LiveObservationRecorder(
    evidence_dir / "xauusd_observations.sqlite", source="OANDA"
)

# WebSocket subscriptions for live market feed
# Build instrument list for subscription
# Symbol to DhanHQ security ID mapping (NSE market data, Dhan Symbol Master)
SYMBOL_TO_ID = {
    "RELIANCE": 2885,
    "TCS": 11536,
    "INFY": 1594,
    "HDFCBANK": 1333,
    "BAJAJ-AUTO": 16669,
    "SENSEX": 51,        # Index
    "NIFTY": 13,         # Index
    "BANKNIFTY": 25,     # Index
}

# Estimated Indian-market paper fee schedule; not a broker statement.
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
}

def calculate_net_pnl(entry_price, exit_price, quantity, trade_type, symbol):
    """Paper P&L with modeled Indian fees and executable OANDA side fills."""
    # Raw P&L
    if trade_type == "BUY":
        raw_pnl = (exit_price - entry_price) * quantity
    else:  # SELL
        raw_pnl = (entry_price - exit_price) * quantity

    if symbol == "XAUUSD":
        # Executable OANDA bid/ask fills already include the quoted spread.
        # Do not add an unverified commission assumption or count spread twice.
        return raw_pnl

    # SENSEX_OPTIONS_SCALPING: Use minimal charges (premium-based, not index-based)
    # Options have different charge structure - for now use minimal charges
    if "SENSEX" in str(symbol) and quantity > 100:  # Options scalping (1000 units)
        # Options trading: minimal charges (~₹50-100 per trade for scalp)
        total_charges = 100  # Flat ₹100 for now
        return raw_pnl - total_charges

    # Determine charge structure based on symbol
    if symbol in ["SENSEX", "BANKNIFTY", "NIFTY"]:
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
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "2885", "Symbol": "RELIANCE"},
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "11536", "Symbol": "TCS"},
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1594", "Symbol": "INFY"},
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1333", "Symbol": "HDFCBANK"},
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "16669", "Symbol": "BAJAJ-AUTO"},
    {"ExchangeSegment": "IDX_I", "SecurityId": "51", "Symbol": "SENSEX"},
    {"ExchangeSegment": "IDX_I", "SecurityId": "13", "Symbol": "NIFTY"},
    {"ExchangeSegment": "IDX_I", "SecurityId": "25", "Symbol": "BANKNIFTY"},
]
boss_agent = None
agent_team = None
autonomous_optimizer = None

portfolio_state = {
    "total_pnl": 0.0,
    "net_worth": settings.INITIAL_CAPITAL,
    "positions": {},
    "active_trades": 0,
    "agent_performance": {}
}

_OPTION_UNDERLYINGS = {
    "SENSEX": 51,
    "BANKNIFTY": 25,
    "NIFTY": 13,
}
_VOLUME_STATE = {}
_AGENT_RUNTIME_STATUS = {
    "STOCKS": {"status": "WAITING_FOR_DATA", "reason": "Waiting for fresh Dhan quotes"},
    "SENSEX": {
        "status": "DISABLED",
        "reason": "Legacy SENSEX multi-leg spread/condor has no supported multi-leg paper execution",
    },
    "OPTIONS": {"status": "WAITING_FOR_DATA", "reason": "Waiting for fresh Dhan quotes and option-chain data"},
    "XAUUSD": {"status": "WAITING_FOR_DATA", "reason": "OANDA pricing collection only; paper entries require validated backtests"},
    "SENSEX_OPTIONS_SCALPING": {
        "status": "WAITING_FOR_DATA",
        "reason": "Waiting for fresh SENSEX index and option-chain data",
    },
}
_AGENT_SYMBOLS = {
    "STOCKS": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "BAJAJ-AUTO"],
    "OPTIONS": ["NIFTY", "BANKNIFTY"],
    "SENSEX_OPTIONS_SCALPING": ["SENSEX"],
}


def _safe_provider_status(status):
    """Expose operational status only; never serialize credentials or arbitrary objects."""
    if not isinstance(status, dict):
        return {"connected": False, "status": "unavailable"}
    allowed = {
        "connected",
        "status",
        "last_error",
        "last_update",
        "last_success_at",
        "age_seconds",
        "stale",
        "symbol",
        "source",
        "environment",
        "configured",
    }
    safe = {
        key: status[key]
        for key in allowed
        if key in status
        and status[key] is not None
        and isinstance(status[key], (str, int, float, bool))
    }
    safe.setdefault("status", "unavailable")
    safe.setdefault("connected", False)
    return safe


def _market_hours_open(agent_name):
    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    utc_now = datetime.now(pytz.UTC)
    if agent_name == "XAUUSD":
        return time(16, 0) <= utc_now.time() < time(23, 0)
    return (
        ist_now.weekday() < 5
        and time(9, 15) <= ist_now.time() <= time(15, 30)
    )


def _fresh_indian_quote(symbol):
    security_id = SYMBOL_TO_ID.get(symbol)
    if not security_id:
        return None
    segment = "NSE_EQ" if symbol in {"RELIANCE", "TCS", "INFY", "HDFCBANK", "BAJAJ-AUTO"} else "IDX_I"
    quote = dhan_client.get_live_data(security_id, symbol, segment)
    if not quote_is_fresh(quote) or not quote_has_timestamp(quote):
        return None
    return quote


def _cached_trade_mark(trade):
    """Read only cached provider prices; never make an HTTP request from a GET route."""
    source = str(getattr(trade, "data_source", "") or "").upper()
    if source == "DHAN":
        contract = parse_option_contract(getattr(trade, "option_strike", None))
        if contract:
            quote = dhan_client.get_option_quote(trade.symbol, **contract)
            prices = option_entry_and_exit_prices(quote)
            return (prices[1], quote) if prices else (None, None)
        quote = _fresh_indian_quote(trade.symbol)
        exit_side = "SELL" if trade.trade_type.value == "BUY" else "BUY"
        return (provider_side_price(quote, exit_side), quote) if quote else (None, None)
    if source == "OANDA":
        cached = getattr(onda_client, "latest_prices", {}).get(trade.symbol)
        if isinstance(cached, dict) and quote_is_fresh(cached):
            exit_side = "SELL" if trade.trade_type.value == "BUY" else "BUY"
            return provider_side_price(cached, exit_side), cached
    return None, None


def _monitor_open_trade(db, trade, agent_name):
    if not _market_hours_open(agent_name):
        return ("MARKET_CLOSED", "No paper fills outside the configured market session")
    if not trade.data_source or not trade.entry_data_timestamp:
        return (
            "UNVERIFIED_LEGACY_TRADE",
            "Existing trade lacks live-data provenance; it is preserved and not repriced",
        )
    current_price, current_quote = _cached_trade_mark(trade)
    if (
        current_price is None
        or not quote_is_fresh(current_quote)
        or not quote_has_timestamp(current_quote)
    ):
        return (
            "WAITING_FOR_DATA",
            "Fresh cached quote for the open position is unavailable",
        )

    now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
    created_at = trade.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    opened_on_previous_session = (
        created_at.astimezone(pytz.timezone("Asia/Kolkata")).date()
        < now_ist.date()
    )
    hard_exit_due = (
        (
            agent_name == "OPTIONS"
            and (
                opened_on_previous_session
                or (now_ist.hour, now_ist.minute) >= (15, 15)
            )
        )
        or (
            agent_name == "SENSEX_OPTIONS_SCALPING"
            and (
                opened_on_previous_session
                or (now_ist.hour, now_ist.minute) >= (15, 25)
            )
        )
    )
    if trade.trade_type.value == "BUY":
        should_close = (
            (trade.take_profit and current_price >= trade.take_profit)
            or (trade.stop_loss and current_price <= trade.stop_loss)
        )
    else:
        should_close = (
            (trade.take_profit and current_price <= trade.take_profit)
            or (trade.stop_loss and current_price >= trade.stop_loss)
        )
    should_close = bool(should_close or hard_exit_due)

    if not should_close:
        return (
            "PAPER_POSITION_OPEN",
            "Monitoring the exact live-provider instrument price",
        )

    trade.exit_price = current_price
    trade.pnl = calculate_net_pnl(
        trade.entry_price,
        current_price,
        trade.quantity,
        trade.trade_type.value,
        trade.symbol,
    )
    trade.status = "CLOSED"
    trade.closed_at = datetime.utcnow()
    trade.exit_data_timestamp = (
        current_quote.get("timestamp")
        if isinstance(current_quote.get("timestamp"), str)
        else None
    )
    db.commit()
    if agent_name == "OPTIONS":
        agents_map[agent_name].close_paper_position(trade.symbol)
    return (
        "TRADE_CLOSED",
        "Closed at fresh cached provider price"
        + (" at the strategy's intraday cutoff" if hard_exit_due else " after a risk threshold"),
    )


def _volume_delta(symbol, quote):
    """Convert Dhan's cumulative day volume into a per-poll interval delta."""
    raw_volume = quote.get("volume")
    if raw_volume is None:
        return 0
    try:
        current = max(0.0, float(raw_volume))
    except (TypeError, ValueError, OverflowError):
        return 0
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date().isoformat()
    previous = _VOLUME_STATE.get(symbol)
    if not previous or previous[0] != today or current < previous[1]:
        delta = current
    else:
        delta = current - previous[1]
    _VOLUME_STATE[symbol] = (today, current)
    return delta


def _agent_history_status(agent_name, symbol):
    agent = agents_map.get(agent_name)
    status_fn = getattr(agent, "get_history_status", None)
    if callable(status_fn):
        try:
            return status_fn(symbol)
        except Exception:
            return {"status": "WARMING_UP", "reason": "Strategy history status unavailable"}
    return {"status": "READY", "reason": "Strategy ready"}


def _option_quote_is_usable(quote):
    return option_entry_and_exit_prices(quote) is not None


def _provider_status():
    dhan_snapshot = {}
    try:
        dhan_snapshot = dhan_client.get_market_snapshot()
    except Exception:
        dhan_snapshot = {}
    dhan_status = _safe_provider_status({
        "source": dhan_snapshot.get("source"),
        "status": dhan_snapshot.get("status"),
        "connected": dhan_snapshot.get("connected"),
        "last_error": dhan_snapshot.get("last_error"),
    })

    oanda_status = {}
    try:
        oanda_status = _safe_provider_status(onda_client.get_status())
    except Exception:
        oanda_status = {"connected": False, "status": "unavailable"}
    return dhan_status, oanda_status

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
                "confidence": 0.0,
                "status": "IDLE",
                "analyzing": False,
            }
        print("[OK] All agents initialized", flush=True)

        print("[INFO] Dhan read-only REST feed will refresh asynchronously.", flush=True)
    except Exception as e:
        print(f"[ERROR] Agent init failed: {e}", flush=True)

    # Initialize boss agent and team (optional - don't block startup)
    try:
        boss_agent = BossAgent(agents_map)
        agent_team = AgentTeam(agents_map)
        logger.info("[OK] Boss agent and team ready")
    except Exception as e:
        logger.warning(f"[WARN] Boss/Team init skipped: {e}")

    async def option_chain_refresher():
        """Refresh real option chains sequentially; the client enforces Dhan limits."""
        while True:
            requests = {(symbol, None) for symbol in _OPTION_UNDERLYINGS}
            contracts = {}
            # Persisted contracts must not lose their feed when nearest expiry changes.
            with SessionLocal() as chain_db:
                for trade in chain_db.query(Trade).filter(Trade.status == "OPEN").all():
                    contract = parse_option_contract(trade.option_strike)
                    if contract and trade.symbol in _OPTION_UNDERLYINGS:
                        requests.add((trade.symbol, contract["expiry"]))
                        contracts.setdefault(trade.symbol, []).append(contract)
            for symbol, expiry in sorted(requests, key=lambda item: (item[0], item[1] or "")):
                security_id = _OPTION_UNDERLYINGS[symbol]
                try:
                    result = await asyncio.to_thread(
                        dhan_client.refresh_option_chain,
                        symbol,
                        security_id,
                        "IDX_I",
                        expiry=expiry,
                    )
                    if result is False or result is None:
                        await asyncio.sleep(1)
                        continue
                    # All option HTTP calls belong here, never in dashboard GETs.
                    for contract in contracts.get(symbol, []):
                        if contract["expiry"] == result.get("expiry"):
                            await asyncio.to_thread(
                                dhan_client.refresh_option_quote, symbol, **contract
                            )
                    if expiry is None:
                        option_snapshots = []
                        for direction in ("BUY", "SELL"):
                            identity = dhan_client.select_atm_option(symbol, direction)
                            if not identity:
                                continue
                            option_quote = await asyncio.to_thread(
                                dhan_client.refresh_option_quote,
                                symbol,
                                strike=identity["strike"],
                                option_type=identity["option_type"],
                                expiry=identity["expiry"],
                            )
                            if option_quote:
                                option_snapshots.append({**option_quote, "source": "DHAN"})
                        await asyncio.to_thread(
                            live_observation_recorder.record, option_snapshots
                        )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning("Dhan option-chain refresh failed for %s", symbol)
                    await asyncio.sleep(1)

    async def live_market_feeder():
        """Refresh provider data once per cycle and paper-trade only fresh quotes."""
        while True:
            db = SessionLocal()
            try:
                dhan_refresh_ok = await asyncio.to_thread(
                    dhan_client.refresh_quotes, _instruments_to_subscribe
                )
                # Pricing collection only: XAU is not in the paper-entry routing.
                xau_quote = await asyncio.to_thread(onda_client.get_live_data, "XAUUSD", "XAUUSD")

                indian_quotes = {}
                recorded_quotes = []
                if dhan_refresh_ok:
                    for symbol in SYMBOL_TO_ID:
                        quote = _fresh_indian_quote(symbol)
                        if quote:
                            quote = dict(quote)
                            quote["symbol"] = symbol
                            quote["source"] = "DHAN"
                            recorded_quotes.append(dict(quote))
                            quote["volume"] = _volume_delta(symbol, quote)
                            indian_quotes[symbol] = quote
                await asyncio.to_thread(live_observation_recorder.record, recorded_quotes)

                if isinstance(xau_quote, dict):
                    xau_quote = dict(xau_quote)
                    xau_quote["symbol"] = "XAUUSD"
                else:
                    xau_quote = None
                xau_fresh = quote_is_fresh(xau_quote) and quote_has_timestamp(xau_quote)
                _AGENT_RUNTIME_STATUS["XAUUSD"] = {
                    "status": "DATA_ONLY" if xau_fresh else "WAITING_FOR_DATA",
                    "reason": (
                        "Fresh OANDA pricing collected; no validated XAUUSD backtest or paper entries"
                        if xau_fresh else "OANDA pricing is unavailable or stale; no prices or fills invented"
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                await asyncio.to_thread(
                    xau_observation_recorder.record, [xau_quote] if xau_fresh else []
                )

                for agent_name, symbols in _AGENT_SYMBOLS.items():
                    agent = agents_map[agent_name]
                    symbol_statuses = []
                    for symbol in symbols:
                        live_data = xau_quote if agent_name == "XAUUSD" else indian_quotes.get(symbol)
                        open_trade = db.query(Trade).filter(
                            Trade.agent == AgentName[agent_name],
                            Trade.symbol == symbol,
                            Trade.status == "OPEN",
                        ).first()
                        if open_trade is not None:
                            symbol_statuses.append(
                                _monitor_open_trade(db, open_trade, agent_name)
                            )
                            continue

                        if (
                            not isinstance(live_data, dict)
                            or not quote_is_fresh(live_data)
                            or not quote_has_timestamp(live_data)
                        ):
                            reason = (
                                "Fresh OANDA data is unavailable"
                                if agent_name == "XAUUSD"
                                else "Fresh Dhan quote is unavailable or stale"
                            )
                            symbol_statuses.append(("WAITING_FOR_DATA", reason))
                            continue

                        live_data = dict(live_data)
                        live_data["symbol"] = symbol

                        if not settings.PAPER_TRADING_ENABLED:
                            symbol_statuses.append((
                                "PAPER_TRADING_DISABLED",
                                "Paper entries are disabled; live order execution is never available",
                            ))
                            continue
                        if not _market_hours_open(agent_name):
                            symbol_statuses.append(("MARKET_CLOSED", "Outside the configured market session"))
                            continue

                        # Fail closed: no strategy currently has an authentic historical
                        # execution backtest. PAPER_TRADING_ENABLED is not an approval.
                        # Do not analyze here: signaling mutates strategy counters.
                        # Historical bootstrap/replay must be validated separately.
                        symbol_statuses.append((
                            "BACKTEST_REQUIRED",
                            "Paper entries blocked until genuine historical execution backtests are verified",
                        ))
                        continue

                        try:
                            signal = agent.analyze(live_data)
                        except Exception:
                            logger.warning("Agent analysis failed for %s/%s", agent_name, symbol)
                            symbol_statuses.append(("ANALYSIS_ERROR", "Strategy analysis failed safely"))
                            continue

                        history = _agent_history_status(agent_name, symbol)
                        if signal.value == "HOLD":
                            symbol_statuses.append((
                                history.get("status", "WARMING_UP"),
                                history.get("reason", "No trade signal"),
                            ))
                            continue

                        option_signal_metadata = (
                            agent.get_last_signal_metadata(symbol)
                            if agent_name == "OPTIONS"
                            else {}
                        )
                        if agent_name == "OPTIONS" and option_signal_metadata.get("tier") == "TIER3":
                            agent.rollback_signal(symbol)
                            symbol_statuses.append((
                                "UNSUPPORTED_SETUP",
                                "The strategy's two-leg straddle is not represented as a single paper trade",
                            ))
                            continue

                        if agent_name in {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}:
                            try:
                                identity = dhan_client.select_atm_option(symbol, signal.value)
                                option_quote = (
                                    dhan_client.get_option_quote(
                                        symbol, strike=identity["strike"],
                                        option_type=identity["option_type"],
                                        expiry=identity["expiry"],
                                    ) if identity else None
                                )
                            except Exception:
                                option_quote = None
                            if not _option_quote_is_usable(option_quote):
                                if agent_name == "OPTIONS":
                                    agent.rollback_signal(symbol)
                                symbol_statuses.append((
                                    "WAITING_FOR_OPTION_QUOTE",
                                    "No fresh valid real option bid/ask/LTP; no paper trade was created",
                                ))
                                continue

                            quantity = getattr(agent, "quantity", 1.0)
                            stop_points = (
                                getattr(agent, "sl_points", 50)
                                if agent_name == "OPTIONS"
                                else getattr(agent, "stop_loss_pips", 25)
                            )
                            target_points = (
                                option_signal_metadata.get("target_points", getattr(agent, "tp_points_conservative", 100))
                                if agent_name == "OPTIONS"
                                else getattr(agent, "last_signal_target_points", getattr(agent, "take_profit_pips_min", 10))
                            )
                            fill = build_long_option_paper_entry(
                                signal.value,
                                option_quote,
                                quantity,
                                stop_points,
                                target_points,
                            )
                            if not fill:
                                if agent_name == "OPTIONS":
                                    agent.rollback_signal(symbol)
                                symbol_statuses.append((
                                    "WAITING_FOR_OPTION_QUOTE",
                                    "Option contract identity or fresh bid/ask was invalid",
                                ))
                                continue

                            trade = Trade(
                                agent=AgentName[agent_name],
                                symbol=symbol,
                                trade_type=TradeType.BUY,
                                quantity=fill["quantity"],
                                entry_price=fill["entry_price"],
                                stop_loss=fill["stop_loss"],
                                take_profit=fill["take_profit"],
                                status="OPEN",
                                option_strike=fill["option_strike"],
                                option_price=fill["option_price"],
                                data_source=fill["data_source"],
                                entry_data_timestamp=fill["entry_data_timestamp"],
                            )
                            db.add(trade)
                            try:
                                db.commit()
                            except Exception:
                                db.rollback()
                                if agent_name == "OPTIONS":
                                    agent.rollback_signal(symbol)
                                raise
                            if agent_name == "SENSEX_OPTIONS_SCALPING":
                                agent.log_trade(signal.value, fill["entry_price"])
                            symbol_statuses.append((
                                "PAPER_POSITION_OPEN",
                                f"Long {fill['option_type']} entered at live ask; marked/exited at live bid",
                            ))
                            continue

                        entry_price = provider_side_price(live_data, signal.value)
                        if not isinstance(entry_price, (int, float)) or entry_price <= 0:
                            symbol_statuses.append(("WAITING_FOR_DATA", "Provider price is invalid"))
                            continue

                        if agent_name == "STOCKS":
                            stop_loss, take_profit = agent.get_risk_levels(symbol)
                            quantity = getattr(agent, "base_quantity", 1.0)
                        else:
                            stop_points = getattr(agent, "stop_loss_pips", None)
                            target_points = getattr(agent, "target_pips", None)
                            quantity = 100.0
                            if not stop_points or not target_points:
                                symbol_statuses.append(("UNSUPPORTED_SETUP", "Strategy has no valid paper risk levels"))
                                continue
                            if signal.value == "BUY":
                                stop_loss = entry_price - stop_points
                                take_profit = entry_price + target_points
                            else:
                                stop_loss = entry_price + stop_points
                                take_profit = entry_price - target_points

                        if (
                            stop_loss is None
                            or take_profit is None
                            or stop_loss <= 0
                            or take_profit <= 0
                        ):
                            symbol_statuses.append(("UNSUPPORTED_SETUP", "Strategy risk levels are invalid"))
                            continue

                        source = "OANDA" if agent_name == "XAUUSD" else "DHAN"
                        trade = Trade(
                            agent=AgentName[agent_name],
                            symbol=symbol,
                            trade_type=TradeType[signal.value],
                            quantity=quantity,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            status="OPEN",
                            data_source=source,
                            entry_data_timestamp=live_data.get("timestamp"),
                        )
                        db.add(trade)
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()
                            raise
                        symbol_statuses.append(("PAPER_POSITION_OPEN", f"{source} paper entry created"))

                    if symbol_statuses:
                        statuses = [item[0] for item in symbol_statuses]
                        reasons = list(dict.fromkeys(item[1] for item in symbol_statuses))
                        if "PAPER_POSITION_OPEN" in statuses:
                            status = "PAPER_POSITION_OPEN"
                        elif "TRADE_CLOSED" in statuses:
                            status = "TRADE_CLOSED"
                        elif all(item == "WARMING_UP" for item in statuses):
                            status = "WARMING_UP"
                        elif len(set(statuses)) == 1:
                            status = statuses[0]
                        else:
                            status = "PARTIAL"
                        _AGENT_RUNTIME_STATUS[agent_name] = {
                            "status": status,
                            "reason": "; ".join(reasons),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Live paper-trading cycle failed safely")
            finally:
                db.close()
            await asyncio.sleep(5)

    ticker_task = asyncio.create_task(live_market_feeder())
    option_chain_task = asyncio.create_task(option_chain_refresher())

    optimizer_task = None
    try:
        autonomous_optimizer = AutonomousOptimizer(
            boss_agent=boss_agent,
            agents_map=agents_map,
            learning_engine=learning_engine,
            backtest_engine=backtest_engine,
            strategy_optimizer=strategy_optimizer,
            market_researcher=market_researcher,
            performance_monitor=performance_monitor,
            db_session=SessionLocal,
        )
        optimizer_task = asyncio.create_task(
            autonomous_optimizer.start_autonomous_improvement_loop()
        )
    except Exception:
        autonomous_optimizer = None
        logger.warning("Continuous verified-performance monitor could not start")
    print("Read-only provider collection started; new paper entries require verified backtests. Live orders disabled.", flush=True)

    yield

    if autonomous_optimizer is not None:
        autonomous_optimizer.stop()
    for task in (ticker_task, option_chain_task, optimizer_task):
        if task is not None:
            task.cancel()
    for task in (ticker_task, option_chain_task, optimizer_task):
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
    for client in (dhan_client, onda_client):
        close = getattr(client, "close", None)
        if callable(close):
            try:
                await asyncio.to_thread(close)
            except Exception:
                logger.warning("Provider client cleanup failed")
    print("[OK] Shutdown complete", flush=True)

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
    dhan_status, oanda_status = _provider_status()
    return {
        "mode": "PAPER",
        "live_orders_enabled": False,
        "dhan": dhan_status,
        "oanda": oanda_status,
        "instruments_requested": _instruments_to_subscribe,
    }

@app.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    trades = db.query(Trade).all()
    closed_metrics = verified_closed_trade_metrics(trades)
    open_trades = [trade for trade in trades if trade.status == "OPEN"]
    positions = {}
    realized_pnl_by_currency = {"INR": 0.0, "USD": 0.0}
    unrealized_pnl_by_currency = {"INR": 0.0, "USD": 0.0}
    unpriced_positions = 0
    for currency in realized_pnl_by_currency:
        currency_trades = [
            trade
            for trade in trades
            if ("USD" if trade.agent.value == "XAUUSD" else "INR") == currency
        ]
        realized_pnl_by_currency[currency] = verified_closed_trade_metrics(
            currency_trades
        )["total_pnl"]
    for trade in open_trades:
        current_price, _ = _cached_trade_mark(trade)
        currency = "USD" if trade.agent.value == "XAUUSD" else "INR"
        pnl = None
        if current_price is not None:
            if trade.trade_type.value == "BUY":
                pnl = (current_price - trade.entry_price) * trade.quantity
            else:
                pnl = (trade.entry_price - current_price) * trade.quantity
            unrealized_pnl_by_currency[currency] += pnl
        else:
            unpriced_positions += 1
        positions[str(trade.id)] = {
            "symbol": trade.symbol,
            "agent": trade.agent.value,
            "currency": currency,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "current_price": current_price,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "data_source": trade.data_source,
        }
    realized_pnl = realized_pnl_by_currency["INR"]
    unrealized_pnl = unrealized_pnl_by_currency["INR"]
    total_pnl_by_currency = {
        currency: round(
            realized_pnl_by_currency[currency]
            + unrealized_pnl_by_currency[currency],
            2,
        )
        for currency in realized_pnl_by_currency
    }
    agent_performance = {}
    for agent_name in agents_map:
        agent_trades = [trade for trade in trades if trade.agent == AgentName[agent_name]]
        agent_performance[agent_name] = {
            **verified_closed_trade_metrics(agent_trades),
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "status": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("status", "WAITING_FOR_DATA"),
            "reason": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("reason", ""),
        }
    portfolio_state.update({
        "total_pnl": round(realized_pnl + unrealized_pnl, 2),
        "realized_pnl": realized_pnl,
        "unrealized_pnl": round(unrealized_pnl, 2),
        "net_worth": round(settings.INITIAL_CAPITAL + realized_pnl + unrealized_pnl, 2),
        "currency": "INR",
        "realized_pnl_by_currency": realized_pnl_by_currency,
        "unrealized_pnl_by_currency": {
            currency: round(value, 2)
            for currency, value in unrealized_pnl_by_currency.items()
        },
        "total_pnl_by_currency": total_pnl_by_currency,
        "consolidation_note": "INR and USD P&L are reported separately; no currency conversion is assumed.",
        "positions": positions,
        "active_trades": len(open_trades),
        "unpriced_positions": unpriced_positions,
        "valuation_complete": unpriced_positions == 0,
        "valuation_note": "Unpriced positions remain open; totals include only available verified marks.",
        "agent_performance": agent_performance,
        "mode": "PAPER",
        "live_orders_enabled": False,
        "metrics_basis": closed_metrics["metrics_basis"],
    })
    return portfolio_state

@app.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    positions = []
    open_trades = db.query(Trade).filter(Trade.status == "OPEN").order_by(Trade.created_at.desc()).all()
    for trade in open_trades:
        current_price, _ = _cached_trade_mark(trade)
        pnl = None
        if current_price is not None:
            if trade.trade_type.value == "BUY":
                pnl = (current_price - trade.entry_price) * trade.quantity
            else:
                pnl = (trade.entry_price - current_price) * trade.quantity
        positions.append({
            "symbol": trade.symbol,
            "agent": trade.agent.value,
            "currency": "USD" if trade.agent.value == "XAUUSD" else "INR",
            "qty": trade.quantity,
            "entryPrice": trade.entry_price,
            "currentPrice": current_price,
            "pnl": pnl,
            "pnlPercent": (
                round(pnl / abs(trade.entry_price * trade.quantity) * 100, 2)
                if pnl is not None and trade.entry_price and trade.quantity
                else None
            ),
            "data_source": trade.data_source,
        })
    return {"positions": positions}

@app.get("/agents/performance")
async def get_agents_performance(db: Session = Depends(get_db)):
    result = {}

    for agent_name in agents_map.keys():
        trades = db.query(Trade).filter(Trade.agent == AgentName[agent_name]).all()
        metrics = verified_closed_trade_metrics(trades)
        runtime = _AGENT_RUNTIME_STATUS.get(agent_name, {})
        result[agent_name] = {
            **metrics,
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "confidence": round(metrics["win_rate"] / 100, 4) if metrics["total_trades"] else 0.0,
            "status": runtime.get("status", "WAITING_FOR_DATA"),
            "reason": runtime.get("reason", "Waiting for live market data"),
            "analyzing": runtime.get("status") in {"RUNNING", "PAPER_POSITION_OPEN"},
            "target_win_rate": 90,
            "target_is_aspirational": True,
            "guaranteed": False,
        }

    return result

@app.post("/market-data")
async def ingest_market_data():
    raise HTTPException(
        status_code=403,
        detail="Disabled: market data is accepted only from configured read-only providers.",
    )

@app.get("/trades")
async def get_trades(agent: str = None, db: Session = Depends(get_db)):
    query = db.query(Trade)
    if agent:
        query = query.filter(Trade.agent == AgentName[agent])
    trades = query.order_by(Trade.created_at.desc()).limit(100).all()

    result = []
    for t in trades:
        contract = parse_option_contract(t.option_strike)
        current_price = t.exit_price if t.status == "CLOSED" else None
        if t.status == "OPEN":
            current_price, _ = _cached_trade_mark(t)
        pnl = t.pnl if t.pnl is not None else 0.0
        if t.status == "OPEN" and current_price is not None:
            if t.trade_type.value == "BUY":
                pnl = (current_price - t.entry_price) * t.quantity
            else:
                pnl = (t.entry_price - current_price) * t.quantity
        pnl_pct = (
            (pnl / (t.entry_price * t.quantity)) * 100
            if t.entry_price and t.quantity
            else 0.0
        )
        currency = "USD" if t.agent.value == "XAUUSD" else "INR"

        result.append({
            "id": t.id,
            "agent": t.agent.value,
            "symbol": t.symbol,
            "type": t.trade_type.value,
            "signal": (
                "SELL" if contract and contract["option_type"] == "PE"
                else "BUY" if contract
                else t.trade_type.value
            ),
            "option_strike": t.option_strike,
            "option_type": contract["option_type"] if contract else None,
            "option_expiry": contract["expiry"] if contract else None,
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "current_price": current_price,
            "pnl": pnl,
            "pnl_percent": pnl_pct,
            "currency": currency,
            "status": t.status,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "data_source": t.data_source,
            "entry_data_timestamp": t.entry_data_timestamp,
            "exit_data_timestamp": t.exit_data_timestamp,
            "entry_time": t.created_at.isoformat(),
            "exit_time": t.closed_at.isoformat() if t.closed_at else None,
            "created_at": t.created_at.isoformat(),
        })

    return result

@app.get("/learning/analysis/{agent}")
async def get_agent_analysis(agent: str, db: Session = Depends(get_db)):
    trades = [
        trade
        for trade in db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
        if is_verified_closed_trade(trade)
    ]
    metrics = verified_closed_trade_metrics(trades)

    return {
        "agent": agent,
        "analysis": {
            **metrics,
            "currency": "USD" if agent == "XAUUSD" else "INR",
            "status": "measurement_only",
            "strategy_recommendations": [],
            "reason": (
                "Strategy recommendations require genuine historical market data "
                "and validated backtests."
            ),
        },
        "confidence": (
            round(metrics["win_rate"] / 100, 4)
            if metrics["total_trades"]
            else None
        ),
        "market_conditions": None,
        "suggestions": [],
        "market_history_status": "unavailable_unverified_legacy_data_excluded",
        "metrics_basis": "closed live-provider-price paper trades only",
        "target_win_rate_is_aspirational": True,
        "win_rate_guaranteed": False,
    }

@app.get("/learning/strategy/{agent}")
async def get_optimized_strategy(agent: str, db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
    verified_count = verified_closed_trade_metrics(trades)["total_trades"]
    return {
        "agent": agent,
        "status": "optimization_paused",
        "optimized_parameters": None,
        "strategy_changed": False,
        "verified_closed_trades": verified_count,
        "reason": (
            "Automatic strategy changes require genuine historical market data "
            "and a validated backtest; neither is currently established."
        ),
    }

@app.get("/learning/performance")
async def get_performance_summary(db: Session = Depends(get_db)):
    summary = {}
    for agent_name in agents_map:
        trades = db.query(Trade).filter(Trade.agent == AgentName[agent_name]).all()
        summary[agent_name] = {
            **verified_closed_trade_metrics(trades),
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "status": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("status", "WAITING_FOR_DATA"),
        }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": summary,
        "target_win_rate": 90,
        "target_is_aspirational": True,
        "guaranteed": False,
        "metrics_basis": "closed live-provider-price paper trades only",
    }

@app.get("/learning/improvement-plan/{agent}")
async def get_improvement_plan(agent: str, db: Session = Depends(get_db)):
    trades = [
        trade
        for trade in db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
        if is_verified_closed_trade(trade)
    ]
    return {
        "agent": agent,
        "status": "insufficient_validated_history",
        "improvement_plan": [],
        "opportunities": [],
        "verified_closed_trades": len(trades),
        "reason": (
            "No strategy upgrades are proposed until genuine historical data "
            "and validated backtests are available."
        ),
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
    all_trades = [
        trade
        for trade in db.query(Trade).all()
        if is_verified_closed_trade(trade)
    ]
    return {
        "status": "consensus_paused",
        "consensus": "HOLD",
        "confidence": None,
        "verified_closed_trades": len(all_trades),
        "metrics_basis": "closed live-provider-price paper trades only",
        "reason": (
            "Team consensus is not inferred from unverified legacy market history; "
            "it requires genuine historical data and validated strategy evaluation."
        ),
    }

@app.get("/boss/leaderboard")
async def get_agent_leaderboard(db: Session = Depends(get_db)):
    if not boss_agent:
        return {"status": "boss_agent_not_initialized", "leaderboard": []}
    agent_metrics = {}
    for agent_name in agents_map:
        trades = db.query(Trade).filter(Trade.agent == AgentName[agent_name]).all()
        metrics = verified_closed_trade_metrics(trades)
        agent_metrics[agent_name] = {
            "win_rate": metrics["win_rate"],
            "total_pnl": metrics["total_pnl"],
            "total_trades": metrics["total_trades"],
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "metrics_basis": metrics["metrics_basis"],
        }
    if not any(metrics["total_trades"] for metrics in agent_metrics.values()):
        return {
            "status": "insufficient_verified_live_paper_data",
            "leaderboard": [],
            "metrics_basis": "closed live-provider-price paper trades only",
        }
    leaderboard = boss_agent.update_performance_leaderboard(agent_metrics)
    return {
        "status": "measured",
        "leaderboard": leaderboard,
        "metrics_basis": "closed live-provider-price paper trades only",
        "target_win_rate_is_aspirational": True,
        "win_rate_guaranteed": False,
    }

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
    if agent == "XAUUSD":
        return {
            "agent": agent, "status": "unavailable_until_verified_history",
            "reason": "OANDA live pricing is enabled; historical XAUUSD strategy validation is not completed",
            "execution_validated": False, "strategy_changed": False,
            "total_trades": None, "win_rate": None, "total_pnl": None,
            "counted_toward_live_target": False,
        }
    report_path = evidence_dir / "latest_backtests.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
            evaluation = report.get("agents", {}).get(agent)
            if isinstance(evaluation, dict):
                return {
                    **evaluation,
                    "agent": agent,
                    "generated_at": report.get("generated_at"),
                    "data_source": report.get("data_source"),
                    "requested_period_days": days,
                    "period_note": "Returns the latest completed evaluation; this request does not change its period.",
                    "counted_toward_live_target": False,
                    "strategy_changed": False,
                }
        except (OSError, ValueError, TypeError):
            raise HTTPException(status_code=503, detail="Backtest evidence report is unavailable")
    return {
        "agent": agent,
        "requested_period_days": days,
        "status": "unavailable_until_verified_history",
        "total_trades": None,
        "win_rate": None,
        "total_pnl": None,
        "counted_toward_live_target": False,
        "strategy_changed": False,
        "reason": (
            "Legacy market-data rows have no verified provider provenance; "
            "backtesting and strategy changes require genuine historical data "
            "and a validated evaluation."
        ),
    }

@app.get("/data/market-snapshot")
async def get_market_snapshot():
    snapshot = dhan_client.get_market_snapshot()
    prices = snapshot.setdefault("prices", {})
    cached_xau = onda_client.get_cached_quote("XAUUSD")
    if isinstance(cached_xau, dict) and quote_is_fresh(cached_xau):
        prices["XAUUSD"] = dict(cached_xau)
    return snapshot


@app.get("/market/status")
async def get_market_status():
    dhan_status, oanda_status = _provider_status()
    return {
        "mode": "PAPER",
        "live_orders_enabled": False,
        "paper_trading_enabled": False,
        "paper_trading_requested": bool(settings.PAPER_TRADING_ENABLED),
        "entry_gate": "BACKTEST_REQUIRED",
        "live_observations": live_observation_recorder.get_status(),
        "xauusd_observations": xau_observation_recorder.get_status(),
        "win_rate_target": 90,
        "win_rate_target_aspirational": True,
        "win_rate_guaranteed": False,
        "metrics_basis": "closed live-provider-price paper trades only",
        "dhan": dhan_status,
        "oanda": oanda_status,
        "performance_monitor": (
            autonomous_optimizer.get_status()
            if autonomous_optimizer is not None
            else {"status": "unavailable"}
        ),
        "agents": {
            name: dict(status)
            for name, status in _AGENT_RUNTIME_STATUS.items()
        },
    }

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
        return {
            "status": "not_initialized",
            "reason": "Verified closed-trade monitor is unavailable",
        }
    return autonomous_optimizer.get_status()

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
