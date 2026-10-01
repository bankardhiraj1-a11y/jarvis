"""Synthetic software fixtures only; no persisted trades or performance evidence."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

# backend/conftest.py sets DATABASE_URL to a process-scoped TemporaryDirectory
# before pytest imports test modules, so main's import-time schema setup cannot
# touch the user's paper-trading SQLite database.
import main
from models import AgentName, TradeType


def open_gold():
    return SimpleNamespace(
        id=123, agent=AgentName.XAUUSD, symbol="XAUUSD",
        trade_type=TradeType.BUY, quantity=100.0, entry_price=4100.0,
        status="OPEN", data_source="OANDA", pnl=None,
    )


def portfolio_with(trades, rate, mark):
    db = SimpleNamespace(query=lambda *args: SimpleNamespace(all=lambda: trades))
    fx = {"status": "available", "rate": rate, "source": "synthetic_test_fixture"} if rate else {"status": "unavailable", "rate": None}
    with patch.object(main.usd_inr_provider, "get_snapshot", return_value=fx):
        with patch.object(main, "_cached_trade_mark", return_value=(mark, "fixture")):
            return dict(asyncio.run(main.get_portfolio(db)))


def test_100_ounces_stay_usd_per_trade_but_total_uses_inr():
    result = portfolio_with([open_gold()], 95, 4101)
    position = result["positions"]["123"]
    assert position["currency"] == "USD"
    assert position["quantity_lots"] == 1
    assert position["quantity_troy_ounces"] == 100
    assert position["pnl"] == 100
    assert result["total_pnl"] == 9500
    assert result["currency"] == "INR"


def test_required_missing_fx_is_not_zero_or_inr_only_sum():
    result = portfolio_with([open_gold()], None, 4101)
    assert result["total_pnl"] is None
    assert result["net_worth"] is None
    assert result["positions"]["123"]["pnl"] == 100
    assert result["valuation_complete"] is False


def test_missing_gold_mark_is_not_partial_known_total():
    result = portfolio_with([open_gold()], 95, None)
    assert result["total_pnl"] is None
    assert result["positions"]["123"]["pnl"] is None
    assert result["unrealized_pnl_by_currency"]["USD"] is None
    assert result["valuation_complete"] is False