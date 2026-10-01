from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from trading.holding_policy import (
    entry_allowed_by_holding_policy,
    holding_exit_decision,
    next_gold_rollover_deadline,
)


def trade(agent, created_at, **kwargs):
    values = {"agent": agent, "created_at": created_at, "status": "OPEN"}
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_options_wind_down_uses_same_ist_date_at_1520_cutoff():
    opened = datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)
    before = holding_exit_decision(
        trade("OPTIONS", opened),
        now=datetime(2025, 1, 2, 9, 49, tzinfo=timezone.utc),  # 15:19 IST
    )
    at_cutoff = holding_exit_decision(
        trade("OPTIONS", opened),
        now=datetime(2025, 1, 2, 9, 50, tzinfo=timezone.utc),  # 15:20 IST
    )
    after_cutoff = holding_exit_decision(
        trade("SENSEX_OPTIONS_SCALPING", opened),
        now=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),  # 15:30 IST
    )

    assert before["due"] is False
    assert before["deadline"] == "2025-01-02T15:20:00+05:30"
    assert at_cutoff["due"] is True
    assert at_cutoff["status"] == "INTRADAY_EXIT_DUE"
    assert after_cutoff["due"] is True
    assert after_cutoff["status"] == "INTRADAY_EXIT_OVERDUE"


def test_intraday_entry_cutoff_is_inclusive_for_both_agents():
    assert entry_allowed_by_holding_policy(
        "OPTIONS", now=datetime(2025, 1, 2, 9, 49, tzinfo=timezone.utc)
    )
    assert not entry_allowed_by_holding_policy(
        "OPTIONS", now=datetime(2025, 1, 2, 9, 50, tzinfo=timezone.utc)
    )
    assert not entry_allowed_by_holding_policy(
        "SENSEX_OPTIONS_SCALPING",
        now=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),
    )


def test_intraday_trade_from_previous_ist_date_is_overdue():
    opened = datetime(2025, 1, 1, 9, 0)  # Naive DB timestamps mean UTC.
    decision = holding_exit_decision(
        trade("OPTIONS", opened),
        now=datetime(2025, 1, 2, 4, 0, tzinfo=timezone.utc),
    )

    assert decision["due"] is True
    assert decision["status"] == "INTRADAY_EXIT_OVERDUE"
    assert decision["deadline"] == "2025-01-01T15:20:00+05:30"


def test_intraday_missing_creation_timestamp_fails_safe():
    decision = holding_exit_decision(
        trade("OPTIONS", None),
        now=datetime(2025, 1, 2, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["due"] is True
    assert decision["status"] == "INTRADAY_EXIT_OVERDUE"
    assert decision["deadline"] is None


def test_xauusd_defaults_to_bounded_short_hold_and_rejects_late_entry():
    opened = datetime(2025, 1, 2, 16, 30, tzinfo=timezone.utc)
    before_max_hold = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 1, 2, 16, 49, tzinfo=timezone.utc),
    )
    at_max_hold = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 1, 2, 16, 50, tzinfo=timezone.utc),
    )

    assert before_max_hold["due"] is False
    assert before_max_hold["policy"] == "xauusd_no_overnight_rollover_safe"
    assert before_max_hold["deadline"] == "2025-01-02T16:50:00+00:00"
    assert at_max_hold["due"] is True
    assert at_max_hold["status"] == "MAX_HOLD_EXIT_DUE"
    assert not entry_allowed_by_holding_policy(
        "XAUUSD", now=datetime(2025, 1, 2, 23, 0, tzinfo=timezone.utc)
    )


def test_xauusd_strategy_supplied_25_minute_exit_bound_is_unchanged():
    opened = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
    intent = {"max_hold_minutes": 25, "allow_overnight": False}
    before_bound = holding_exit_decision(
        trade("XAUUSD", opened),
        now=opened + timedelta(minutes=24),
        holding_intent=intent,
    )
    at_bound = holding_exit_decision(
        trade("XAUUSD", opened),
        now=opened + timedelta(minutes=25),
        holding_intent=intent,
    )

    assert before_bound["due"] is False
    assert before_bound["deadline"] == "2025-01-15T09:25:00+00:00"
    assert at_bound["due"] is True
    assert at_bound["status"] == "MAX_HOLD_EXIT_DUE"


