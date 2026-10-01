import json
import math
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from data.dhan_live_client import DhanLiveClient


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.closed = False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class ProfileFakeSession(FakeSession):
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        return self.responses.pop(0)


def quote_record(last_price=101.25, bid=100.0, ask=102.0):
    return {
        "last_price": last_price,
        "last_trade_time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
        "ohlc": {
            "open": 99.5,
            "high": 103.0,
            "low": 98.75,
            "close": 100.0,
        },
        "volume": 1234,
        "depth": {
            "buy": [{"price": bid, "quantity": 25, "orders": 1}],
            "sell": [{"price": ask, "quantity": 40, "orders": 1}],
        },
    }


def option_quote_response(security_id, last_price, bid, ask):
    return {
        "status": "success",
        "data": {
            "NSE_FNO": {
                str(security_id): quote_record(last_price, bid, ask),
            },
        },
    }


def option_contract(security_id, last_price, bid, ask):
    return {
        "security_id": security_id,
        "last_price": last_price,
        "top_bid_price": bid,
        "top_ask_price": ask,
        "volume": 500,
        "oi": 1800,
        "greeks": {
            "delta": 0.52,
            "theta": -8.0,
            "gamma": 0.001,
            "vega": 14.0,
        },
    }


def option_chain_response(underlying_price=44005.0):
    return {
        "status": "success",
        "data": {
            "last_price": underlying_price,
            "oc": {
                "44000.000000": {
                    "ce": option_contract(101, 102.0, 100.0, 104.0),
                    "pe": option_contract(102, 98.0, 96.0, 100.0),
                },
                "44010.000000": {
                    "ce": option_contract(103, 95.0, 93.0, 97.0),
                    "pe": option_contract(104, 106.0, 104.0, 108.0),
                },
            },
        },
    }


