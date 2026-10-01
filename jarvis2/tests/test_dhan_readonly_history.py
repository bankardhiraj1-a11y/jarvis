import csv
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from data.dhan_history import DhanHistoryClient, DhanHistoryError
from data.dhan_live_client import DhanLiveClient


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        return self.responses.pop(0)


def _exchange_time(offset_seconds=0):
    value = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(seconds=offset_seconds)
    return value.strftime("%d/%m/%Y %H:%M:%S")


def _quote_record(last_price=101.25, last_trade_time=None):
    return {
        "last_price": last_price,
        "last_trade_time": last_trade_time or _exchange_time(),
        "ohlc": {"open": 99.5, "high": 103.0, "low": 98.75, "close": 100.0},
        "volume": 1234,
        "depth": {
            "buy": [
                {"price": 101.0, "quantity": 25, "orders": 1},
                {"price": 100.75, "quantity": 0, "orders": 0},
            ],
            "sell": [
                {"price": 101.5, "quantity": 40, "orders": 1},
            ],
        },
    }


def _chain(expiry, security_id):
    return {
        "status": "success",
        "data": {
            "last_price": 22000.0,
            "oc": {
                "22000": {
                    "ce": {
                        "security_id": security_id,
                        "last_price": 100,
                        "top_bid_price": 99,
                        "top_ask_price": 101,
                        "volume": 20,
                        "oi": 200,
                    }
                }
            },
        },
    }


def _bar_response():
    return {
        "open": [100.0, 101.0],
        "high": [102.0, 103.0],
        "low": [99.0, 100.0],
        "close": [101.0, 102.0],
        "volume": [1000, 1200],
        "timestamp": [1704067200, 1704070800],
        "open_interest": [200, 220],
    }