def test_xauusd_overnight_requires_explicit_intent_reason_and_verified_costs():
    opened = datetime(2025, 1, 2, 17, 0, tzinfo=timezone.utc)
    now = datetime(2025, 1, 2, 17, 10, tzinfo=timezone.utc)
    incomplete_intents = (
        {"allow_overnight": True, "reason": "Strategy setup"},
        {
            "allow_overnight": True,
            "reason": "Strategy setup",
            "cost_aware": True,
        },
        {
            "allow_overnight": True,
            "financing_verified": True,
            "cost_aware": True,
        },
    )

    for intent in incomplete_intents:
        decision = holding_exit_decision(
            trade("XAUUSD", opened), now=now, holding_intent=intent
        )
        assert decision["policy"] == "xauusd_no_overnight_rollover_safe"
        assert entry_allowed_by_holding_policy(
            "XAUUSD", now=now, holding_intent=intent
        ) is True

    valid_intent = {
        "allow_overnight": True,
        "reason": "Hold for the strategy's multi-session target",
        "cost_aware": True,
        "financing_verified": True,
        "max_hold_minutes": 180,
    }
    decision = holding_exit_decision(
        trade("XAUUSD", opened), now=now, holding_intent=valid_intent
    )
    assert decision["due"] is False
    assert decision["policy"] == "xauusd_verified_overnight_max_hold"
    assert decision["deadline"] == "2025-01-02T20:00:00+00:00"
    due = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 1, 2, 20, 1, tzinfo=timezone.utc),
        holding_intent=valid_intent,
    )
    assert due["due"] is True


def test_xauusd_verified_overnight_without_bound_still_closes_at_23_utc():
    intent = {
        "allow_overnight": True,
        "reason": "Explicit strategy requirement",
        "cost_awareness": True,
        "account_financing_verified": True,
        "max_hold_minutes": 0,
    }
    decision = holding_exit_decision(
        trade("XAUUSD", datetime(2025, 1, 2, 17, 0, tzinfo=timezone.utc)),
        now=datetime(2025, 1, 2, 23, 1, tzinfo=timezone.utc),
        holding_intent=intent,
    )

    assert decision["due"] is True
    assert decision["status"] == "UTC_SESSION_EXIT_OVERDUE"


def test_gold_rollover_helper_tracks_new_york_dst_and_is_strictly_next():
    summer = datetime(2025, 6, 15, 20, 34, tzinfo=timezone.utc)
    winter = datetime(2025, 1, 15, 21, 34, tzinfo=timezone.utc)
    just_after_summer_rollover = datetime(
        2025, 6, 15, 21, 0, tzinfo=timezone.utc
    )

    assert next_gold_rollover_deadline(summer) == datetime(
        2025, 6, 15, 21, 0, tzinfo=timezone.utc
    )
    assert next_gold_rollover_deadline(winter) == datetime(
        2025, 1, 15, 22, 0, tzinfo=timezone.utc
    )
    assert next_gold_rollover_deadline(just_after_summer_rollover) == datetime(
        2025, 6, 16, 21, 0, tzinfo=timezone.utc
    )


def test_gold_entry_must_fit_full_requested_duration_before_rollover_buffer():
    max_25 = {"max_hold_minutes": 25}
    summer_open = datetime(2025, 6, 15, 20, 34, tzinfo=timezone.utc)
    summer_too_late = datetime(2025, 6, 15, 20, 35, tzinfo=timezone.utc)
    winter_open = datetime(2025, 1, 15, 21, 34, tzinfo=timezone.utc)
    winter_too_late = datetime(2025, 1, 15, 21, 35, tzinfo=timezone.utc)

    assert entry_allowed_by_holding_policy(
        "XAUUSD", now=summer_open, holding_intent=max_25
    )
    assert not entry_allowed_by_holding_policy(
        "XAUUSD", now=summer_too_late, holding_intent=max_25
    )
    assert entry_allowed_by_holding_policy(
        "XAUUSD", now=winter_open, holding_intent=max_25
    )
    assert not entry_allowed_by_holding_policy(
        "XAUUSD", now=winter_too_late, holding_intent=max_25
    )
    assert entry_allowed_by_holding_policy(
        "XAUUSD", now=datetime(2025, 6, 15, 20, 39, tzinfo=timezone.utc)
    )
    assert not entry_allowed_by_holding_policy(
        "XAUUSD", now=datetime(2025, 6, 15, 20, 40, tzinfo=timezone.utc)
    )


