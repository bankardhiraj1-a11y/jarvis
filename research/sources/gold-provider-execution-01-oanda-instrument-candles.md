Source: https://developer.oanda.com/rest-live-v20/instrument-df/
Title: Instrument
Fetched: 2026-10-01T11:48:13.153Z

- [Introduction](https://developer.oanda.com/rest-live-v20/introduction/)
- [Development Guide](https://developer.oanda.com/rest-live-v20/development-guide/)
- [Best Practices](https://developer.oanda.com/rest-live-v20/best-practices/)
- [Authentication](https://developer.oanda.com/rest-live-v20/authentication/)
- [Troubleshooting & Errors](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/)
- [Sample Code](https://developer.oanda.com/rest-live-v20/sample-code/)
- [Release Notes](https://developer.oanda.com/rest-live-v20/release-notes/)
- [API Comparison](https://developer.oanda.com/rest-live-v20/api-comparison/)

* * *

#### Endpoints

[Account](https://developer.oanda.com/rest-live-v20/account-ep/)

[Order](https://developer.oanda.com/rest-live-v20/order-ep/)

[Trade](https://developer.oanda.com/rest-live-v20/trade-ep/)

[Position](https://developer.oanda.com/rest-live-v20/position-ep/)

[Transaction](https://developer.oanda.com/rest-live-v20/transaction-ep/)

[Pricing](https://developer.oanda.com/rest-live-v20/pricing-ep/)

#### Definitions

[Account](https://developer.oanda.com/rest-live-v20/account-df/)

[Instrument](https://developer.oanda.com/rest-live-v20/instrument-df/)

[Order](https://developer.oanda.com/rest-live-v20/order-df/)

[Trade](https://developer.oanda.com/rest-live-v20/trade-df/)

[Position](https://developer.oanda.com/rest-live-v20/position-df/)

[Transaction](https://developer.oanda.com/rest-live-v20/transaction-df/)

[Pricing](https://developer.oanda.com/rest-live-v20/pricing-df/)

[Pricing Common](https://developer.oanda.com/rest-live-v20/pricing-common-df/)

[Primitives](https://developer.oanda.com/rest-live-v20/primitives-df/)

# Instrument Definitions

[CandlestickGranularityThe granularity of a candlestick](https://developer.oanda.com/rest-live-v20/instrument-df/#collapse_definition_1)

| Value | Description |
| --- | --- |
| S5 | 5 second candlesticks, minute alignment |
| S10 | 10 second candlesticks, minute alignment |
| S15 | 15 second candlesticks, minute alignment |
| S30 | 30 second candlesticks, minute alignment |
| M1 | 1 minute candlesticks, minute alignment |
| M2 | 2 minute candlesticks, hour alignment |
| M4 | 4 minute candlesticks, hour alignment |
| M5 | 5 minute candlesticks, hour alignment |
| M10 | 10 minute candlesticks, hour alignment |
| M15 | 15 minute candlesticks, hour alignment |
| M30 | 30 minute candlesticks, hour alignment |
| H1 | 1 hour candlesticks, hour alignment |
| H2 | 2 hour candlesticks, day alignment |
| H3 | 3 hour candlesticks, day alignment |
| H4 | 4 hour candlesticks, day alignment |
| H6 | 6 hour candlesticks, day alignment |
| H8 | 8 hour candlesticks, day alignment |
| H12 | 12 hour candlesticks, day alignment |
| D | 1 day candlesticks, day alignment |
| W | 1 week candlesticks, aligned to start of week |
| M | 1 month candlesticks, aligned to first day of the month |

[WeeklyAlignmentThe day of the week to use for candlestick granularities with weekly alignment.](https://developer.oanda.com/rest-live-v20/instrument-df/#collapse_definition_2)

| Value | Description |
| --- | --- |
| Monday | Monday |
| Tuesday | Tuesday |
| Wednesday | Wednesday |
| Thursday | Thursday |
| Friday | Friday |
| Saturday | Saturday |
| Sunday | Sunday |

[CandlestickThe Candlestick representation](https://developer.oanda.com/rest-live-v20/instrument-df/#collapse_definition_3)

Candlestick is an application/json object with the following Schema:

```
{
    #
    # The start time of the candlestick
    #
    time : (DateTime),

    #
    # The candlestick data based on bids. Only provided if bid-based candles
    # were requested.
    #
    bid : (CandlestickData),

    #
    # The candlestick data based on asks. Only provided if ask-based candles
    # were requested.
    #
    ask : (CandlestickData),

    #
    # The candlestick data based on midpoints. Only provided if midpoint-based
    # candles were requested.
    #
    mid : (CandlestickData),

    #
    # The number of prices created during the time-range represented by the
    # candlestick.
    #
    volume : (integer),

    #
    # A flag indicating if the candlestick is complete. A complete candlestick
    # is one whose ending time is not in the future.
    #
    complete : (boolean)
}
```

[CandlestickDataThe price data (open, high, low, close) for the Candlestick representation.](https://developer.oanda.com/rest-live-v20/instrument-df/#collapse_definition_4)

CandlestickData is an application/json object with the following Schema:

```
{
    #
    # The first (open) price in the time-range represented by the candlestick.
    #
    o : (PriceValue),

    #
    # The highest price in the time-range represented by the candlestick.
    #
    h : (PriceValue),

    #
    # The lowest price in the time-range represented by the candlestick.
    #
    l : (PriceValue),

    #
    # The last (closing) price in the time-range represented by the
    # candlestick.
    #
    c : (PriceValue)
}
```

[CandlestickResponseResponse containing instrument, granularity, and list of candles.](https://developer.oanda.com/rest-live-v20/instrument-df/#collapse_definition_5)

CandlestickResponse is an application/json object with the following Schema:

```
{
    #
    # The instrument whose Prices are represented by the candlesticks.
    #
    instrument : (InstrumentName),

    #
    # The granularity of the candlesticks provided.
    #
    granularity : (CandlestickGranularity),

    #
    # The list of candlesticks that satisfy the request.
    #
    candles : (Array[Candlestick])
}
```

![](https://fonts.gstatic.com/s/i/productlogos/translate/v14/24px.svg)

Original text

Rate this translation

Your feedback will be used to help improve Google Translate