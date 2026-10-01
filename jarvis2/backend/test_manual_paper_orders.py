"""Synthetic, provider-isolated tests for durable manual paper orders."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import ManualPaperOrder, Trade
from trading.manual_paper_orders import (
    ManualOrderError,
    _safe_gold_deadline,
    cancel_manual_order,
    create_manual_order,
    list_manual_orders,
    manual_holding_decision,
    manual_order_for_trade,
    process_manual_orders,
    serialize_manual_order,
)


UTC = timezone.utc


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


@pytest.fixture(autouse=True)
def synthetic_quote_freshness(monkeypatch):
    # Processor validates event age against its injected `now`; this avoids any
    # dependency on wall-clock time while exercising provider-side price helpers.
    monkeypatch.setattr("trading.live_paper.quote_is_fresh", lambda *_args, **_kwargs: True)


def now_utc():
    return datetime(2025, 1, 15, 9, 0, tzinfo=UTC)


def indian_session_now():
    return now_utc()


def stock_payload(**changes):
    result = {
        "market": "STOCKS",
        "symbol": "RELIANCE",
        "side": "BUY",
        "order_type": "MARKET",
        "stop_loss": 90,
        "take_profit": 110,
        "quantity": 5,
    }
    result.update(changes)
    return result


def stock_quote(at, *, bid=99.5, ask=100, **changes):
    result = {
        "source": "DHAN",
        "symbol": "RELIANCE",
        "segment": "NSE_EQ",
        "timestamp": at.isoformat(),
        "timestamp_basis": "exchange",
        "status": "live",
        "close": (bid + ask) / 2,
        "bid": bid,
        "ask": ask,
        "market_session_open": True,
    }
    result.update(changes)
    return result


def option_payload(at, **changes):
    expiry = (at.astimezone(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=14)).isoformat()
    result = {
        "market": "OPTIONS",
        "symbol": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "stop_loss": 85,
        "take_profit": 120,
        "quantity_lots": 2,
        "option_type": "CE",
        "strike": 24000,
        "expiry": expiry,
    }
    result.update(changes)
    return result


def option_quote(at, *, lot_size=25, **changes):
    quote = {
        "source": "DHAN",
        "symbol": "NIFTY",
        "segment": "NSE_FNO",
        "timestamp": at.isoformat(),
        "timestamp_basis": "exchange",
        "status": "live",
        "close": 100,
        "last_price": 100,
        "bid": 99,
        "ask": 100,
        "market_session_open": True,
        "lot_size": lot_size,
        "security_id": 70001,
        "contract": {
            "security_id": 70001,
            "symbol": "NIFTY",
            "exchange": "NSE",
            "strike": 24000,
            "option_type": "CE",
            "expiry": option_payload(at)["expiry"],
        },
        "strike": 24000,
        "option_type": "CE",
        "expiry": option_payload(at)["expiry"],
    }
    quote.update(changes)
    return quote


def test_create_validate_serialize_and_cancel(db):
    now = now_utc()
    order = create_manual_order(db, stock_payload(
        order_type="LIMIT", limit_price=100, take_profit_2=120,
    ), now=now)
    result = serialize_manual_order(order, db)
    assert result["id"] == f"manual-{order.id}"
    assert result["status"] == "PENDING"
    assert result["mode"] == "PAPER"
    assert isinstance(result["client_order_id"], str)
    assert len(result["client_order_id"]) == 36
    assert result["legs"][0]["quantity"] == 2
    assert result["legs"][1]["quantity"] == 3
    assert list_manual_orders(db)[0]["id"] == result["id"]
    assert cancel_manual_order(db, result["id"]).status == "CANCELLED"
    assert cancel_manual_order(db, order.id).status == "CANCELLED"


def test_client_order_id_replay_conflict_and_cancelled_replay(db):
    now = now_utc()
    request = stock_payload(client_order_id="same-request-17")
    first = create_manual_order(db, request, now=now)
    replay = create_manual_order(
        db, request, now=now + timedelta(days=20),
    )
    assert replay.id == first.id
    assert db.query(ManualPaperOrder).count() == 1

    with pytest.raises(ManualOrderError, match="different manual order"):
        create_manual_order(
            db, stock_payload(client_order_id="same-request-17", quantity=6),
            now=now,
        )

    cancel_manual_order(db, first.id)
    cancelled_replay = create_manual_order(
        db, request, now=now + timedelta(days=20),
    )
    assert cancelled_replay.id == first.id
    assert cancelled_replay.status == "CANCELLED"


def test_gold_idempotent_replay_uses_original_validation_clock(db):
    created = datetime(2025, 1, 15, 20, 0, tzinfo=UTC)
    payload = {
        "market": "GOLD", "symbol": "XAUUSD", "side": "SELL",
        "order_type": "MARKET", "stop_loss": 2010,
        "take_profit": 1980, "quantity": 2,
        "client_order_id": "gold-retry-after-cutoff",
    }
    order = create_manual_order(db, payload, now=created)
    assert created < _safe_gold_deadline(created, 25)
    retry = create_manual_order(
        db, payload, now=order.expires_at + timedelta(minutes=1),
    )
    assert retry.id == order.id
    assert retry.status == "PENDING"


@pytest.mark.parametrize("key", [7, "", "x" * 81])
def test_client_order_id_requires_nonempty_string_at_most_80_chars(db, key):
    with pytest.raises(ManualOrderError, match="client_order_id"):
        create_manual_order(
            db, stock_payload(client_order_id=key), now=now_utc(),
        )


def test_create_resolves_ambiguous_commit_by_idempotency_key(db, monkeypatch):
    real_commit = db.commit
    request = stock_payload(client_order_id="ambiguous-commit-01")

    def commit_then_disconnect():
        real_commit()
        raise RuntimeError("commit acknowledgement lost")

    monkeypatch.setattr(db, "commit", commit_then_disconnect)
    order = create_manual_order(db, request, now=now_utc())
    assert order.client_order_id == request["client_order_id"]
    assert db.query(ManualPaperOrder).count() == 1


def test_parallel_creation_returns_matching_unique_key_winner(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'manual-create-race.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = now_utc()
    request = stock_payload(client_order_id="parallel-create-01")
    with factory() as first, factory() as second:
        first_commit = first.commit
        winner_ids = []

        def concurrent_commit():
            winner = create_manual_order(second, request, now=now)
            winner_ids.append(winner.id)
            first_commit()

        monkeypatch.setattr(first, "commit", concurrent_commit)
        resolved = create_manual_order(first, request, now=now)
        assert winner_ids == [resolved.id]
        assert first.query(ManualPaperOrder).filter(
            ManualPaperOrder.client_order_id == request["client_order_id"]
        ).count() == 1
    engine.dispose()


@pytest.mark.parametrize("payload", [
    {"market": "STOCKS", "symbol": "NIFTY", "side": "BUY", "order_type": "MARKET",
     "stop_loss": 90, "take_profit": 110, "quantity": 1},
    {"market": "OPTIONS", "symbol": "FINNIFTY", "side": "BUY", "order_type": "MARKET",
     "stop_loss": 80, "take_profit": 110, "quantity_lots": 1,
     "option_type": "CE", "strike": 20000, "expiry": "2030-01-01"},
    {"market": "OPTIONS", "symbol": "NIFTY", "side": "SELL", "order_type": "MARKET",
     "stop_loss": 120, "take_profit": 80, "quantity_lots": 1,
     "option_type": "CE", "strike": 20000, "expiry": "2030-01-01"},
])
def test_rejects_unsupported_index_naked_option_and_unregistered_underlying(db, payload):
    with pytest.raises(ManualOrderError):
        create_manual_order(db, payload, now=now_utc())


def test_market_fill_uses_provider_ask_splits_whole_shares_and_maps_parent(db):
    now = indian_session_now()
    order = create_manual_order(
        db, stock_payload(take_profit_2=120), now=now,
    )
    result = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=99.5, ask=100.25), now=now,
    )
    assert result["filled_trade_ids"] == [order.first_trade_id, order.second_trade_id]
    assert result["filled_orders"][0]["fill_price"] == 100.25
    assert [trade.quantity for trade in db.query(Trade).order_by(Trade.id)] == [2, 3]
    assert all(trade.entry_price == 100.25 for trade in db.query(Trade).all())
    assert manual_order_for_trade(db, order.first_trade_id).id == order.id


def test_limit_sell_and_stop_buy_use_correct_trigger_sides(db):
    now = indian_session_now()
    sell = create_manual_order(db, stock_payload(
        side="SELL", order_type="LIMIT", limit_price=100,
        stop_loss=110, take_profit=90, quantity=2,
    ), now=now)
    not_triggered = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=99, ask=100), now=now,
    )
    assert not not_triggered["filled_order_ids"]
    filled = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=101, ask=101.2), now=now,
    )
    assert filled["filled_order_ids"] == [sell.id]
    trade = db.get(Trade, sell.first_trade_id)
    assert trade.trade_type.value == "SELL"
    assert trade.entry_price == 101

    db.query(Trade).update({"status": "CLOSED"})
    db.commit()
    stop_buy = create_manual_order(db, stock_payload(
        order_type="STOP", limit_price=105, stop_loss=95, take_profit=115,
        quantity=2,
    ), now=now)
    filled_stop = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=105, ask=106), now=now,
    )
    assert filled_stop["filled_order_ids"] == [stop_buy.id]
    assert db.get(Trade, stop_buy.first_trade_id).entry_price == 106


def test_stop_sell_triggers_on_bid_and_limit_buy_on_ask(db):
    now = indian_session_now()
    order = create_manual_order(db, stock_payload(
        order_type="STOP", limit_price=95, stop_loss=105, take_profit=85,
        side="SELL", quantity=2,
    ), now=now)
    summary = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=94, ask=94.5), now=now,
    )
    assert summary["filled_order_ids"] == [order.id]
    assert db.get(Trade, order.first_trade_id).entry_price == 94

    db.query(Trade).update({"status": "CLOSED"})
    db.commit()
    limit_buy = create_manual_order(db, stock_payload(
        order_type="LIMIT", limit_price=100, stop_loss=90, take_profit=110,
        quantity=2,
    ), now=now)
    summary = process_manual_orders(
        db, lambda _order: stock_quote(now, bid=98, ask=99), now=now,
    )
    assert summary["filled_order_ids"] == [limit_buy.id]
    assert db.get(Trade, limit_buy.first_trade_id).entry_price == 99


def test_quote_provenance_session_blocking_and_actual_stop_risk(db):
    now = indian_session_now()
    order = create_manual_order(
        db, stock_payload(quantity=60, take_profit=120), now=now,
    )
    stale = process_manual_orders(
        db, lambda _order: stock_quote(now - timedelta(seconds=16)), now=now,
    )
    assert not stale["filled_order_ids"]
    blocked = process_manual_orders(
        db, lambda _order: stock_quote(now, market_session_open=False), now=now,
    )
    assert not blocked["filled_order_ids"]
    blocked_reason = process_manual_orders(
        db, lambda _order: stock_quote(now, entry_blocked_reason="risk gate"), now=now,
    )
    assert not blocked_reason["filled_order_ids"]
    gap_quote = stock_quote(now, bid=100, ask=111)
    gap = process_manual_orders(db, lambda _order: gap_quote, now=now)
    assert not gap["filled_order_ids"]
    assert gap["skipped"][-1]["reason"].startswith("Actual-fill stop risk")
    assert db.get(ManualPaperOrder, order.id).status == "PENDING"


def test_available_capital_callback_includes_notional_and_fee_buffer(db):
    now = indian_session_now()
    order = create_manual_order(db, stock_payload(quantity=5), now=now)
    insufficient = process_manual_orders(
        db,
        lambda _order: stock_quote(now),
        now=now,
        available_capital=lambda received: 500 if received.id == order.id else 0,
    )
    assert not insufficient["filled_order_ids"]
    assert "capital" in insufficient["skipped"][-1]["reason"]
    funded = process_manual_orders(
        db,
        lambda _order: stock_quote(now),
        now=now,
        available_capital=lambda received: 1000 if received.id == order.id else 0,
    )
    assert funded["filled_order_ids"] == [order.id]


def test_option_contract_lots_exact_quantity_and_missing_lot_blocks(db):
    now = indian_session_now()
    order = create_manual_order(
        db, option_payload(now, take_profit_2=140), now=now,
    )
    blocked = process_manual_orders(
        db, lambda _order: option_quote(now, lot_size=None), now=now,
    )
    assert not blocked["filled_order_ids"]
    assert "lot_size" in blocked["skipped"][-1]["reason"]
    filled = process_manual_orders(
        db, lambda _order: option_quote(now, lot_size=25), now=now,
    )
    assert filled["filled_order_ids"] == [order.id]
    children = db.query(Trade).order_by(Trade.id).all()
    assert [trade.quantity for trade in children] == [25, 25]
    assert all(trade.trade_type.value == "BUY" for trade in children)
    assert all(trade.option_strike == f"24000 CE {order.expiry}" for trade in children)
    assert db.get(ManualPaperOrder, order.id).option_lot_size == 25
    intent = manual_holding_decision(
        order, children[0].created_at, children[0].created_at + timedelta(minutes=21),
    )
    assert intent["due"] is True


def test_option_metadata_mismatch_and_one_lot_two_target_rejected(db):
    now = indian_session_now()
    with pytest.raises(ManualOrderError, match="at least two"):
        create_manual_order(db, option_payload(now, quantity_lots=1, take_profit_2=130), now=now)
    order = create_manual_order(db, option_payload(now), now=now)
    bad = option_quote(now)
    bad["contract"]["security_id"] = 0
    summary = process_manual_orders(db, lambda _order: bad, now=now)
    assert not summary["filled_order_ids"]
    assert db.get(ManualPaperOrder, order.id).status == "PENDING"


def test_gold_two_target_fill_and_conservative_daily_cap(db):
    now = now_utc()
    deadline = _safe_gold_deadline(now, 25)
    assert now < deadline
    payload = {
        "market": "GOLD", "symbol": "XAUUSD", "side": "BUY",
        "order_type": "MARKET", "stop_loss": 2005, "take_profit": 2020,
        "take_profit_2": 2030, "quantity": 15,
    }
    order = create_manual_order(db, payload, now=now)
    quote = {
        "source": "OANDA", "instrument": "XAU_USD", "environment": "practice",
        "tradeable": True, "timestamp": now.isoformat(),
        "timestamp_basis": "provider", "status": "live", "close": 2010,
        "bid": 2010, "ask": 2011,
    }
    cap = process_manual_orders(
        db, lambda _order: quote, now=now, gold_entries_today=2,
    )
    assert not cap["filled_order_ids"]
    assert "daily cap" in cap["skipped"][-1]["reason"]
    filled = process_manual_orders(
        db, lambda _order: quote, now=now, gold_entries_today=0,
    )
    assert filled["filled_order_ids"] == [order.id]
    assert [trade.quantity for trade in db.query(Trade).order_by(Trade.id)] == [7.5, 7.5]
    assert [trade.entry_price for trade in db.query(Trade).all()] == [2011, 2011]


def test_order_expiry_and_fill_transaction_rollback(db, monkeypatch):
    now = indian_session_now()
    order = create_manual_order(db, stock_payload(), now=now)
    real_commit = db.commit

    def fail_commit():
        raise RuntimeError("private database details must not leak")

    monkeypatch.setattr(db, "commit", fail_commit)
    result = process_manual_orders(
        db, lambda _order: stock_quote(now), now=now,
    )
    assert not result["filled_order_ids"]
    assert result["exceptions"][0]["reason"] == "Could not commit provider fill; all fill legs were rolled back"
    assert db.query(Trade).count() == 0
    monkeypatch.setattr(db, "commit", real_commit)
    due = process_manual_orders(
        db, lambda _order: stock_quote(now), now=order.expires_at + timedelta(seconds=1),
    )
    assert due["expired_order_ids"] == [order.id]
    assert db.get(ManualPaperOrder, order.id).status == "EXPIRED"


def test_optimistic_cancel_cannot_overwrite_committed_fill(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'manual-race.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = indian_session_now()
    with factory() as first, factory() as second:
        order = create_manual_order(first, stock_payload(), now=now)
        first.expire_all()
        stale = first.get(ManualPaperOrder, order.id)
        assert stale.status == "PENDING"
        process_manual_orders(
            second, lambda _order: stock_quote(now), now=now,
        )
        with pytest.raises(ManualOrderError, match="concurrently"):
            cancel_manual_order(first, order.id)
        first.expire_all()
        assert first.get(ManualPaperOrder, order.id).status == "FILLED"
        assert first.query(Trade).count() == 1
    engine.dispose()


def test_competing_fill_rolls_back_losing_session_legs(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'manual-fill-race.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = indian_session_now()
    with factory() as first, factory() as second:
        order = create_manual_order(
            first, stock_payload(take_profit_2=120), now=now,
        )
        first.expire_all()
        first.get(ManualPaperOrder, order.id)
        original_flush = first.flush
        competed = []

        def concurrent_fill(*args, **kwargs):
            if not competed and any(isinstance(item, Trade) for item in first.new):
                competed.append(True)
                process_manual_orders(
                    second, lambda _order: stock_quote(now), now=now,
                )
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(first, "flush", concurrent_fill)
        result = process_manual_orders(
            first, lambda _order: stock_quote(now), now=now,
        )
        assert competed
        assert result["exceptions"]
        first.expire_all()
        saved = first.get(ManualPaperOrder, order.id)
        assert saved.status == "FILLED"
        assert first.query(Trade).count() == 2
        assert {saved.first_trade_id, saved.second_trade_id} == {
            trade.id for trade in first.query(Trade).all()
        }
    engine.dispose()