def test_gold_due_at_rollover_winddown_and_session_end_remains_a_later_bound():
    opened = datetime(2025, 6, 15, 20, 34, tzinfo=timezone.utc)
    max_25 = {"max_hold_minutes": 25}
    before_winddown = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 6, 15, 20, 58, tzinfo=timezone.utc),
        holding_intent=max_25,
    )
    at_winddown = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 6, 15, 20, 59, tzinfo=timezone.utc),
        holding_intent=max_25,
    )

    assert before_winddown["due"] is False
    assert before_winddown["deadline"] == "2025-06-15T20:59:00+00:00"
    assert at_winddown["due"] is True
    assert at_winddown["status"] == "NY_ROLLOVER_EXIT_DUE"
    assert "fresh quote" in at_winddown["reason"]


def test_gold_rollover_can_precede_longer_max_hold_and_utc_session_end():
    opened = datetime(2025, 6, 15, 20, 30, tzinfo=timezone.utc)
    intent = {"max_hold_minutes": 90}
    decision = holding_exit_decision(
        trade("XAUUSD", opened),
        now=datetime(2025, 6, 15, 20, 59, tzinfo=timezone.utc),
        holding_intent=intent,
    )

    assert decision["due"] is True
    assert decision["status"] == "NY_ROLLOVER_EXIT_DUE"
    assert decision["deadline"] == "2025-06-15T20:59:00+00:00"


def test_gold_after_rollover_uses_tomorrows_rollover_but_same_day_session_end():
    opened = datetime(2025, 6, 15, 22, 10, tzinfo=timezone.utc)
    now = datetime(2025, 6, 15, 22, 20, tzinfo=timezone.utc)
    max_25 = {"max_hold_minutes": 25}
    decision = holding_exit_decision(
        trade("XAUUSD", opened), now=now, holding_intent=max_25
    )

    assert next_gold_rollover_deadline(opened) == datetime(
        2025, 6, 16, 21, 0, tzinfo=timezone.utc
    )
    assert entry_allowed_by_holding_policy(
        "XAUUSD", now=now, holding_intent=max_25
    )
    assert decision["deadline"] == "2025-06-15T22:35:00+00:00"


def test_stocks_have_no_arbitrary_timeout_but_cash_delivery_short_is_rejected():
    decision = holding_exit_decision(
        trade("STOCKS", datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        now=datetime(2025, 1, 10, 15, 0, tzinfo=timezone.utc),
    )

    assert decision["due"] is False
    assert decision["policy"] == "stock_strategy_managed"
    assert entry_allowed_by_holding_policy(
        "STOCKS", now=datetime(2025, 1, 2, 4, 0, tzinfo=timezone.utc)
    )
    assert not entry_allowed_by_holding_policy(
        "STOCKS",
        now=datetime(2025, 1, 2, 4, 0, tzinfo=timezone.utc),
        holding_intent={"side": "SELL"},
    )


def test_closed_trade_and_invalid_now_are_handled_without_mutation():
    closed = trade(
        "OPTIONS",
        datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        status="CLOSED",
    )
    decision = holding_exit_decision(
        closed, now=datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)
    )
    invalid_now = holding_exit_decision(closed, now="not-a-time")

    assert decision["status"] == "NOT_OPEN"
    assert decision["due"] is False
    assert invalid_now["status"] == "POLICY_TIME_INVALID"
    assert invalid_now["due"] is True
    assert closed.status == "CLOSED"