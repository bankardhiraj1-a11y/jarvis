"""Isolated synthetic adapter fixtures. Never connect to the trading database."""

import ast
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base
from models import Trade
from trading.manual_paper_orders import (
    create_manual_order, process_manual_orders, manual_holding_decision,
)


NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("market,symbol,side,option_type,segment", [
    ("STOCKS", "RELIANCE", "BUY", None, "NSE_EQ"),
    ("STOCKS", "RELIANCE", "SELL", None, "NSE_EQ"),
    ("OPTIONS", "NIFTY", "BUY", "CE", "NSE_FNO"),
    ("OPTIONS", "NIFTY", "BUY", "PE", "NSE_FNO"),
    ("OPTIONS", "SENSEX", "BUY", "CE", "BSE_FNO"),
    ("OPTIONS", "SENSEX", "BUY", "PE", "BSE_FNO"),
])
def test_real_adapter_shape_reaches_manual_processor(market, symbol, side, option_type, segment, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            current = NOW + timedelta(seconds=1)
            return current.astimezone(tz) if tz else current.replace(tzinfo=None)

    monkeypatch.setattr("trading.live_paper.datetime", Clock)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        payload = {
            "market": market, "symbol": symbol, "side": side,
            "order_type": "MARKET", "stop_loss": 90 if side == "BUY" else 110,
            "take_profit": 125 if side == "BUY" else 75,
            "quantity": 10,
        }
        if option_type:
            payload.update({
                "quantity_lots": 1, "option_type": option_type,
                "strike": 25000 if symbol == "NIFTY" else 80000,
                "expiry": "2026-10-08",
            })
        order = create_manual_order(db, payload, now=NOW)
        raw = {
            "symbol": symbol, "bid": 100, "ask": 100.5, "close": 100.25,
            "timestamp": (NOW + timedelta(seconds=1)).isoformat(),
            "security_id": "12345", "segment": segment,
        }
        if option_type:
            raw.update({key: payload[key] for key in ("strike", "option_type", "expiry")})
        assert "source" not in raw and "contract" not in raw
        source = ast.parse(Path(__file__).with_name("main.py").read_text())
        names = {"_manual_agent_name", "_manual_order_quote", "_verified_option_lot_size"}
        functions = [
            node for node in source.body
            if isinstance(node, ast.FunctionDef) and node.name in names
        ]
        namespace = {
            "dhan_client": SimpleNamespace(get_option_quote=lambda *args: dict(raw)),
            "_fresh_indian_quote": lambda _: dict(raw),
            "_market_hours_open": lambda _: True,
            "_DHAN_LOT_SIZES": {"12345": 20},
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "adapter-fixture", "exec"), namespace)
        result = process_manual_orders(
            db, namespace["_manual_order_quote"], now=NOW + timedelta(seconds=1),
            available_capital=lambda _: 100000,
        )
        assert result["filled_trade_ids"], result["skipped"]
        trade = db.query(Trade).one()
        assert trade.entry_price == (100.5 if side == "BUY" else 100)
        assert trade.data_source == "DHAN"
        assert trade.quantity == (20 if option_type else 10)
        assert (trade.option_strike is not None) == bool(option_type)
        holding = manual_holding_decision(order, NOW, NOW + timedelta(minutes=21))
        assert holding["due"], "Manual Indian positions must not use cash-delivery holding policy"
    engine.dispose()