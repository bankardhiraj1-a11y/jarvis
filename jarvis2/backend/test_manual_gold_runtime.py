"""Synthetic isolated fixtures only; these never write to the trading database."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base
from models import Trade
from trading.holding_policy import holding_exit_decision
from trading.paper_limit_orders import (
    create_order, manual_order_for_trade, process_pending_orders,
)


NOW = datetime(2026, 10, 1, 17, 20, tzinfo=timezone.utc)


@pytest.fixture
def manual_monitor():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        order = create_order(db, {
            "client_order_id": "isolated-unit-fixture",
            "symbol": "XAUUSD", "side": "SELL",
            "manual_order": True, "session_override": True,
            "limit_price": 4177, "stop_loss": 4187,
            "take_profit": 4161, "take_profit_2": 4151,
            "quantity_troy_ounces": 15,
        }, now=NOW - timedelta(minutes=2))
        quote = {
            "source": "OANDA", "environment": "practice",
            "tradeable": True, "bid": 4177.5, "ask": 4177.8,
            "close": 4177.65,
            "timestamp": (NOW - timedelta(minutes=1)).isoformat(),
        }
        result = process_pending_orders(
            db, quote, now=NOW - timedelta(minutes=1), accepted_entries_today=0,
        )
        assert result["filled_order_ids"] == [order.id]
        legs = db.query(Trade).order_by(Trade.id).all()
        clock = {"now": NOW, "price": 4175.0, "fresh": True}
        closed = []

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock["now"].astimezone(tz) if tz else clock["now"].replace(tzinfo=None)

            @classmethod
            def utcnow(cls):
                return clock["now"].replace(tzinfo=None)

        source = ast.parse(Path(__file__).with_name("main.py").read_text())
        monitor = next(
            node for node in source.body
            if isinstance(node, ast.FunctionDef) and node.name == "_monitor_open_trade"
        )
        namespace = {
            "datetime": Clock, "timezone": timezone, "timedelta": timedelta,
            "pytz": pytz,
            "Trade": Trade, "AgentName": __import__("models").AgentName,
            "manual_order_for_trade": manual_order_for_trade,
            "general_manual_order_for_trade": lambda _db, _trade_id: None,
            "_provider_time": lambda value: datetime.fromisoformat(str(value).replace("Z", "+00:00")),
            "holding_exit_decision": holding_exit_decision,
            "agents_map": {"XAUUSD": SimpleNamespace(
                should_force_research_time_exit=lambda _: True,
                mark_research_position_closed=lambda: closed.append(True),
            )},
            "_cached_trade_mark": lambda _: (clock["price"], {
                "timestamp": clock["now"].isoformat(),
            }),
            "quote_is_fresh": lambda _: clock["fresh"],
            "quote_has_timestamp": lambda _: True,
            "calculate_net_pnl": lambda entry, exit, qty, side, symbol, **_: (entry - exit) * qty,
        }
        exec(compile(ast.Module(body=[monitor], type_ignores=[]), "monitor-fixture", "exec"), namespace)
        yield db, legs, namespace["_monitor_open_trade"], clock, closed
    engine.dispose()


def test_manual_legs_do_not_exit_just_because_london_is_closed(manual_monitor):
    db, legs, monitor, _, closed = manual_monitor
    assert monitor(db, legs[0], "XAUUSD")[0] == "PAPER_POSITION_OPEN"
    assert monitor(db, legs[1], "XAUUSD")[0] == "PAPER_POSITION_OPEN"
    assert closed == []


def test_tp1_and_tp2_exit_separately_at_executable_quotes(manual_monitor):
    db, legs, monitor, clock, closed = manual_monitor
    clock["price"] = 4161.0
    assert monitor(db, legs[0], "XAUUSD")[0] == "TRADE_CLOSED"
    assert monitor(db, legs[1], "XAUUSD")[0] == "PAPER_POSITION_OPEN"
    assert closed == []
    clock["price"] = 4150.8
    assert monitor(db, legs[1], "XAUUSD")[0] == "TRADE_CLOSED"
    assert closed == [True]
    assert legs[1].exit_price == 4150.8


def test_manual_maximum_hold_still_closes_without_target(manual_monitor):
    db, legs, monitor, clock, _ = manual_monitor
    clock["now"] = NOW + timedelta(minutes=25)
    assert monitor(db, legs[0], "XAUUSD")[0] == "TRADE_CLOSED"
    assert legs[0].exit_price == 4175.0


def test_overdue_manual_exit_waits_for_real_quote(manual_monitor):
    db, legs, monitor, clock, _ = manual_monitor
    clock["now"] = NOW + timedelta(minutes=25)
    clock["fresh"] = False
    assert monitor(db, legs[0], "XAUUSD")[0] == "EXIT_PENDING_QUOTE"
    assert legs[0].status == "OPEN"
    assert legs[0].exit_price is None


def test_both_manual_legs_use_the_common_stop(manual_monitor):
    db, legs, monitor, clock, closed = manual_monitor
    clock["price"] = 4187.4
    for leg in legs:
        assert monitor(db, leg, "XAUUSD")[0] == "TRADE_CLOSED"
        assert leg.exit_price == 4187.4
    assert closed == [True]


def test_manual_daily_cap_uses_provider_day_at_midnight():
    source = ast.parse(Path(__file__).with_name("main.py").read_text())
    helper = next(
        node for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name == "_manual_gold_entry_day"
    )
    namespace = {
        "_provider_time": lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value else None,
    }
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "entry-day-fixture", "exec"), namespace)
    assert namespace["_manual_gold_entry_day"](
        {"timestamp": "2026-10-01T23:59:58Z"},
        datetime(2026, 10, 2, 0, 0, 1, tzinfo=timezone.utc),
    ).isoformat() == "2026-10-01"