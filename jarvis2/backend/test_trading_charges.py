from datetime import datetime, timezone

import pytest

from trading.charges import (
    ChargeInputError,
    calculate_charges,
    charges_for_trade,
    get_charge_rules,
    get_charge_trades,
    sized_stock_entry,
)


_WEEKDAY_CHARGES = {
    "Monday": 1,
    "Tuesday": 1,
    "Wednesday": 3,
    "Thursday": 1,
    "Friday": 1,
    "Saturday": 0,
    "Sunday": 0,
}


def _component(result, code):
    return next(item for item in result["components"] if item["code"] == code)


def test_intraday_calculator_reference_sample_and_buy_sell_quantity_sides():
    buy = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "exchange": "NSE",
        "quantity": 4000,
        "entry_price": 100,
        "exit_price": 110,
    })
    assert _component(buy, "brokerage_entry")["amount"] == 20
    assert _component(buy, "brokerage_exit")["amount"] == 20
    assert _component(buy, "stt_entry")["amount"] == 0
    assert _component(buy, "stt_exit")["amount"] == 110
    assert _component(buy, "exchange_entry")["amount"] == 12.28
    assert _component(buy, "exchange_exit")["amount"] == 13.51
    assert buy["known_additional_charges"] == 200.62
    assert buy["total_additional_charges"] == 200.62
    assert buy["price_pnl_before_additional_fees"] == 40000
    assert buy["net_pnl"] == 39799.38
    assert buy["complete"] is True

    sell = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "exchange": "NSE",
        "quantity": 4000,
        "entry_price": 100,
        "exit_price": 110,
        "side": "SELL",
    })
    assert _component(sell, "stt_entry")["amount"] == 100
    assert _component(sell, "stt_exit")["amount"] == 0
    assert _component(sell, "stamp_duty")["amount"] == 13
    assert sell["price_pnl_before_additional_fees"] == -40000

    half_quantity = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "quantity": 2000,
        "entry_price": 100,
        "exit_price": 110,
    })
    assert half_quantity["known_additional_charges"] < buy["known_additional_charges"]
    assert half_quantity["price_pnl_before_additional_fees"] == 20000


def test_stt_rounding_matches_calculator_not_an_unverified_statutory_rule():
    result = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "quantity": 20,
        "entry_price": 100,
        "exit_price": 100,
    })
    # 0.025% of ₹2,000 = ₹0.50; the official calculator JavaScript Math.round
    # convention displays ₹1. This does not establish a separate statutory rule.
    assert _component(result, "stt_exit")["amount"] == 1
    assert "not a claim about statutory half-rupee rounding" in _component(
        result, "stt_exit"
    )["basis"]

    intermediate_rounding = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 1998.4,
    })
    # ₹0.4996 first rounds to paise (₹0.50), then the calculator displays ₹1.
    assert _component(intermediate_rounding, "stt_exit")["amount"] == 1


def test_delivery_reference_sample_keeps_unknown_dp_fee_partial():
    result = calculate_charges({
        "market": "INDIA",
        "product": "equity_delivery",
        "exchange": "NSE",
        "quantity": 4000,
        "entry_price": 100,
        "exit_price": 110,
    })
    assert _component(result, "brokerage_entry")["amount"] == 0
    assert _component(result, "stt_entry")["amount"] == 400
    assert _component(result, "stt_exit")["amount"] == 440
    assert _component(result, "stamp_duty")["amount"] == 60
    assert result["known_additional_charges"] == 931.42
    assert _component(result, "dp_delivery_sell")["amount"] is None
    assert result["status"] == "partial_estimate"
    assert result["total_additional_charges"] is None
    assert result["net_pnl"] is None
    assert result["net_pnl_after_known_charges"] == 39068.58


def test_delivery_dp_stays_unknown_unless_a_scrip_count_assumption_is_explicit():
    request = {
        "market": "INDIA",
        "product": "equity_delivery",
        "exchange": "NSE",
        "quantity": 10,
        "entry_price": 100,
        "exit_price": 110,
    }
    default = calculate_charges(request)
    assert _component(default, "dp_delivery_sell")["amount"] is None
    assert default["total_additional_charges"] is None

    estimate = calculate_charges(request, dp_scrips=1)
    dp = _component(estimate, "dp_delivery_sell")
    assert dp["amount"] == 15.34
    assert dp["status"] == "assumption"
    assert "not an actual verified account invoice" in dp["basis"]
    assert estimate["complete"] is True