class DhanLiveClientTests(unittest.TestCase):
    def make_client(self, responses=None, **kwargs):
        env = {
            "DHAN_CLIENT_ID": "test-client-id",
            "DHAN_ACCESS_TOKEN": "test-access-token",
        }
        with patch.dict("os.environ", env, clear=False):
            session = FakeSession(responses)
            client = DhanLiveClient(session=session, **kwargs)
        elapsed = [0.0]
        client._monotonic = lambda: elapsed[0]
        client._sleep = lambda seconds: elapsed.__setitem__(
            0, elapsed[0] + seconds
        )
        return client, session

    def test_token_only_profile_resolves_client_id_for_read_only_quote(self):
        quote = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        session = ProfileFakeSession(
            [
                FakeResponse({"dhanClientId": "private-account-id"}),
                FakeResponse(quote),
            ]
        )
        with patch.dict(
            "os.environ",
            {"DHAN_ACCESS_TOKEN": "test-access-token"},
            clear=False,
        ):
            os.environ.pop("DHAN_CLIENT_ID", None)
            client = DhanLiveClient(session=session)
        elapsed = [0.0]
        client._monotonic = lambda: elapsed[0]
        client._sleep = lambda seconds: elapsed.__setitem__(
            0, elapsed[0] + seconds
        )

        self.assertTrue(
            client.refresh_quotes(
                [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
            )
        )
        self.assertEqual(
            [call[0] for call in session.calls],
            [
                "https://api.dhan.co/v2/profile",
                "https://api.dhan.co/v2/marketfeed/quote",
            ],
        )
        profile_headers = session.calls[0][1]["headers"]
        self.assertEqual(profile_headers, {
            "access-token": "test-access-token",
            "Accept": "application/json",
        })
        quote_headers = session.calls[1][1]["headers"]
        self.assertEqual(quote_headers["client-id"], "private-account-id")
        self.assertEqual(quote_headers["access-token"], "test-access-token")
        self.assertNotIn("private-account-id", client.get_market_snapshot().__repr__())

    def test_token_only_profile_failure_does_not_try_market_feed(self):
        session = ProfileFakeSession(
            [FakeResponse({"message": "unauthorized"}, 401)]
        )
        with patch.dict(
            "os.environ",
            {"DHAN_ACCESS_TOKEN": "test-access-token"},
            clear=False,
        ):
            os.environ.pop("DHAN_CLIENT_ID", None)
            client = DhanLiveClient(session=session)
        self.assertFalse(
            client.refresh_quotes(
                [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
            )
        )
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][0], "https://api.dhan.co/v2/profile")
        self.assertNotIn("private-account-id", str(client.last_error))

    def test_profile_identity_overrides_mismatched_configured_client_id(self):
        configured_id = "configured-fixture-id"
        profile_id = "profile-fixture-id"
        response = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        session = ProfileFakeSession(
            [
                FakeResponse({"dhanClientId": profile_id}),
                FakeResponse(response),
            ]
        )
        with patch.dict(
            "os.environ",
            {
                "DHAN_CLIENT_ID": configured_id,
                "DHAN_ACCESS_TOKEN": "test-access-token",
            },
            clear=False,
        ):
            client = DhanLiveClient(session=session)

        self.assertTrue(
            client.refresh_quotes(
                [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
            )
        )
        self.assertEqual(
            [call[0] for call in session.calls],
            [
                "https://api.dhan.co/v2/profile",
                "https://api.dhan.co/v2/marketfeed/quote",
            ],
        )
        quote_headers = session.calls[1][1]["headers"]
        self.assertEqual(quote_headers["client-id"], profile_id)
        self.assertNotEqual(quote_headers["client-id"], configured_id)

    def test_concurrent_collectors_wait_for_the_verified_profile_identity(self):
        started, release = Event(), Event()
        class DelayedProfileSession:
            def get(self, url, **kwargs):
                started.set()
                assert release.wait(2)
                return FakeResponse({"dhanClientId": "verified-fixture-id"})
        with patch.dict("os.environ", {
            "DHAN_CLIENT_ID": "wrong-fixture-id",
            "DHAN_ACCESS_TOKEN": "fixture-token",
        }):
            client = DhanLiveClient(session=DelayedProfileSession())
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(lambda: client._has_credentials)
            assert started.wait(2)
            second = pool.submit(lambda: client._has_credentials)
            assert not second.done()
            release.set()
            assert first.result(2)
            assert second.result(2)
        self.assertEqual(client._client_id, "verified-fixture-id")

    def test_dashboard_cache_reads_do_not_resolve_profile_over_http(self):
        session = ProfileFakeSession([])
        with patch.dict("os.environ", {
            "DHAN_CLIENT_ID": "",
            "DHAN_ACCESS_TOKEN": "fixture-token",
        }):
            client = DhanLiveClient(session=session)
        client.get_live_data(1333, "HDFCBANK", "NSE_EQ")
        client.get_market_snapshot()
        self.assertEqual(session.calls, [])

    def test_configured_id_fallback_stops_after_market_feed_401(self):
        configured_id = "configured-fixture-id"
        quote = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        instruments = [
            {"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}
        ]

        # If profile lookup is unavailable, a configured ID can still be
        # verified against a successful read-only quote request.
        valid_fallback_session = ProfileFakeSession(
            [
                FakeResponse({"message": "not found"}, 404),
                FakeResponse(quote),
            ]
        )
        with patch.dict(
            "os.environ",
            {
                "DHAN_CLIENT_ID": configured_id,
                "DHAN_ACCESS_TOKEN": "test-access-token",
            },
            clear=False,
        ):
            valid_fallback_client = DhanLiveClient(session=valid_fallback_session)
        self.assertTrue(valid_fallback_client.refresh_quotes(instruments))
        self.assertEqual(
            valid_fallback_session.calls[1][1]["headers"]["client-id"],
            configured_id,
        )

        rejected_session = ProfileFakeSession(
            [
                FakeResponse({"message": "not found"}, 404),
                FakeResponse({"message": "unauthorized"}, 401),
            ]
        )
        with patch.dict(
            "os.environ",
            {
                "DHAN_CLIENT_ID": configured_id,
                "DHAN_ACCESS_TOKEN": "test-access-token",
            },
            clear=False,
        ):
            rejected_client = DhanLiveClient(session=rejected_session)
        self.assertFalse(rejected_client.refresh_quotes(instruments))
        self.assertFalse(rejected_client.refresh_quotes(instruments))
        self.assertEqual(len(rejected_session.calls), 2)
        self.assertEqual(rejected_client._client_id, "")

    def test_batch_quote_payload_headers_and_normalization(self):
        response = {
            "status": "success",
            "data": {
                "NSE_EQ": {"1333": quote_record()},
                "IDX_I": {"51": quote_record(78000.5)},
            },
        }
        client, session = self.make_client([FakeResponse(response)])

        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = client.refresh_quotes(
                [
                    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1333", "Symbol": "HDFCBANK"},
                    {"ExchangeSegment": "IDX_I", "SecurityId": "51", "Symbol": "SENSEX"},
                ]
            )

        self.assertTrue(result)
        self.assertEqual(len(session.calls), 1)
        url, request = session.calls[0]
        self.assertEqual(url, "https://api.dhan.co/v2/marketfeed/quote")
        self.assertEqual(
            request["json"],
            {"NSE_EQ": [1333], "IDX_I": [51]},
        )
        self.assertEqual(request["headers"]["client-id"], "test-client-id")
        self.assertEqual(request["headers"]["access-token"], "test-access-token")
        self.assertNotIn("test-access-token", output.getvalue())
        self.assertNotIn("test-client-id", output.getvalue())

        quote = client.get_live_data("1333", "HDFCBANK", "NSE_EQ")
        self.assertEqual(quote["close"], 101.25)
        self.assertEqual(quote["open"], 99.5)
        self.assertEqual(quote["high"], 103.0)
        self.assertEqual(quote["low"], 98.75)
        self.assertEqual(quote["volume"], 1234)
        self.assertFalse(quote["stale"])
        self.assertGreaterEqual(quote["age_seconds"], 0)
        self.assertTrue(quote["timestamp"])

        snapshot = client.get_market_snapshot()
        self.assertEqual(snapshot["status"], "live")
        self.assertIn("SENSEX", snapshot["prices"])
        serialized = json.dumps(snapshot)
        self.assertNotIn("test-access-token", serialized)
        self.assertNotIn("test-client-id", serialized)

    def test_missing_credentials_do_not_request_or_create_prices(self):
        session = FakeSession()
        with patch.dict(
            "os.environ",
            {"DHAN_CLIENT_ID": "", "DHAN_ACCESS_TOKEN": ""},
            clear=False,
        ):
            client = DhanLiveClient(session=session)

        self.assertFalse(
            client.refresh_quotes(
                [{"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"}]
            )
        )
        self.assertEqual(session.calls, [])
        quote = client.get_live_data("1333", "HDFCBANK")
        self.assertIsNone(quote["close"])
        self.assertTrue(quote["stale"])
        self.assertEqual(client.get_market_snapshot()["status"], "credentials_missing")

    def test_invalid_quote_and_api_errors_fail_closed(self):
        invalid = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record(math.nan)}},
        }
        client, session = self.make_client(
            [
                FakeResponse(invalid),
                FakeResponse({"status": "failure", "data": {}}, status_code=200),
                FakeResponse({"status": "success"}, status_code=503),
            ]
        )
        instruments = [{"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"}]

        self.assertFalse(client.refresh_quotes(instruments))
        self.assertFalse(client.refresh_quotes(instruments))
        self.assertFalse(client.refresh_quotes(instruments))
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(client.latest_prices, {})
        self.assertIsNone(client.get_live_data("1333")["close"])
        self.assertNotIn("test-access-token", client.last_error or "")

    def test_quote_batch_spacing_is_enforced(self):
        response = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        client, _ = self.make_client([FakeResponse(response), FakeResponse(response)])
        elapsed = [0.0]
        client._monotonic = lambda: elapsed[0]
        client._sleep = lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)
        instruments = [{"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"}]

        self.assertTrue(client.refresh_quotes(instruments))
        self.assertTrue(client.refresh_quotes(instruments))
        self.assertGreaterEqual(elapsed[0], 1.0)

    def test_stale_quotes_are_explicitly_marked(self):
        response = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        client, session = self.make_client(
            [FakeResponse(response)],
            quote_max_age_seconds=5,
        )
        self.assertTrue(
            client.refresh_quotes(
                [{"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"}]
            )
        )
        client._quote_received_at["1333"] -= 6

        quote = client.get_live_data("1333")
        self.assertTrue(quote["stale"])
        self.assertGreater(quote["age_seconds"], 5)
        self.assertIsNone(quote["close"])
        self.assertIsNone(quote["open"])

    def test_failed_refresh_invalidates_previously_cached_quote(self):
        response = {
            "status": "success",
            "data": {"NSE_EQ": {"1333": quote_record()}},
        }
        client, _ = self.make_client(
            [
                FakeResponse(response),
                FakeResponse({"status": "failure"}, status_code=503),
            ]
        )
        instruments = [{"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"}]

        self.assertTrue(client.refresh_quotes(instruments))
        self.assertEqual(client.get_live_data("1333")["close"], 101.25)
        self.assertFalse(client.refresh_quotes(instruments))
        self.assertIsNone(client.get_live_data("1333")["close"])
        self.assertNotIn("1333", client.latest_prices)

    def test_expiry_list_and_option_chain_use_documented_payloads_and_match_expiry(self):
        expiry = (date.today() + timedelta(days=7)).isoformat()
        client, session = self.make_client(
            [
                FakeResponse({"status": "success", "data": [expiry]}),
                FakeResponse(option_chain_response()),
                FakeResponse(option_quote_response(101, 102.0, 100.0, 104.0)),
                FakeResponse(option_quote_response(102, 98.0, 96.0, 100.0)),
            ]
        )

        chain = client.refresh_option_chain("BANKNIFTY", 25)
        self.assertIsNotNone(chain)
        self.assertEqual(chain["expiry"], expiry)
        self.assertEqual(chain["underlying_price"], 44005.0)
        self.assertEqual(chain["options"]["44000"]["CE"]["security_id"], 101)

        expiry_url, expiry_request = session.calls[0]
        self.assertEqual(
            expiry_url,
            "https://api.dhan.co/v2/optionchain/expirylist",
        )
        self.assertEqual(
            expiry_request["json"],
            {"UnderlyingScrip": 25, "UnderlyingSeg": "IDX_I"},
        )
        chain_url, chain_request = session.calls[1]
        self.assertEqual(chain_url, "https://api.dhan.co/v2/optionchain")
        self.assertEqual(
            chain_request["json"],
            {
                "UnderlyingScrip": 25,
                "UnderlyingSeg": "IDX_I",
                "Expiry": expiry,
            },
        )
        self.assertEqual(
            expiry_request["headers"]["access-token"],
            "test-access-token",
        )
        self.assertEqual(
            chain_request["headers"]["client-id"],
            "test-client-id",
        )

        call = client.select_atm_option("BANKNIFTY", "BUY")
        put = client.select_atm_option("BANKNIFTY", "SELL")
        self.assertEqual(call["option_type"], "CE")
        self.assertEqual(call["strike"], 44000.0)
        self.assertEqual(call["expiry"], expiry)
        self.assertEqual(call["security_id"], 101)
        self.assertEqual(call["source"], "option_chain")
        self.assertNotIn("bid", call)
        self.assertNotIn("close", call)
        self.assertEqual(put["option_type"], "PE")
        self.assertEqual(put["strike"], 44000.0)
        self.assertEqual(len(session.calls), 2)

        call_quote = client.refresh_option_quote(
            "BANKNIFTY",
            strike=call["strike"],
            option_type=call["option_type"],
            expiry=call["expiry"],
        )
        put_quote = client.refresh_option_quote(
            "BANKNIFTY",
            strike=put["strike"],
            option_type=put["option_type"],
            expiry=put["expiry"],
        )
        self.assertEqual(call_quote["option_type"], "CE")
        self.assertEqual(put_quote["option_type"], "PE")
        self.assertEqual(call_quote["timestamp_basis"], "exchange")
        self.assertNotEqual(call_quote["timestamp"], call_quote["observed_at"])

        matched = client.get_option_quote(
            "BANKNIFTY", 44000, "CALL", expiry=expiry
        )
        self.assertEqual(matched["security_id"], 101)
        self.assertEqual(len(session.calls), 4)
        self.assertIsNone(
            client.get_option_quote(
                "BANKNIFTY",
                44000,
                "CE",
                expiry="2099-01-01",
            )
        )

    def test_option_requests_share_three_second_global_spacing(self):
        expiry = (date.today() + timedelta(days=7)).isoformat()
        client, _ = self.make_client(
            [
                FakeResponse({"status": "success", "data": [expiry]}),
                FakeResponse(option_chain_response()),
            ]
        )
        elapsed = [0.0]
        client._monotonic = lambda: elapsed[0]
        client._sleep = lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)

        self.assertIsNotNone(client.refresh_option_chain("BANKNIFTY", 25))
        self.assertGreaterEqual(elapsed[0], 3.0)

    def test_chain_identity_selection_is_independent_of_chain_prices(self):
        response = option_chain_response()
        response["data"]["oc"]["44000.000000"]["ce"]["top_ask_price"] = 0
        client, session = self.make_client(
            [
                FakeResponse(response),
                FakeResponse(option_quote_response(101, 102.0, 100.0, 104.0)),
            ],
            option_max_age_seconds=5,
        )
        self.assertIsNotNone(
            client.refresh_option_chain(
                "BANKNIFTY",
                25,
                expiry="2099-01-01",
            )
        )
        # ATM selection returns a contract identity; chain prices need not be
        # executable because the explicit quote refresh supplies the live mark.
        selected = client.select_atm_option("BANKNIFTY", "BUY")
        self.assertEqual(selected["strike"], 44000.0)
        self.assertEqual(selected["security_id"], 101)
        self.assertEqual(len(session.calls), 1)
        refreshed = client.refresh_option_quote(
            "BANKNIFTY",
            strike=selected["strike"],
            option_type=selected["option_type"],
            expiry=selected["expiry"],
        )
        self.assertEqual(refreshed["security_id"], 101)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(
            client.get_option_quote("BANKNIFTY", 44000, "CE")["security_id"],
            101,
        )
        self.assertEqual(len(session.calls), 2)
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44010, "CE")
        )

        client._option_received_at[("BANKNIFTY", "2099-01-01")] -= 6
        self.assertIsNone(client.select_atm_option("BANKNIFTY", "BUY"))
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44010, "CE")
        )

    def test_option_quote_getter_never_requests_http_for_missing_or_stale_data(self):
        expiry = (date.today() + timedelta(days=7)).isoformat()
        client, session = self.make_client(
            [
                FakeResponse(option_chain_response()),
                FakeResponse(option_quote_response(101, 102.0, 100.0, 104.0)),
            ],
            option_max_age_seconds=5,
        )

        # An absent chain/quote is simply absent; a GET-style accessor never
        # attempts to populate it from Dhan.
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44000, "CE", expiry=expiry)
        )
        self.assertIsNone(client.select_atm_option("BANKNIFTY", "BUY"))
        self.assertEqual(session.calls, [])

        self.assertIsNotNone(
            client.refresh_option_chain("BANKNIFTY", 25, expiry=expiry)
        )
        calls_after_chain = len(session.calls)
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 45000, "CE", expiry=expiry)
        )
        identity = client.select_atm_option("BANKNIFTY", "BUY")
        self.assertEqual(identity["security_id"], 101)
        self.assertEqual(len(session.calls), calls_after_chain)

        self.assertIsNotNone(
            client.refresh_option_quote(
                "BANKNIFTY",
                strike=identity["strike"],
                option_type=identity["option_type"],
                expiry=identity["expiry"],
            )
        )
        calls_after_explicit_refresh = len(session.calls)
        cache_key = ("BANKNIFTY", expiry, "44000", "CE")
        client._option_quote_received_at[cache_key] -= 6
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44000, "CE", expiry=expiry)
        )
        self.assertEqual(len(session.calls), calls_after_explicit_refresh)

        client._option_received_at[("BANKNIFTY", expiry)] -= 6
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44000, "CE", expiry=expiry)
        )
        self.assertIsNone(client.select_atm_option("BANKNIFTY", "BUY"))
        self.assertEqual(len(session.calls), calls_after_explicit_refresh)

    def test_failed_option_response_does_not_cache_a_chain(self):
        client, session = self.make_client(
            [FakeResponse({"status": "failure", "data": {}})]
        )
        chain = client.refresh_option_chain(
            "BANKNIFTY",
            25,
            expiry="2099-01-01",
        )
        self.assertIsNone(chain)
        self.assertEqual(client.option_chains, {})
        self.assertEqual(session.calls[0][0], "https://api.dhan.co/v2/optionchain")


if __name__ == "__main__":
    unittest.main()