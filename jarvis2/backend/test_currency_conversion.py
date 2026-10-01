"""Tests for sourced FX conversion; ECB/network responses are tested with fixtures."""

import json
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.currency_conversion import (
    ECB_SERIES,
    EcbUsdInrRateProvider,
    consolidate_pnl_currencies,
    gold_lot_display,
    gold_quantity_from_lots,
)


class FakeResponse:
    def __init__(self, csv_text, status_code=200):
        self.text = csv_text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("fixture HTTP error")


def reference_csv(series_key, currency, rate_rows):
    result = (
        '"KEY","FREQ","CURRENCY","CURRENCY_DENOM","EXR_TYPE","EXR_SUFFIX",'
        '"TIME_PERIOD","OBS_VALUE"\n'
    )
    return result + "".join(
        f'"{series_key}","D","{currency}","EUR","SP00","A","{day}","{rate}"\n'
        for day, rate in rate_rows
    )


class FakeSession:
    def __init__(self, *, statuses=None, fail=False):
        self.statuses = statuses or {}
        self.fail = fail
        self.calls = []
        self.closed = False

    def get(self, url, *, params, headers, timeout):
        self.calls.append({
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        })
        if self.fail:
            raise requests.Timeout("fixture error; no secrets in the exception")
        key = url.rsplit("/", 1)[-1]
        currency, series_key = (
            ("USD", ECB_SERIES["usd_per_eur"])
            if key == ECB_SERIES["usd_per_eur"]
            else ("INR", ECB_SERIES["inr_per_eur"])
        )
        return FakeResponse(reference_csv(
            series_key, currency, self.statuses.get(currency, [])
        ))

    def close(self):
        self.closed = True


class TimeoutOnceSession(FakeSession):
    def __init__(self, *, statuses):
        super().__init__(statuses=statuses)
        self.timed_out = False

    def get(self, url, *, params, headers, timeout):
        if not self.timed_out:
            self.timed_out = True
            self.calls.append({
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            })
            raise requests.Timeout("transient fixture timeout")
        return super().get(url, params=params, headers=headers, timeout=timeout)


class CurrencyConversionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        self.date = "2026-09-30"
        self.session = FakeSession(statuses={
            "USD": [(self.date, "1.1355")],
            "INR": [(self.date, "108.8205")],
        })
        self.provider = EcbUsdInrRateProvider(session=self.session)

    def test_fetches_official_matching_series_and_calculates_usd_to_inr(self):
        snapshot = self.provider.refresh(now=self.now)
        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["source_date"], self.date)
        self.assertAlmostEqual(snapshot["rate"], 108.8205 / 1.1355, places=7)
        self.assertEqual(snapshot["source"], "European Central Bank daily reference rates")
        self.assertEqual(snapshot["rate_type"], "daily_reference_not_executable")
        self.assertEqual(len(self.session.calls), 2)
        self.assertEqual(snapshot["conversion_method"], "same_date_inr_per_eur_divided_by_usd_per_eur")
        self.assertEqual(snapshot["source_series"]["usd_per_eur"], "D.USD.EUR.SP00.A")
        self.assertIn(
            "/service/data/EXR/D.USD.EUR.SP00.A",
            snapshot["source_observation_urls"]["usd_per_eur"],
        )
        self.assertTrue(all(
            isinstance(call["timeout"], tuple)
            and 0 < call["timeout"][0] <= call["timeout"][1]
            for call in self.session.calls
        ))
        self.assertTrue(all(
            call["headers"]["User-Agent"]
            for call in self.session.calls
        ))
        self.assertNotIn("/EXR/EXR.", self.session.calls[0]["url"])
        self.assertTrue(all(
            call["params"]["format"] == "csvdata"
            for call in self.session.calls
        ))
        pnl = consolidate_pnl_currencies(
            realized_inr=0,
            realized_usd=1,
            unrealized_inr=0,
            unrealized_usd=0,
            fx_snapshot=snapshot,
        )
        self.assertEqual(
            pnl["usd_inr_conversion"]["source_observation_urls"],
            snapshot["source_observation_urls"],
        )
        self.assertEqual(
            pnl["usd_inr_conversion"]["conversion_method"],
            snapshot["conversion_method"],
        )

    def test_one_transient_timeout_is_retried_once_then_real_series_is_used(self):
        session = TimeoutOnceSession(statuses={
            "USD": [(self.date, "1.1355")],
            "INR": [(self.date, "108.8205")],
        })
        snapshot = EcbUsdInrRateProvider(session=session).refresh(now=self.now)
        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["source_date"], self.date)
        self.assertAlmostEqual(snapshot["rate"], 95.83487450, places=8)
        self.assertEqual(len(session.calls), 3)

    def test_cached_read_never_requests_network_and_exposes_sanitized_metadata(self):
        self.provider.refresh(now=self.now)
        calls_before = len(self.session.calls)
        snapshot = self.provider.get_snapshot(now=self.now)
        self.assertEqual(len(self.session.calls), calls_before)
        safe = json.dumps(snapshot)
        self.assertNotIn("account", safe.lower())
        self.assertNotIn("token", safe.lower())

    def test_refresh_requires_same_observation_date(self):
        self.session.statuses["INR"] = [("2026-09-29", "108.991")]
        failed = self.provider.refresh(now=self.now)
        self.assertEqual(failed["status"], "unavailable")
        self.assertIsNone(failed["rate"])
        self.assertEqual(failed["reason"], "ecb_reference_refresh_failed")

    def test_rates_fail_closed_when_stale_and_do_not_convert_nonzero_usd(self):
        snapshot = self.provider.refresh(now=self.now)
        ten_days_later = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
        stale = self.provider.get_snapshot(now=ten_days_later)
        self.assertEqual(stale["status"], "stale")
        self.assertIsNone(stale["rate"])
        pnl = consolidate_pnl_currencies(
            realized_inr=500,
            realized_usd=10,
            unrealized_inr=-20,
            unrealized_usd=-2,
            fx_snapshot=stale,
        )
        self.assertIsNone(pnl["total_pnl_inr"])
        self.assertEqual(pnl["pnl_by_currency"]["total"]["INR"], None)
        self.assertEqual(pnl["pnl_by_currency"]["total"]["USD"], 8)
        self.assertEqual(pnl["usd_inr_conversion"]["total_pnl_conversion"], "fx_rate_unavailable_or_stale")

    def test_zero_usd_consolidates_even_without_a_rate(self):
        pnl = consolidate_pnl_currencies(
            realized_inr=100.005,
            realized_usd=0,
            unrealized_inr=-30,
            unrealized_usd=0,
            fx_snapshot={"status": "unavailable", "rate": None},
        )
        self.assertEqual(pnl["total_pnl_inr"], 70.01)
        self.assertEqual(pnl["pnl_by_currency"]["total"]["USD"], 0.0)
        self.assertEqual(pnl["usd_inr_conversion"]["total_pnl_conversion"], "not_required")

    def test_mixed_positive_negative_currency_sums_keep_units_and_rate(self):
        snapshot = {
            "status": "available",
            "rate": 80.5,
            "source": "test-only reference fixture",
            "source_date": "2026-09-30",
        }
        pnl = consolidate_pnl_currencies(
            realized_inr=1000,
            realized_usd=-10,
            unrealized_inr=-250,
            unrealized_usd=5,
            fx_snapshot=snapshot,
        )
        self.assertEqual(pnl["pnl_by_currency"]["realized"], {"INR": 1000.0, "USD": -10.0})
        self.assertEqual(pnl["pnl_by_currency"]["unrealized"], {"INR": -250.0, "USD": 5.0})
        self.assertEqual(pnl["pnl_by_currency"]["total"], {"INR": 347.5, "USD": -5.0})
        self.assertEqual(pnl["total_pnl_inr"], 347.5)
        self.assertEqual(pnl["usd_inr_conversion"]["rate"], 80.5)

    def test_lot_to_ounce_is_one_hundred_to_one_not_a_hundred_lots(self):
        self.assertEqual(gold_quantity_from_lots(1), 100.0)
        self.assertEqual(gold_lot_display(100), {
            "quantity": 100.0,
            "quantity_unit": "troy_ounce",
            "quantity_currency": "USD",
            "quantity_lots": 1.0,
            "quantity_troy_ounces": 100.0,
            "lot_size_troy_ounces": 100,
        })
        self.assertEqual(gold_quantity_from_lots(0.5), 50.0)
        with self.assertRaises(ValueError):
            gold_quantity_from_lots(0)

    def test_validation_rejects_nonfinite_money_and_rates(self):
        with self.assertRaises(ValueError):
            consolidate_pnl_currencies(
                realized_inr=float("nan"),
                realized_usd=1,
                unrealized_inr=0,
                unrealized_usd=0,
                fx_snapshot={"status": "available", "rate": 80},
            )
        pnl = consolidate_pnl_currencies(
            realized_inr=0,
            realized_usd=1,
            unrealized_inr=0,
            unrealized_usd=0,
            fx_snapshot={"status": "available", "rate": Decimal("Infinity")},
        )
        self.assertIsNone(pnl["total_pnl_inr"])
        self.assertEqual(pnl["usd_inr_conversion"]["total_pnl_conversion"], "fx_rate_unavailable_or_stale")

    def test_refresh_failure_does_not_replace_existing_snapshot_with_bad_data(self):
        self.provider.refresh(now=self.now)
        self.session.fail = True
        result = self.provider.refresh(now=self.now)
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["reason"], "ecb_reference_refresh_failed")
        self.assertEqual(result["source_date"], self.date)
        calls_after_failure = len(self.session.calls)
        cached = self.provider.get_snapshot(now=self.now)
        self.assertEqual(cached["reason"], "ecb_reference_refresh_failed")
        self.assertEqual(len(self.session.calls), calls_after_failure)

    def test_failed_initial_refresh_reason_persists_on_cached_reads(self):
        self.session.fail = True
        snapshot = self.provider.refresh(now=self.now)
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertEqual(snapshot["rate"], None)
        self.assertEqual(snapshot["reason"], "ecb_reference_refresh_failed")
        requests_after_failure = len(self.session.calls)
        cached = self.provider.get_snapshot(now=self.now)
        self.assertEqual(cached["reason"], "ecb_reference_refresh_failed")
        self.assertEqual(len(self.session.calls), requests_after_failure)
        self.assertEqual(requests_after_failure, 2)


if __name__ == "__main__":
    unittest.main()