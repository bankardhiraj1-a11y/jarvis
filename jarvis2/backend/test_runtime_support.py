from datetime import date, datetime, timezone
from types import SimpleNamespace

from trading.runtime_support import (
    daily_trade_review,
    exchange_session_status,
    load_indian_exchange_calendar,
)


def test_official_2026_exchange_calendar_excludes_settlement_and_mcx_only_dates():
    calendar = load_indian_exchange_calendar()

    assert calendar["verified_through"] == "2026-12-31"
    assert "2026-10-02" in calendar["holidays"]
    assert "2026-02-19" not in calendar["holidays"]
    assert "2026-08-15" not in calendar["holidays"]
    assert "2026-11-08" not in calendar["holidays"]
    assert len(calendar["holidays"]) == 16

    holiday = exchange_session_status(
        datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc), calendar
    )
    assert holiday["status"] == "EXCHANGE_HOLIDAY"
    assert holiday["open"] is False
    beyond_coverage = exchange_session_status(
        datetime(2027, 1, 4, 5, 0, tzinfo=timezone.utc), calendar
    )
    assert beyond_coverage["status"] == "CALENDAR_UNKNOWN"
    assert beyond_coverage["open"] is False


def test_daily_review_includes_authentic_gold_gross_but_not_unknown_net():
    trade = SimpleNamespace(
        id=7,
        status="CLOSED",
        data_source="OANDA",
        entry_data_timestamp="2026-10-01T23:58:00Z",
        exit_data_timestamp="2026-10-02T00:03:00Z",
        created_at=datetime(2026, 10, 1, 23, 58),
        closed_at=datetime(2026, 10, 2, 0, 3),
        entry_price=4177.0,
        exit_price=4178.0,
        quantity=100.0,
        trade_type="BUY",
        pnl=None,
    )

    report = daily_trade_review(
        [trade],
        review_date=date(2026, 10, 2),
        calls=12,
        quote_currency="USD",
        session_timezone="UTC",
    )

    assert report["closed_verified_paper_trades"] == 1
    assert report["classified_trades"] == 0
    assert report["unclassified_cost_or_provenance"] == 1
    assert report["gross_price_pnl"] == 100.0
    assert report["win_rate_pct"] is None