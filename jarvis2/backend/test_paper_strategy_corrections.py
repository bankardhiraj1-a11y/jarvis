"""Isolated synthetic tests for audited legacy PAPER time-exit corrections."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base
from models import (
    AgentName,
    PaperLimitOrder,
    PaperTradeCorrection,
    Trade,
    TradeType,
)
from trading.paper_strategy_corrections import (
    PaperTradeCorrectionError,
    correct_time_exit,
    correction_for_trade,
)


UTC = timezone.utc
ENTRY = datetime(2026, 10, 1, 17, 30, 4, 711652, tzinfo=UTC)
OLD_EXIT = datetime(2026, 10, 1, 17, 55, 9, 728578, tzinfo=UTC)
NOW = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)


@pytest.fixture
def correction_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        parent = PaperLimitOrder(
            client_order_id="legacy-gold-filled",
            origin="paper_manual",
            symbol="XAUUSD",
            side="SELL",
            manual_order=True,
            session_override=True,
            limit_price=4180.4,
            stop_loss=4187.0,
            take_profit=4161.0,
            take_profit_2=4151.0,
            quantity_troy_ounces=15.0,
            status="FILLED",
            created_at=ENTRY.replace(tzinfo=None) - timedelta(minutes=1),
            expires_at=ENTRY.replace(tzinfo=None) + timedelta(hours=2),
            filled_at=ENTRY.replace(tzinfo=None),
            fill_price=4180.4,
            state_version=7,
        )
        db.add(parent)
        db.flush()
        legs = [
            Trade(
                agent=AgentName.XAUUSD,
                symbol="XAUUSD",
                trade_type=TradeType.SELL,
                quantity=7.5,
                entry_price=4180.4,
                exit_price=4169.76,
                stop_loss=4187.0,
                take_profit=target,
                pnl=(4180.4 - 4169.76) * 7.5,
                status="CLOSED",
                created_at=ENTRY.replace(tzinfo=None),
                closed_at=OLD_EXIT.replace(tzinfo=None),
                data_source="OANDA",
                entry_data_timestamp=ENTRY.isoformat().replace("+00:00", "Z"),
                exit_data_timestamp=OLD_EXIT.isoformat().replace("+00:00", "Z"),
            )
            for target in (4161.0, 4151.0)
        ]
        db.add_all(legs)
        db.flush()
        parent.first_trade_id, parent.second_trade_id = legs[0].id, legs[1].id
        db.commit()
        yield db, parent, legs
    engine.dispose()


def quote(at, ask, bid=None, **overrides):
    value = {
        "source": "OANDA",
        "environment": "practice",
        "tradeable": True,
        "bid": bid if bid is not None else ask - 0.2,
        "ask": ask,
        "provider_timestamp": at.isoformat().replace("+00:00", "Z"),
        "timestamp": at.isoformat().replace("+00:00", "Z"),
        "status": "ok",
        "age_seconds": 0,
    }
    value.update(overrides)
    return value


def replay(db, parent, observations, current, request="strategy-fix"):
    return correct_time_exit(
        db, parent.id, request, observations, current, now=NOW
    )


def test_idempotent_correction_keeps_entry_and_old_close_audited(correction_db):
    db, parent, legs = correction_db
    entry_before = [
        (leg.entry_price, leg.created_at, leg.entry_data_timestamp, leg.quantity,
         leg.stop_loss, leg.take_profit)
        for leg in legs
    ]
    old_close = (legs[0].exit_price, legs[0].closed_at, legs[0].exit_data_timestamp, legs[0].pnl)
    observations = [quote(OLD_EXIT + timedelta(seconds=10), 4165.0)]
    current = quote(NOW, 4164.5)
    first = replay(db, parent, observations, current)
    second = replay(db, parent, [], current)

    assert first == second
    assert first["label"] == "Strategy-corrected PAPER; prior timed close retained"
    assert first["resumed_trade_ids"] == [leg.id for leg in legs]
    assert first["replay_closed_trade_ids"] == []
    assert first["uninterrupted_forward_results"] is False
    assert [(leg.entry_price, leg.created_at, leg.entry_data_timestamp, leg.quantity,
             leg.stop_loss, leg.take_profit) for leg in legs] == entry_before
    assert (legs[0].exit_price, legs[0].closed_at, legs[0].exit_data_timestamp, legs[0].pnl) == (
        None, None, None, None
    )
    audit = correction_for_trade(db, legs[0].id)
    assert audit["label"] == "Strategy-corrected PAPER; prior timed close retained"
    assert audit["original_close"] == {
        "status": "CLOSED",
        "exit_price": old_close[0],
        "closed_at": OLD_EXIT.isoformat().replace("+00:00", "Z"),
        "exit_data_timestamp": old_close[2],
        "pnl": old_close[3],
    }
    assert audit["original_entry_fields"]["entry_price"] == 4180.4
    assert "unobserved intratick movements unknown" in audit["replay_data_note"]
    assert parent.status == "FILLED"
    assert parent.state_version == 7
    assert db.query(PaperTradeCorrection).count() == 2


def test_first_target_observation_closes_legs_separately(correction_db):
    db, parent, legs = correction_db
    first_target = quote(OLD_EXIT + timedelta(seconds=10), 4160.5)
    second_target = quote(OLD_EXIT + timedelta(seconds=20), 4150.5)
    result = replay(
        db, parent, [second_target, first_target], quote(NOW, 4149.0)
    )

    assert result["replay_closed_trade_ids"] == [leg.id for leg in legs]
    assert legs[0].exit_price == 4160.5
    assert legs[0].exit_data_timestamp == first_target["provider_timestamp"]
    assert legs[1].exit_price == 4150.5
    assert legs[1].exit_data_timestamp == second_target["provider_timestamp"]
    assert legs[0].pnl is None and legs[1].pnl is None
    assert "take profit" in correction_for_trade(db, legs[0].id)["reason"]


def test_stop_is_replayed_at_first_observed_ask(correction_db):
    db, parent, legs = correction_db
    stop = quote(OLD_EXIT + timedelta(seconds=15), 4187.2)
    replay(db, parent, [stop], quote(NOW, 4186.0))

    assert all(leg.status == "CLOSED" for leg in legs)
    assert all(leg.exit_price == 4187.2 for leg in legs)
    assert all(leg.exit_data_timestamp == stop["provider_timestamp"] for leg in legs)
    assert all("stop loss" in correction_for_trade(db, leg.id)["reason"] for leg in legs)


def test_current_quote_is_last_replay_sample_and_can_trigger_target(correction_db):
    db, parent, legs = correction_db
    observation = quote(OLD_EXIT + timedelta(seconds=10), 4165.0)
    current = quote(NOW, 4160.0)
    result = replay(db, parent, [observation], current)

    assert result["replay_closed_trade_ids"] == [legs[0].id]
    assert legs[0].exit_price == 4160.0
    assert legs[0].exit_data_timestamp == current["provider_timestamp"]
    assert legs[1].status == "OPEN"


def test_missing_history_and_invalid_current_quote_are_rejected(correction_db):
    db, parent, _ = correction_db
    with pytest.raises(PaperTradeCorrectionError, match="No historical"):
        replay(db, parent, [], quote(NOW, 4160.0))
    with pytest.raises(PaperTradeCorrectionError, match="stale"):
        replay(
            db,
            parent,
            [quote(OLD_EXIT + timedelta(seconds=10), 4160.0)],
            quote(NOW - timedelta(seconds=16), 4160.0),
        )
    assert db.query(PaperTradeCorrection).count() == 0


def test_no_replay_event_after_original_close_is_not_a_fill(correction_db):
    db, parent, _ = correction_db
    before_close = quote(OLD_EXIT - timedelta(seconds=1), 4160.0)
    with pytest.raises(PaperTradeCorrectionError, match="after trade"):
        replay(db, parent, [before_close], quote(NOW, 4160.0))
    assert db.query(PaperTradeCorrection).count() == 0


def test_second_leg_failure_rolls_back_first_leg_and_audits(correction_db):
    db, parent, legs = correction_db
    first_before = (legs[0].status, legs[0].exit_price, legs[0].closed_at, legs[0].pnl)
    legs[1].exit_data_timestamp = None
    db.flush()
    with pytest.raises(PaperTradeCorrectionError, match="timestamps"):
        replay(
            db,
            parent,
            [quote(OLD_EXIT + timedelta(seconds=10), 4160.0)],
            quote(NOW, 4159.0),
        )

    db.refresh(legs[0])
    assert (legs[0].status, legs[0].exit_price, legs[0].closed_at, legs[0].pnl) == first_before
    assert db.query(PaperTradeCorrection).count() == 0