import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from data.oanda_pricing import OandaPricingClient


class OandaPricingTests(unittest.TestCase):
    def client(self):
        with patch.dict("os.environ", {
            "OANDA_ACCESS_TOKEN": "test-fixture-not-a-credential",
            "OANDA_ACCOUNT_ID": "test-account", "OANDA_ENVIRONMENT": "practice",
        }):
            client = OandaPricingClient()
        client._session = Mock()
        return client

    def response(self, age=0, bid="2500", ask="2501", tradeable=True):
        return {"prices": [{
            "instrument": "XAU_USD", "tradeable": tradeable,
            "time": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat(),
            "bids": [{"price": bid}], "asks": [{"price": ask}],
        }]}

    def test_actual_bid_ask_and_provider_timestamp(self):
        client = self.client()
        client._session.get.return_value = Mock(status_code=200, json=lambda: self.response())
        quote = client.get_live_data()
        self.assertEqual(quote["close"], 2500.5)
        self.assertEqual(quote["source"], "OANDA")
        self.assertFalse(quote["stale"])
        self.assertIn("/pricing", client._session.get.call_args.args[0])

    def test_stale_missing_and_closed_quotes_fail_closed(self):
        for body in (self.response(age=60), self.response(tradeable=False), {"prices": []}):
            client = self.client()
            client._session.get.return_value = Mock(status_code=200, json=lambda: body)
            self.assertIsNone(client.get_live_data()["close"])
            self.assertEqual(client.latest_prices, {})

    def test_crossed_or_invalid_prices_rejected(self):
        for bid, ask in (("2502", "2501"), ("nan", "2501"), ("0", "2501")):
            client = self.client()
            client._session.get.return_value = Mock(
                status_code=200, json=lambda: self.response(bid=bid, ask=ask))
            self.assertIsNone(client.get_live_data()["close"])

    def test_provider_error_never_leaks_body(self):
        client = self.client()
        client._session.get.return_value = Mock(status_code=401, text="sensitive-body")
        quote = client.get_live_data()
        self.assertNotIn("sensitive-body", str(quote))
        self.assertFalse(client.get_status()["connected"])

    def test_missing_account_never_calls_provider(self):
        client = self.client()
        client.account_id = ""
        self.assertIsNone(client.get_live_data()["close"])
        client._session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()