def test_index_option_rates_use_sell_side_015_percent_and_calculator_rounding():
    result = calculate_charges({
        "market": "INDIA",
        "product": "index_options",
        "exchange": "NSE",
        "quantity": 1000,
        "entry_price": 40,
        "exit_price": 44,
        "entry_orders": 1,
        "exit_orders": 1,
    })
    assert _component(result, "stt_entry")["amount"] == 0
    assert _component(result, "stt_exit")["amount"] == 66
    assert _component(result, "exchange_entry")["amount"] == 14.21
    assert _component(result, "exchange_exit")["amount"] == 15.64
    assert _component(result, "stamp_duty")["amount"] == 1
    assert result["known_additional_charges"] == 149.52

    sold = calculate_charges({
        "market": "INDIA",
        "product": "index_options",
        "exchange": "NSE",
        "quantity": 1000,
        "entry_price": 44,
        "exit_price": 40,
        "side": "SELL",
    })
    assert _component(sold, "stt_entry")["amount"] == 66
    assert _component(sold, "stt_exit")["amount"] == 0

    rules = get_charge_rules()
    assert "0.15%" in rules["indian_rules"]["index_options"]["stt"]
    assert any(source["name"].startswith("Government of India") for source in rules["sources"])


def test_bse_equity_unknown_scrip_group_is_never_guessed():
    result = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "exchange": "BSE",
        "quantity": 100,
        "entry_price": 100,
        "exit_price": 101,
    })
    assert _component(result, "exchange_entry")["amount"] is None
    assert _component(result, "gst_entry")["amount"] is None
    assert result["status"] == "partial_estimate"
    assert result["total_additional_charges"] is None
    assert any("BSE equity transaction charges vary" in note for note in result["notes"])


def test_bse_index_option_exchange_and_stamp_rates_are_distinct_from_nse():
    result = calculate_charges({
        "market": "INDIA",
        "product": "index_options",
        "exchange": "BSE",
        "quantity": 1000,
        "entry_price": 40,
        "exit_price": 44,
    })
    assert _component(result, "exchange_entry")["amount"] == 13
    assert _component(result, "exchange_exit")["amount"] == 14.3
    assert _component(result, "stamp_duty")["amount"] == 1
    assert _component(result, "stt_exit")["amount"] == 66
    assert result["complete"] is True


def test_missing_exit_price_is_partial_and_does_not_invent_exit_fees_or_pnl():
    result = calculate_charges({
        "market": "INDIA",
        "product": "equity_intraday",
        "quantity": 10,
        "entry_price": 100,
    })
    assert _component(result, "brokerage_entry")["amount"] == 0.3
    assert _component(result, "brokerage_exit")["amount"] is None
    assert result["price_pnl_before_additional_fees"] is None
    assert result["net_pnl"] is None
    assert result["total_additional_charges"] is None


def test_gold_spread_is_displayed_separately_and_costs_remain_unknown():
    stamp = datetime.now(timezone.utc).isoformat()
    result = calculate_charges(
        {
            "market": "XAUUSD",
            "exchange": "OANDA",
            "quantity": 100,
            "entry_price": 2000,
            "exit_price": 1999,
        },
        gold_quote={
            "source": "OANDA",
            "instrument": "XAU_USD",
            "bid": 1999.9,
            "ask": 2000.1,
            "timestamp": stamp,
            "stale": False,
        },
    )
    assert result["currency"] == "USD"
    assert result["price_pnl_before_additional_fees"] == -100
    assert result["embedded_spread_cost"] == 20
    assert _component(result, "commission_entry")["amount"] is None
    assert _component(result, "financing")["amount"] is None
    assert result["total_additional_charges"] is None
    assert result["net_pnl"] is None
    assert result["net_pnl_after_known_charges"] == -100
    assert any("not deducted a second time" in note for note in result["notes"])


def test_gold_metadata_requires_verified_source_and_sanitizes_private_url():
    metadata = {
        "verified": True,
        "instrument": "XAU_USD",
        "source": {
            "name": "OANDA official schedule",
            "url": "https://www.oanda.com/us-en/pricing/",
        },
        "account_id": "private-account-id",
        "commission_usd_per_million_side": 25,
        "minimum_commission_usd_per_order": 0,
    }
    result = calculate_charges(
        {
            "market": "XAUUSD",
            "quantity": 100,
            "entry_price": 2000,
            "exit_price": 2001,
        },
        gold_cost_metadata=metadata,
    )
    assert _component(result, "commission_entry")["amount"] == 5
    assert _component(result, "commission_exit")["amount"] == 5
    assert _component(result, "financing")["amount"] is None
    assert all("account" not in str(source) and "pricing" not in str(source) for source in result["sources"])
    assert result["status"] == "partial_estimate"


