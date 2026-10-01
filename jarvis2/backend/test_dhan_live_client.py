import json
import math
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

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


def quote_record(last_price=101.25):
    return {
        "last_price": last_price,
        "ohlc": {
            "open": 99.5,
            "high": 103.0,
            "low": 98.75,
            "close": 100.0,
        },
        "volume": 1234,
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
        client, _ = self.make_client(
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
        self.assertEqual(put["option_type"], "PE")
        self.assertEqual(put["strike"], 44000.0)

        matched = client.get_option_quote(
            "BANKNIFTY", 44000, "CALL", expiry=expiry
        )
        self.assertEqual(matched["security_id"], 101)
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

    def test_unusable_option_prices_or_stale_chains_cannot_be_selected(self):
        response = option_chain_response()
        response["data"]["oc"]["44000.000000"]["ce"]["top_ask_price"] = 0
        client, _ = self.make_client(
            [FakeResponse(response)],
            option_max_age_seconds=5,
        )
        self.assertIsNotNone(
            client.refresh_option_chain(
                "BANKNIFTY",
                25,
                expiry="2099-01-01",
            )
        )
        # The invalid nearest call is rejected; the next fresh, valid strike is used.
        selected = client.select_atm_option("BANKNIFTY", "BUY")
        self.assertEqual(selected["strike"], 44010.0)
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44000, "CE")
        )

        client._option_received_at["BANKNIFTY"] -= 6
        self.assertIsNone(client.select_atm_option("BANKNIFTY", "BUY"))
        self.assertIsNone(
            client.get_option_quote("BANKNIFTY", 44010, "CE")
        )

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