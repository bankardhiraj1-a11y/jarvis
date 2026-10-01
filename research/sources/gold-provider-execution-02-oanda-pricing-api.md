Source: https://developer.oanda.com/rest-live-v20/pricing-ep/
Title: Pricing
Fetched: 2026-10-01T11:48:15.930Z

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

# Pricing Endpoints

[GET/v3/accounts/{accountID}/candles/latest\\
Get dancing bears and most recently completed candles within an Account for specified combinations of instrument, granularity, and price component.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_endpoint_2)

#### Request

[Request Parameters](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_2_parameters)

| Name | Located In | Type | Description |
| --- | --- | --- | --- |
| Authorization | header | string | The authorization bearer token previously obtained by the client \[required\] |
| Accept-Datetime-Format | header | [AcceptDatetimeFormat](https://developer.oanda.com/rest-live-v20/primitives-df/#AcceptDatetimeFormat) | Format of DateTime fields in the request and response. |
| accountID | path | [AccountID](https://developer.oanda.com/rest-live-v20/account-df/#AccountID) | Account Identifier \[required\] |
| candleSpecifications | query | List of [CandleSpecification](https://developer.oanda.com/rest-live-v20/pricing-df/#CandleSpecification) (csv) | List of candle specifications to get pricing for. \[required\] |
| units | query | [DecimalNumber](https://developer.oanda.com/rest-live-v20/primitives-df/#DecimalNumber) | The number of units used to calculate the volume-weighted average bid and ask prices in the returned candles. \[default=1\] |
| smooth | query | boolean | A flag that controls whether the candlestick is “smoothed” or not. A smoothed candlestick uses the previous candle’s close price as its open price, while an unsmoothed candlestick uses the first price from its time range as its open price. \[default=False\] |
| dailyAlignment | query | integer | The hour of the day (in the specified timezone) to use for granularities that have daily alignments. \[default=17, minimum=0, maximum=23\] |
| alignmentTimezone | query | string | The timezone to use for the dailyAlignment parameter. Candlesticks with daily alignment will be aligned to the dailyAlignment hour within the alignmentTimezone. Note that the returned times will still be represented in UTC. \[default=America/New\_York\] |
| weeklyAlignment | query | [WeeklyAlignment](https://developer.oanda.com/rest-live-v20/instrument-df/#WeeklyAlignment) | The day of the week used for granularities that have weekly alignment. \[default=Friday\] |

#### Responses

[**HTTP 200** – Pricing information has been successfully provided.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_2_200)

**Response Headers**

- RequestID - The unique identifier generated for the request

**Response Body Schema (application/json)**

```
{
    #
    # The latest candle sticks.
    #
    latestCandles : (Array[CandlestickResponse])
}
```

Other Error Responses: [400](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#400), [401](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#401), [404](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#404), [405](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#405)

[GET/v3/accounts/{accountID}/pricing\\
Get pricing information for a specified list of Instruments within an Account.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_endpoint_3)

#### Request

[Request Parameters](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_3_parameters)

| Name | Located In | Type | Description |
| --- | --- | --- | --- |
| Authorization | header | string | The authorization bearer token previously obtained by the client \[required\] |
| Accept-Datetime-Format | header | [AcceptDatetimeFormat](https://developer.oanda.com/rest-live-v20/primitives-df/#AcceptDatetimeFormat) | Format of DateTime fields in the request and response. |
| accountID | path | [AccountID](https://developer.oanda.com/rest-live-v20/account-df/#AccountID) | Account Identifier \[required\] |
| instruments | query | List of [InstrumentName](https://developer.oanda.com/rest-live-v20/primitives-df/#InstrumentName) (csv) | List of Instruments to get pricing for. \[required\] |
| since | query | [DateTime](https://developer.oanda.com/rest-live-v20/primitives-df/#DateTime) | Date/Time filter to apply to the response. Only prices and home conversions (if requested) with a time later than this filter (i.e. the price has changed after the since time) will be provided, and are filtered independently. |
| includeUnitsAvailable | query | boolean | Flag that enables the inclusion of the unitsAvailable field in the returned Price objects. \[default=True\]<br> <br>**Deprecated:** Will be removed in a future API update. |
| includeHomeConversions | query | boolean | Flag that enables the inclusion of the homeConversions field in the returned response. An entry will be returned for each currency in the set of all base and quote currencies present in the requested instruments list. \[default=False\] |

#### Responses

[**HTTP 200** – Pricing information has been successfully provided.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_3_200)

**Response Headers**

- RequestID - The unique identifier generated for the request

**Response Body Schema (application/json)**

```
{
    #
    # The list of Price objects requested.
    #
    prices : (Array[ClientPrice], required),

    #
    # The list of home currency conversion factors requested. This field will
    # only be present if includeHomeConversions was set to true in the request.
    #
    homeConversions : (Array[HomeConversions]),

    #
    # The DateTime value to use for the “since” parameter in the next poll
    # request.
    #
    time : (DateTime)
}
```

Other Error Responses: [400](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#400), [401](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#401), [404](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#404), [405](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#405)

#### Examples

[curl: Get current pricing for EUR\_USD and USD\_CAD](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_3_example_curl_1)

**Request** ![](https://developer.oanda.com/images/gear.svg)![Copy to clipboard](https://developer.oanda.com/images/clippy.svg)

```
curl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <AUTHENTICATION TOKEN>" \
  "https://api-fxtrade.oanda.com/v3/accounts/<ACCOUNT>/pricing?instruments=EUR_USD%2CUSD_CAD"
```

**Response Headers**

```
HTTP/1.1 200 OK
Access-Control-Allow-Headers: Authorization, Content-Type, Accept-Datetime-Format
Content-Encoding: gzip
Transfer-Encoding: chunked
Server: openresty/1.7.0.1
Connection: keep-alive
Date: Wed, 22 Jun 2016 18:41:38 GMT
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: PUT, PATCH, POST, GET, OPTIONS, DELETE
Content-Type: application/json
```

**Response Body**

```
{
  "prices": [\
    {\
      "asks": [\
        {\
          "liquidity": 10000000,\
          "price": "1.13028"\
        },\
        {\
          "liquidity": 10000000,\
          "price": "1.13030"\
        }\
      ],\
      "bids": [\
        {\
          "liquidity": 10000000,\
          "price": "1.13015"\
        },\
        {\
          "liquidity": 10000000,\
          "price": "1.13013"\
        }\
      ],\
      "closeoutAsk": "1.13032",\
      "closeoutBid": "1.13011",\
      "instrument": "EUR_USD",\
      "quoteHomeConversionFactors": {\
        "negativeUnits": "0.95904000",\
        "positiveUnits": "0.95886000"\
      },\
      "status": "tradeable",\
      "time": "2016-06-22T18:41:36.201836422Z",\
      "unitsAvailable": {\
        "default": {\
          "long": "2013434",\
          "short": "2014044"\
        },\
        "openOnly": {\
          "long": "2013434",\
          "short": "2014044"\
        },\
        "reduceFirst": {\
          "long": "2013434",\
          "short": "2014044"\
        },\
        "reduceOnly": {\
          "long": "0",\
          "short": "0"\
        }\
      }\
    },\
    {\
      "asks": [\
        {\
          "liquidity": 1000000,\
          "price": "1.28260"\
        },\
        {\
          "liquidity": 2000000,\
          "price": "1.28261"\
        },\
        {\
          "liquidity": 5000000,\
          "price": "1.28262"\
        },\
        {\
          "liquidity": 10000000,\
          "price": "1.28264"\
        }\
      ],\
      "bids": [\
        {\
          "liquidity": 1000000,\
          "price": "1.28241"\
        },\
        {\
          "liquidity": 2000000,\
          "price": "1.28240"\
        },\
        {\
          "liquidity": 5000000,\
          "price": "1.28239"\
        },\
        {\
          "liquidity": 10000000,\
          "price": "1.28237"\
        }\
      ],\
      "closeoutAsk": "1.28264",\
      "closeoutBid": "1.28237",\
      "instrument": "USD_CAD",\
      "quoteHomeConversionFactors": {\
        "negativeUnits": "0.74785000",\
        "positiveUnits": "0.74759000"\
      },\
      "status": "tradeable",\
      "time": "2016-06-22T18:41:36.042678456Z",\
      "unitsAvailable": {\
        "default": {\
          "long": "2275373",\
          "short": "2276522"\
        },\
        "openOnly": {\
          "long": "2275373",\
          "short": "2276522"\
        },\
        "reduceFirst": {\
          "long": "2275373",\
          "short": "2276522"\
        },\
        "reduceOnly": {\
          "long": "0",\
          "short": "0"\
        }\
      }\
    }\
  ]
}
```

[GET/v3/accounts/{accountID}/pricing/stream\\
Get a stream of Account Prices starting from when the request is made.\\
This pricing stream does not include every single price created for the Account, but instead will provide at most 4 prices per second (every 250 milliseconds) for each instrument being requested.\\
If more than one price is created for an instrument during the 250 millisecond window, only the price in effect at the end of the window is sent. This means that during periods of rapid price movement, subscribers to this stream will not be sent every price.\\
Pricing windows for different connections to the price stream are not all aligned in the same way (i.e. they are not all aligned to the top of the second). This means that during periods of rapid price movement, different subscribers may observe different prices depending on their alignment.\\
\\
**Note:** This endpoint is served by the streaming URLs.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_endpoint_4)

#### Request

[Request Parameters](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_4_parameters)

| Name | Located In | Type | Description |
| --- | --- | --- | --- |
| Authorization | header | string | The authorization bearer token previously obtained by the client \[required\] |
| Accept-Datetime-Format | header | [AcceptDatetimeFormat](https://developer.oanda.com/rest-live-v20/primitives-df/#AcceptDatetimeFormat) | Format of DateTime fields in the request and response. |
| accountID | path | [AccountID](https://developer.oanda.com/rest-live-v20/account-df/#AccountID) | Account Identifier \[required\] |
| instruments | query | List of [InstrumentName](https://developer.oanda.com/rest-live-v20/primitives-df/#InstrumentName) (csv) | List of Instruments to stream Prices for. \[required\] |
| snapshot | query | boolean | Flag that enables/disables the sending of a pricing snapshot when initially connecting to the stream. \[default=True\] |
| includeHomeConversions | query | boolean | Flag that enables the inclusion of the homeConversions field in the returned response. An entry will be returned for each currency in the set of all base and quote currencies present in the requested instruments list. \[default=False\] |

#### Responses

[**HTTP 200** – Connecting to the Price Stream was successful.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_4_200)

**Response Body Schema (application/octet-stream)**

The response body for the Pricing Stream uses chunked transfer encoding. Each chunk contains Price and/or PricingHeartbeat objects encoded as JSON. Each JSON object is serialized into a single line of text, and multiple objects found in the same chunk are separated by newlines.
Heartbeats are sent every 5 seconds.

The specification for the objects found in response stream are as follows:

- [ClientPrice](https://developer.oanda.com/rest-live-v20/pricing-df/#ClientPrice)
- [PricingHeartbeat](https://developer.oanda.com/rest-live-v20/pricing-df/#PricingHeartbeat)

Other Error Responses: [400](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#400), [401](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#401), [404](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#404), [405](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#405)

#### Examples

[curl: Subscribe to EUR\_USD and USD\_CAD price stream](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_4_example_curl_1)

**Request** ![](https://developer.oanda.com/images/gear.svg)![Copy to clipboard](https://developer.oanda.com/images/clippy.svg)

```
curl \
  -H "Authorization: Bearer <AUTHENTICATION TOKEN>" \
  "https://stream-fxtrade.oanda.com/v3/accounts/<ACCOUNT>/pricing/stream?instruments=EUR_USD%2CUSD_CAD"
```

**Response Headers**

```
HTTP/1.1 200 OK
Access-Control-Allow-Headers: Authorization, Content-Type, Accept-Datetime-Format, OANDA-Agent
Access-Control-Allow-Methods: PUT, PATCH, POST, GET, OPTIONS, DELETE
Access-Control-Allow-Origin: *
Content-Type: application/octet-stream
```

**Response Body**

```
{"asks":[{"liquidity":10000000,"price":"1.11704"},{"liquidity":10000000,"price":"1.11706"}],"bids":                        [{"liquidity":10000000,"price":"1.11690"},{"liquidity":10000000,"price":"1.11688"}],"closeoutAsk":"1.11708","closeoutBid":"1.11686","instrument":"EUR_USD","status":"tradeable","time":"2016-09-20T15:05:47.960449532Z"}
{"asks":[{"liquidity":1000000,"price":"1.32149"},{"liquidity":2000000,"price":"1.32150"},{"liquidity":5000000,"price":"1.32151"},{"liquidity":10000000,"price":"1.32153"}],"bids":[{"liquidity":1000000,"price":"1.32128"},{"liquidity":2000000,"price":"1.32127"},{"liquidity":5000000,"price":"1.32126"},{"liquidity":10000000,"price":"1.32124"}],"closeoutAsk":"1.32153","closeoutBid":"1.32124","instrument":"USD_CAD","status":"tradeable","time":"2016-09-20T15:05:48.157162748Z"}
{"asks":[{"liquidity":1000000,"price":"1.32145"},{"liquidity":2000000,"price":"1.32146"},{"liquidity":5000000,"price":"1.32147"},{"liquidity":10000000,"price":"1.32149"}],"bids":[{"liquidity":1000000,"price":"1.32123"},{"liquidity":2000000,"price":"1.32122"},{"liquidity":5000000,"price":"1.32121"},{"liquidity":10000000,"price":"1.32119"}],"closeoutAsk":"1.32149","closeoutBid":"1.32119","instrument":"USD_CAD","status":"tradeable","time":"2016-09-20T15:05:48.272079801Z"}
{"asks":[{"liquidity":1000000,"price":"1.32147"},{"liquidity":2000000,"price":"1.32148"},{"liquidity":5000000,"price":"1.32149"},{"liquidity":10000000,"price":"1.32151"}],"bids":[{"liquidity":1000000,"price":"1.32126"},{"liquidity":2000000,"price":"1.32125"},{"liquidity":5000000,"price":"1.32124"},{"liquidity":10000000,"price":"1.32122"}],"closeoutAsk":"1.32151","closeoutBid":"1.32122","instrument":"USD_CAD","status":"tradeable","time":"2016-09-20T15:05:48.540813660Z"}
{"time":"2016-09-20T15:05:50.163791738Z","type":"HEARTBEAT"}
```

[GET/v3/accounts/{accountID}/instruments/{instrument}/candles\\
Fetch candlestick data for an instrument.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_endpoint_5)

#### Request

[Request Parameters](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_5_parameters)

| Name | Located In | Type | Description |
| --- | --- | --- | --- |
| Authorization | header | string | The authorization bearer token previously obtained by the client \[required\] |
| Accept-Datetime-Format | header | [AcceptDatetimeFormat](https://developer.oanda.com/rest-live-v20/primitives-df/#AcceptDatetimeFormat) | Format of DateTime fields in the request and response. |
| accountID | path | [AccountID](https://developer.oanda.com/rest-live-v20/account-df/#AccountID) | Account Identifier \[required\] |
| instrument | path | [InstrumentName](https://developer.oanda.com/rest-live-v20/primitives-df/#InstrumentName) | Name of the Instrument \[required\] |
| price | query | [PricingComponent](https://developer.oanda.com/rest-live-v20/primitives-df/#PricingComponent) | The Price component(s) to get candlestick data for. \[default=M\] |
| granularity | query | [CandlestickGranularity](https://developer.oanda.com/rest-live-v20/instrument-df/#CandlestickGranularity) | The granularity of the candlesticks to fetch \[default=S5\] |
| count | query | integer | The number of candlesticks to return in the response. Count should not be specified if both the start and end parameters are provided, as the time range combined with the granularity will determine the number of candlesticks to return. \[default=500, maximum=5000\] |
| from | query | [DateTime](https://developer.oanda.com/rest-live-v20/primitives-df/#DateTime) | The start of the time range to fetch candlesticks for. |
| to | query | [DateTime](https://developer.oanda.com/rest-live-v20/primitives-df/#DateTime) | The end of the time range to fetch candlesticks for. |
| smooth | query | boolean | A flag that controls whether the candlestick is “smoothed” or not. A smoothed candlestick uses the previous candle’s close price as its open price, while an unsmoothed candlestick uses the first price from its time range as its open price. \[default=False\] |
| includeFirst | query | boolean | A flag that controls whether the candlestick that is covered by the from time should be included in the results. This flag enables clients to use the timestamp of the last completed candlestick received to poll for future candlesticks but avoid receiving the previous candlestick repeatedly. \[default=True\] |
| dailyAlignment | query | integer | The hour of the day (in the specified timezone) to use for granularities that have daily alignments. \[default=17, minimum=0, maximum=23\] |
| alignmentTimezone | query | string | The timezone to use for the dailyAlignment parameter. Candlesticks with daily alignment will be aligned to the dailyAlignment hour within the alignmentTimezone. Note that the returned times will still be represented in UTC. \[default=America/New\_York\] |
| weeklyAlignment | query | [WeeklyAlignment](https://developer.oanda.com/rest-live-v20/instrument-df/#WeeklyAlignment) | The day of the week used for granularities that have weekly alignment. \[default=Friday\] |
| units | query | [DecimalNumber](https://developer.oanda.com/rest-live-v20/primitives-df/#DecimalNumber) | The number of units used to calculate the volume-weighted average bid and ask prices in the returned candles. \[default=1\] |

#### Responses

[**HTTP 200** – Pricing information has been successfully provided.](https://developer.oanda.com/rest-live-v20/pricing-ep/#collapse_5_200)

**Response Headers**

- RequestID - The unique identifier generated for the request

**Response Body Schema (application/json)**

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

Other Error Responses: [400](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#400), [401](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#401), [404](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#404), [405](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/#405)

![](https://fonts.gstatic.com/s/i/productlogos/translate/v14/24px.svg)

Original text

Rate this translation

Your feedback will be used to help improve Google Translate