def _gold_cost_metadata(weekday_charges=None):
    metadata = {
        "verified": True,
        "instrument": "XAU_USD",
        "source": "OANDA account instrument metadata",
        "as_of": "2026-10-01T00:00:00Z",
        "long_financing_annual_pct": 365,
        "short_financing_annual_pct": -365,
        "financing_day_basis": 365,
        "commission_usd_per_million_side": 60,
        "minimum_commission_usd_per_order": 1,
    }
    if weekday_charges is not None:
        metadata["weekday_charges"] = weekday_charges
    return metadata


def test_oanda_financing_requires_complete_explicit_weekday_charges():
    incomplete = dict(_WEEKDAY_CHARGES)
    incomplete.pop("Sunday")
    for schedule in (None, incomplete):
        result = calculate_charges({
            "market": "XAUUSD",
            "quantity": 1,
            "entry_price": 100,
            "exit_price": 100,
            "entry_time": "2026-10-03T21:01:00Z",
            "exit_time": "2026-10-04T21:01:00Z",
        }, gold_cost_metadata=_gold_cost_metadata(schedule))
        assert _component(result, "commission_entry")["amount"] == 1
        assert _component(result, "commission_exit")["amount"] == 1
        assert _component(result, "financing")["amount"] is None
        assert result["status"] == "partial_estimate"


def test_oanda_weekday_financing_does_not_double_charge_weekends_and_honors_dst():
    weekend = calculate_charges({
        "market": "XAUUSD",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 100,
        "entry_time": "2026-10-02T21:01:00Z",  # Friday 17:01 EDT
        "exit_time": "2026-10-04T21:01:00Z",   # Sunday 17:01 EDT
    }, gold_cost_metadata=_gold_cost_metadata(_WEEKDAY_CHARGES))
    assert _component(weekend, "financing")["amount"] == 0
    assert "2 New York 17:00 rollover(s), 0 financing day(s)" in _component(
        weekend, "financing"
    )["basis"]
    assert weekend["complete"] is True

    dst_schedule = dict(_WEEKDAY_CHARGES)
    dst_schedule["Sunday"] = 1
    dst = calculate_charges({
        "market": "XAUUSD",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 100,
        "entry_time": "2026-03-08T20:59:00Z",  # Sunday 16:59 EDT after DST switch
        "exit_time": "2026-03-08T21:01:00Z",   # Sunday 17:01 EDT
    }, gold_cost_metadata=_gold_cost_metadata(dst_schedule))
    assert _component(dst, "financing")["amount"] == 1


def test_oanda_weekday_three_day_charge_comes_only_from_verified_schedule():
    result = calculate_charges({
        "market": "XAUUSD",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 100,
        "entry_time": "2026-10-07T20:59:00Z",  # Wednesday 16:59 EDT
        "exit_time": "2026-10-07T21:01:00Z",   # Wednesday 17:01 EDT
    }, gold_cost_metadata=_gold_cost_metadata(_WEEKDAY_CHARGES))
    assert _component(result, "financing")["amount"] == 3
    assert "1 New York 17:00 rollover(s), 3 financing day(s)" in _component(
        result, "financing"
    )["basis"]
    rules = get_charge_rules(gold_cost_metadata=_gold_cost_metadata(_WEEKDAY_CHARGES))
    assert rules["gold"]["cost_metadata"]["financing"] == "verified"
    assert rules["gold"]["cost_metadata"]["weekday_charges"]["SATURDAY"] == 0


def test_oanda_provider_weekday_schedule_shape_is_accepted_without_assuming_commission():
    metadata = _gold_cost_metadata()
    metadata.pop("weekday_charges", None)
    metadata.pop("minimum_commission_usd_per_order", None)
    metadata["financing_days_of_week"] = [
        {
            "day_of_week": day.upper(),
            "weekday": index,
            "days_charged": charged,
        }
        for index, (day, charged) in enumerate(_WEEKDAY_CHARGES.items())
    ]
    result = calculate_charges({
        "market": "XAUUSD",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 100,
        "entry_time": "2026-10-07T20:59:00Z",
        "exit_time": "2026-10-07T21:01:00Z",
    }, gold_cost_metadata=metadata)
    assert _component(result, "financing")["amount"] == 3
    assert _component(result, "commission_entry")["amount"] is None
    rules = get_charge_rules(gold_cost_metadata=metadata)
    assert rules["gold"]["cost_metadata"]["commission"] == "unknown"
    assert rules["gold"]["cost_metadata"]["weekday_charges"]["WEDNESDAY"] == 3


