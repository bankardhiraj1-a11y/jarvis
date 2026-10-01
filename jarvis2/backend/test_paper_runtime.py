"""Restart, cooldown, and evidence regressions over isolated SQLite records."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import gettempdir

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from models import AgentName, Trade, TradeType
from agents.xauusd_highwin import initial_highwin_state
from trading.holding_policy import (
    entry_allowed_by_holding_policy,
    holding_exit_decision,
)


@pytest.fixture
def paper_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    main.Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        yield db
    engine.dispose()


def test_main_import_schema_uses_process_scoped_temporary_database():
    assert Path(main.engine.url.database).parent.is_relative_to(Path(gettempdir()))
    assert Path(main.engine.url.database).name == "paper-tests.sqlite"


def insert_gold_trade(
    db,
    *,
    entry_time,
    exit_time=None,
    status="OPEN",
    pnl=None,
):
    trade = Trade(
        agent=AgentName.XAUUSD,
        symbol="XAUUSD",
        trade_type=TradeType.BUY,
        quantity=100,
        entry_price=4100,
        exit_price=4101 if exit_time else None,
        stop_loss=4098,
        take_profit=4105,
        pnl=pnl,
        status=status,
        created_at=datetime.fromisoformat(entry_time.replace("Z", "+00:00")).replace(
            tzinfo=None
        ),
        closed_at=(
            datetime.fromisoformat(exit_time.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
            if exit_time
            else None
        ),
        data_source="OANDA",
        entry_data_timestamp=entry_time,
        exit_data_timestamp=exit_time,
    )
    db.add(trade)
    db.flush()
    if pnl is None and status == "CLOSED":
        # SQLAlchemy's column default inserts zero for Python None; force the
        # persisted value to NULL to represent genuinely unavailable net P&L.
        trade.pnl = None
        db.flush()
    return trade


def insert_sensex_trade(
    db,
    *,
    entry_time,
    status="OPEN",
    closed_at=None,
    pnl=None,
):
    trade = Trade(
        agent=AgentName.SENSEX_OPTIONS_SCALPING,
        symbol="SENSEX",
        trade_type=TradeType.BUY,
        quantity=25,
        entry_price=100,
        exit_price=95 if status == "CLOSED" else None,
        stop_loss=75,
        take_profit=115,
        pnl=pnl,
        status=status,
        created_at=datetime.fromisoformat(entry_time.replace("Z", "+00:00")).replace(
            tzinfo=None
        ),
        closed_at=closed_at,
        option_strike="SENSEX_20261002_85000_CE",
        option_price=100,
        data_source="DHAN",
        entry_data_timestamp=entry_time,
        exit_data_timestamp=(
            closed_at.isoformat() + "Z" if closed_at is not None else None
        ),
    )
    db.add(trade)
    db.flush()
    return trade


def test_gold_daily_review_uses_utc_dates_and_rebuilds_versioned_evidence(
    paper_db, tmp_path, monkeypatch
):
    historical_entries = [
        "2026-10-02T20:00:00Z",
        "2026-10-02T20:10:00Z",
        "2026-10-02T20:20:00Z",
    ]
    for entry_time in historical_entries:
        entry = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
        exit_time = (entry.replace(minute=entry.minute + 4)).isoformat().replace(
            "+00:00", "Z"
        )
        insert_gold_trade(
            paper_db,
            entry_time=entry_time,
            exit_time=exit_time,
            status="CLOSED",
            pnl=None,
        )
    paper_db.commit()

    # A legacy file with the old, incorrect XAU date comparison is not trusted.
    legacy_directory = tmp_path / "daily_reviews"
    legacy_directory.mkdir()
    (legacy_directory / "xauusd-2026-10-02.json").write_text(
        '{"closed_verified_paper_trades": 0}', encoding="utf-8"
    )
    monkeypatch.setattr(main, "evidence_dir", tmp_path)
    monkeypatch.setattr(main, "_REVIEWED_SESSION_DATES", set())

    main._write_daily_review(
        paper_db, datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)
    )

    versioned = legacy_directory / "xauusd-v2-2026-10-02.json"
    report = json.loads(versioned.read_text(encoding="utf-8"))
    assert report["review_schema_version"] == 2
    assert report["closed_verified_paper_trades"] == 3
    assert report["daily_entries"] == 3
    assert report["daily_exits"] == 3
    assert report["classified_trades"] == 0
    assert report["gross_price_pnl"] == 300.0
    assert main._daily_trade_datetime(
        paper_db.query(Trade).first(), "closed_at", "XAUUSD"
    ) == date(2026, 10, 2)


def test_gold_restart_restores_persisted_daily_entry_cap_without_warmup(paper_db, monkeypatch):
    accepted = [
        "2026-10-02T16:05:00Z",
        "2026-10-02T17:05:00Z",
        "2026-10-02T18:05:00Z",
    ]
    for entry_time in accepted:
        insert_gold_trade(paper_db, entry_time=entry_time)
    paper_db.commit()

    agent = main.agents_map["XAUUSD"]
    monkeypatch.setattr(agent, "highwin_state", initial_highwin_state())
    monkeypatch.setattr(agent, "_highwin_active_entry_time", None)

    restored_count = main._restore_gold_runtime_state(
        paper_db, datetime(2026, 10, 2, 19, 0, tzinfo=timezone.utc)
    )

    assert restored_count == 3
    assert agent.highwin_state["daily_entry_count"] == 3
    assert agent.highwin_state["last_utc_day"] == date(2026, 10, 2)
    assert agent.highwin_state["closes"] == []
    assert agent.open_trade_count == 3
    assert agent._highwin_active_entry_time == datetime(
        2026, 10, 2, 16, 5, tzinfo=timezone.utc
    )


def test_sensex_restart_restores_trade_ids_entry_and_realized_loss_cooldowns(
    paper_db, monkeypatch
):
    loss = insert_sensex_trade(
        paper_db,
        entry_time="2026-10-02T09:00:00Z",
        status="CLOSED",
        closed_at=datetime(2026, 10, 2, 10, 0),
        pnl=-125.0,
    )
    latest = insert_sensex_trade(
        paper_db,
        entry_time="2026-10-02T09:30:00Z",
    )
    paper_db.commit()
    agent = main.agents_map["SENSEX_OPTIONS_SCALPING"]
    monkeypatch.setattr(agent, "trades_today", [])
    monkeypatch.setattr(agent, "last_trade_time", None)

    restored = main._restore_sensex_runtime_state(
        paper_db, datetime(2026, 10, 2, 10, 1, tzinfo=timezone.utc)
    )
    before_entry_cooldown = main._sensex_cooldown_status(
        paper_db, datetime(2026, 10, 2, 9, 39, 59, tzinfo=timezone.utc)
    )
    before_loss_cooldown = main._sensex_cooldown_status(
        paper_db, datetime(2026, 10, 2, 10, 14, 59, tzinfo=timezone.utc)
    )
    after_cooldowns = main._sensex_cooldown_status(
        paper_db, datetime(2026, 10, 2, 10, 15, 0, tzinfo=timezone.utc)
    )

    assert restored == 2
    assert {item["trade_id"] for item in agent.trades_today} == {loss.id, latest.id}
    assert agent.last_trade_time == main.pytz.timezone(
        "Asia/Kolkata"
    ).localize(datetime(2026, 10, 2, 15, 0))
    assert agent.last_realized_loss_time == datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)
    assert before_entry_cooldown[0] is False
    assert "accepted-entry cooldown" in before_entry_cooldown[1]
    assert before_loss_cooldown[0] is False
    assert "realized-loss cooldown" in before_loss_cooldown[1]
    assert after_cooldowns[0] is True


def test_sensex_close_updates_persisted_trade_id_not_matching_entry_price(
    paper_db, monkeypatch
):
    entry_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    prior = insert_sensex_trade(
        paper_db,
        entry_time=(entry_time - timedelta(minutes=20)).isoformat().replace(
            "+00:00", "Z"
        ),
        status="CLOSED",
        closed_at=(entry_time - timedelta(minutes=10)).replace(tzinfo=None),
        pnl=0.0,
    )
    opened = insert_sensex_trade(
        paper_db,
        entry_time=(entry_time - timedelta(minutes=5)).isoformat().replace(
            "+00:00", "Z"
        ),
    )
    opened.created_at = datetime.utcnow()
    paper_db.commit()

    agent = main.agents_map["SENSEX_OPTIONS_SCALPING"]
    monkeypatch.setattr(agent, "trades_today", [
        {"trade_id": prior.id, "entry_price": 100.0, "pnl": 0.0},
        {"trade_id": opened.id, "entry_price": 100.0, "pnl": 0.0},
    ])
    quote = {"timestamp": datetime.now(timezone.utc).isoformat()}
    monkeypatch.setattr(main, "_cached_trade_mark", lambda trade: (110.0, quote))
    monkeypatch.setattr(main, "quote_is_fresh", lambda value: True)
    monkeypatch.setattr(main, "quote_has_timestamp", lambda value: True)
    monkeypatch.setattr(main, "calculate_net_pnl", lambda *args, **kwargs: 4.25)

    result = main._monitor_open_trade(
        paper_db, opened, "SENSEX_OPTIONS_SCALPING"
    )

    assert result[0] == "TRADE_CLOSED"
    assert agent.trades_today[0]["pnl"] == 0.0
    assert agent.trades_today[1]["pnl"] == 4.25


def test_gold_entry_and_exit_respect_next_new_york_rollover():
    policy = {"allow_overnight": False, "max_hold_minutes": 25}
    rollover_utc = datetime(2026, 10, 30, 21, 0, tzinfo=timezone.utc)
    one_minute_before_rollover = rollover_utc - timedelta(minutes=1)
    # Entry with only 25 minutes plus the required rollover buffer remaining
    # is blocked; a full holding window before that buffer remains eligible.
    assert not entry_allowed_by_holding_policy(
        "XAUUSD",
        now=datetime(2026, 10, 30, 20, 35, tzinfo=timezone.utc),
        holding_intent=policy,
    )
    assert entry_allowed_by_holding_policy(
        "XAUUSD",
        now=datetime(2026, 10, 30, 20, 30, tzinfo=timezone.utc),
        holding_intent=policy,
    )
    due = holding_exit_decision(
        {
            "agent": "XAUUSD",
            "status": "OPEN",
            "created_at": datetime(2026, 10, 30, 20, 45, tzinfo=timezone.utc),
        },
        now=one_minute_before_rollover,
        holding_intent=policy,
    )
    assert due["due"] is True
    assert "rollover" in due["reason"].lower()


def test_gold_runtime_parameters_match_the_fixed_london_study_candidate():
    study_path = Path(main.__file__).resolve().parents[1] / "evidence" / "xauusd_session_study.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    candidate = next(
        item
        for item in study["candidate_results"]
        if item["candidate_id"]
        == "RSI_BB_EXISTING_BEST_COVERAGE_FIXED__Europe_London_08_17"
    )
    agent = main.agents_map["XAUUSD"]

    assert agent.highwin_parameters == candidate["parameters"]
    assert main._XAU_SESSION_STUDY_STATUS["candidate_count"] == 12
    assert main._XAU_SESSION_STUDY_STATUS["fit_validation_eligible_candidates"] == 0
    assert main._XAU_SESSION_STUDY_STATUS["all_candidates_rejected"] is True
    assert main._XAU_SESSION_STUDY_STATUS["holdout_evaluated_candidates"] == 0
    assert main._XAU_SESSION_STUDY_STATUS["profitability_claim"] is False


def test_gold_entry_window_is_london_local_and_dst_aware():
    winter_open = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
    summer_open = datetime(2026, 8, 15, 7, 0, tzinfo=timezone.utc)

    assert main._market_hours_open(
        "XAUUSD", winter_open - timedelta(seconds=1)
    ) is False
    assert main._market_hours_open("XAUUSD", winter_open) is True
    assert main._market_hours_open(
        "XAUUSD", datetime(2026, 1, 15, 17, 0, tzinfo=timezone.utc)
    ) is False
    assert main._market_hours_open(
        "XAUUSD", summer_open - timedelta(seconds=1)
    ) is False
    assert main._market_hours_open("XAUUSD", summer_open) is True
    assert main._market_hours_open(
        "XAUUSD", datetime(2026, 8, 15, 16, 0, tzinfo=timezone.utc)
    ) is False

    status = main._xau_entry_window_status(summer_open)
    assert status["timezone"] == "Europe/London"
    assert status["local_hours"] == "08:00-17:00"
    assert status["current_utc"] == summer_open.isoformat()
    assert status["current_ist"].startswith("2026-08-15T12:30:00")
    assert status["current_local"].startswith("2026-08-15T08:00:00")
    assert status["opens_utc"] == "2026-08-15T07:00:00+00:00"
    assert status["closes_utc"] == "2026-08-15T16:00:00+00:00"
    assert status["opens_ist"] == "2026-08-15T12:30:00+05:30"
    assert status["closes_ist"] == "2026-08-15T21:30:00+05:30"
    assert status["is_open"] is True