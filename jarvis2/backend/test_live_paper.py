from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect, text

from agents.options import OptionsAgent
from agents.stocks import StocksAgent
from trading.live_paper import (
    build_long_option_paper_entry,
    encode_option_contract,
    ensure_trade_provenance_columns,
    option_entry_and_exit_prices,
    parse_option_contract,
    provider_side_price,
    quote_is_fresh,
    verified_closed_trade_metrics,
)


def _quote(**overrides):
    quote = {
        "status": "ok",
        "close": 100.0,
        "last_price": 100.0,
        "bid": 99.0,
        "ask": 101.0,
        "age_seconds": 1.0,
        "stale": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    quote.update(overrides)
    return quote


def test_freshness_requires_recent_real_quote():
    assert quote_is_fresh(_quote())
    assert not quote_is_fresh(_quote(stale=True))
    assert not quote_is_fresh(_quote(age_seconds=16.0))
    assert not quote_is_fresh(_quote(close=0.0))
    assert not quote_is_fresh({"close": 100.0})


def test_option_paper_fill_uses_ask_to_enter_and_bid_to_exit():
    assert option_entry_and_exit_prices(_quote()) == (101.0, 99.0)
    assert option_entry_and_exit_prices(_quote(ask=98.0)) is None
    assert option_entry_and_exit_prices(_quote(bid=None)) is None
    assert option_entry_and_exit_prices(_quote(stale=True)) is None
    assert option_entry_and_exit_prices(
        {key: value for key, value in _quote().items() if key != "timestamp"}
    ) is None


def test_provider_execution_price_uses_executable_bid_ask_side():
    quote = _quote(bid=99.0, ask=101.0)
    assert provider_side_price(quote, "BUY") == 101.0
    assert provider_side_price(quote, "SELL") == 99.0
    assert provider_side_price(_quote(status="live"), "BUY") == 101.0
    assert provider_side_price(_quote(bid=None), "SELL") is None
    assert provider_side_price(_quote(stale=True), "BUY") is None


def test_bearish_signal_buys_the_real_put_quote_in_paper_mode():
    put = _quote(
        option_type="PE",
        strike=49500,
        expiry="2026-10-08",
        timestamp="2026-10-08T10:00:00+00:00",
    )
    trade = build_long_option_paper_entry("SELL", put, 1000, 25, 12)
    assert trade["trade_type"] == "BUY"
    assert trade["signal"] == "SELL"
    assert trade["option_strike"] == "49500 PE 2026-10-08"
    assert trade["entry_price"] == 101.0
    assert trade["stop_loss"] == 76.0
    assert trade["take_profit"] == 113.0
    assert trade["data_source"] == "DHAN"
    assert build_long_option_paper_entry("BUY", put, 1000, 25, 12) is None


def test_option_contract_round_trip_fits_existing_column():
    encoded = encode_option_contract(49500.0, "CE", "2026-10-08")
    assert encoded == "49500 CE 2026-10-08"
    assert len(encoded) <= 20
    assert parse_option_contract(encoded) == {
        "strike": 49500.0,
        "option_type": "CE",
        "expiry": "2026-10-08",
    }
    assert parse_option_contract("legacy-option") is None
    with pytest.raises(ValueError):
        encode_option_contract(49500, "CALL", "2026-10-08")


def test_metrics_exclude_open_legacy_and_non_provider_trades():
    now = datetime.now(timezone.utc)
    closed = SimpleNamespace(
        status="CLOSED",
        data_source="DHAN",
        entry_data_timestamp=(now - timedelta(minutes=5)).isoformat(),
        exit_data_timestamp=(now - timedelta(minutes=1)).isoformat(),
        closed_at=now,
        pnl=20.0,
        entry_price=100.0,
        exit_price=110.0,
        quantity=1.0,
    )
    open_trade = SimpleNamespace(**{**closed.__dict__, "status": "OPEN"})
    legacy_trade = SimpleNamespace(**{**closed.__dict__, "data_source": None})
    failed_source = SimpleNamespace(**{**closed.__dict__, "data_source": "YFINANCE"})
    missing_exit = SimpleNamespace(**{**closed.__dict__, "exit_data_timestamp": None})
    loss = SimpleNamespace(**{**closed.__dict__, "pnl": -5.0})
    metrics = verified_closed_trade_metrics(
        [closed, open_trade, legacy_trade, failed_source, missing_exit, loss]
    )
    assert metrics["total_trades"] == 2
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate"] == 50.0
    assert metrics["total_pnl"] == 15.0


def test_existing_trade_table_gets_nullable_provenance_columns():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE trades (id INTEGER PRIMARY KEY)"))
    ensure_trade_provenance_columns(engine)
    ensure_trade_provenance_columns(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("trades")}
    assert {"data_source", "entry_data_timestamp", "exit_data_timestamp"} <= columns


def test_stock_strategy_keeps_live_daily_candles_per_symbol():
    agent = StocksAgent()
    agent.analyze({"symbol": "RELIANCE", "close": 2500, "volume": 10})
    agent.analyze({"symbol": "TCS", "close": 4000, "volume": 20})
    reliance = agent._symbol_states["RELIANCE"]["current_candle"]
    tcs = agent._symbol_states["TCS"]["current_candle"]
    assert reliance["open"] == 2500
    assert tcs["open"] == 4000
    assert agent.get_history_status("RELIANCE")["completed_bars"] == 0
    assert agent.get_history_status("TCS")["completed_bars"] == 0


def test_options_strategy_keeps_15_minute_history_per_underlying():
    agent = OptionsAgent()
    agent.analyze({"symbol": "NIFTY", "close": 25000, "volume": 100})
    agent.analyze({"symbol": "BANKNIFTY", "close": 50000, "volume": 200})
    nifty = agent._symbol_states["NIFTY"]["current_candle_15m"]
    banknifty = agent._symbol_states["BANKNIFTY"]["current_candle_15m"]
    assert nifty["open"] == 25000
    assert banknifty["open"] == 50000
    assert agent.get_history_status("NIFTY")["completed_bars"] == 0
    assert agent.get_history_status("BANKNIFTY")["completed_bars"] == 0