def test_sizing_covers_fees_inside_risk_and_capital_and_applies_net_gate():
    sizing = sized_stock_entry(
        available_capital=100000,
        risk_capital=1000,
        entry_price=100,
        stop_price=95,
        expected_exit_price=110,
        product="equity_intraday",
    )
    assert sizing["accepted"] is True
    assert sizing["quantity"] > 0
    assert sizing["quantity"] * 100 <= sizing["available_capital"]
    assert sizing["estimated_risk_including_known_charges"] <= 1000
    assert sizing["estimated_capital_including_known_charges"] <= 100000
    assert sizing["expected_net_profit"] > 0
    assert sizing["orders_placed"] is False

    gated = sized_stock_entry(
        available_capital=100000,
        risk_capital=1000,
        entry_price=100,
        stop_price=95,
        expected_exit_price=110,
        expected_net_profit_min=100000,
        product="equity_intraday",
    )
    assert gated["quantity"] > 0
    assert gated["accepted"] is False
    assert "does not exceed" in gated["reason"]

    unknown_delivery = sized_stock_entry(
        available_capital=100000,
        risk_capital=1000,
        entry_price=100,
        stop_price=95,
        expected_exit_price=110,
        product="equity_delivery",
    )
    assert unknown_delivery["quantity"] == 0
    assert unknown_delivery["accepted"] is False
    assert unknown_delivery["orders_placed"] is False

    delivery_with_dp_assumption = sized_stock_entry(
        available_capital=100000,
        risk_capital=1000,
        entry_price=100,
        stop_price=95,
        expected_exit_price=110,
        product="equity_delivery",
        dp_scrips=1,
    )
    assert delivery_with_dp_assumption["quantity"] > 0
    assert delivery_with_dp_assumption["accepted"] is True
    assert delivery_with_dp_assumption["estimated_risk_including_known_charges"] <= 1000


def test_trade_serializer_is_pure_and_uses_stock_hold_delivery_reference():
    trade = {
        "id": 12,
        "agent": "STOCKS",
        "symbol": "RELIANCE",
        "trade_type": "BUY",
        "quantity": 10,
        "entry_price": 100,
        "exit_price": 110,
        "status": "CLOSED",
    }
    output = get_charge_trades([trade])
    assert output["trades"][0]["trade_id"] == 12
    assert output["trades"][0]["currency"] == "INR"
    assert _component(output["trades"][0]["charges"], "dp_delivery_sell")["amount"] is None
    assert charges_for_trade(trade)["status"] == "partial_estimate"

    sensex_option = {
        "id": 13,
        "agent": "SENSEX_OPTIONS_SCALPING",
        "symbol": "SENSEX",
        "trade_type": "BUY",
        "quantity": 20,
        "entry_price": 100,
        "exit_price": 110,
        "option_strike": "80000",
        "status": "CLOSED",
    }
    sensex_result = charges_for_trade(sensex_option)
    assert _component(sensex_result, "exchange_entry")["basis"].startswith("BSE rate")
    assert _component(sensex_result, "stamp_duty")["basis"].startswith("BSE buy-side")


def test_gold_trade_serializer_treats_persisted_naive_datetimes_as_utc():
    # In-memory ORM-shaped row only; no database write or live position lookup.
    trade = {
        "id": 99,
        "agent": "XAUUSD",
        "symbol": "XAUUSD",
        "trade_type": "BUY",
        "quantity": 1,
        "entry_price": 100,
        "exit_price": 100,
        "status": "CLOSED",
        "created_at": datetime(2026, 10, 7, 20, 59),  # Legacy datetime.utcnow() storage.
        "closed_at": datetime(2026, 10, 7, 21, 1),
    }
    result = charges_for_trade(
        trade,
        gold_cost_metadata=_gold_cost_metadata(_WEEKDAY_CHARGES),
    )
    assert _component(result, "financing")["amount"] == 3
    assert "1 New York 17:00 rollover(s), 3 financing day(s)" in _component(
        result, "financing"
    )["basis"]
    assert any("interpreted as UTC" in note for note in result["notes"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"quantity": 0},
        {"quantity": float("inf")},
        {"entry_price": float("nan")},
        {"entry_price": 0},
        {"exit_price": 0},
        {"side": "HOLD"},
        {"entry_orders": 1.2},
        {"exit_orders": True},
        {"dp_scrips": 0},
        {"dp_scrips": True},
        {"entry_time": "2026-10-01T12:00:00"},
        {"market": []},
        {"exit_time": "2026-10-01T12:00:00Z"},
    ],
)
def test_invalid_inputs_raise_explicit_validation_error(overrides):
    request = {
        "market": "INDIA",
        "product": "equity_intraday",
        "quantity": 1,
        "entry_price": 100,
    }
    request.update(overrides)
    with pytest.raises(ChargeInputError):
        calculate_charges(request)