def test_quote_uses_exchange_trade_time_and_keeps_executable_depth():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "status": "success",
                    "data": {"NSE_EQ": {"1333": _quote_record()}},
                }
            )
        ]
    )
    client = DhanLiveClient(session=session)
    client._client_id = "not-used-in-output"
    client._access_token = "not-used-in-output"
    client._monotonic = lambda: 100.0

    assert client.refresh_quotes(
        [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
    )
    quote = client.get_live_data(1333)
    assert quote["timestamp_basis"] == "exchange"
    assert quote["timestamp"] != quote["received_at_timestamp"]
    assert quote["bid"] == 101.0
    assert quote["ask"] == 101.5
    assert quote["bid_quantity"] == 25
    assert quote["ask_quantity"] == 40
    assert quote["close"] == 101.25
    assert not quote["stale"]


@pytest.mark.parametrize("trade_time", [None, "01/01/1980 00:00:00"])
def test_missing_or_sentinel_trade_time_never_becomes_receipt_time(trade_time):
    record = _quote_record()
    record["last_trade_time"] = trade_time
    session = FakeSession(
        [
            FakeResponse(
                {
                    "status": "success",
                    "data": {"NSE_EQ": {"1333": record}},
                }
            )
        ]
    )
    client = DhanLiveClient(session=session)
    client._client_id = "test"
    client._access_token = "test"
    client._monotonic = lambda: 100.0

    assert client.refresh_quotes(
        [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
    )
    quote = client.get_live_data(1333)
    assert quote["timestamp"] is None
    assert quote["timestamp_basis"] is None
    assert quote["received_at_timestamp"]
    assert quote["stale"]
    assert quote["close"] is None
    assert quote["bid"] is None


def test_old_exchange_trade_time_is_stale_even_when_http_receipt_is_recent():
    record = _quote_record(last_trade_time=_exchange_time(offset_seconds=60))
    session = FakeSession(
        [
            FakeResponse(
                {
                    "status": "success",
                    "data": {"NSE_EQ": {"1333": record}},
                }
            )
        ]
    )
    client = DhanLiveClient(session=session, quote_max_age_seconds=15)
    client._client_id = "test"
    client._access_token = "test"
    client._monotonic = lambda: 100.0

    assert client.refresh_quotes(
        [{"ExchangeSegment": "NSE_EQ", "SecurityId": 1333, "Symbol": "HDFCBANK"}]
    )
    quote = client.get_live_data(1333)
    assert quote["timestamp_basis"] == "exchange"
    assert quote["receipt_age_seconds"] == 0.0
    assert quote["exchange_age_seconds"] > 15
    assert quote["stale"]
    assert quote["close"] is None


def test_old_and_nearest_expiry_option_chains_are_cached_independently():
    old_expiry = (date.today() + timedelta(days=4)).isoformat()
    new_expiry = (date.today() + timedelta(days=11)).isoformat()
    session = FakeSession(
        [
            FakeResponse(_chain(old_expiry, 501)),
            FakeResponse(_chain(new_expiry, 502)),
            FakeResponse(
                {
                    "status": "success",
                    "data": {
                        "NSE_FNO": {
                            "501": _quote_record(last_trade_time=_exchange_time())
                        }
                    },
                }
            ),
        ]
    )
    client = DhanLiveClient(session=session)
    client._client_id = "test"
    client._access_token = "test"
    elapsed = [100.0]
    client._monotonic = lambda: elapsed[0]
    client._sleep = lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)

    old_chain = client.refresh_option_chain(
        "NIFTY", 13, expiry=old_expiry
    )
    nearest_chain = client.refresh_option_chain(
        "NIFTY", 13, expiry=new_expiry
    )
    assert old_chain["timestamp"] is None
    assert old_chain["timestamp_basis"] == "receipt"
    assert old_chain["received_at_timestamp"]
    assert nearest_chain["expiry"] == new_expiry
    assert ("NIFTY", old_expiry) in client.option_chains
    assert ("NIFTY", new_expiry) in client.option_chains

    # The old exact contract is explicitly refreshed by its security ID and
    # provider trade timestamp; its getter then reads only that cached result.
    old_quote = client.refresh_option_quote(
        "NIFTY",
        strike=22000,
        option_type="CE",
        expiry=old_expiry,
    )
    assert old_quote["security_id"] == 501
    assert old_quote["timestamp_basis"] == "exchange"
    assert old_quote["observed_at"]
    assert old_quote["bid"] == 101.0
    assert old_quote["ask"] == 101.5
    assert client.get_option_quote("NIFTY", 22000, "CE", old_expiry)["expiry"] == old_expiry
    assert client.get_option_quote("NIFTY", 22000, "CE", new_expiry) is None

    snapshot = client.get_market_snapshot()
    assert f"NIFTY:{old_expiry}" in snapshot["option_chains"]
    assert f"NIFTY:{new_expiry}" in snapshot["option_chains"]


def test_option_chain_receipt_timestamp_alone_is_not_an_executable_option_quote():
    expiry = (date.today() + timedelta(days=7)).isoformat()
    client = DhanLiveClient(session=FakeSession([FakeResponse(_chain(expiry, 510))]))
    client._client_id = "test"
    client._access_token = "test"
    client._monotonic = lambda: 50.0
    assert client.refresh_option_chain("NIFTY", 13, expiry=expiry)
    assert client.get_option_quote("NIFTY", 22000, "CE", expiry) is None


def test_daily_history_uses_read_only_endpoint_and_validates_provider_bars():
    session = FakeSession([FakeResponse(_bar_response())])
    client = DhanHistoryClient(session=session, access_token="test-token")
    start = date(2024, 1, 1)
    end = date(2024, 1, 3)
    rows = client.fetch_daily(13, "IDX_I", "INDEX", start, end)

    assert len(rows) == 2
    assert rows[0]["data_source"] == "DHAN_HISTORICAL"
    assert rows[0]["timestamp"].endswith("+00:00")
    url, request = session.calls[0]
    assert url.endswith("/charts/historical")
    assert request["json"] == {
        "securityId": "13",
        "exchangeSegment": "IDX_I",
        "instrument": "INDEX",
        "expiryCode": 0,
        "oi": False,
        "fromDate": "2024-01-01",
        "toDate": "2024-01-03",
    }
    assert request["headers"]["access-token"] == "test-token"
    assert "client-id" not in request["headers"]


def test_intraday_history_has_capped_documented_window_and_rejects_bad_arrays():
    session = FakeSession([FakeResponse(_bar_response())])
    client = DhanHistoryClient(session=session, access_token="test")
    rows = client.fetch_intraday(
        1333,
        "NSE_EQ",
        "EQUITY",
        15,
        "2024-01-01",
        "2024-01-03",
    )
    assert len(rows) == 2
    assert session.calls[0][0].endswith("/charts/intraday")
    assert session.calls[0][1]["json"]["interval"] == "15"
    with pytest.raises(ValueError, match="90-day"):
        client.fetch_intraday(
            1333,
            "NSE_EQ",
            "EQUITY",
            1,
            "2024-01-01",
            "2024-04-02",
        )

    with pytest.raises(DhanHistoryError, match="mismatched lengths"):
        DhanHistoryClient(
            session=FakeSession(
                [
                    FakeResponse(
                        {
                            **_bar_response(),
                            "close": [101.0],
                        }
                    )
                ]
            ),
            access_token="test",
        ).fetch_daily(1333, "NSE_EQ", "EQUITY", "2024-01-01", "2024-01-02")


def test_expired_option_history_fetch_and_csv_export_are_authentic_and_explicit():
    payload = {
        "status": "success",
        "data": {
            "ce": {
                "timestamp": [1704067200, 1704067260],
                "open": [90, 91],
                "high": [92, 93],
                "low": [89, 90],
                "close": [91, 92],
                "volume": [10, 15],
                "iv": [15.5, 15.8],
                "strike": [22000, 22050],
                "spot": [22010, 22060],
            },
            "pe": None,
        },
    }
    session = FakeSession([FakeResponse(payload)])
    client = DhanHistoryClient(session=session, access_token="test")
    rows = client.fetch_expired_options(
        13,
        "NSE_FNO",
        "OPTIDX",
        1,
        "WEEK",
        0,
        "ATM+1",
        "CALL",
        "2024-01-01",
        "2024-01-02",
        required_data=["iv", "volume"],
    )

    assert len(rows) == 2
    assert rows[0]["option_type"] == "CALL"
    assert rows[0]["strike"] == 22000.0
    assert rows[0]["spot"] == 22010.0
    assert "bid" not in rows[0]
    request = session.calls[0][1]
    assert session.calls[0][0].endswith("/charts/rollingoption")
    assert request["json"]["requiredData"] == [
        "iv",
        "volume",
        "open",
        "high",
        "low",
        "close",
    ]

    with TemporaryDirectory() as directory:
        destination = Path(directory) / "nested" / "historical.csv"
        assert DhanHistoryClient.export_csv(rows, destination) == 2
        with destination.open(newline="", encoding="utf-8") as source:
            exported = list(csv.DictReader(source))
        assert len(exported) == 2
        assert exported[0]["data_source"] == "DHAN_EXPIRED_OPTION_HISTORICAL"


def test_history_errors_are_sanitized_and_no_token_means_no_request():
    session = FakeSession([])
    client = DhanHistoryClient(session=session, access_token="")
    with pytest.raises(DhanHistoryError, match="not configured"):
        client.fetch_daily(13, "IDX_I", "INDEX", "2024-01-01", "2024-01-02")
    assert session.calls == []
    assert "test-token" not in (client.last_error or "")