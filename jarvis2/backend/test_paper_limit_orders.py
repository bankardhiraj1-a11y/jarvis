def test_stale_session_cannot_cancel_a_committed_fill(tmp_path):
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    from database import Base
    from trading.paper_limit_orders import PaperOrderError

    engine = create_engine(f"sqlite:///{tmp_path / 'cancel-race.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as first, Session(engine) as second:
        order = create_pending(first)
        assert order.status == "PENDING"  # Hold the old version in this session.
        event = CREATED + timedelta(seconds=5)
        process_pending_orders(second, live_quote(event, bid=4178, ask=4178.2), now=event)
        with pytest.raises(PaperOrderError):
            cancel_order(first, order.id)
        first.expire_all()
        assert first.get(PaperLimitOrder, order.id).status == "FILLED"
        assert first.query(Trade).count() == 2
    engine.dispose()


def test_competing_fill_rolls_back_extra_legs(tmp_path, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    from database import Base
    from trading.paper_limit_orders import PaperOrderError

    engine = create_engine(f"sqlite:///{tmp_path / 'fill-race.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as first, Session(engine) as second:
        order = create_pending(first)
        assert order.status == "PENDING"
        event = CREATED + timedelta(seconds=5)
        real_flush = first.flush
        competed = []

        def concurrent_fill(*args, **kwargs):
            if not competed and any(isinstance(item, Trade) for item in first.new):
                competed.append(True)
                process_pending_orders(
                    second, live_quote(event, bid=4178, ask=4178.2), now=event,
                )
            return real_flush(*args, **kwargs)

        monkeypatch.setattr(first, "flush", concurrent_fill)
        with pytest.raises(PaperOrderError):
            process_pending_orders(
                first, live_quote(event, bid=4178, ask=4178.2), now=event,
            )
        assert competed
        first.expire_all()
        assert first.query(Trade).count() == 2
        saved = first.get(PaperLimitOrder, order.id)
        assert saved.status == "FILLED"
        assert {saved.first_trade_id, saved.second_trade_id} == {
            item.id for item in first.query(Trade).all()
        }
        data = serialize_order(saved, first)
        assert data["first_trade_id"] == saved.first_trade_id
        assert data["second_trade_id"] == saved.second_trade_id
    engine.dispose()
"""Focused synthetic tests for durable OANDA-backed manual paper limits."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import PaperLimitOrder, Trade
from trading.paper_limit_orders import (
    OrderError,
    cancel_order,
    create_order,
    list_orders,
    manual_holding_intent,
    manual_order_for_trade,
    process_pending_orders,
    serialize_order,
)


UTC = timezone.utc
CREATED = datetime(2025, 1, 15, 18, 0, tzinfo=UTC)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        yield session
    engine.dispose()


def payload(**overrides):
    result = {
        "client_order_id": "gold-manual-4177",
        "symbol": "XAUUSD",
        "side": "SELL",
        "limit_price": 4177,
        "stop_loss": 4187,
        "take_profit": 4161,
        "take_profit_2": 4151,
        "quantity_troy_ounces": 15,
        "manual_order": True,
        "session_override": True,
    }
    result.update(overrides)
    return result


def live_quote(at, *, bid=4176.5, ask=4176.8, **overrides):
    result = {
        "source": "OANDA",
        "environment": "practice",
        "tradeable": True,
        "timestamp": at.isoformat(),
        "close": (bid + ask) / 2,
        "bid": bid,
        "ask": ask,
        "stale": False,
    }
    result.update(overrides)
    return result


def create_pending(db, *, when=CREATED, **overrides):
    return create_order(db, payload(**overrides), now=when)


def test_pending_order_has_no_trade_until_a_fresh_executable_bid_reaches_limit(db):
    order = create_pending(db)
    assert order.status == "PENDING"
    assert db.query(Trade).count() == 0

    summary = process_pending_orders(
        db, live_quote(CREATED + timedelta(seconds=5)), now=CREATED + timedelta(seconds=5)
    )
    assert summary["filled_order_ids"] == []
    assert db.query(Trade).count() == 0
    assert "has not reached SELL limit" in summary["skipped"][0]["reason"]


def test_trigger_creates_two_atomic_sell_legs_at_actual_improved_bid(db):
    order = create_pending(db)
    event = CREATED + timedelta(seconds=5)
    summary = process_pending_orders(
        db, live_quote(event, bid=4178.25, ask=4178.5), now=event
    )
    trades = db.query(Trade).order_by(Trade.id).all()

    assert summary["filled_order_ids"] == [order.id]
    assert len(summary["filled_trade_ids"]) == 2
    assert len(trades) == 2
    assert [trade.quantity for trade in trades] == [7.5, 7.5]
    assert [trade.take_profit for trade in trades] == [4161, 4151]
    assert all(trade.trade_type.value == "SELL" for trade in trades)
    assert all(trade.entry_price == 4178.25 for trade in trades)
    assert all(trade.data_source == "OANDA" for trade in trades)
    assert all(trade.created_at == event.replace(tzinfo=None) for trade in trades)
    assert order.status == "FILLED"
    assert order.fill_price == 4178.25
    assert order.first_trade_id == trades[0].id
    assert order.second_trade_id == trades[1].id
    assert order.origin == "paper_manual"
    assert manual_order_for_trade(db, trades[0].id).id == order.id
    intent = manual_holding_intent(order)
    assert intent["max_hold_minutes"] == 25
    assert intent["allow_overnight"] is False
    assert intent["session_override"] is True

    serialized = serialize_order(order, db)
    assert serialized["status"] == "FILLED"
    assert serialized["planned_risk_usd"] == 150
    assert [leg["status"] for leg in serialized["legs"]] == ["OPEN", "OPEN"]
    assert "not guarantees" in serialized["potential_disclaimer"]
    assert len(list_orders(db)) == 1


def test_improved_bid_is_used_without_inventing_the_requested_limit(db):
    order = create_pending(db)
    event = CREATED + timedelta(seconds=2)
    process_pending_orders(db, live_quote(event, bid=4179, ask=4179.1), now=event)
    assert order.fill_price == 4179
    assert {trade.entry_price for trade in db.query(Trade).all()} == {4179}


def test_reprocessing_filled_order_is_idempotent(db):
    order = create_pending(db)
    event = CREATED + timedelta(seconds=2)
    quote = live_quote(event, bid=4177, ask=4177.2)
    first = process_pending_orders(db, quote, now=event)
    second = process_pending_orders(db, quote, now=event + timedelta(seconds=1))
    assert len(first["filled_trade_ids"]) == 2
    assert second["filled_order_ids"] == []
    assert db.query(Trade).count() == 2


@pytest.mark.parametrize(
    "quote_factory,reason",
    [
        (lambda at: live_quote(at - timedelta(seconds=30)), "stale"),
        (lambda at: live_quote(at + timedelta(seconds=1), bid=4180, ask=4181), "future"),
        (lambda at: live_quote(at, bid=4181, ask=4180), "crossed"),
        (lambda at: live_quote(at, bid=4180, ask=4181, source="MOCK"), "provenance"),
        (lambda at: live_quote(at, bid=4180, ask=4181, environment="sandbox"), "environment"),
        (lambda at: live_quote(at, bid=4180, ask=4181, tradeable=False), "tradeable"),
    ],
)
def test_invalid_quote_provenance_or_market_state_never_fills(db, quote_factory, reason):
    order = create_pending(db)
    now = CREATED + timedelta(seconds=5)
    summary = process_pending_orders(db, quote_factory(now), now=now)
    assert order.status == "PENDING"
    assert db.query(Trade).count() == 0
    assert reason in summary["skipped"][0]["reason"].lower()


def test_provider_event_before_order_creation_does_not_fill(db):
    order = create_pending(db)
    event = CREATED - timedelta(seconds=1)
    summary = process_pending_orders(
        db, live_quote(event, bid=4180, ask=4181), now=CREATED + timedelta(seconds=1)
    )
    assert order.status == "PENDING"
    assert db.query(Trade).count() == 0
    assert "predates order creation" in summary["skipped"][0]["reason"]


def test_order_expires_before_new_york_rollover_cutoff(db):
    created = datetime(2025, 1, 15, 21, 33, tzinfo=UTC)
    order = create_pending(db, when=created, client_order_id="expires-near-rollover")
    assert order.expires_at == datetime(2025, 1, 15, 21, 34)
    now = datetime(2025, 1, 15, 21, 34, tzinfo=UTC)
    summary = process_pending_orders(db, live_quote(now, bid=4180, ask=4181), now=now)
    assert summary["expired_order_ids"] == [order.id]
    assert order.status == "EXPIRED"
    assert db.query(Trade).count() == 0


def test_utc_entry_cutoff_expires_pending_order(db):
    created = datetime(2025, 1, 15, 22, 34, tzinfo=UTC)
    order = create_pending(db, when=created, client_order_id="expires-utc")
    assert order.expires_at == datetime(2025, 1, 15, 22, 35)
    now = datetime(2025, 1, 15, 22, 35, tzinfo=UTC)
    summary = process_pending_orders(db, live_quote(now, bid=4180, ask=4181), now=now)
    assert summary["expired_order_ids"] == [order.id]


def test_cancel_pending_order_and_reject_cancelling_filled_order(db):
    pending = create_pending(db)
    cancelled = cancel_order(db, pending.id)
    assert cancelled.status == "CANCELLED"
    assert cancel_order(db, pending.id).status == "CANCELLED"
    assert db.query(Trade).count() == 0

    filled = create_pending(db, client_order_id="filled-cannot-cancel")
    now = CREATED + timedelta(seconds=3)
    process_pending_orders(db, live_quote(now, bid=4177, ask=4177.2), now=now)
    with pytest.raises(OrderError, match="cannot be cancelled"):
        cancel_order(db, filled.id)


def test_duplicate_creation_is_idempotent_and_conflicting_reuse_is_rejected(db):
    first = create_pending(db)
    repeated = create_pending(db)
    assert repeated.id == first.id
    assert db.query(PaperLimitOrder).count() == 1
    with pytest.raises(OrderError, match="different order"):
        create_pending(db, take_profit=4160)


def test_stop_gap_open_position_and_daily_cap_all_block_fills(db):
    gap_order = create_pending(db, client_order_id="gap-order")
    gap_now = CREATED + timedelta(seconds=1)
    gap = process_pending_orders(
        db,
        live_quote(gap_now, bid=4188, ask=4188.2),
        now=gap_now,
    )
    assert gap_order.status == "PENDING"
    assert "unsafe entry gap" in gap["skipped"][0]["reason"]

    # Cancel the gap order so the later scenarios isolate their own order.
    cancel_order(db, gap_order.id)
    open_trade_order = create_pending(db, client_order_id="open-position")
    existing = Trade(
        agent="XAUUSD",
        symbol="XAUUSD",
        trade_type="SELL",
        quantity=1,
        entry_price=4170,
        stop_loss=4180,
        take_profit=4160,
        status="OPEN",
        created_at=CREATED.replace(tzinfo=None),
        data_source="OANDA",
        entry_data_timestamp=CREATED.isoformat(),
    )
    db.add(existing)
    db.commit()
    now = CREATED + timedelta(seconds=2)
    open_result = process_pending_orders(
        db, live_quote(now, bid=4178, ask=4178.2), now=now
    )
    assert open_trade_order.status == "PENDING"
    assert "already exists" in open_result["skipped"][0]["reason"]
    existing.status = "CLOSED"
    db.commit()

    cap_order = create_pending(db, client_order_id="daily-cap")
    cap_result = process_pending_orders(
        db,
        live_quote(now, bid=4178, ask=4178.2),
        now=now,
        accepted_entries_today=2,
    )
    assert cap_order.status == "PENDING"
    assert "daily cap" in cap_result["skipped"][0]["reason"]
    assert db.query(Trade).filter(Trade.status == "OPEN").count() == 0


def test_payload_validation_blocks_buy_wrong_risk_and_unsafe_stop_gap(db):
    with pytest.raises(OrderError, match="Only manual"):
        create_pending(db, side="BUY")
    with pytest.raises(OrderError, match="risk"):
        create_pending(db, stop_loss=4188)
    with pytest.raises(OrderError, match="stop_loss must be above"):
        create_pending(db, stop_loss=4177)


def test_fill_transaction_rolls_back_both_trade_legs_on_commit_failure(db, monkeypatch):
    order = create_pending(db)
    now = CREATED + timedelta(seconds=1)

    def fail_commit():
        raise RuntimeError("synthetic commit failure")

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(OrderError, match="atomically"):
        process_pending_orders(
            db, live_quote(now, bid=4178, ask=4178.2), now=now
        )
    monkeypatch.undo()
    db.expire_all()
    assert db.query(Trade).count() == 0
    assert db.get(PaperLimitOrder, order.id).status == "PENDING"


def test_creation_refuses_to_leave_order_pending_past_a_safe_cutoff(db):
    with pytest.raises(OrderError, match="22:35 UTC cutoff"):
        create_pending(
            db,
            when=datetime(2025, 1, 15, 22, 35, tzinfo=UTC),
            client_order_id="too-late-utc",
        )