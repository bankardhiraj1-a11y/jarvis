"""Deterministic candle/replay regression tests; these are not trading results."""

import sys
from datetime import datetime, timedelta
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from agents.options import OptionsAgent
from agents.sensex_options_scalping import SensexOptionsScalpingAgent
from agents.stocks import StocksAgent


def _event_time(day, hour, minute, second=0):
    return datetime(2024, 1, day, hour, minute, second).isoformat()


def test_stock_calendar_rollover_closes_old_bar_before_new_tick():
    agent = StocksAgent()
    agent.process_daily_tick(100, 2, "2024-01-02T10:00:00+05:30")
    agent.process_daily_tick(110, 3, "2024-01-02T14:00:00+05:30")
    agent.process_daily_tick(95, 4, "2024-01-02T15:00:00+05:30")
    agent.process_daily_tick(130, 7, "2024-01-04T10:00:00+05:30")

    assert agent.completed_candles == [
        {"open": 100, "high": 110, "low": 95, "close": 95, "volume": 9}
    ]
    assert agent.current_candle == {
        "open": 130, "high": 130, "low": 130, "close": 130, "volume": 7
    }
    # Jan 3 had no observations and therefore has no generated daily candle.
    assert len(agent.completed_candles) == 1


def test_stock_retains_enough_daily_history_for_200_bar_regime():
    agent = StocksAgent()
    first_day = datetime(2023, 1, 1, 10, 0)
    for offset in range(261):
        event_time = (first_day + timedelta(days=offset)).isoformat()
        agent.analyze({
            "symbol": "RELIANCE",
            "close": 100,
            "volume": 1,
            "timestamp": event_time,
        })

    assert len(agent._symbol_states["RELIANCE"]["completed_candles"]) == 250
    history = agent.get_history_status("RELIANCE")
    assert history["status"] == "READY"
    assert history["completed_bars"] >= history["required_bars"] == 200


def test_minute_rollover_excludes_first_tick_of_next_minute():
    agent = SensexOptionsScalpingAgent()
    agent.process_tick(100, 2, _event_time(2, 9, 15, 10))
    agent.process_tick(110, 3, _event_time(2, 9, 15, 40))
    agent.process_tick(120, 5, _event_time(2, 9, 16))

    assert agent.completed_candles == [
        {"open": 100, "high": 110, "low": 100, "close": 110, "volume": 5}
    ]
    assert agent.current_candle == {
        "open": 120, "high": 120, "low": 120, "close": 120, "volume": 5
    }


def test_minute_gaps_and_session_rollover_do_not_create_bars():
    agent = SensexOptionsScalpingAgent()
    agent.process_tick(100, 1, _event_time(2, 9, 15))
    agent.process_tick(120, 1, _event_time(2, 9, 17))
    assert agent.completed_candles == []
    assert agent.current_candle_start == agent.ist.localize(datetime(2024, 1, 2, 9, 17))

    agent.process_tick(130, 1, _event_time(3, 9, 15))
    assert agent.completed_candles == []
    assert agent.current_candle["open"] == 130


def test_15_minute_rollover_excludes_boundary_tick_and_skips_missing_buckets():
    agent = OptionsAgent()
    agent.process_15m_candle(100, 2, _event_time(2, 9, 15, 10))
    agent.process_15m_candle(110, 3, _event_time(2, 9, 29, 50))
    agent.process_15m_candle(120, 5, _event_time(2, 9, 30))

    assert agent.completed_candles_15m == [
        {"open": 100, "high": 110, "low": 100, "close": 110, "volume": 5}
    ]
    assert agent.current_candle_15m == {
        "open": 120, "high": 120, "low": 120, "close": 120, "volume": 5
    }

    gap_agent = OptionsAgent()
    gap_agent.process_15m_candle(100, 1, _event_time(2, 9, 15))
    gap_agent.process_15m_candle(130, 1, _event_time(2, 9, 45))
    assert gap_agent.completed_candles_15m == []
    assert gap_agent.current_candle_start_15m == gap_agent.ist.localize(
        datetime(2024, 1, 2, 9, 45)
    )


def test_options_hard_exit_uses_replayed_market_timestamp():
    agent = OptionsAgent()
    agent.tier1_positions.append({"symbol": "NIFTY", "entry": 100})

    agent.analyze({
        "symbol": "NIFTY",
        "close": 100,
        "volume": 1,
        "timestamp": _event_time(2, 15, 15),
    })

    assert agent._symbol_states["NIFTY"]["tier1_positions"] == []


def test_scalper_trade_cooldown_uses_replay_timestamp():
    agent = SensexOptionsScalpingAgent()
    trade_time = datetime(2024, 1, 2, 10, 0, tzinfo=agent.ist)
    agent.log_trade("BUY", 100, trade_time)

    assert not agent.can_trade_now(trade_time + timedelta(minutes=9))
    assert agent.can_trade_now(trade_time + timedelta(minutes=10))
