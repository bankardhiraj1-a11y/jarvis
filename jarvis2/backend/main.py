from fastapi import FastAPI, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import asyncio
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
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
from agents.xauusd import entry_window_intervals_utc, within_entry_window
from agents.xauusd_highwin import XAUUSDHighWinResearchAgent
from agents.base import Signal
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
from data.currency_conversion import (
    EcbUsdInrRateProvider, consolidate_pnl_currencies,
    gold_quantity_from_lots, gold_lot_display,
)
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
from trading.charges import (
    ChargeInputError,
    calculate_charges,
    get_charge_rules,
    get_charge_trades,
    sized_stock_entry,
)
from trading.holding_policy import (
    entry_allowed_by_holding_policy,
    holding_exit_decision,
)
from trading.dhan_lot_size import fetch_official_dhan_lot_sizes
from trading.runtime_support import (
    daily_trade_review,
    exchange_session_status,
    load_indian_exchange_calendar,
)
try:
    from data.oanda_costs import OandaCostMetadataProvider
except ImportError:
    # The provider is supplied by the parallel currency-display integration.
    OandaCostMetadataProvider = None

settings = get_settings()
Base.metadata.create_all(bind=engine)
ensure_trade_provenance_columns(engine)

agents_map = {
    "STOCKS": StocksAgent(),
    "SENSEX": SensexAgent(),
    "OPTIONS": OptionsAgent(),
    "XAUUSD": XAUUSDHighWinResearchAgent({
        "bar_interval_minutes": 1,
        "rsi_period": 7,
        "rsi_reentry_threshold": 20,
        "bollinger_period": 20,
        "bollinger_stddev": 2.0,
        "regime_fast_ema": 20,
        "regime_slow_ema": 50,
        "max_range_ema_separation_usd": 2.0,
        "stop_loss_usd_per_oz": 1.5,
        "take_profit_usd_per_oz": 3.75,
        "max_hold_minutes": 25,
        "allow_overnight": False,
        "entry_window": {
            "name": "Europe_London_08_17",
            "mode": "any",
            "day_timezone": "Europe/London",
            "clauses": [
                {
                    "timezone": "Europe/London",
                    "start": "08:00",
                    "end": "17:00",
                }
            ],
        },
        "max_trades_per_utc_day": 3,
        "position_quantity_units": 100,
    }),
    "SENSEX_OPTIONS_SCALPING": SensexOptionsScalpingAgent(),
}

learning_engine = LearningEngine()
strategy_optimizer = StrategyOptimizer()
market_researcher = MarketResearcher()
performance_monitor = PerformanceMonitor(target_win_rate=0.90)
backtest_engine = BacktestEngine()
dhan_client = DhanLiveClient()
onda_client = OndaClient()
usd_inr_provider = EcbUsdInrRateProvider()
oanda_cost_metadata_provider = (
    OandaCostMetadataProvider(onda_client) if OandaCostMetadataProvider else None
)
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

PAPER_EXPERIMENTAL_AGENTS = {"SENSEX_OPTIONS_SCALPING", "XAUUSD"}
LIVE_ORDERS_ENABLED = False
DAILY_REVIEW_SCHEMA_VERSION = 2
_DHAN_LOT_SIZES = {}
_DAILY_CALL_COUNTS = {}
_REVIEWED_SESSION_DATES = set()
_EXCHANGE_CALENDAR = load_indian_exchange_calendar()


def _gold_charge_quote():
    """Return only an already-cached provider quote; never refresh from a route."""
    price_cache = getattr(onda_client, "latest_prices", {})
    cached = price_cache.get("XAUUSD") if isinstance(price_cache, dict) else None
    if not isinstance(cached, dict):
        return None
    return {
        **cached,
        "source": "OANDA",
        "instrument": "XAU_USD",
        "provider_timestamp": cached.get("provider_timestamp") or cached.get("timestamp"),
    }


def _gold_cost_metadata():
    """Use the cached instrument-specific provider snapshot only."""
    provider = oanda_cost_metadata_provider
    if provider is None:
        return None
    try:
        snapshot = provider.get_snapshot()
    except Exception:
        return None
    return snapshot if isinstance(snapshot, dict) else None


def _trade_gross_pnl(entry_price, exit_price, quantity, trade_type):
    direction = 1 if str(getattr(trade_type, "value", trade_type)).upper() == "BUY" else -1
    return (float(exit_price) - float(entry_price)) * float(quantity) * direction


def _india_date(timestamp):
    if not isinstance(timestamp, datetime):
        return None
    normalized = (
        timestamp.replace(tzinfo=timezone.utc)
        if timestamp.tzinfo is None
        else timestamp
    )
    return normalized.astimezone(pytz.timezone("Asia/Kolkata")).date()


def calculate_net_pnl(
    entry_price,
    exit_price,
    quantity,
    trade_type,
    symbol,
    *,
    agent_name=None,
    created_at=None,
    closed_at=None,
    option_trade=False,
):
    """Deduct only fees completely modeled by the published charge engine."""
    agent = str(getattr(agent_name, "value", agent_name) or "").upper()
    is_gold = agent == "XAUUSD" or str(symbol).upper() == "XAUUSD"
    is_option = option_trade or agent in {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}
    side = str(getattr(trade_type, "value", trade_type)).upper()
    if is_gold:
        result = calculate_charges(
            {
                "market": "XAUUSD",
                "exchange": "OANDA",
                "quantity": quantity,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "side": side,
                "entry_time": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                "exit_time": closed_at.isoformat() if hasattr(closed_at, "isoformat") else closed_at,
            },
            gold_quote=_gold_charge_quote(),
            gold_cost_metadata=_gold_cost_metadata(),
        )
        # Unknown OANDA commission/financing never becomes an assumed zero.
        return result["net_pnl"]

    if is_option:
        product = "index_options"
        exchange = "BSE" if agent == "SENSEX_OPTIONS_SCALPING" else "NSE"
    elif agent == "STOCKS":
        opened = _india_date(created_at)
        closed = _india_date(closed_at)
        product = "equity_intraday" if opened is not None and opened == closed else "equity_delivery"
        exchange = "NSE"
    else:
        product, exchange = "equity_intraday", "NSE"
    result = calculate_charges(
        {
            "market": "INDIA",
            "product": product,
            "exchange": exchange,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "side": side,
        }
    )
    return result["net_pnl"]


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
    "STOCKS": {
        "status": "BACKTEST_REQUIRED",
        "reason": "Stock paper entries remain blocked until validated execution backtests are available",
    },
    "SENSEX": {
        "status": "DISABLED",
        "reason": "Legacy SENSEX multi-leg spread/condor has no supported multi-leg paper execution",
    },
    "OPTIONS": {
        "status": "BACKTEST_REQUIRED",
        "reason": "Unvalidated options strategies remain entry-blocked",
    },
    "XAUUSD": {
        "status": "WAITING_FOR_DATA",
        "reason": (
            "London 08:00-17:00 Europe/London is an unvalidated forward-paper "
            "hypothesis only; the session study rejected all candidates and "
            "reported negative fit and validation quote-side P&L"
        ),
        "learner_status": "EXPERIMENTAL_PAPER_LEARNING",
        "provenance": "OANDA live bid/ask quotes and completed bars",
        "research_status": "NO_VALIDATED_WINNER_FORWARD_PAPER_HYPOTHESIS_ONLY",
        "live_orders_enabled": False,
        "forward_paper_hypothesis_only": True,
        "profitability_claim": False,
        "quote_collection_independent_of_entry_session": True,
    },
    "SENSEX_OPTIONS_SCALPING": {
        "status": "WAITING_FOR_DATA",
        "reason": "Waiting for fresh SENSEX index and option-chain data",
        "learner_status": "EXPERIMENTAL_PAPER_LEARNING",
        "provenance": "Dhan live index/option quotes; experimental parameters only",
        "risk_limitations": (
            "Signals use completed SENSEX underlying candles, while paper stop/target "
            "are fixed option-premium points; the prior-candle underlying stop is not mapped"
        ),
        "research_status": "RESEARCH_NOT_VALIDATED",
        "live_orders_enabled": False,
    },
}
_AGENT_SYMBOLS = {
    "STOCKS": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "BAJAJ-AUTO"],
    "OPTIONS": ["NIFTY", "BANKNIFTY"],
    "SENSEX_OPTIONS_SCALPING": ["SENSEX"],
    "XAUUSD": ["XAUUSD"],
}


def _verified_option_lot_size(option_quote):
    try:
        contract_id = str(int(option_quote.get("security_id")))
    except (TypeError, ValueError, OverflowError):
        return None
    supplied = option_quote.get("lot_size") or option_quote.get("lot_units")
    try:
        lot_size = int(supplied) if supplied is not None else _DHAN_LOT_SIZES.get(contract_id)
    except (TypeError, ValueError, OverflowError):
        return None
    return lot_size if isinstance(lot_size, int) and lot_size > 0 else None


def _size_sensex_option(option_quote, target_points, allocation):
    """Find whole verified contract lots within the explicit paper loss/cash caps."""
    lot_size = _verified_option_lot_size(option_quote)
    prices = option_entry_and_exit_prices(option_quote)
    if lot_size is None or prices is None:
        return None, "WAITING_FOR_CONTRACT_METADATA"
    entry_price, _ = prices
    stop_price = max(0.05, entry_price - 25.0)
    target_price = entry_price + float(target_points)
    max_lots = int(float(allocation) // (entry_price * lot_size))
    for lots in range(max_lots, 0, -1):
        quantity = lots * lot_size
        stop_estimate = calculate_charges({
            "market": "INDIA",
            "product": "index_options",
            "exchange": "BSE",
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": stop_price,
            "side": "BUY",
        })
        risk = max(0.0, entry_price - stop_price) * quantity
        if (
            not stop_estimate["complete"]
            or risk + stop_estimate["total_additional_charges"] > 1000
            or entry_price * quantity + stop_estimate["total_additional_charges"] > allocation
        ):
            continue
        target_estimate = calculate_charges({
            "market": "INDIA",
            "product": "index_options",
            "exchange": "BSE",
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": target_price,
            "side": "BUY",
        })
        if target_estimate["complete"] and target_estimate["net_pnl"] is not None and target_estimate["net_pnl"] > 0:
            return {
                "quantity": quantity,
                "lot_size": lot_size,
                "lots": lots,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "estimated_risk": risk + stop_estimate["total_additional_charges"],
                "expected_net_profit": target_estimate["net_pnl"],
            }, None
    return None, "NO_SIZE_WITHIN_ALLOCATED_CAPITAL_OR_RISK"


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


def _market_hours_open(agent_name, now=None):
    if now is None:
        utc_now = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        utc_now = (
            now.replace(tzinfo=timezone.utc)
            if now.tzinfo is None
            else now.astimezone(timezone.utc)
        )
    else:
        utc_now = _provider_time(now)
    if utc_now is None:
        return False
    if agent_name == "XAUUSD":
        agent = agents_map["XAUUSD"]
        return bool(
            within_entry_window(
                utc_now,
                {"entry_window": agent.highwin_parameters["entry_window"]},
            )
        )
    ist_now = utc_now.astimezone(pytz.timezone("Asia/Kolkata"))
    exchange_status = exchange_session_status(ist_now, _EXCHANGE_CALENDAR)
    return bool(
        exchange_status["open"]
        and time(9, 15) <= ist_now.time() <= time(15, 30)
    )


def _xau_entry_window_status(now=None):
    if now is None:
        now_utc = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        now_utc = (
            now.replace(tzinfo=timezone.utc)
            if now.tzinfo is None
            else now.astimezone(timezone.utc)
        )
    else:
        now_utc = _provider_time(now)
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    agent = agents_map["XAUUSD"]
    window = agent.highwin_parameters["entry_window"]
    local_zone = ZoneInfo(window["day_timezone"])
    local_now = now_utc.astimezone(local_zone)
    session_day = local_now.date()
    intervals = entry_window_intervals_utc(session_day, window)
    first_start = intervals[0][0] if intervals else None
    last_end = intervals[-1][1] if intervals else None
    ist_zone = pytz.timezone("Asia/Kolkata")
    clause = window["clauses"][0]
    return {
        "name": window["name"],
        "timezone": window["day_timezone"],
        "local_hours": f'{clause["start"]}-{clause["end"]}',
        "session_day_local": session_day.isoformat(),
        "current_utc": now_utc.isoformat(),
        "current_ist": now_utc.astimezone(ist_zone).isoformat(),
        "current_local": local_now.isoformat(),
        "opens_utc": first_start.isoformat() if first_start else None,
        "closes_utc": last_end.isoformat() if last_end else None,
        "opens_ist": first_start.astimezone(ist_zone).isoformat() if first_start else None,
        "closes_ist": last_end.astimezone(ist_zone).isoformat() if last_end else None,
        "is_open": _market_hours_open("XAUUSD", now_utc),
    }


def _xau_strategy_parameters():
    return dict(agents_map["XAUUSD"].highwin_parameters)


_XAU_SESSION_STUDY_STATUS = {
    "status": "NO_VALIDATED_WINNER",
    "candidate_count": 12,
    "fit_validation_eligible_candidates": 0,
    "holdout_evaluated_candidates": 0,
    "holdout_inspected_for_selection": False,
    "all_candidates_rejected": True,
    "forward_paper_hypothesis_only": True,
    "profitability_claim": False,
    "selected_session_hypothesis": "Europe_London_08_17",
    "selection_note": (
        "London was chosen only as an explicitly unvalidated forward-paper hypothesis: "
        "its fixed RSI/Bollinger validation loss was the smallest among adequately sampled "
        "windows, but both fit and validation P&L were negative. It is not a profitable "
        "prediction or validated winner."
    ),
    "strategy_key": "RSI_BB_EXISTING_BEST_COVERAGE_FIXED",
    "fit": {
        "closed_trades": 86,
        "wins": 19,
        "losses": 67,
        "win_rate_pct": 22.09,
        "quote_side_pnl_before_unverified_additional_costs_usd": -3217.0,
    },
    "validation": {
        "closed_trades": 30,
        "wins": 8,
        "losses": 22,
        "win_rate_pct": 26.67,
        "quote_side_pnl_before_unverified_additional_costs_usd": -300.0,
    },
    "comparison_context": {
        "us_validation_quote_side_pnl_usd": -1275.0,
        "us_validation_closed_trades": 33,
        "original_utc_16_23_validation_quote_side_pnl_usd": -1875.0,
        "original_utc_16_23_validation_closed_trades": 30,
        "europe_us_overlap_validation_quote_side_pnl_usd": 375.0,
        "europe_us_overlap_validation_closed_trades": 8,
        "europe_us_overlap_rejected_for_inadequate_sample": True,
    },
    "pnl_basis": (
        "Historical executable-side bid/ask P&L includes observed spread, but excludes "
        "unverified OANDA commission and financing; it is not final net P&L."
    ),
    "holdout_rule": (
        "Final holdout was not evaluated because zero candidates qualified on fit and validation."
    ),
    "live_orders_enabled": False,
}


_AGENT_RUNTIME_STATUS["XAUUSD"].update({
    "research_status": "NO_VALIDATED_WINNER_FORWARD_PAPER_HYPOTHESIS_ONLY",
    "session_study": _XAU_SESSION_STUDY_STATUS,
    "active_entry_window": _xau_entry_window_status(),
    "forward_paper_hypothesis_only": True,
    "profitability_claim": False,
    "quote_collection_independent_of_entry_session": True,
    "strategy_parameters": _xau_strategy_parameters(),
})


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
    now_utc = datetime.now(timezone.utc)
    entry_event_time = _provider_time(
        getattr(trade, "entry_data_timestamp", None)
    ) if agent_name == "XAUUSD" else None
    holding_intent = (
        {
            "max_hold_minutes": 25,
            "allow_overnight": False,
        }
        if agent_name == "XAUUSD"
        else None
    )
    holding_trade = trade
    if agent_name == "XAUUSD" and entry_event_time is not None:
        holding_trade = {
            "agent": agent_name,
            "status": trade.status,
            "created_at": entry_event_time,
        }
    holding = holding_exit_decision(
        holding_trade,
        now=now_utc,
        holding_intent=holding_intent,
    )
    gold_time_due = False
    gold_session_exit_due = False
    gold_deadline = None
    if agent_name == "XAUUSD":
        created_utc = entry_event_time or _provider_time(trade.created_at)
        gold_deadline = (
            created_utc + timedelta(minutes=25) if created_utc is not None else None
        )
        gold_time_due = bool(gold_deadline and now_utc >= gold_deadline)
        gold_session_exit_due = bool(
            agents_map["XAUUSD"].should_force_research_time_exit(now_utc)
        )
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
        if holding["due"] or gold_time_due or gold_session_exit_due:
            return (
                "EXIT_PENDING_QUOTE",
                (
                    "XAUUSD session-close, 25-minute maximum-hold, or rollover exit is due"
                    if gold_session_exit_due
                    else "XAUUSD 25-minute maximum hold is due"
                    if gold_time_due
                    else holding["reason"]
                )
                + "; fresh quote unavailable, position remains open with no synthetic fill",
            )
        return (
            "WAITING_FOR_DATA",
            "Fresh cached quote for the open position is unavailable",
        )

    hard_exit_due = bool(holding["due"])
    if agent_name == "XAUUSD":
        observed_exit_time = current_quote.get("provider_timestamp") or current_quote.get("timestamp")
        hard_exit_due = (
            hard_exit_due
            or agents_map["XAUUSD"].should_force_research_time_exit(observed_exit_time)
        )
        try:
            parsed_exit_time = datetime.fromisoformat(
                str(observed_exit_time).replace("Z", "+00:00")
            )
            if parsed_exit_time.tzinfo is None:
                parsed_exit_time = parsed_exit_time.replace(tzinfo=timezone.utc)
            hard_exit_due = hard_exit_due or bool(
                gold_deadline
                and parsed_exit_time.astimezone(timezone.utc) >= gold_deadline
            )
        except (TypeError, ValueError):
            pass
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
        now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
        if (
            agent_name in {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}
            and holding["status"] == "INTRADAY_EXIT_OVERDUE"
        ):
            return (
                "EXIT_PENDING_QUOTE",
                "Intraday position is overdue; no stop/target crossed and no fabricated end-of-day fill was created",
            )
        return (
            "PAPER_POSITION_OPEN",
            "Monitoring the exact live-provider instrument price",
        )

    trade.exit_price = current_price
    trade.closed_at = datetime.utcnow()
    trade.exit_data_timestamp = (
        current_quote.get("timestamp")
        if isinstance(current_quote.get("timestamp"), str)
        else None
    )
    trade.pnl = calculate_net_pnl(
        trade.entry_price,
        current_price,
        trade.quantity,
        trade.trade_type.value,
        trade.symbol,
        agent_name=agent_name,
        created_at=(
            trade.entry_data_timestamp
            if agent_name == "XAUUSD" and trade.entry_data_timestamp
            else trade.created_at
        ),
        closed_at=(
            trade.exit_data_timestamp
            if agent_name == "XAUUSD" and trade.exit_data_timestamp
            else trade.closed_at
        ),
        option_trade=trade.option_strike is not None,
    )
    trade.status = "CLOSED"
    db.commit()
    if agent_name == "OPTIONS":
        agents_map[agent_name].close_paper_position(trade.symbol)
    if agent_name == "SENSEX_OPTIONS_SCALPING":
        gross_pnl = _trade_gross_pnl(
            trade.entry_price, current_price, trade.quantity, trade.trade_type
        )
        closed_entry = next(
            (
                item for item in reversed(agents_map[agent_name].trades_today)
                if item.get("trade_id") == trade.id
            ),
            None,
        )
        if closed_entry is not None:
            closed_entry["pnl"] = trade.pnl if trade.pnl is not None else gross_pnl
        if (
            isinstance(trade.pnl, (int, float))
            and math.isfinite(float(trade.pnl))
            and float(trade.pnl) < 0
        ):
            agents_map[agent_name].last_realized_loss_time = _provider_time(
                trade.closed_at
            )
    if agent_name == "XAUUSD":
        agents_map["XAUUSD"].mark_research_position_closed()
    return (
        "TRADE_CLOSED",
        "Closed at a fresh provider quote"
        + (f" under {holding['status']}" if holding["due"] else " after a stop/target/time threshold"),
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


def _daily_trade_datetime(trade, field_name, agent_name):
    value = getattr(trade, field_name, None)
    if not isinstance(value, datetime):
        return None
    if agent_name == "XAUUSD":
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return normalized.astimezone(timezone.utc).date()
    return _india_date(value)


def _provider_time(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    try:
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _has_ordered_provider_timestamps(trade):
    entry = _provider_time(getattr(trade, "entry_data_timestamp", None))
    exit_time = _provider_time(getattr(trade, "exit_data_timestamp", None))
    closed = _provider_time(getattr(trade, "closed_at", None))
    return bool(entry and exit_time and closed and entry <= exit_time <= closed)


def _accepted_provider_entry_time(trade, agent_name):
    source = str(getattr(trade, "data_source", "") or "").upper()
    expected_source = "OANDA" if agent_name == "XAUUSD" else "DHAN"
    if (
        str(getattr(getattr(trade, "agent", None), "value", getattr(trade, "agent", ""))).upper()
        != agent_name
        or source != expected_source
        or not getattr(trade, "entry_data_timestamp", None)
    ):
        return None
    if agent_name == "SENSEX_OPTIONS_SCALPING" and not getattr(
        trade, "option_strike", None
    ):
        return None
    return _provider_time(trade.entry_data_timestamp)


def _gold_entries_for_utc_day(db, utc_day):
    trades = db.query(Trade).filter(
        Trade.agent == AgentName.XAUUSD,
        Trade.data_source == "OANDA",
        Trade.entry_data_timestamp.isnot(None),
    ).all()
    return [
        (trade, entry_time)
        for trade in trades
        if (
            (entry_time := _accepted_provider_entry_time(trade, "XAUUSD")) is not None
            and entry_time.date() == utc_day
        )
    ]


def _restore_gold_runtime_state(db, now_utc):
    """Restore accepted-entry risk state from provider-provenanced paper rows."""
    agent = agents_map["XAUUSD"]
    today = now_utc.astimezone(timezone.utc).date()
    entries = _gold_entries_for_utc_day(db, today)
    state = agent.highwin_state
    state["last_utc_day"] = today
    state["daily_entry_count"] = len(entries)
    agent._daily_entry_count = len(entries)
    agent.open_trade_count = len(entries)

    open_entries = [
        (trade, entry_time)
        for trade, entry_time in entries
        if str(getattr(trade, "status", "")).upper() == "OPEN"
    ]
    if open_entries:
        oldest_entry = min(entry_time for _, entry_time in open_entries)
        agent._highwin_active_entry_time = oldest_entry
    else:
        agent._highwin_active_entry_time = None
    return len(entries)


def _sensex_paper_entries(db):
    trades = db.query(Trade).filter(
        Trade.agent == AgentName.SENSEX_OPTIONS_SCALPING,
        Trade.data_source == "DHAN",
        Trade.entry_data_timestamp.isnot(None),
    ).all()
    return [
        (trade, entry_time)
        for trade in trades
        if (entry_time := _accepted_provider_entry_time(
            trade, "SENSEX_OPTIONS_SCALPING"
        )) is not None
    ]


def _restore_sensex_runtime_state(db, now_utc):
    """Rebuild cooldown/daily tracking without matching trades on float prices."""
    agent = agents_map["SENSEX_OPTIONS_SCALPING"]
    now_ist = now_utc.astimezone(pytz.timezone("Asia/Kolkata"))
    entries = [
        (trade, entry_time)
        for trade, entry_time in _sensex_paper_entries(db)
        if entry_time.astimezone(pytz.timezone("Asia/Kolkata")).date()
        == now_ist.date()
    ]
    agent.trades_today = [
        {
            "trade_id": trade.id,
            "date": entry_time.astimezone(pytz.timezone("Asia/Kolkata")),
            "signal": trade.trade_type.value,
            "entry_price": trade.entry_price,
            "pnl": (
                trade.pnl
                if str(trade.status).upper() == "CLOSED" and trade.pnl is not None
                else 0
            ),
        }
        for trade, entry_time in sorted(entries, key=lambda item: item[1])
    ]
    agent.last_trade_time = agent.trades_today[-1]["date"] if agent.trades_today else None

    losses = []
    for trade, _ in _sensex_paper_entries(db):
        if (
            str(trade.status).upper() == "CLOSED"
            and isinstance(trade.pnl, (int, float))
            and math.isfinite(float(trade.pnl))
            and float(trade.pnl) < 0
        ):
            closed_at = _provider_time(trade.closed_at)
            if closed_at is not None:
                losses.append((closed_at, trade.id))
    agent.last_realized_loss_time = max(losses, default=(None, None))[0]
    return len(entries)


def _sensex_cooldown_status(db, entry_time):
    """Enforce persisted 10-minute entry and 15-minute realized-loss cooldowns."""
    observed_at = _provider_time(entry_time)
    if observed_at is None:
        return False, "Provider timestamp is missing; Sensex entry cooldown cannot be verified"
    entries = _sensex_paper_entries(db)
    if entries:
        latest_entry = max(entry_at for _, entry_at in entries)
        elapsed = observed_at - latest_entry
        if elapsed < timedelta(minutes=10):
            remaining = max(0, int((timedelta(minutes=10) - elapsed).total_seconds()))
            return False, f"Persisted accepted-entry cooldown: wait {remaining} more seconds"

    latest_loss = None
    for trade, _ in entries:
        if (
            str(trade.status).upper() == "CLOSED"
            and isinstance(trade.pnl, (int, float))
            and math.isfinite(float(trade.pnl))
            and float(trade.pnl) < 0
        ):
            closed_at = _provider_time(trade.closed_at)
            if closed_at is not None and (
                latest_loss is None or closed_at > latest_loss
            ):
                latest_loss = closed_at
    if latest_loss is not None:
        elapsed = observed_at - latest_loss
        if elapsed < timedelta(minutes=15):
            remaining = max(0, int((timedelta(minutes=15) - elapsed).total_seconds()))
            return False, f"Persisted realized-loss cooldown: wait {remaining} more seconds"
    return True, "Persisted Sensex entry and realized-loss cooldowns have elapsed"


def _increment_daily_call(agent_name):
    if agent_name == "XAUUSD":
        session_name = "XAUUSD"
        session_date = datetime.now(timezone.utc).date().isoformat()
    else:
        session_name = "INDIA"
        session_date = datetime.now(pytz.timezone("Asia/Kolkata")).date().isoformat()
    key = (session_name, session_date)
    _DAILY_CALL_COUNTS[key] = _DAILY_CALL_COUNTS.get(key, 0) + 1


def _daily_review_records(trades, review_date, agent_name):
    records = []
    for trade in trades:
        if (
            str(getattr(trade, "status", "")).upper() != "CLOSED"
            or str(getattr(trade, "data_source", "")).upper() not in {"DHAN", "OANDA"}
            or not trade.entry_data_timestamp
            or not trade.exit_data_timestamp
            or not _has_ordered_provider_timestamps(trade)
            or _daily_trade_datetime(trade, "closed_at", agent_name) != review_date
        ):
            continue
        if not all(
            isinstance(value, (int, float)) and math.isfinite(float(value))
            for value in (trade.entry_price, trade.exit_price, trade.quantity)
        ) or min(float(trade.entry_price), float(trade.exit_price), float(trade.quantity)) <= 0:
            continue
        try:
            charges = calculate_charges(
                _charge_request_for_trade(trade),
                gold_quote=_gold_charge_quote(),
                gold_cost_metadata=_gold_cost_metadata(),
            )
        except ChargeInputError as exc:
            charges = {"status": "unavailable", "complete": False, "error": str(exc)}
        records.append({
            "trade_id": trade.id,
            "agent": trade.agent.value,
            "symbol": trade.symbol,
            "data_source": trade.data_source,
            "entry_data_timestamp": trade.entry_data_timestamp,
            "exit_data_timestamp": trade.exit_data_timestamp,
            "created_at": trade.created_at.isoformat() if trade.created_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "gross_price_pnl": round(
                _trade_gross_pnl(
                    trade.entry_price,
                    trade.exit_price,
                    trade.quantity,
                    trade.trade_type,
                ),
                2,
            ),
            "stored_net_pnl": trade.pnl,
            "fees": charges,
        })
    return records


def _write_daily_review(db, now_utc):
    """Write date-stamped evidence from closed paper DB rows; never create fills."""
    now_utc = now_utc.astimezone(timezone.utc)
    now_ist = now_utc.astimezone(pytz.timezone("Asia/Kolkata"))
    all_trades = db.query(Trade).all()
    sessions = (
        (
            "INDIA",
            now_ist.date(),
            now_ist,
            time(15, 35),
            {"STOCKS", "OPTIONS", "SENSEX_OPTIONS_SCALPING"},
            "Asia/Kolkata",
            "INR",
        ),
        (
            "XAUUSD",
            now_utc.date(),
            now_utc,
            time(23, 5),
            {"XAUUSD"},
            "UTC",
            "USD",
        ),
    )
    for session_name, today, local_now, cutoff, agent_names, zone_name, currency in sessions:
        zone = pytz.timezone(zone_name) if zone_name != "UTC" else timezone.utc
        for days_back in range(8):
            review_date = today - timedelta(days=days_back)
            if days_back == 0 and local_now.time().replace(tzinfo=None) < cutoff:
                continue
            review_key = (
                f"{session_name}:v{DAILY_REVIEW_SCHEMA_VERSION}:"
                f"{review_date.isoformat()}"
            )
            versioned_session = f"{session_name.lower()}-v{DAILY_REVIEW_SCHEMA_VERSION}"
            path = evidence_dir / "daily_reviews" / f"{versioned_session}-{review_date.isoformat()}.json"
            if review_key in _REVIEWED_SESSION_DATES or path.exists():
                _REVIEWED_SESSION_DATES.add(review_key)
                continue
            scoped = [
                trade for trade in all_trades
                if getattr(trade.agent, "value", str(trade.agent)) in agent_names
            ]
            activity_exists = any(
                _daily_trade_datetime(trade, "created_at", "XAUUSD" if session_name == "XAUUSD" else "") == review_date
                or _daily_trade_datetime(trade, "closed_at", "XAUUSD" if session_name == "XAUUSD" else "") == review_date
                for trade in scoped
            )
            if days_back and not activity_exists:
                continue
            calls = _DAILY_CALL_COUNTS.get((session_name, review_date.isoformat()))
            summary = daily_trade_review(
                scoped,
                review_date=review_date,
                calls=calls,
                quote_currency=currency,
                session_timezone=zone_name,
            )
            records = _daily_review_records(scoped, review_date, "XAUUSD" if session_name == "XAUUSD" else "")
            entries = sum(
                1 for trade in scoped
                if _daily_trade_datetime(trade, "created_at", "XAUUSD" if session_name == "XAUUSD" else "") == review_date
                and getattr(trade, "data_source", None) in {"DHAN", "OANDA"}
                and getattr(trade, "entry_data_timestamp", None)
            )
            exits = len(records)
            summary.update({
                "review_schema_version": DAILY_REVIEW_SCHEMA_VERSION,
                "session": session_name,
                "daily_entries": entries,
                "daily_exits": exits,
                "daily_call_count_source": (
                    "In-memory strategy invocation count for this API process; resets on restart"
                ),
                "fee_complete_trades": sum(
                    record["fees"].get("complete") is True for record in records
                ),
                "fee_incomplete_trades": sum(
                    record["fees"].get("complete") is not True for record in records
                ),
                "closed_trade_evidence": records,
                "source": "Closed paper database trades with live-provider provenance only",
                "scheduler_scope": "Runs only while the API process is active; continuous 24/7 operation is not guaranteed",
                "live_orders_enabled": False,
                "strategy_validation_claim": False,
            })
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
                encoding="utf-8",
            )
            temporary.replace(path)
            _REVIEWED_SESSION_DATES.add(review_key)


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
    global boss_agent, agent_team, autonomous_optimizer, _DHAN_LOT_SIZES

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

    try:
        _DHAN_LOT_SIZES = await asyncio.to_thread(fetch_official_dhan_lot_sizes)
    except Exception:
        _DHAN_LOT_SIZES = {}
    if not _DHAN_LOT_SIZES:
        _AGENT_RUNTIME_STATUS["SENSEX_OPTIONS_SCALPING"] = {
            **_AGENT_RUNTIME_STATUS["SENSEX_OPTIONS_SCALPING"],
            "status": "WAITING_FOR_CONTRACT_METADATA",
            "reason": "Official Dhan contract lot-size metadata is unavailable; no lot size is assumed",
        }
    with SessionLocal() as state_db:
        startup_now = datetime.now(timezone.utc)
        gold_entries = _restore_gold_runtime_state(state_db, startup_now)
        sensex_entries = _restore_sensex_runtime_state(state_db, startup_now)
    logger.info(
        "Restored provider-provenanced paper risk state: XAUUSD entries today=%d; Sensex entries today=%d",
        gold_entries,
        sensex_entries,
    )

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
                xau_shadow_signal = "HOLD"
                # Always advance the shared closed-bar reducer when fresh quotes
                # arrive, even outside entry hours or while a position is open.
                if xau_fresh:
                    try:
                        xau_shadow_signal = agents_map["XAUUSD"].analyze(xau_quote).value
                        _increment_daily_call("XAUUSD")
                    except Exception:
                        logger.warning("XAUUSD research strategy evaluation failed safely")
                xau_entry_window = _xau_entry_window_status()
                _AGENT_RUNTIME_STATUS["XAUUSD"] = {
                    "status": "EXPERIMENTAL_PAPER_LEARNING" if xau_fresh else "WAITING_FOR_DATA",
                    "reason": (
                        "London RSI/Bollinger is an unvalidated forward-paper hypothesis only: "
                        "fit was 86 trades and -$3,217 quote-side P&L; validation was 30 trades "
                        "and -$300. All 12 candidates were rejected; no validated winner or "
                        "profitability claim."
                        if xau_fresh else
                        "OANDA pricing is unavailable or stale; no prices or fills invented. "
                        "Session-window-independent quote collection and indicator warmup remain active."
                    ),
                    "shadow_signal": xau_shadow_signal,
                    "paper_entries_enabled": bool(settings.PAPER_TRADING_ENABLED),
                    "quantity_lots": 1.0,
                    "quantity_troy_ounces": gold_quantity_from_lots(1),
                    "currency": "USD",
                    "learner_status": "EXPERIMENTAL_PAPER_LEARNING",
                    "provenance": "OANDA provider-timestamped XAU_USD bid/ask and completed strategy bars",
                    "research_status": "NO_VALIDATED_WINNER_FORWARD_PAPER_HYPOTHESIS_ONLY",
                    "session_study": _XAU_SESSION_STUDY_STATUS,
                    "active_entry_window": xau_entry_window,
                    "strategy_parameters": _xau_strategy_parameters(),
                    "forward_paper_hypothesis_only": True,
                    "profitability_claim": False,
                    "quote_collection_independent_of_entry_session": True,
                    "live_orders_enabled": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                await asyncio.to_thread(
                    xau_observation_recorder.record, [xau_quote] if xau_fresh else []
                )

                open_trade_statuses = {}
                open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
                for existing_trade in open_trades:
                    existing_agent = (
                        existing_trade.agent.value
                        if hasattr(existing_trade.agent, "value")
                        else str(existing_trade.agent)
                    )
                    exit_status = _monitor_open_trade(
                        db, existing_trade, existing_agent
                    )
                    open_trade_statuses.setdefault(
                        (existing_agent, existing_trade.symbol), []
                    ).append(exit_status)
                    if existing_agent not in _AGENT_SYMBOLS:
                        _AGENT_RUNTIME_STATUS[existing_agent] = {
                            "status": exit_status[0],
                            "reason": exit_status[1],
                            "live_orders_enabled": False,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }

                for existing_trade in open_trades:
                    if (
                        existing_trade.status == "OPEN"
                        and existing_trade.agent == AgentName.SENSEX_OPTIONS_SCALPING
                    ):
                        underlying = indian_quotes.get("SENSEX")
                        if (
                            isinstance(underlying, dict)
                            and quote_is_fresh(underlying)
                            and quote_has_timestamp(underlying)
                        ):
                            try:
                                agents_map["SENSEX_OPTIONS_SCALPING"].process_tick(
                                    underlying.get("close", 0),
                                    underlying.get("volume", 0),
                                    underlying.get("timestamp"),
                                )
                            except Exception:
                                logger.warning("SENSEX research candle update failed safely")

                for agent_name, symbols in _AGENT_SYMBOLS.items():
                    agent = agents_map[agent_name]
                    symbol_statuses = []
                    for symbol in symbols:
                        live_data = xau_quote if agent_name == "XAUUSD" else indian_quotes.get(symbol)
                        if (agent_name, symbol) in open_trade_statuses:
                            symbol_statuses.extend(open_trade_statuses[(agent_name, symbol)])
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

                        if agent_name not in PAPER_EXPERIMENTAL_AGENTS:
                            symbol_statuses.append((
                                "BACKTEST_REQUIRED",
                                "This agent has not been approved for experimental paper entries",
                            ))
                            continue
                        if not settings.PAPER_TRADING_ENABLED:
                            symbol_statuses.append((
                                "PAPER_TRADING_DISABLED",
                                "Paper entries are disabled; live order execution is never available",
                            ))
                            continue
                        if agent_name != "XAUUSD" and not _market_hours_open(agent_name):
                            session = exchange_session_status(
                                datetime.now(pytz.timezone("Asia/Kolkata")),
                                _EXCHANGE_CALENDAR,
                            )
                            symbol_statuses.append((
                                session["status"] if session["status"] != "WEEKDAY" else "MARKET_CLOSED",
                                session.get("reason", "Outside the configured Indian exchange session"),
                            ))
                            continue
                        try:
                            signal = (
                                Signal(xau_shadow_signal)
                                if agent_name == "XAUUSD"
                                else agent.analyze(live_data)
                            )
                            if agent_name != "XAUUSD":
                                _increment_daily_call(agent_name)
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
                        if (
                            agent_name == "STOCKS"
                            and not entry_allowed_by_holding_policy(
                                "STOCKS",
                                now=datetime.now(timezone.utc),
                                holding_intent={"trade_type": signal.value},
                            )
                        ):
                            symbol_statuses.append((
                                "UNSUPPORTED_DELIVERY_SELL",
                                "Cash-equity delivery short entries are unsupported",
                            ))
                            continue
                        if agent_name == "SENSEX_OPTIONS_SCALPING":
                            entry_event_time = _provider_time(
                                live_data.get("timestamp")
                            )
                            cooldown_allowed, cooldown_reason = _sensex_cooldown_status(
                                db, entry_event_time
                            )
                            if not cooldown_allowed:
                                symbol_statuses.append((
                                    "ENTRY_COOLDOWN",
                                    cooldown_reason,
                                ))
                                continue
                            local_entry_date = entry_event_time.astimezone(
                                pytz.timezone("Asia/Kolkata")
                            ).date()
                            today_entries = sum(
                                entry_time.astimezone(
                                    pytz.timezone("Asia/Kolkata")
                                ).date() == local_entry_date
                                for _, entry_time in _sensex_paper_entries(db)
                            )
                            if today_entries >= 3:
                                symbol_statuses.append((
                                    "DAILY_ENTRY_CAP",
                                    "Maximum three accepted experimental Sensex paper entries per IST date",
                                ))
                                continue
                        if agent_name == "XAUUSD":
                            entry_time = (
                                live_data.get("provider_timestamp")
                                or live_data.get("timestamp")
                            )
                            entry_event_time = _provider_time(entry_time)
                            if entry_event_time is None:
                                symbol_statuses.append((
                                    "WAITING_FOR_DATA",
                                    "Provider event time is missing; no Gold entry or daily-cap state can be verified",
                                ))
                                continue
                            persisted_gold_entries = _gold_entries_for_utc_day(
                                db, entry_event_time.date()
                            )
                            # The database is authoritative for accepted entries;
                            # indicator warmup may reset independently at restart.
                            agent.highwin_state["last_utc_day"] = entry_event_time.date()
                            agent.highwin_state["daily_entry_count"] = len(
                                persisted_gold_entries
                            )
                            agent._daily_entry_count = len(persisted_gold_entries)
                            agent.open_trade_count = len(persisted_gold_entries)
                            if (
                                not _market_hours_open("XAUUSD", entry_event_time)
                                or not entry_allowed_by_holding_policy(
                                    "XAUUSD",
                                    now=entry_event_time,
                                    holding_intent={
                                        "trade_type": signal.value,
                                        "allow_overnight": False,
                                        "max_hold_minutes": 25,
                                    },
                                )
                                or not agent.research_entry_policy_allows(entry_time)
                            ):
                                symbol_statuses.append((
                                    "ENTRY_CUTOFF",
                                    "XAUUSD entry requires the Europe/London 08:00-17:00 local session and a full 25-minute no-overnight window",
                                ))
                                continue
                            if len(persisted_gold_entries) >= 3:
                                symbol_statuses.append((
                                    "DAILY_ENTRY_CAP",
                                    "Maximum three accepted experimental XAUUSD paper entries per UTC date",
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
                            if not entry_allowed_by_holding_policy(
                                agent_name,
                                now=datetime.now(timezone.utc),
                                holding_intent={"trade_type": signal.value},
                            ):
                                symbol_statuses.append((
                                    "ENTRY_CUTOFF",
                                    "Intraday option entries close at 15:20 Asia/Kolkata",
                                ))
                                continue
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
                            if agent_name == "SENSEX_OPTIONS_SCALPING":
                                target_points = agent.last_signal_target_points
                                sizing, sizing_reason = _size_sensex_option(
                                    option_quote,
                                    target_points,
                                    settings.ALLOCATION_SENSEX,
                                )
                                if sizing is None:
                                    symbol_statuses.append((
                                        sizing_reason or "SIZING_BLOCKED",
                                        f"No verified whole-lot size fits the ₹{settings.ALLOCATION_SENSEX:,.0f} allocation, ₹1,000 max loss and positive after-fee target gate",
                                    ))
                                    continue
                                quantity = sizing["quantity"]
                                stop_points = 25
                            else:
                                quantity = getattr(agent, "quantity", 1.0)
                                stop_points = getattr(agent, "sl_points", 50)
                                target_points = option_signal_metadata.get(
                                    "target_points",
                                    getattr(agent, "tp_points_conservative", 100),
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
                                agent.log_trade(
                                    signal.value,
                                    fill["entry_price"],
                                    timestamp=live_data.get("timestamp"),
                                )
                                if agent.trades_today:
                                    agent.trades_today[-1]["trade_id"] = trade.id
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
                            commitment = sum(
                                float(open_stock.quantity) * float(open_stock.entry_price)
                                for open_stock in db.query(Trade).filter(
                                    Trade.agent == AgentName.STOCKS,
                                    Trade.status == "OPEN",
                                ).all()
                            )
                            allocation = float(settings.ALLOCATION_STOCKS)
                            if allocation - commitment <= 0:
                                symbol_statuses.append((
                                    "ALLOCATION_EXHAUSTED",
                                    "The stock allocation is fully committed to existing open paper positions",
                                ))
                                continue
                            maximum_risk = min(
                                allocation * float(getattr(agent, "max_risk_per_trade", 0.01)),
                                allocation * float(getattr(agent, "max_loss_per_trade", 0.03)),
                            )
                            sizing = sized_stock_entry(
                                available_capital=max(0.0, allocation - commitment),
                                risk_capital=maximum_risk,
                                entry_price=entry_price,
                                stop_price=stop_loss,
                                expected_exit_price=take_profit,
                                exchange="NSE",
                                product="equity_delivery",
                                expected_net_profit_min=0,
                                side=signal.value,
                            )
                            if not sizing["accepted"]:
                                symbol_statuses.append((
                                    "FEE_AWARE_SIZING_BLOCKED",
                                    sizing["reason"],
                                ))
                                continue
                            quantity = sizing["quantity"]
                        else:
                            stop_points = getattr(agent, "stop_loss_pips", None)
                            target_points = getattr(agent, "target_pips", None)
                            quantity = gold_quantity_from_lots(1)
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
                        if agent_name == "XAUUSD" and not agent.register_research_entry(
                            live_data.get("provider_timestamp") or live_data.get("timestamp")
                        ):
                            db.delete(trade)
                            db.commit()
                            symbol_statuses.append((
                                "DAILY_ENTRY_CAP",
                                "Research accepted-entry cap rejected the paper entry",
                            ))
                            continue
                        symbol_statuses.append(("PAPER_POSITION_OPEN", f"{source} paper entry created"))

                    if symbol_statuses:
                        statuses = [item[0] for item in symbol_statuses]
                        reasons = list(dict.fromkeys(item[1] for item in symbol_statuses))
                        if "PAPER_POSITION_OPEN" in statuses:
                            status = "PAPER_POSITION_OPEN"
                        elif "TRADE_CLOSED" in statuses:
                            status = "TRADE_CLOSED"
                        elif "EXIT_PENDING_QUOTE" in statuses:
                            status = "EXIT_PENDING_QUOTE"
                        elif all(item == "WARMING_UP" for item in statuses):
                            status = "WARMING_UP"
                        elif len(set(statuses)) == 1:
                            status = statuses[0]
                        else:
                            status = "PARTIAL"
                        runtime_status = {
                            **_AGENT_RUNTIME_STATUS.get(agent_name, {}),
                            "status": status,
                            "reason": "; ".join(reasons),
                            "learner_status": (
                                "EXPERIMENTAL_PAPER_LEARNING"
                                if agent_name in PAPER_EXPERIMENTAL_AGENTS
                                else "BACKTEST_REQUIRED"
                            ),
                            "research_status": (
                                "NO_VALIDATED_WINNER_FORWARD_PAPER_HYPOTHESIS_ONLY"
                                if agent_name == "XAUUSD"
                                else "RESEARCH_NOT_VALIDATED"
                            ),
                            "risk_limitations": (
                                "Underlying breakout signals use completed SENSEX candles; paper stops/targets are "
                                "fixed option-premium points and do not map the prior-candle underlying stop"
                                if agent_name == "SENSEX_OPTIONS_SCALPING"
                                else None
                            ),
                            "provenance": (
                                "OANDA provider-timestamped bid/ask and completed strategy bars"
                                if agent_name == "XAUUSD"
                                else "Dhan exchange-timestamped underlying/option quotes"
                                if agent_name == "SENSEX_OPTIONS_SCALPING"
                                else "Not entry-enabled"
                            ),
                            "paper_entries_enabled": bool(
                                settings.PAPER_TRADING_ENABLED
                                and agent_name in PAPER_EXPERIMENTAL_AGENTS
                            ),
                            "live_orders_enabled": False,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if agent_name == "XAUUSD":
                            runtime_status.update({
                                "session_study": _XAU_SESSION_STUDY_STATUS,
                                "active_entry_window": _xau_entry_window_status(),
                                "forward_paper_hypothesis_only": True,
                                "profitability_claim": False,
                                "quote_collection_independent_of_entry_session": True,
                            })
                        _AGENT_RUNTIME_STATUS[agent_name] = runtime_status

                try:
                    _write_daily_review(db, datetime.now(timezone.utc))
                except Exception:
                    logger.warning("Closed-paper daily review could not be written safely")

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Live paper-trading cycle failed safely")
            finally:
                db.close()
            await asyncio.sleep(5)

    async def refresh_currency_reference():
        while True:
            try:
                await asyncio.to_thread(usd_inr_provider.refresh)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("USD/INR reference refresh failed; conversion stays unavailable")
            await asyncio.sleep(1800)

    async def refresh_oanda_cost_metadata():
        if oanda_cost_metadata_provider is None:
            return
        while True:
            try:
                await asyncio.to_thread(oanda_cost_metadata_provider.refresh)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("OANDA instrument cost metadata refresh failed; unknown costs remain unknown")
            await asyncio.sleep(3600)

    fx_task = asyncio.create_task(refresh_currency_reference())
    ticker_task = asyncio.create_task(live_market_feeder())
    option_chain_task = asyncio.create_task(option_chain_refresher())
    cost_metadata_task = asyncio.create_task(refresh_oanda_cost_metadata())

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
    print("Read-only provider collection started; approved Gold/Sensex experiments may enter paper trades after data, risk and holding checks. Other new entries remain backtest-blocked. Live orders disabled.", flush=True)

    yield

    if autonomous_optimizer is not None:
        autonomous_optimizer.stop()
    for task in (ticker_task, option_chain_task, optimizer_task, fx_task, cost_metadata_task):
        if task is not None:
            task.cancel()
    for task in (ticker_task, option_chain_task, optimizer_task, fx_task, cost_metadata_task):
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
    for client in (dhan_client, onda_client, usd_inr_provider):
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


def _charge_request_for_trade(trade):
    agent = trade.agent.value if hasattr(trade.agent, "value") else str(trade.agent)
    side = trade.trade_type.value if hasattr(trade.trade_type, "value") else str(trade.trade_type)
    is_gold = agent == "XAUUSD" or trade.symbol.upper() == "XAUUSD"
    if is_gold:
        return {
            "market": "XAUUSD",
            "exchange": "OANDA",
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "side": side,
            "entry_time": (
                trade.entry_data_timestamp
                or (trade.created_at.isoformat() if trade.created_at else None)
            ),
            "exit_time": (
                trade.exit_data_timestamp
                or (trade.closed_at.isoformat() if trade.closed_at else None)
            ) if trade.exit_price is not None else None,
        }
    if trade.option_strike is not None or agent in {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}:
        return {
            "market": "INDIA",
            "product": "index_options",
            "exchange": "BSE" if agent == "SENSEX_OPTIONS_SCALPING" else "NSE",
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "side": side,
        }
    if agent == "STOCKS":
        entry_day = _india_date(trade.created_at)
        relevant_exit_time = trade.closed_at if trade.status == "CLOSED" else datetime.now(pytz.timezone("Asia/Kolkata"))
        exit_day = _india_date(relevant_exit_time)
        product = "equity_intraday" if entry_day is not None and entry_day == exit_day else "equity_delivery"
    else:
        product = "equity_intraday"
    return {
        "market": "INDIA",
        "product": product,
        "exchange": "NSE",
        "symbol": trade.symbol,
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "side": side,
    }


def _charge_preview_for_trade(trade, *, gold_quote=None, gold_cost_metadata=None):
    try:
        return calculate_charges(
            _charge_request_for_trade(trade),
            gold_quote=gold_quote,
            gold_cost_metadata=gold_cost_metadata,
        )
    except ChargeInputError as exc:
        return {
            "currency": "USD" if trade.agent.value == "XAUUSD" else "INR",
            "status": "unavailable",
            "complete": False,
            "error": str(exc),
            "components": [],
            "total_additional_charges": None,
            "net_pnl": None,
            "price_pnl_before_additional_fees": None,
            "net_pnl_after_known_charges": None,
        }


def _gold_realized_fee_metrics(trades, *, gold_quote=None, gold_cost_metadata=None):
    eligible = [
        trade for trade in trades
        if (
            trade.agent == AgentName.XAUUSD
            and trade.status == "CLOSED"
            and str(trade.data_source or "").upper() == "OANDA"
            and trade.entry_data_timestamp
            and trade.exit_data_timestamp
            and _has_ordered_provider_timestamps(trade)
            and all(
                isinstance(value, (int, float))
                and math.isfinite(float(value))
                for value in (
                    trade.entry_price,
                    trade.exit_price,
                    trade.quantity,
                )
            )
        )
    ]
    gross = 0.0
    after_known = 0.0
    complete_net = 0.0
    all_complete = True
    for trade in eligible:
        try:
            result = calculate_charges(
                _charge_request_for_trade(trade),
                gold_quote=gold_quote,
                gold_cost_metadata=gold_cost_metadata,
            )
        except ChargeInputError:
            result = {"complete": False}
        raw = result.get("price_pnl_before_additional_fees")
        known_net = result.get("net_pnl_after_known_charges")
        if raw is None or known_net is None:
            all_complete = False
            continue
        gross += float(raw)
        after_known += float(known_net)
        if result.get("complete") is True and result.get("net_pnl") is not None:
            complete_net += float(result["net_pnl"])
        else:
            all_complete = False
    return {
        "total_trades": len(eligible),
        "gross_price_pnl_before_additional_fees": round(gross, 2),
        "net_pnl_after_known_charges": round(after_known, 2),
        "net_pnl": round(complete_net, 2) if all_complete else None,
        "net_pnl_status": (
            "complete_estimate"
            if all_complete
            else "unknown_additional_charges"
            if eligible
            else "no_closed_trades"
        ),
        "fees_complete": all_complete,
        "pnl_basis": "Provider-side execution price P&L before additional OANDA costs",
    }


@app.post("/charges/calculate")
async def post_charges_calculate(payload: dict = Body(...)):
    try:
        return calculate_charges(
            payload,
            gold_quote=_gold_charge_quote(),
            gold_cost_metadata=_gold_cost_metadata(),
        )
    except ChargeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/charges/rules")
async def get_charges_rules():
    metadata_snapshot = _gold_cost_metadata()
    result = get_charge_rules(
        gold_quote=_gold_charge_quote(),
        gold_cost_metadata=metadata_snapshot,
    )
    cost_status = result.get("gold", {}).get("cost_metadata", {})
    if isinstance(metadata_snapshot, dict):
        provider_reason = metadata_snapshot.get("reason")
        cost_status["provider_status"] = (
            str(metadata_snapshot.get("status"))
            if metadata_snapshot.get("status") is not None
            else "unknown"
        )
        if cost_status.get("as_of") is None and isinstance(
            metadata_snapshot.get("as_of"), str
        ):
            cost_status["as_of"] = metadata_snapshot["as_of"]
        for field in ("age_seconds", "max_age_seconds", "refresh_warning"):
            value = metadata_snapshot.get(field)
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                cost_status[field] = value
        if isinstance(provider_reason, str) and len(provider_reason) <= 100:
            cost_status["reason"] = provider_reason
        elif metadata_snapshot.get("status") == "unavailable":
            cost_status["reason"] = "OANDA cost metadata is unavailable"
    else:
        cost_status["provider_status"] = "unavailable"
        cost_status["reason"] = "OANDA cost metadata provider is not initialized"
    quote = result.get("gold", {}).get("quote")
    if quote:
        midpoint = (quote["bid"] + quote["ask"]) / 2
        quote["price"] = midpoint
        quote["mid"] = midpoint
    return result


@app.get("/charges/trades")
async def get_charges_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(500).all()
    quote = _gold_charge_quote()
    metadata = _gold_cost_metadata()
    # Keep the module serializer's stable tab contract, then override its
    # stock product estimate using actual same-day versus later-held dates.
    result = get_charge_trades(
        trades,
        gold_quote=quote,
        gold_cost_metadata=metadata,
    )
    for serialized, trade in zip(result["trades"], trades):
        serialized["charges"] = _charge_preview_for_trade(
            trade,
            gold_quote=quote,
            gold_cost_metadata=metadata,
        )
    return result


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
    unpriced_currencies = set()
    for currency in realized_pnl_by_currency:
        currency_trades = [
            trade
            for trade in trades
            if ("USD" if trade.agent.value == "XAUUSD" else "INR") == currency
        ]
        realized_pnl_by_currency[currency] = verified_closed_trade_metrics(
            currency_trades
        )["total_pnl"]
    gold_fee_metrics = _gold_realized_fee_metrics(
        trades,
        gold_quote=_gold_charge_quote(),
        gold_cost_metadata=_gold_cost_metadata(),
    )
    unknown_gold_realized_costs = (
        gold_fee_metrics["total_trades"] > 0
        and not gold_fee_metrics["fees_complete"]
    )
    if not unknown_gold_realized_costs:
        realized_pnl_by_currency["USD"] = gold_fee_metrics["net_pnl"] or 0.0
    else:
        # The internal conversion helper requires a numeric input. This zero is
        # never serialized as a P&L; affected public subtotals are nulled below.
        realized_pnl_by_currency["USD"] = 0.0
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
            unpriced_currencies.add(currency)
        positions[str(trade.id)] = {
            "symbol": trade.symbol,
            "agent": trade.agent.value,
            "currency": currency,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "current_price": current_price,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_basis": (
                "Provider-side marked price P&L before additional OANDA costs"
                if currency == "USD"
                else "Provider-side marked price P&L before charge preview"
            ),
            "final_net_pnl": None,
            "data_source": trade.data_source,
            **(gold_lot_display(trade.quantity) if currency == "USD" else {}),
        }
    consolidation = consolidate_pnl_currencies(
        realized_inr=realized_pnl_by_currency["INR"],
        realized_usd=realized_pnl_by_currency["USD"],
        unrealized_inr=unrealized_pnl_by_currency["INR"],
        unrealized_usd=unrealized_pnl_by_currency["USD"],
        fx_snapshot=usd_inr_provider.get_snapshot(),
    )
    if unknown_gold_realized_costs:
        consolidation["realized_pnl_inr"] = None
        consolidation["total_pnl_inr"] = None
        consolidation["pnl_by_currency"]["realized"]["USD"] = None
        consolidation["pnl_by_currency"]["total"]["USD"] = None
        consolidation["pnl_by_currency"]["total"]["INR"] = None
    realized_pnl = consolidation["realized_pnl_inr"]
    unrealized_pnl = (
        consolidation["unrealized_pnl_inr"] if not unpriced_positions else None
    )
    total_pnl = consolidation["total_pnl_inr"] if not unpriced_positions else None
    if unpriced_positions:
        consolidation["total_pnl_inr"] = None
        consolidation["unrealized_pnl_inr"] = None
        consolidation["pnl_by_currency"]["total"]["INR"] = None
        for currency in unpriced_currencies:
            consolidation["pnl_by_currency"]["unrealized"][currency] = None
            if currency == "USD":
                consolidation["pnl_by_currency"]["total"]["USD"] = None
    total_pnl_by_currency = {
        currency: None if currency in unpriced_currencies else round(
            realized_pnl_by_currency[currency]
            + unrealized_pnl_by_currency[currency],
            2,
        )
        for currency in realized_pnl_by_currency
    }
    if unknown_gold_realized_costs:
        realized_pnl_by_currency["USD"] = None
        total_pnl_by_currency["USD"] = None
    agent_performance = {}
    for agent_name in agents_map:
        agent_trades = [trade for trade in trades if trade.agent == AgentName[agent_name]]
        agent_performance[agent_name] = {
            **verified_closed_trade_metrics(agent_trades),
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "status": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("status", "WAITING_FOR_DATA"),
            "reason": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("reason", ""),
        }
        if agent_name == "XAUUSD":
            agent_performance[agent_name].update(gold_fee_metrics)
            if unknown_gold_realized_costs:
                agent_performance[agent_name]["total_trades"] = gold_fee_metrics["total_trades"]
                agent_performance[agent_name]["total_pnl"] = None
                agent_performance[agent_name]["winning_trades"] = None
                agent_performance[agent_name]["losing_trades"] = None
                agent_performance[agent_name]["win_rate"] = None
                agent_performance[agent_name]["confidence"] = None
    portfolio_state.update({
        "total_pnl": total_pnl,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "net_worth": round(settings.INITIAL_CAPITAL + total_pnl, 2) if total_pnl is not None else None,
        "currency": "INR",
        "realized_pnl_by_currency": realized_pnl_by_currency,
        "unrealized_pnl_by_currency": {
            currency: None if currency in unpriced_currencies else round(value, 2)
            for currency, value in unrealized_pnl_by_currency.items()
        },
        "total_pnl_by_currency": total_pnl_by_currency,
        "pnl_by_currency": consolidation["pnl_by_currency"],
        "usd_inr_conversion": consolidation["usd_inr_conversion"],
        "consolidation_note": "Individual XAUUSD P&L is USD; portfolio INR totals use the timestamped ECB daily USD/INR reference rate, not an executable FX quote.",
        "positions": positions,
        "active_trades": len(open_trades),
        "unpriced_positions": unpriced_positions,
        "valuation_complete": unpriced_positions == 0 and total_pnl is not None,
        "valuation_note": "Missing marks or required FX leave consolidated totals unavailable; no partial sum is presented as complete.",
        "agent_performance": agent_performance,
        "mode": "PAPER",
        "live_orders_enabled": False,
        "metrics_basis": closed_metrics["metrics_basis"],
        "gold_realized_performance": gold_fee_metrics,
        "realized_net_complete": not unknown_gold_realized_costs,
        "pnl_note": (
            "Gold performance shows provider-side gross price P&L before additional fees; "
            "unknown OANDA costs leave final net P&L unavailable."
        ),
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
            "pnl_basis": (
                "Current provider-side marked price P&L before additional OANDA costs"
                if trade.agent.value == "XAUUSD"
                else "Current provider-side marked price P&L before charge preview"
            ),
            "final_net_pnl": None,
            "pnlPercent": (
                round(pnl / abs(trade.entry_price * trade.quantity) * 100, 2)
                if pnl is not None and trade.entry_price and trade.quantity
                else None
            ),
            "data_source": trade.data_source,
            **(gold_lot_display(trade.quantity) if trade.agent.value == "XAUUSD" else {}),
        })
    return {"positions": positions}

@app.get("/agents/performance")
async def get_agents_performance(db: Session = Depends(get_db)):
    result = {}

    for agent_name in agents_map.keys():
        trades = db.query(Trade).filter(Trade.agent == AgentName[agent_name]).all()
        metrics = verified_closed_trade_metrics(trades)
        gold_fee_metrics = None
        if agent_name == "XAUUSD":
            gold_fee_metrics = _gold_realized_fee_metrics(
                trades,
                gold_quote=_gold_charge_quote(),
                gold_cost_metadata=_gold_cost_metadata(),
            )
            metrics.update(gold_fee_metrics)
            if gold_fee_metrics["total_trades"] > 0 and not gold_fee_metrics["fees_complete"]:
                metrics.update({
                    "total_trades": gold_fee_metrics["total_trades"],
                    "total_pnl": None,
                    "winning_trades": None,
                    "losing_trades": None,
                    "win_rate": None,
                    "confidence": None,
                })
        runtime = _AGENT_RUNTIME_STATUS.get(agent_name, {})
        result[agent_name] = {
            **metrics,
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "confidence": (
                round(metrics["win_rate"] / 100, 4)
                if metrics.get("total_trades") and metrics.get("win_rate") is not None
                else None if agent_name == "XAUUSD" and metrics.get("net_pnl") is None
                else 0.0
            ),
            "status": runtime.get("status", "WAITING_FOR_DATA"),
            "reason": runtime.get("reason", "Waiting for live market data"),
            "risk_limitations": runtime.get("risk_limitations"),
            "research_status": runtime.get("research_status"),
            "active_entry_window": (
                _xau_entry_window_status()
                if agent_name == "XAUUSD"
                else runtime.get("active_entry_window")
            ),
            "session_study": runtime.get("session_study"),
            "forward_paper_hypothesis_only": runtime.get(
                "forward_paper_hypothesis_only", False
            ),
            "profitability_claim": runtime.get("profitability_claim", False),
            "quote_collection_independent_of_entry_session": runtime.get(
                "quote_collection_independent_of_entry_session", False
            ),
            "strategy_parameters": runtime.get("strategy_parameters"),
            "analyzing": runtime.get("status") in {"RUNNING", "PAPER_POSITION_OPEN"},
            "target_win_rate": 90,
            "target_is_aspirational": True,
            "guaranteed": False,
            **(
                {
                    "pnl_basis": gold_fee_metrics["pnl_basis"],
                    "net_pnl_after_known_charges": gold_fee_metrics["net_pnl_after_known_charges"],
                    "net_pnl_status": gold_fee_metrics["net_pnl_status"],
                    "fees_complete": gold_fee_metrics["fees_complete"],
                    "research_status": runtime.get("research_status"),
                }
                if gold_fee_metrics is not None else {}
            ),
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
    gold_quote = _gold_charge_quote()
    gold_cost_metadata = _gold_cost_metadata()
    for t in trades:
        contract = parse_option_contract(t.option_strike)
        current_price = t.exit_price if t.status == "CLOSED" else None
        if t.status == "OPEN":
            current_price, _ = _cached_trade_mark(t)
        pnl = t.pnl
        if t.status == "OPEN" and current_price is None:
            pnl = None
        if t.status == "OPEN" and current_price is not None:
            if t.trade_type.value == "BUY":
                pnl = (current_price - t.entry_price) * t.quantity
            else:
                pnl = (t.entry_price - current_price) * t.quantity
        pnl_pct = (
            (pnl / (t.entry_price * t.quantity)) * 100
            if pnl is not None and t.entry_price and t.quantity
            else None
        )
        currency = "USD" if t.agent.value == "XAUUSD" else "INR"
        charges = _charge_preview_for_trade(
            t,
            gold_quote=gold_quote,
            gold_cost_metadata=gold_cost_metadata,
        )
        gross_price_pnl = charges.get("price_pnl_before_additional_fees")
        if t.status == "OPEN" and current_price is not None:
            gross_price_pnl = pnl

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
            "gross_price_pnl_before_additional_fees": gross_price_pnl,
            "net_pnl_after_known_charges": charges.get("net_pnl_after_known_charges"),
            "net_pnl_preview": charges.get("net_pnl"),
            "fees_complete": charges.get("complete"),
            "pnl_basis": (
                "Provider-side execution price P&L before additional OANDA costs"
                if currency == "USD" and t.status == "CLOSED"
                else "Current provider-side marked price P&L before additional OANDA costs"
                if currency == "USD"
                else "Stored/marked trade P&L; fee preview is reported separately"
            ),
            "charges": charges,
            "pnl_percent": pnl_pct,
            "currency": currency,
            **(gold_lot_display(t.quantity) if currency == "USD" else {}),
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
    all_agent_trades = db.query(Trade).filter(Trade.agent == AgentName[agent]).all()
    trades = [
        trade
        for trade in all_agent_trades
        if is_verified_closed_trade(trade)
    ]
    metrics = verified_closed_trade_metrics(trades)
    gold_metrics = None
    if agent == "XAUUSD":
        gold_metrics = _gold_realized_fee_metrics(
            all_agent_trades,
            gold_quote=_gold_charge_quote(),
            gold_cost_metadata=_gold_cost_metadata(),
        )
        metrics.update(gold_metrics)
        if gold_metrics["total_trades"] and not gold_metrics["fees_complete"]:
            metrics.update({
                "total_trades": gold_metrics["total_trades"],
                "total_pnl": None,
                "winning_trades": None,
                "losing_trades": None,
                "win_rate": None,
            })

    return {
        "agent": agent,
        "analysis": {
            **metrics,
            "currency": "USD" if agent == "XAUUSD" else "INR",
            "pnl_basis": gold_metrics["pnl_basis"] if gold_metrics else metrics.get("metrics_basis"),
            "net_pnl_after_known_charges": (
                gold_metrics["net_pnl_after_known_charges"] if gold_metrics else None
            ),
            "net_pnl_status": (
                gold_metrics["net_pnl_status"] if gold_metrics else "stored_trade_pnl"
            ),
            "status": "measurement_only",
            "strategy_recommendations": [],
            "reason": (
                "Strategy recommendations require genuine historical market data "
                "and validated backtests."
            ),
        },
        "confidence": (
            round(metrics["win_rate"] / 100, 4)
            if metrics["total_trades"] and metrics.get("win_rate") is not None
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
        metrics = verified_closed_trade_metrics(trades)
        if agent_name == "XAUUSD":
            gold_metrics = _gold_realized_fee_metrics(
                trades,
                gold_quote=_gold_charge_quote(),
                gold_cost_metadata=_gold_cost_metadata(),
            )
            metrics.update(gold_metrics)
            if gold_metrics["total_trades"] and not gold_metrics["fees_complete"]:
                metrics.update({
                    "total_trades": gold_metrics["total_trades"],
                    "total_pnl": None,
                    "winning_trades": None,
                    "losing_trades": None,
                    "win_rate": None,
                })
        summary[agent_name] = {
            **metrics,
            "currency": "USD" if agent_name == "XAUUSD" else "INR",
            "status": _AGENT_RUNTIME_STATUS.get(agent_name, {}).get("status", "WAITING_FOR_DATA"),
        }
        if agent_name == "XAUUSD":
            runtime = _AGENT_RUNTIME_STATUS.get(agent_name, {})
            summary[agent_name].update({
                "research_status": runtime.get("research_status"),
                "active_entry_window": _xau_entry_window_status(),
                "session_study": runtime.get("session_study"),
                "forward_paper_hypothesis_only": runtime.get(
                    "forward_paper_hypothesis_only", True
                ),
                "profitability_claim": runtime.get("profitability_claim", False),
                "quote_collection_independent_of_entry_session": runtime.get(
                    "quote_collection_independent_of_entry_session", True
                ),
                "strategy_parameters": runtime.get("strategy_parameters"),
            })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": summary,
        "target_win_rate": 90,
        "target_is_aspirational": True,
        "guaranteed": False,
        "metrics_basis": "closed live-provider-price paper trades only",
        "pnl_note": "XAUUSD gross price P&L is before additional OANDA costs; final net remains unavailable while any costs are unknown.",
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
    report_path = evidence_dir / (
        "xauusd_backtest.json" if agent == "XAUUSD" else "latest_backtests.json"
    )
    if report_path.exists():
        try:
            from backtest.comparison_report import load_agent_evaluation
            return {
                **load_agent_evaluation(evidence_dir, agent),
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

@app.get("/backtest-review")
async def get_backtest_review():
    """Research evidence stays separate from paper performance endpoints."""
    from backtest.comparison_report import build_comparison
    try:
        return build_comparison(evidence_dir)
    except (OSError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="All-agent backtest evidence is unavailable")

@app.get("/data/market-snapshot")
async def get_market_snapshot():
    snapshot = dhan_client.get_market_snapshot()
    prices = snapshot.setdefault("prices", {})
    cached_xau = onda_client.get_cached_quote("XAUUSD")
    if isinstance(cached_xau, dict) and quote_is_fresh(cached_xau):
        prices["XAUUSD"] = dict(cached_xau)
    return snapshot

@app.get("/data/gold")
async def get_gold_market():
    """Expose only the cached OANDA spot-gold quote; no request or price fallback."""
    quote = getattr(onda_client, "latest_prices", {}).get("XAUUSD")
    usable = (
        isinstance(quote, dict)
        and quote.get("source") == "OANDA"
        and quote.get("instrument") == "XAU_USD"
        and quote_is_fresh(quote)
        and quote_has_timestamp(quote)
    )
    result = {
        "symbol": "XAUUSD",
        "provider_instrument": "XAU_USD",
        "chart_symbol": "OANDA:XAUUSD",
        "name": "Gold Spot / U.S. Dollar",
        "source": "OANDA",
        "currency": "USD",
        "price_unit": "USD_per_troy_ounce",
        **gold_lot_display(gold_quantity_from_lots(1)),
        "status": "available" if usable else "unavailable",
        "bid": quote.get("bid") if usable else None,
        "ask": quote.get("ask") if usable else None,
        "provider_timestamp": quote.get("timestamp") if usable else None,
        "environment": quote.get("environment") if isinstance(quote, dict) else None,
        "market_open": (
            quote.get("tradeable") if usable and isinstance(quote.get("tradeable"), bool) else None
        ),
        "execution_note": "Buy at ask and sell at bid; chart snapshots are not fixed execution prices.",
        "paper_entries_enabled": bool(
            settings.PAPER_TRADING_ENABLED and "XAUUSD" in PAPER_EXPERIMENTAL_AGENTS
        ),
        "entry_window": _xau_entry_window_status(),
        "research_status": _AGENT_RUNTIME_STATUS["XAUUSD"]["research_status"],
        "forward_paper_hypothesis_only": True,
        "live_orders_enabled": False,
    }
    return result


@app.get("/market/status")
async def get_market_status():
    dhan_status, oanda_status = _provider_status()
    return {
        "mode": "PAPER",
        "live_orders_enabled": False,
        "paper_trading_enabled": bool(settings.PAPER_TRADING_ENABLED),
        "paper_trading_requested": bool(settings.PAPER_TRADING_ENABLED),
        "entry_gate": (
            "EXPERIMENTAL_PAPER_WITH_DATA_RISK_AND_HOLDING_GATES"
            if settings.PAPER_TRADING_ENABLED
            else "PAPER_DISABLED"
        ),
        "experimental_paper_agents": sorted(PAPER_EXPERIMENTAL_AGENTS),
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
            name: {
                **status,
                "paper_entries_enabled": bool(
                    settings.PAPER_TRADING_ENABLED and name in PAPER_EXPERIMENTAL_AGENTS
                ),
                "live_orders_enabled": False,
            }
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
