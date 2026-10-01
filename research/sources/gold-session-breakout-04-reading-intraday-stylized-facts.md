Source: https://centaur.reading.ac.uk/79175/1/BattenLuceyMcGroartyPeatUrquhart2017.pdf
Title: Stylized facts of intraday precious metals
Fetched: 2026-10-01T11:48:51.708Z

# Stylized facts of intraday precious metals

Article

Published Version

Creative Commons: Attribution-Noncommercial-No Derivative Works 4.0

Open access

Batten, J., Lucey, B., McGroarty, F., Peat, M. and Urquhart, A.
ORCID: [https://orcid.org/0000-0001-8834-4243](https://orcid.org/0000-0001-8834-4243) (2017) Stylized
facts of intraday precious metals. PLoS ONE, 12 (4). ISSN
1932-6203 doi: 10.1371/journal.pone.0174232 Available at
[https://centaur.reading.ac.uk/79175/](https://centaur.reading.ac.uk/79175/)

It is advisable to refer to the publisher’s version if you intend to cite from the
work. See Guidance on citing.

To link to this article DOI: [http://dx.doi.org/10.1371/journal.pone.0174232](http://dx.doi.org/10.1371/journal.pone.0174232)

Publisher: Public Library of Science

All outputs in CentAUR are protected by Intellectual Property Rights law,
including copyright law. Copyright and IPR is retained by the creators or other
copyright holders. Terms and conditions for use of this material are defined in
the End User Agreement.

[www.reading.ac.uk/centaur](http://www.reading.ac.uk/centaur)

## CentAUR

Central Archive at the University of Reading

Reading’s research outputs online

* * *

# RESEARCH ARTICLE

# Stylized facts of intraday precious metals

**Jonathan Batten1, Brian Lucey2\*, Frank McGroarty3, Maurice Peat4, Andrew Urquhart5**

**1** Monash University Business School, Monash University, Caulfield, Victoria, Australia, **2** Trinity Business
School, Trinity College Dublin, Dublin, Ireland, **3** Southampton Business School, University of Southampton,
Southampton, United Kingdom, **4** University of Sydney Business School, Sydney, New South Wales,
Australia, **5** Southampton Business School, University of Southampton, Southampton, United Kingdom

## OPEN ACCESS

**Citation:** Batten J, Lucey B, McGroarty F, Peat M,
Urquhart A (2017) Stylized facts of intraday
precious metals. PLoS ONE 12(4): e0174232.
[https://doi.org/10.1371/journal.pone.0174232](https://doi.org/10.1371/journal.pone.0174232)

**Editor:** Wei-Xing Zhou, East China University of
Science and Technology, CHINA

**Received:** November 16, 2016

**Accepted:** March 5, 2017

**Published:** April 27, 2017

**Copyright:** © 2017 Batten et al. This is an open
access article distributed under the terms of the
Creative Commons Attribution License, which
permits unrestricted use, distribution, and
reproduction in any medium, provided the original
author and source are credited.

**Data Availability Statement:** All data are fully
described in the paper and are available from a
commercial source, Thomson Reuters Tick History
Database. This is however a subscription database.
Readers may contact Thomson Reuters Tick
History Database at the following link to access the
data in the same manner by which the authors
obtained it: [https://customers.reuters.com/rph/trth/](https://customers.reuters.com/rph/trth/)
sliver.aspx?section=ContactUs. On request to
Maurice Peat, readers may request the data
( [maurice.peat@sydney.edu.au](mailto:maurice.peat@sydney.edu.au)).

- [blucey@tcd.ie](mailto:blucey@tcd.ie)

**Funding:** Np specific funding was required.

## Abstract

This paper examines the stylized facts, correlation and interaction between volatility and
returns at the 5-minute frequency for gold, silver, platinum and palladium from May 2000 to
April 2015. We study the full sample period, as well as three subsamples to determine how
high-frequency data of precious metals have developed over time. We find that over the full
sample, the number of trades has increased substantially over time for each precious metal,
while the bid-ask spread has narrowed over time, indicating an increase in liquidity and price
efficiency. We also find strong evidence of periodicity in returns, volatility, volume and bidask spread. Returns and volume both experience strong intraday periodicity linked to the
opening and closing of major markets around the world while the bid-ask spread is at its lowest when European markets are open. We also show a bilateral Granger causality between
returns and volatility of each precious metal, which holds for the vast majority subsamples.

### Introduction

This paper examines the intraday periodicity, correlation and volatility interaction in four precious metals markets. Our data set covers over 15-years of 5-minute data on gold, silver, platinum and palladium and finds significant evidence of intraday periodicity in returns, volatility,
trading volumes and bid-ask spreads as well as strong evidence of bilateral Granger causality
between returns and volatility. As well as being important in its own right in explaining highfrequency precious metal dynamics and trading behaviour, intraday periodicity, correlation
and volatility interaction have important implications for investors trading precious metals
intraday.

Gold is one of the most intensively traded assets, a feature not often understood by market
participants. In 2011, estimated daily international turnover in gold was of the order of 4,000
metric tons, equivalent to a then average value of over $240 billion. This is approximately the
same as the daily dollar volume of trade on all of the world’s stock exchanges combined \[1\]. If,
as is common, we consider gold as a currency its turnover exceeds that in all but four currency
pairs \[2\]. Gold trading is also highly concentrated, as it is in the foreign exchange market, with
the two major centers for gold trading, London (physical, over-the-counter (LOTC) spot
trade) and the New York Mercantile Exchange Futures Market (COMEX), totaling 85%
(78.0% and 7.7% respectively) of global turnover value \[3\]. We study gold, silver, platinum and

* * *

**Competing interests:** The authors have declared
that no competing interests exist.

palladium since they are the most traded due to them having ISO-4217 currency codes which
means they are traded as a currency, see [http://www.iso.org/iso/home/standards/currency](http://www.iso.org/iso/home/standards/currency)\_
codes.htm

Our study is motivated by the fact that most financial time series exhibit periodicity. With
high-frequency data the problem of periodicity becomes more complex since the entire form
of the daily activity has to be taken into account. There is widespread empirical evidence that
trading patterns vary systematically over the trading day and these patterns are highly correlated with intraday variations in returns, volatility, volume and bid-ask spreads in stock markets (for example see \[4\], \[5\], \[6\], \[7\], \[8\]), Foreign Exchange (FX) markets (see for example
\[9\], \[10\], \[11\]) and Exchange Traded Funds (ETFs) (see for example \[12\]).

The finance literature has also shown that most intraday trading activity exhibits a Ushaped pattern, (for example \[13\] for Toronto stock exchange; \[14\] for the New York Stock
Exchange (NYSE); \[15\] for the Tokyo stock exchange), while UK markets experience a Mshape where the volume is higher around the opening of US markets, see \[16\] and \[17\]. Also,
\[5\] document a reverse J-shaped pattern of NYSE quotations and \[18\] support this pattern
with London Stock Exchange (LSE) intraday spreads. Elevated opening and closing returns
have been reflected in the volatility patterns, where a U-shape is found by \[13\], \[19\], \[20\] and
\[21\].

This paper fills three lacunae in the literature. First, despite the extensive literature on periodicity in stock markets and FX markets, there is a notable lack of studies examining the periodicity of precious metals. \[22\] study the main stylized facts and dynamic properties of spot
precious metals from 27th December 2008 to 30th November 2010 at 5-minute and 50-minute
frequencies. They find clear evidence of periodic patterns matching the trading hours of the
most active markets round-the-clock and therefore conclude that precious metals spot returns
have similar properties to those of traditional financial assets. \[23\] examine the 5-minute gold
futures market and find periodicity in absolute returns and the returns movements in response
to macroeconomic announcements. \[24\] study the dynamic behaviour of six commodities,
including gold, and find that intraday returns have long memory. \[25\] study high-frequency
futures data for gold, silver and copper from 1999 to 2008 through four measures of volatility
and find that each of the return distributions are not normal. \[3\] examine the gold markets
and find intraday periodicity in the context of how the London and New York markets interrelate. Given the size of the market, there remains a lack of studies examining the intraday periodicity of precious metals spot rates, this study seeks to fill this gap.

$$
30^{th}
$$

$$
27^{th}
$$

Second, a further gap in the literature revolves around the well-known stylised fact in
finance that stock index returns are negatively correlated with changes in volatility \[26\]. This
distinctive cross dependence pattern plays an essential role in the development of volatility as
an asset class, in modelling volatility and in option pricing. Many studies have examined this
phenomenon in stock markets, see \[27\], \[28\], \[29\], \[30\], \[31\]. However, there are to our knowledge no extant studies that study this relationship in precious metals at a high-frequency.

A third gap relates to the evaluation of intraday features in over the counter trades. By contrast to futures markets, where there is a great deal of research across a large number of assets,
over the counter markets have received much less attention. In the area of gold the only comparable study to this paper is that of \[32\]. A frequent assumption of over the counter market
analysis is that the over the counter market is illiquid see \[33\] and \[34\]. That is not the case
here.

Transparency in the OTC markets are typically rather low. There is no public record of
trade volumes or prices, only the quotes are observable. For gold, this lack of transparency
was the genesis of the Loco London Liquidity Survey \[35\] which has gone some way to demonstrate gold as a liquid asset. Evidence in this paper on bid-ask spread and volume will
therefore be of use to fill this gap.

This paper considers the intraday patterns in the returns, volatility, volume and the bid-ask
spread of gold, silver, platinum and palladium at a 5-minute frequency from May 2000 to
April 2015. The intraday patterns of precious metals have not received detailed empirical
attention in the literature, which is all the more surprising given the growth of precious metals
as investment assets as well as the growth of high-frequency trading. This paper also investigates the lead-lag relationship and Granger causality between returns and volatility of precious
metals at high frequency, an area currently unexplored.

Therefore, this study contributes to the literature in a number of ways. Firstly, this is the
first study to examine the stylized facts of all precious metals at high frequency over a long
sample period. \[22\] study high-frequency precious metals from December 2008 to November
2010, which may not be the best time to determine the stylized facts of precious metals given
the aftermath of the financial crisis. Secondly, by splitting our data into three equally-sized
subsamples, we also study how the stylized facts of precious metals have developed over time
in a dynamic framework. Thirdly, we document the intraday periodicity of precious metals
which can offer valuable information to investors trading precious metals. Fourthly, we also
study the relationship between returns and volatility of high-frequency precious metals, which
has been unexplored in the empirical literature.

The remainder of the paper is organized in as follows. The next section presents the data
and methodology while Section 3 reports the empirical results. Section 4 reports the empirical
results while Section 5 summarises the findings and provides conclusions.

### Material and methods

The data is collected from Thomson Reuters Tick History for the period 1st May 2000 to 30th
April 2015 and consist of the closing prices, time stamp, the bid/ask price, and the number of
trades for gold, silver, platinum and palladium. These prices are made by wholesale market
practitioners with prices and trades time-stamped as they arise in online trading platforms.

$$
1^{\\mathrm{st}}
$$

$$
30^{th}
$$

In order to examine the periodicity of these precious metals, it is important to use short
enough intervals to capture the high frequency behaviour of the data, but at the same time
long enough to avoid any undue noise \[36\]. Therefore, we follow \[37\] who suggests that
5-minute intervals are the best compromise. The markets of all four precious metals trade
from Sunday 22.00 to Friday with a daily break between 21.00 and 22.00 GMT. We filter the
data by removing any errors caused by missing bid/ask data and also remove any data when
the market is closed.

Given our large sample period, the increased attention to precious as an investment and
attention in the academic literature, the stylized facts may change over our 15-year full sample
period. Therefore as well as studying the full sample period, we also split our sample into three
equal-sized subsamples, from 1st May 2000 to 30th April 2005, 1st May 2005 to 30th April 2010
and 1st May 2010 to 30th April 2015.

$$
1^{\\mathrm{st}}
$$

$$
30^{\\bar{\\mathrm{th}}}
$$

$$
1^{\\mathrm{st}}
$$

$$
1^{\\mathrm{st}}
$$

$$
30^{\\bar{\\mathrm{th}}}
$$

$$
30^{th}
$$

The variables of interest in this paper are returns, volume, volatility and the bid-ask spread
(BAS). From 5-minute transaction prices of each precious metal, we calculate the return following \[38\] such that;

$$
r\_{t,d}=\\left(\\ln CP\_{t,d}-\\ln CP\_{t,d-1}\\right)\\times100
$$

ð1Þ

where rt,d is the return for the intraday period d on trading day t and CPt,d is the closing price
for the intraday period _d_ on trading day _t._ Following \[5\] and \[39\], we calculate the bid-ask

$$
r\_{t,d}
$$

$$
CP\_{t,d}
$$ spread as the difference in prices;

$$
B A S\_{i}=\\frac{A S K\_{i}-B I D\_{i}}{(A S K\_{i}+B I D\_{i})/2}
$$

ð2Þ

where ASKi is the ask price of precious metal i and BIDi is the bid price of precious metal i.
Given that true volatility is unobservable, the empirical results may be sensitive to the chosen
volatility measure. In this paper, the intraday volatility is calculated using three approaches;

$$
A S K\_{i}
$$

$$
BID\_{i}
$$

$$
V O\_{t}^{S Q}=\\ln\\left(\\left.C P\_{t}\\right/ _{C P_{t-1}}\\right)^{2}
$$

ð3Þ

$$
VO\_{t}^{GK}=0.5\\left\[ln\\left(HP\_{t}\\right)-ln\\left(LP\_{t}\\right)\\right\]^{2}-\\left\[2ln2-1\\right\]\\left\[ln\\left(CP\_{t}\\right)-ln\\left(OP\_{t}\\right)\\right\]^{2}
$$

ð4Þ

$$
VO\_{t}^{RS}=\[ln(HP\_{t}-ln(OP\_{t})\]\[ln(HP\_{t})-ln(CP\_{t})\]+\[ln(LP\_{t})-ln(OP\_{t})\]\[ln(LP\_{t})-ln(CP\_{t})\]
$$

ð5Þ

Where _VOSQ_ t, _VOGK_ tand _VORS_ tare the square return, volatility proposed by \[40\], and the volatility of \[41\] and \[42\]. _HP, LP, CP_ and _OP_ represent the high price, low price, closing price and
opening price respectively. These different measures of volatility are calculated in different
ways and therefore may provide differing results. The GK and RS measures that take into
account the high, low, opening and closing prices of the precious metals when calculating volatility while the SQ measure just takes into account the returns of the precious metals. The GK
and RS measures guard against the potential distorting impact of high-frequency real-world
frictions by incorporating range information in the estimation of volatility, while the SQ measure does not. Therefore, although all three measures do calculate volatility, they do so in a
slightly different manner and consequently may provide contrasting results.

$$
VO\_{ _t}^{SQ},VO_{\_t}^{GK}
$$

$$
VO\_{t}^{RS}
$$

The time-series graph of each of the precious metals prices is reported in Fig 1, where the
four precious metals seem to follow a similar pattern over time. We can see that silver has been
very volatile and that palladium’s value is much less than the other three precious metals. Gold
and silver have followed very similar paths since 2012 and that all four were affected by the
2008 global financial crisis. Fig 2 presents the volume of trades of each precious metal over
time and we can see that each precious metal experiences a large increase in the number of
trades throughout the sample period. It is also evident that gold has the largest volume of

| Category | XAU (Dollars) | XPT (Dollars) | XPD (Dollars) | XAG (Dollars, rhs) |
| --- | --- | --- | --- | --- |
| 05-2000 | 270 | 550 | 650 | 5.5 |
| 09-2000 | 270 | 580 | 750 | 5.5 |
| 02-2001 | 280 | 600 | 1050 | 5.5 |
| 06-2001 | 280 | 550 | 600 | 5 |
| 11-2001 | 290 | 450 | 350 | 4.5 |
| 04-2002 | 300 | 500 | 350 | 4.5 |
| 08-2002 | 310 | 550 | 300 | 4.5 |
| 01-2003 | 330 | 580 | 250 | 4 |
| 05-2003 | 350 | 650 | 200 | 4 |
| 10-2003 | 380 | 750 | 200 | 4 |
| 03-2004 | 400 | 850 | 250 | 5 |
| 07-2004 | 400 | 850 | 200 | 5 |
| 12-2004 | 430 | 880 | 200 | 5 |
| 05-2005 | 440 | 900 | 180 | 5 |
| 09-2005 | 460 | 950 | 200 | 6 |
| 02-2006 | 550 | 1050 | 300 | 8 |
| 06-2006 | 650 | 1200 | 400 | 10 |
| 11-2006 | 650 | 1150 | 350 | 11 |
| 04-2007 | 680 | 1250 | 350 | 12 |
| 08-2007 | 700 | 1300 | 350 | 13 |
| 01-2008 | 850 | 1500 | 400 | 15 |
| 05-2008 | 900 | 2000 | 450 | 17 |
| 10-2008 | 800 | 1000 | 250 | 12 |
| 03-2009 | 950 | 1150 | 200 | 13 |
| 07-2009 | 1000 | 1300 | 250 | 15 |
| 12-2009 | 1100 | 1500 | 350 | 16 |
| 04-2010 | 1200 | 1600 | 400 | 17 |
| 09-2010 | 1300 | 1700 | 500 | 18 |
| 01-2011 | 1400 | 1800 | 750 | 20 |
| 06-2011 | 1600 | 1800 | 750 | 22 |
| 11-2011 | 1700 | 1700 | 650 | 25 |
| 03-2012 | 1600 | 1500 | 650 | 28 |
| 08-2012 | 1650 | 1500 | 600 | 30 |
| 12-2012 | 1700 | 1600 | 650 | 32 |
| 05-2013 | 1300 | 1200 | 700 | 25 |
| 10-2013 | 1300 | 1300 | 750 | 18 |
| 02-2014 | 1300 | 1400 | 800 | 18 |
| 07-2014 | 1300 | 1450 | 800 | 19 |
| 12-2014 | 1200 | 1250 | 750 | 16 |
| 04-2015 | 1150 | 1150 | 750 | 15 |

**Fig 1. Time-series graphs of the prices of the four precious metals where XAU, XPT and XPD are on the**
**primary y-axis and XAG is on the secondary y-axis.**

[https://doi.org/10.1371/journal.pone.0174232.g001](https://doi.org/10.1371/journal.pone.0174232.g001)

* * *

| Date | XAU |
| --- | --- |
| 05-2009 | 5 |
| 09-2009 | 5 |
| 02-2010 | 5 |
| 06-2010 | 5 |
| 11-2010 | 5 |
| 04-2011 | 5 |
| 08-2011 | 5 |
| 01-2012 | 5 |
| 05-2012 | 5 |
| 10-2012 | 5 |
| 02-2013 | 10 |
| 07-2013 | 50 |
| 12-2013 | 100 |
| 04-2014 | 100 |

| Date | XAG |
| --- | --- |
| 05-2009 | 2 |
| 09-2009 | 2 |
| 02-2010 | 2 |
| 06-2010 | 2 |
| 11-2010 | 2 |
| 04-2011 | 2 |
| 08-2011 | 2 |
| 01-2012 | 2 |
| 05-2012 | 2 |
| 10-2012 | 2 |
| 02-2013 | 5 |
| 07-2013 | 10 |
| 12-2013 | 30 |
| 04-2014 | 100 |

| Category | XAG |
| --- | --- |
| 05-2000 | 0 |
| 09-2000 | 0 |
| 02-2001 | 0 |
| 06-2001 | 0 |
| 11-2001 | 0 |
| 04-2002 | 0 |
| 08-2002 | 0 |
| 01-2003 | 0 |
| 05-2003 | 0 |
| 10-2003 | 0 |
| 03-2004 | 0 |
| 07-2004 | 0 |
| 12-2004 | 0 |
| 05-2005 | 0 |
| 09-2005 | 0 |
| 02-2006 | 0 |
| 06-2006 | 0 |
| 11-2006 | 0 |
| 04-2007 | 0 |
| 08-2007 | 10 |
| 01-2008 | 0 |
| 05-2008 | 0 |
| 10-2008 | 5 |
| 03-2009 | 5 |
| 07-2009 | 5 |
| 12-2009 | 5 |
| 04-2010 | 5 |
| 09-2010 | 20 |
| 01-2011 | 15 |
| 06-2011 | 10 |
| 11-2011 | 10 |
| 03-2012 | 10 |
| 08-2012 | 20 |
| 12-2012 | 15 |
| 05-2013 | 10 |
| 10-2013 | 10 |
| 02-2014 | 10 |
| 07-2014 | 30 |
| 12-2014 | 80 |
| 04-2015 | 100 |

| Category | XPT |
| --- | --- |
| 05-2000 | 0 |
| 09-2000 | 0 |
| 02-2001 | 0 |
| 06-2001 | 0 |
| 11-2001 | 0 |
| 04-2002 | 0 |
| 08-2002 | 0 |
| 01-2003 | 0 |
| 05-2003 | 0 |
| 10-2003 | 0 |
| 03-2004 | 0 |
| 07-2004 | 0 |
| 12-2004 | 0 |
| 05-2005 | 0 |
| 09-2005 | 0 |
| 02-2006 | 0 |
| 06-2006 | 0 |
| 11-2006 | 0 |
| 04-2007 | 0 |
| 08-2007 | 0 |
| 01-2008 | 0 |
| 05-2008 | 0 |
| 10-2008 | 5 |
| 03-2009 | 5 |
| 07-2009 | 10 |
| 12-2009 | 10 |
| 04-2010 | 10 |
| 09-2010 | 50 |
| 01-2011 | 30 |
| 06-2011 | 20 |
| 11-2011 | 15 |
| 03-2012 | 15 |
| 08-2012 | 15 |
| 12-2012 | 10 |
| 05-2013 | 15 |
| 10-2013 | 15 |
| 02-2014 | 15 |
| 07-2014 | 40 |
| 12-2014 | 100 |
| 04-2015 | 80 |

| Category | XPT |
| --- | --- |
| 05-2000 | 0 |
| 09-2000 | 0 |
| 02-2001 | 0 |
| 06-2001 | 0 |
| 11-2001 | 0 |
| 04-2002 | 0 |
| 08-2002 | 0 |
| 01-2003 | 0 |
| 05-2003 | 0 |
| 10-2003 | 0 |
| 03-2004 | 0 |
| 07-2004 | 0 |
| 12-2004 | 0 |
| 05-2005 | 0 |
| 09-2005 | 0 |
| 02-2006 | 0 |
| 06-2006 | 0 |
| 11-2006 | 0 |
| 04-2007 | 0 |
| 08-2007 | 0 |
| 01-2008 | 0 |
| 05-2008 | 2 |
| 10-2008 | 3 |
| 03-2009 | 5 |
| 07-2009 | 10 |
| 12-2009 | 12 |
| 04-2010 | 12 |
| 09-2010 | 20 |
| 01-2011 | 25 |
| 06-2011 | 20 |
| 11-2011 | 15 |
| 03-2012 | 10 |
| 08-2012 | 15 |
| 12-2012 | 15 |
| 05-2013 | 15 |
| 10-2013 | 15 |
| 02-2014 | 20 |
| 07-2014 | 60 |
| 12-2014 | 100 |
| 04-2015 | 60 |

| Category | XPD |
| --- | --- |
| 05-2000 | 0 |
| 09-2000 | 0 |
| 02-2001 | 0 |
| 06-2001 | 0 |
| 11-2001 | 0 |
| 04-2002 | 0 |
| 08-2002 | 0 |
| 01-2003 | 0 |
| 05-2003 | 0 |
| 10-2003 | 0 |
| 03-2004 | 0 |
| 07-2004 | 0 |
| 12-2004 | 0 |
| 05-2005 | 0 |
| 09-2005 | 0 |
| 02-2006 | 0 |
| 06-2006 | 0 |
| 11-2006 | 0 |
| 04-2007 | 0 |
| 08-2007 | 0 |
| 01-2008 | 0 |
| 05-2008 | 1 |
| 10-2008 | 2 |
| 03-2009 | 3 |
| 07-2009 | 5 |
| 12-2009 | 8 |
| 04-2010 | 10 |
| 09-2010 | 15 |
| 01-2011 | 20 |
| 06-2011 | 15 |
| 11-2011 | 10 |
| 03-2012 | 5 |
| 08-2012 | 10 |
| 12-2012 | 15 |
| 05-2013 | 10 |
| 10-2013 | 10 |
| 02-2014 | 15 |
| 07-2014 | 50 |
| 12-2014 | 60 |
| 04-2015 | 40 |

| Category | XPD |
| --- | --- |
| 05-2000 | 0 |
| 09-2000 | 0 |
| 02-2001 | 0 |
| 06-2001 | 0 |
| 11-2001 | 0 |
| 04-2002 | 0 |
| 08-2002 | 0 |
| 01-2003 | 0 |
| 05-2003 | 0 |
| 10-2003 | 0 |
| 03-2004 | 0 |
| 07-2004 | 0 |
| 12-2004 | 0 |
| 05-2005 | 0 |
| 09-2005 | 0 |
| 02-2006 | 0 |
| 06-2006 | 0 |
| 11-2006 | 0 |
| 04-2007 | 0 |
| 08-2007 | 0 |
| 01-2008 | 0 |
| 05-2008 | 0 |
| 10-2008 | 0 |
| 03-2009 | 0 |
| 07-2009 | 0 |
| 12-2009 | 0 |
| 04-2010 | 0 |
| 09-2010 | 0 |
| 01-2011 | 10 |
| 06-2011 | 15 |
| 11-2011 | 20 |
| 03-2012 | 5 |
| 08-2012 | 5 |
| 12-2012 | 15 |
| 05-2013 | 5 |
| 10-2013 | 5 |
| 02-2014 | 10 |
| 07-2014 | 40 |
| 12-2014 | 50 |
| 04-2015 | 30 |

**Fig 2. Time-series graphs of the volume of trades of the four precious metals.**

[https://doi.org/10.1371/journal.pone.0174232.g002](https://doi.org/10.1371/journal.pone.0174232.g002)

trades, followed by silver, platinum and palladium, which is also reported in Tables 1 and 2.
The BAS are reported in Fig 3 and all precious show a large BAS at the beginning of the sample
period. The spread does decreases after May 2003 for all precious metals and stays low
throughout the sample period, except a sharp increase in the spread during the 2008 global
financial crisis. Fig 4 reports the squared returns measure for volatility and shows that volatility
for each precious metal was highest during the 2008 global financial crisis and at certain points
in the early 2000s. Volatility is relatively low from 2010 to 2015, which may be due to the
increase in volume of trading and thus efficiency.

### Results

This section provides the results for the stylized facts of gold, silver, platinum and palladium
returns, volatility, volume and BAS.

### Full sample descriptive statistics

The descriptive statistics for the return series, the volatility measures, volume and BAS for the
full sample period of the four precious metals are reported in Table 1. Panel A shows gold is
the only precious metal to report a positive mean return over are sample period while platinum
has the highest negative mean return and palladium the least negative mean return. Gold
returns are also the least volatile of the precious metals while palladium is found to be the most
volatile. This is consistent with the finding of \[22\] that gold has a larger interest than other precious metals that may lead to higher efficiency compared to other precious metals, which leads
to smaller risk. The kurtosis of gold is much higher than other precious metals with silver having the lowest kurtosis. All precious metals have negative skewness, which is behaviour similar
to that observed in equities.

* * *

**Table 1. Descriptive statistics for the full sample gold, silver, platinum and palladium.** ‘SQ’ denotes the squared returns measure of volatility, ‘GK’
denotes the Garman-Klass measure while ‘RS’ denotes the Rogers-Satchell measure.

|  | XAU | XAG | XPT | XPD |
| --- | --- | --- | --- | --- |
| Panel A: Returns |  |  |  |  |
| Mean | 0.0000901 | -0.0000231 | -0.0000507 | -0.0001706 |
| Std | 0.0796037 | 0.162851 | 0.2070907 | 0.4134391 |
| Kurt | 85.36 | 67.57 | 212.65 | 44.37 |
| Skew | -0.6 | -1.14 | -1.25 | -0.99 |
| 5% quant | 0.0306469 | -0.244998 | -0.271639 | -0.4814728 |
| 25% quant | 0.1053416 | -0.0516929 | 0 | 0 |
| 50% quant | 0 | 0 | 0 | 0 |
| 75% quant | 0.0306469 | 0.0579207 | 0.0059419 | 0 |
| 95% quant | 0.1053416 | 0.229095 | 0.2757941 | 0.558661 |
| Panel B: VolSQ |  |  |  |  |
| Mean | 0.0000006 | 0.0265204 | 0.0428865 | 0.1709317 |
| Std | 0.0000059 | 0.2211995 | 0.6283358 | 1.1639475 |
| Kurt | 82650.17 | 89129.77 | 79533.57 | 129184.22 |
| Skew | 227.69 | 240.32 | 249.7 | 258.3 |
| 5% quant | 0 | 0 | 0 | 0 |
| 25% quant | 0 | 0 | 0 | 0 |
| 50% quant | 0.0000001 | 0.0030575 | 0 | 0 |
| 75% quant | 0.0000005 | 0.0227153 | 0.0143255 | 0.017405 |
| 95% quant | 0.0000023 | 0.1054145 | 0.1758024 | 0.9005991 |
| Panel C: VolGK |  |  |  |  |
| Mean | 0.0075703 | 0.0152828 | 0.0127282 | 0.0142494 |
| Std | 0.0265717 | 0.037425 | 0.0164499 | 0.0213277 |
| Kurt | 88192.25 | 36409.7 | 115.87 | 42.3 |
| Skew | 283.82 | 173.29 | 4.74 | 3.81 |
| 5% quant | 0 | 0 | 0 | 0 |
| 25% quant | 0.0026343 | 0.0028133 | 0 | 0 |
| 50% quant | 0.0063165 | 0.0124145 | 0.0063408 | 0.0040314 |
| 75% quant | 0.010535 | 0.0233759 | 0.0223845 | 0.0242976 |
| 95% quant | 0.0192804 | 0.0409709 | 0.0415909 | 0.051246 |
| Panel D: VolRS |  |  |  |  |
| Mean | 0.007523 | 0.0150185 | 0.0125224 | 0.0125509 |
| Std | 0.0370348 | 0.0159083 | 0.0169529 | 0.0212931 |
| Kurt | 93433.62 | 74.61 | 17.39 | 52.94 |
| Skew | 296.35 | 2.84 | 2.1 | 3.52 |
| 5% quant | 0 | 0 | 0 | 0 |
| 25% quant | 0.001585 | 0 | 0 | 0 |
| 50% quant | 0.0063565 | 0.0125744 | 0 | 0 |
| 75% quant | 0.0107109 | 0.0245575 | 0.0237169 | 0.0210129 |
| 95% quant | 0.0197609 | 0.042643 | 0.0442581 | 0.0533983 |
| Panel E: Volume |  |  |  |  |
| Mean | 21.9704 | 13.2289 | 6.1089 | 3.7997 |
| Std | 27.2509 | 22.2185 | 11.6664 | 106.15 |
| Kurt | 3.36 | 2082.75 | 4842.18 | 121075.1 |
| Skew | 1.64 | 12.47 | 20.91 | 346.2 |
| 5% quant | 0 | 0 | 0 | 0 |

_(Continued)_

* * *

**Table 1.** _(Continued)_

|  | XAU | XAG | XPT | XPD |
| --- | --- | --- | --- | --- |
| 25% quant | 1 | 0 | 0 | 0 |
| 50% quant | 10 | 3 | 0 | 0 |
| 75% quant | 37 | 19 | 9 | 4 |
| 95% quant | 75 | 52 | 27 | 17 |
| Panel F: BAS |  |  |  |  |
| Mean | 0.0012838 | 0.0038627 | 0.0068356 | 0.0173066 |
| Std | 0.000765 | 0.0176961 | 0.010543 | 0.0109459 |
| Kurt | 162.94 | 12592.23 | 30361.7 | 3988.74 |
| Skew | 4.97 | 111.66 | -146.85 | 22.96 |
| 5% quant | 0.000438 | 0.0012642 | 0.0029789 | 0.0066687 |
| 25% quant | 0.0006769 | 0.0025233 | 0.004324 | 0.0084034 |
| 50% quant | 0.0012001 | 0.0037922 | 0.0057904 | 0.0148368 |
| 75% quant | 0.0017833 | 0.0044623 | 0.0081533 | 0.0234192 |
| 95% quant | 0.0023684 | 0.0069136 | 0.0149254 | 0.0377358 |
| Obs | 1,079,830 | 1,079,750 | 1,079,679 | 1,079,688 |

[https://doi.org/10.1371/journal.pone.0174232.t001](https://doi.org/10.1371/journal.pone.0174232.t001)

Panels B, C and D of Table 1 report the descriptive statistics for the volatility measures of
the four precious metals. The SQ measure suggests that platinum has the highest mean volatility, while the GK and RS measures both suggest that silver has the highest mean volatility.
Gold has the highest positive kurtosis according to the GK and RS measures, while the SQ
measure suggests that palladium has the highest kurtosis. All four precious metals volatility
measures have positive skewness, with the SQ measure attributing the highest skewness to palladium, while the GK and RS measures suggest that gold has the highest skewness. Panel E of
Table 1 reports the descriptive statistics of the volume of trades and shows that gold has the
largest mean volume and palladium has the highest variation in volume, followed by silver,
platinum and palladium. All four precious metals volume measures have excess kurtosis and
positive skewness, which increases as the number of trades fall. The BAS analysis of the precious metals is reported in Panel F of Table 1 and shows that platinum has the largest mean
spread, followed by silver, palladium and finally gold. Gold has the smallest mean standard
deviation of BAS while silver has the greatest. The kurtosis of each precious metals BAS indicates leptokurtic distributions and positive skewness.

Overall, from the full sample analysis we can see that gold has the highest mean return and
seems the most liquid since it has the highest mean volume and lowest mean BAS over the full
sample. Palladium seems the least liquid precious metal with the lowest mean volume and
highest mean BAS.

### Subsample descriptive statistics

In order to see how the stylized facts of these precious metals have behaved over our sample
period, we split the full sample period into three equal sub-periods and repeat the analysis
reported in Table 1. The results are reported in Table 2 for gold and silver and Table 3 for platinum and palladium.

Table 2 reports the sub-sample analysis of the descriptive statistics of gold and shows that
the 2005–2010 period had the largest mean return, while the 2010–2015 period had a negative
mean return. The 2005–2010 period also had the largest standard deviation, the highest kurtosis and largest negative skewness of the three sub-samples. In the 2010–2015 period for gold,

* * *

**Table 2. Descriptive statistics for gold and silver over the three subsamples.** ‘SQ’ denotes the squared returns measure of volatility, ‘GK’ denotes the
Garman-Klass measure while ‘RS’ denotes the Rogers-Satchell measure.

|  | XAU 2000-2005 | XAU 2005-2010 | XAU 2010-2015 | XAG 2000-2005 | XAG 2005-2010 | XAG 2010-2015 |
| --- | --- | --- | --- | --- | --- | --- |
| Panel A: Returns |  |  |  |  |  |  |
| Mean | 0.0001539 | 0.0001586 | -0.0000423 | 0.0001313 | -0.000046 | -0.0001547 |
| Std | 0.0781752 | 0.0911624 | 0.0677261 | 0.1545071 | 0.1856633 | 0.1456374 |
| Kurt | 43.64 | 106.39 | 60.87 | 81.44 | 36.9 | 115.62 |
| Skew | -0.52 | -0.94 | 0.16 | -0.98 | -1.2 | -1.14 |
| 5% quant | -0.131098 | -0.1290822 | -0.0926088 | -0.233918 | -0.291971 | -0.207361 |
| 25% quant | -0.0139772 | -0.0329164 | -0.0260909 | 0 | -0.0743218 | -0.0621311 |
| 50% quant | 0 | 0 | 0 | 0 | 0 | 0 |
| 75% quant | 0.0280181 | 0.0369622 | 0.0264651 | 0 | 0.0783392 | 0.0619195 |
| 95% quant | 0.100007 | 0.1232224 | 0.0927663 | 0.223464 | 0.277393 | 0.208877 |
| Panel B: VolSQ |  |  |  |  |  |  |
| Mean | 0.0061114 | 0.0083106 | 0.0045868 | 0.0238724 | 0.0344708 | 0.0212102 |
| Std | 0.0412832 | 0.0865177 | 0.0363694 | 0.2180535 | 0.2150014 | 0.2300389 |
| Kurt | 22665.23 | 52354.51 | 27800.73 | 48209.64 | 46520.06 | 154210.01 |
| Skew | 119.76 | 196.31 | 129.54 | 185.24 | 174.42 | 340.88 |
| 5% quant | 0 | 0 | 0.0000004 | 0 | 0 | 0 |
| 25% quant | 0 | 0.0001551 | 0.0001293 | 0 | 0 | 0.0009529 |
| 50% quant | 0.0005131 | 0.0012179 | 0.0006903 | 0 | 0.0058316 | 0.0038483 |
| 75% quant | 0.0062739 | 0.005627 | 0.0027779 | 0.0255591 | 0.0288249 | 0.0164745 |
| 95% quant | 0.0230615 | 0.0308749 | 0.0166092 | 0.0955546 | 0.1418637 | 0.0761584 |
| Panel C: VolGK |  |  |  |  |  |  |
| Mean | 0.0042371 | 0.0089173 | 0.0095536 | 0.0072037 | 0.0147717 | 0.0238685 |
| Std | 0.0056034 | 0.0444597 | 0.0095908 | 0.0491881 | 0.014154 | 0.038006 |
| Kurt | 11.53 | 33674.9 | 16676.48 | 26452.65 | 9.36 | 28674.04 |
| Skew | 2.39 | 180.48 | 106.98 | 155.4 | 2.18 | 160.03 |
| 5% quant | 0 | 0 | 0.0034378 | 0 | 0 | 0.0066652 |
| 025% quant | 0 | 0.0035623 | 0.0059895 | 0 | 0.0048847 | 0.0151101 |
| 50% quant | 0.002106 | 0.006749 | 0.0085167 | 0 | 0.0114479 | 0.0224272 |
| 75% quant | 0.0063465 | 0.0116234 | 0.0117261 | 0.0106443 | 0.0206488 | 0.0303305 |
| 95% quant | 0.0153137 | 0.0228446 | 0.0190101 | 0.0294107 | 0.0406244 | 0.0450477 |
| Panel D: VolRS |  |  |  |  |  |  |
| Mean | 0.0038064 | 0.0089922 | 0.0097673 | 0.0056961 | 0.0146151 | 0.0247391 |
| Std | 0.0061344 | 0.062423 | 0.0125277 | 0.0134366 | 0.0152348 | 0.012847 |
| Kurt | 17.98 | 34649.13 | 22924.51 | 444.32 | 11.65 | 4.26 |
| Skew | 2.72 | 184.37 | 135.53 | 10.25 | 2.17 | 1.06 |
| 5% quant | 0 | 0 | 0.0034769 | 0 | 0 | 0.0068632 |
| 25% quant | 0 | 0.0033214 | 0.0061366 | 0 | 0 | 0.0159229 |
| 50% quant | 0 | 0.0067261 | 0.008711 | 0 | 0.0116377 | 0.0236178 |
| 75% quant | 0.0062108 | 0.0117933 | 0.0119516 | 0.0320555 | 0.0213779 | 0.0317143 |
| 95% quant | 0.0159441 | 0.0233382 | 0.0192981 | 0.2578042 | 0.0420991 | 0.0467666 |
| Panel E: Volume |  |  |  |  |  |  |
| Mean | 2.28512 | 16.5572 | 47.06131 | 0.9122 | 7.3949 | 31.3766 |
| Std | 4.93763 | 118.59424 | 28.48518 | 2.3133 | 10.7082 | 29.0856 |
| Kurt | 32.67 | 1.13 | 2.52713 | 148.16 | 6.5689 | 2088.77 |
| Skew | 4.51 | 1.31 | 1.23702 | 7.19 | 2.3733 | 14.62 |

_(Continued)_

* * *

**Table 2.** _(Continued)_

|  | XAU 2000-2005 | 2005-2010 | 2010-2015 | XAG 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- | --- | --- | --- |
| 5% quant | 0 | 0 | 11 | 0 | 0 | 3 |
| 25% quant | 0 | 2 | 27 | 0 | 0 | 14 |
| 50% quant | 0 | 9 | 44 | 0 | 3 | 25 |
| 75% quant | 2 | 26 | 59 | 1 | 10 | 39 |
| 95% quant | 12 | 57 | 104 | 5 | 31 | 89 |

| Mean | 0.0018539 | 0.0013977 | 0.0006002 | 0.0043048 | 0.0044053 | 0.0028778 |
| --- | --- | --- | --- | --- | --- | --- |
| Std | 0.0006416 | 0.0006908 | 0.0002486 | 0.0011092 | 0.0019853 | 0.0305432 |
| Kurt | 263.96 | 504.39 | 15.14 | 733.25 | 6.01 | 4263.46 |
| Skew | 11.68 | 8.94 | 2.33 | 15.35 | 1.72 | 65.25 |
| 5% quant | 0.0012523 | 0.0007244 | 0.0002016 | 0.0028531 | 0.0023895 | 0.0010045 |
| 25% quant | 0.0016095 | 0.0009029 | 0.0004774 | 0.0040241 | 0.0030143 | 0.0014489 |
| 50% quant | 0.0018152 | 0.0012031 | 0.0005766 | 0.0043073 | 0.0037125 | 0.002007 |
| 75% quant | 0.0018972 | 0.001642 | 0.0006846 | 0.0045351 | 0.005301 | 0.0028531 |
| 95% quant | 0.0025924 | 0.0025238 | 0.0009878 | 0.0060423 | 0.0085561 | 0.0050865 |
| Obs | 359,772 | 360,180 | 359,928 | 359,676 | 360,180 | 359,894 |

[https://doi.org/10.1371/journal.pone.0174232.t002](https://doi.org/10.1371/journal.pone.0174232.t002)

returns were positively skewed compared to negative skewness in the previous two periods,
indicating that the gold returns in the 2010–2015 period behaved differently to the previous
periods. The SQ and GK volatility measures show that volatility increased from the first subsample to the second subsample, but in the final subsample the volatility is at its lowest. The
RS measure, however, suggests that volatility has increased over time in each subsample

| Category | XAU |
| --- | --- |
| 05-2000 | 0.002 |
| 09-2000 | 0.002 |
| 02-2001 | 0.003 |
| 06-2001 | 0.002 |
| 11-2001 | 0.017 |
| 04-2002 | 0.002 |
| 08-2002 | 0.001 |
| 01-2003 | 0.001 |
| 05-2003 | 0.002 |
| 10-2003 | 0.001 |
| 03-2004 | 0.001 |
| 07-2004 | 0.001 |
| 12-2004 | 0.001 |
| 05-2005 | 0.001 |
| 09-2005 | 0.001 |
| 02-2006 | 0.002 |
| 06-2006 | 0.002 |
| 11-2006 | 0.002 |
| 04-2007 | 0.001 |
| 08-2007 | 0.001 |
| 01-2008 | 0.001 |
| 05-2008 | 0.001 |
| 10-2008 | 0.002 |
| 03-2009 | 0.003 |
| 07-2009 | 0.001 |
| 12-2009 | 0.001 |
| 04-2010 | 0.001 |
| 09-2010 | 0.001 |
| 01-2011 | 0.001 |
| 06-2011 | 0.001 |
| 11-2011 | 0.001 |
| 03-2012 | 0.001 |
| 08-2012 | 0.001 |
| 12-2012 | 0.001 |
| 05-2013 | 0.001 |
| 10-2013 | 0.001 |
| 02-2014 | 0.001 |
| 07-2014 | 0.001 |
| 12-2014 | 0.001 |
| 04-2015 | 0.001 |

| Category | XAG |
| --- | --- |
| 05-2000 | 0.007 |
| 09-2000 | 0.007 |
| 02-2001 | 0.008 |
| 06-2001 | 0.026 |
| 11-2001 | 0.008 |
| 04-2002 | 0.007 |
| 08-2002 | 0.005 |
| 01-2003 | 0.005 |
| 05-2003 | 0.005 |
| 10-2003 | 0.004 |
| 03-2004 | 0.004 |
| 07-2004 | 0.007 |
| 12-2004 | 0.005 |
| 05-2005 | 0.004 |
| 09-2005 | 0.004 |
| 02-2006 | 0.004 |
| 06-2006 | 0.008 |
| 11-2006 | 0.012 |
| 04-2007 | 0.006 |
| 08-2007 | 0.004 |
| 01-2008 | 0.003 |
| 05-2008 | 0.004 |
| 10-2008 | 0.008 |
| 03-2009 | 0.008 |
| 07-2009 | 0.006 |
| 12-2009 | 0.005 |
| 04-2010 | 0.004 |
| 09-2010 | 0.003 |
| 01-2011 | 0.003 |
| 06-2011 | 0.003 |
| 11-2011 | 0.004 |
| 03-2012 | 0.004 |
| 08-2012 | 0.003 |
| 12-2012 | 0.003 |
| 05-2013 | 0.004 |
| 10-2013 | 0.006 |
| 02-2014 | 0.006 |
| 07-2014 | 0.006 |
| 12-2014 | 0.006 |
| 04-2015 | 0.005 |

| Category | XAG |
| --- | --- |
| 05-2000 | 0.005 |
| 09-2000 | 0.005 |
| 02-2001 | 0.005 |
| 06-2001 | 0.005 |
| 11-2001 | 0.005 |
| 04-2002 | 0.005 |
| 08-2002 | 0.005 |
| 01-2003 | 0.005 |
| 05-2003 | 0.005 |
| 10-2003 | 0.005 |
| 03-2004 | 0.005 |
| 07-2004 | 0.005 |
| 12-2004 | 0.005 |
| 05-2005 | 0.005 |
| 09-2005 | 0.005 |
| 02-2006 | 0.005 |
| 06-2006 | 0.01 |
| 11-2006 | 0.01 |
| 04-2007 | 0.005 |
| 08-2007 | 0.005 |
| 01-2008 | 0.005 |
| 05-2008 | 0.005 |
| 10-2008 | 0.01 |
| 03-2009 | 0.01 |
| 07-2009 | 0.005 |
| 12-2009 | 0.005 |
| 04-2010 | 0.005 |
| 09-2010 | 0.005 |
| 01-2011 | 0.005 |
| 06-2011 | 0.005 |
| 11-2011 | 0.005 |
| 03-2012 | 0.005 |
| 08-2012 | 0.005 |
| 12-2012 | 0.005 |
| 05-2013 | 0.005 |
| 10-2013 | 0.005 |
| 02-2014 | 0.005 |
| 07-2014 | 0.005 |
| 12-2014 | 0.005 |
| 04-2015 | 0.005 |

| Category | XPT |
| --- | --- |
| 05-2000 | 0.02 |
| 09-2000 | 0.015 |
| 02-2001 | 0.015 |
| 06-2001 | 0.015 |
| 11-2001 | 0.02 |
| 04-2002 | 0.045 |
| 08-2002 | 0.015 |
| 01-2003 | 0.005 |
| 05-2003 | 0.005 |
| 10-2003 | 0.005 |
| 03-2004 | 0.005 |
| 07-2004 | 0.005 |
| 12-2004 | 0.005 |
| 05-2005 | 0.005 |
| 09-2005 | 0.005 |
| 02-2006 | 0.005 |
| 06-2006 | 0.005 |
| 11-2006 | 0.005 |
| 04-2007 | 0.005 |
| 08-2007 | 0.005 |
| 01-2008 | 0.005 |
| 05-2008 | 0.005 |
| 10-2008 | 0.02 |
| 03-2009 | 0.02 |
| 07-2009 | 0.01 |
| 12-2009 | 0.005 |
| 04-2010 | 0.005 |
| 09-2010 | 0.005 |
| 01-2011 | 0.005 |
| 06-2011 | 0.005 |
| 11-2011 | 0.005 |
| 03-2012 | 0.005 |
| 08-2012 | 0.005 |
| 12-2012 | 0.005 |
| 05-2013 | 0.005 |
| 10-2013 | 0.005 |
| 02-2014 | 0.005 |
| 07-2014 | 0.005 |
| 12-2014 | 0.005 |
| 04-2015 | 0.005 |

| Category | XPT |
| --- | --- |
| 05-2000 | 0.035 |
| 09-2000 | 0.015 |
| 02-2001 | 0.015 |
| 06-2001 | 0.015 |
| 11-2001 | 0.045 |
| 04-2002 | 0.045 |
| 08-2002 | 0.015 |
| 01-2003 | 0.005 |
| 05-2003 | 0.005 |
| 10-2003 | 0.005 |
| 03-2004 | 0.005 |
| 07-2004 | 0.005 |
| 12-2004 | 0.005 |
| 05-2005 | 0.005 |
| 09-2005 | 0.005 |
| 02-2006 | 0.005 |
| 06-2006 | 0.005 |
| 11-2006 | 0.005 |
| 04-2007 | 0.005 |
| 08-2007 | 0.005 |
| 01-2008 | 0.005 |
| 05-2008 | 0.005 |
| 10-2008 | 0.03 |
| 03-2009 | 0.015 |
| 07-2009 | 0.01 |
| 12-2009 | 0.005 |
| 04-2010 | 0.005 |
| 09-2010 | 0.005 |
| 01-2011 | 0.005 |
| 06-2011 | 0.005 |
| 11-2011 | 0.005 |
| 02-2012 | 0.005 |
| 08-2012 | 0.005 |
| 12-2012 | 0.005 |
| 05-2013 | 0.005 |
| 10-2013 | 0.005 |
| 02-2014 | 0.005 |
| 07-2014 | 0.005 |
| 12-2014 | 0.005 |
| 04-2015 | 0.005 |

| Category | XPD |
| --- | --- |
| 05-2000 | 0.025 |
| 09-2000 | 0.02 |
| 02-2001 | 0.025 |
| 06-2001 | 0.03 |
| 11-2001 | 0.04 |
| 04-2002 | 0.04 |
| 08-2002 | 0.035 |
| 01-2003 | 0.035 |
| 05-2003 | 0.035 |
| 10-2003 | 0.03 |
| 03-2004 | 0.025 |
| 07-2004 | 0.025 |
| 12-2004 | 0.025 |
| 05-2005 | 0.025 |
| 09-2005 | 0.02 |
| 02-2006 | 0.02 |
| 06-2006 | 0.02 |
| 11-2006 | 0.015 |
| 04-2007 | 0.015 |
| 08-2007 | 0.015 |
| 01-2008 | 0.015 |
| 05-2008 | 0.015 |
| 10-2008 | 0.05 |
| 03-2009 | 0.03 |
| 07-2009 | 0.02 |
| 12-2009 | 0.015 |
| 04-2010 | 0.01 |
| 09-2010 | 0.01 |
| 01-2011 | 0.01 |
| 06-2011 | 0.01 |
| 11-2011 | 0.01 |
| 02-2012 | 0.01 |
| 08-2012 | 0.01 |
| 12-2012 | 0.01 |
| 05-2013 | 0.01 |
| 10-2013 | 0.01 |
| 02-2014 | 0.01 |
| 07-2014 | 0.01 |
| 12-2014 | 0.01 |
| 04-2015 | 0.01 |

| Category | XPD |
| --- | --- |
| 05-2000 | 0.03 |
| 09-2000 | 0.025 |
| 02-2001 | 0.03 |
| 06-2001 | 0.035 |
| 11-2001 | 0.04 |
| 04-2002 | 0.04 |
| 08-2002 | 0.035 |
| 01-2003 | 0.035 |
| 05-2003 | 0.04 |
| 10-2003 | 0.035 |
| 03-2004 | 0.025 |
| 07-2004 | 0.025 |
| 12-2004 | 0.025 |
| 05-2005 | 0.025 |
| 09-2005 | 0.02 |
| 02-2006 | 0.015 |
| 06-2006 | 0.015 |
| 11-2006 | 0.01 |
| 04-2007 | 0.01 |
| 08-2007 | 0.008 |
| 01-2008 | 0.008 |
| 05-2008 | 0.01 |
| 10-2008 | 0.05 |
| 03-2009 | 0.03 |
| 07-2009 | 0.02 |
| 12-2009 | 0.015 |
| 04-2010 | 0.01 |
| 09-2010 | 0.008 |
| 01-2011 | 0.008 |
| 06-2011 | 0.008 |
| 11-2011 | 0.008 |
| 03-2012 | 0.007 |
| 08-2012 | 0.006 |
| 12-2012 | 0.005 |
| 05-2013 | 0.004 |
| 10-2013 | 0.003 |
| 02-2014 | 0.003 |
| 07-2014 | 0.002 |
| 12-2014 | 0.002 |
| 04-2015 | 0.001 |

**Fig 3. Time-series graphs of the BAS of the four precious metals.**

[https://doi.org/10.1371/journal.pone.0174232.g003](https://doi.org/10.1371/journal.pone.0174232.g003)

* * *

| Category | XAU |
| --- | --- |
| 05-2000 | 0.1 |
| 09-2000 | 0.1 |
| 02-2001 | 0.05 |
| 06-2001 | 0.6 |
| 11-2001 | 0.05 |
| 04-2002 | 0.05 |
| 08-2002 | 0.05 |
| 01-2003 | 0.1 |
| 05-2003 | 0.2 |
| 10-2003 | 0.05 |
| 03-2004 | 0.05 |
| 07-2004 | 0.45 |
| 12-2004 | 0.1 |
| 05-2005 | 0.05 |
| 09-2005 | 0.05 |
| 02-2006 | 0.5 |
| 06-2006 | 0.5 |
| 11-2006 | 0.55 |
| 04-2007 | 0.05 |
| 08-2007 | 0.05 |
| 01-2008 | 0.3 |
| 05-2008 | 0.1 |
| 10-2008 | 0.6 |
| 03-2009 | 0.05 |
| 07-2009 | 0.05 |
| 12-2009 | 0.05 |
| 04-2010 | 0.05 |
| 09-2010 | 0.05 |
| 01-2011 | 0.05 |
| 06-2011 | 0.05 |
| 11-2011 | 0.05 |
| 03-2012 | 0.05 |
| 08-2012 | 0.05 |
| 12-2012 | 0.05 |
| 05-2013 | 0.3 |
| 10-2013 | 0.05 |
| 02-2014 | 0.05 |
| 07-2014 | 0.05 |
| 12-2014 | 0.05 |
| 04-2015 | 0.05 |

| Category | XAG |
| --- | --- |
| 05-2000 | 0.1 |
| 09-2000 | 0.1 |
| 02-2001 | 1.2 |
| 06-2001 | 0.1 |
| 11-2001 | 1 |
| 04-2002 | 0.1 |
| 08-2002 | 0.1 |
| 01-2003 | 0.1 |
| 05-2003 | 0.5 |
| 10-2003 | 0.1 |
| 03-2004 | 0.1 |
| 07-2004 | 1 |
| 12-2004 | 0.1 |
| 05-2005 | 0.1 |
| 09-2005 | 0.1 |
| 02-2006 | 0.1 |
| 06-2006 | 0.5 |
| 11-2006 | 0.1 |
| 04-2007 | 0.05 |
| 08-2007 | 0.05 |
| 01-2008 | 0.05 |
| 05-2008 | 0.1 |
| 10-2008 | 1.9 |
| 03-2009 | 0.1 |
| 07-2009 | 0.05 |
| 12-2009 | 0.05 |
| 04-2010 | 0.05 |
| 09-2010 | 0.05 |
| 01-2011 | 0.05 |
| 06-2011 | 0.1 |
| 11-2011 | 0.6 |
| 03-2012 | 0.05 |
| 08-2012 | 0.05 |
| 12-2012 | 0.05 |
| 05-2013 | 0.05 |
| 10-2013 | 0.05 |
| 02-2014 | 0.05 |
| 07-2014 | 0.05 |
| 12-2014 | 0.05 |
| 04-2015 | 0.05 |

| Category | XPT |
| --- | --- |
| 05-2000 | 2.2 |
| 09-2000 | 0.1 |
| 02-2001 | 0.1 |
| 06-2001 | 0.1 |
| 11-2001 | 0.05 |
| 04-2002 | 2.5 |
| 08-2002 | 1.6 |
| 01-2003 | 2.3 |
| 05-2003 | 0.1 |
| 10-2003 | 0.1 |
| 03-2004 | 0.1 |
| 07-2004 | 1.3 |
| 12-2004 | 0.05 |
| 05-2005 | 0.05 |
| 09-2005 | 0.05 |
| 02-2006 | 0.05 |
| 06-2006 | 0.05 |
| 11-2006 | 0.05 |
| 04-2007 | 0.05 |
| 08-2007 | 0.05 |
| 01-2008 | 0.05 |
| 05-2008 | 0.05 |
| 10-2008 | 2.5 |
| 03-2009 | 1.5 |
| 07-2009 | 0.1 |
| 12-2009 | 0.05 |
| 04-2010 | 0.05 |
| 09-2010 | 0.05 |
| 01-2011 | 0.05 |
| 06-2011 | 0.05 |
| 11-2011 | 0.05 |
| 03-2012 | 0.05 |
| 08-2012 | 0.05 |
| 12-2012 | 0.05 |
| 05-2013 | 0.05 |
| 10-2013 | 0.05 |
| 02-2014 | 0.05 |
| 07-2014 | 0.05 |
| 12-2014 | 0.05 |
| 04-2015 | 0.05 |

| Category | XPD |
| --- | --- |
| 05-2000 | 0.5 |
| 09-2000 | 0.5 |
| 02-2001 | 0.5 |
| 06-2001 | 0.5 |
| 11-2001 | 0.5 |
| 04-2002 | 3 |
| 08-2002 | 6 |
| 01-2003 | 3 |
| 05-2003 | 7 |
| 10-2003 | 5 |
| 03-2004 | 2 |
| 07-2004 | 4 |
| 12-2004 | 2 |
| 05-2005 | 2 |
| 09-2005 | 2 |
| 02-2006 | 2 |
| 06-2006 | 6 |
| 11-2006 | 8 |
| 04-2007 | 0.5 |
| 08-2007 | 0.5 |
| 01-2008 | 10 |
| 05-2008 | 2 |
| 10-2008 | 12 |
| 03-2009 | 3 |
| 07-2009 | 1 |
| 12-2009 | 0.5 |
| 04-2010 | 0.5 |
| 09-2010 | 0.5 |
| 01-2011 | 0.5 |
| 06-2011 | 0.5 |
| 11-2011 | 0.5 |
| 03-2012 | 0.5 |
| 08-2012 | 0.5 |
| 12-2012 | 0.5 |
| 05-2013 | 0.5 |
| 10-2013 | 0.5 |
| 02-2014 | 0.5 |
| 07-2014 | 0.5 |
| 12-2014 | 0.5 |
| 04-2015 | 0.5 |

**Fig 4. Time-series graphs of the squared returns measure of volatility of the four precious metals.**

[https://doi.org/10.1371/journal.pone.0174232.g004](https://doi.org/10.1371/journal.pone.0174232.g004)

period. The volume results show that the number of trades for gold has increased substantially
over time, from 2.28 in the first subsample to 47.06 in the third subsample indicating the
increase in trading in gold over the previous 15 years. The mean BAS has also decreased substantially over time, from 0.00185 in the 2000–2005 period to 0.000600 in the 2010–2015
period, also indicating an increase in liquidity and efficiency of the gold market. This finding
is consistent with a number of other empirical studies.

The silver sub-sample results show that in the first period silver had a positive mean return,
which turned negative in the middle period and increasingly negative in the final period. The
2005–2010 period has the largest standard deviation of returns, while the 2010–2015 period
experiences the largest kurtosis of returns. All periods experience negative skewness with the
2005–2010 period experiencing the largest negative skewness. The SQ volatility measure suggests that the 2005–2010 subsample has the highest mean volatility, while the GK and RS measures both suggest that volatility has increased over time with the final subsample exhibiting
the largest volatility. Similar to gold, the mean volume of trades of silver increases over time,
from 0.91 in the 2000–2005 period to 31.38 in the 2010–2015 period indicating an increase in
liquidity over time. Furthermore, the BAS has decreased over time from 0.00430 in the 2000–
2005 period to 0.00288 in the 2010–2015 period, again suggesting an increase in liquidity and
efficiency in the silver market.

The sub-sample platinum results are reported in Table 3, the largest mean return is in the
2000–2005 period while the other two subsamples have negative mean returns. The first period
has the largest standard deviation of returns and all the returns have positive kurtosis and negative skewness, with the 2000–2005 period having the largest negative skewness. All three volatility measures suggest that the 2000–2005 period has the largest mean volatility and the 2005–
2010 subsample is the least volatile period. The mean volume of platinum increases over time
from 1.11 in the 2000–2005 period to 15.91 in the 2010–2015 period indicating a substantial

* * *

**Table 3. Descriptive statistics for platinum and palladium over the three subsamples.** ‘SQ’ denotes the squared returns measure of volatility, ‘GK’
denotes the Garman-Klass measure while ‘RS’ denotes the Rogers-Satchell measure.

|  | XPT 2000-2005 | XPT 2005-2010 | XPT 2010-2015 | XPD 2000-2005 | XPD 2005-2010 | XPD 2010-2015 |
| --- | --- | --- | --- | --- | --- | --- |
| Panel A: Returns |  |  |  |  |  |  |
| Mean | 0.0000261 | -0.0002689 | -0.0004081 | -0.0003236 | 0.0001407 | -0.0003292 |
| Std | 0.2316635 | 0.1313224 | 0.1325972 | 0.4563751 | 0.5106873 | 0.2089926 |
| Kurt | 65.16 | 12.4 | 10.22 | 21.24 | 42.34 | 4.9 |
| Skew | -0.31 | -0.27 | -0.22 | -1.3 | -0.64 | -0.1664 |
| 5% quant | -0.3243761 | -0.2131644 | -0.2161918 | 0 | -0.835078 | -0.3611549 |
| 25% quant | 0 | -0.0642675 | -0.0650618 | 0 | 0 | -0.0831324 |
| 50% quant | 0 | 0 | 0 | 0 | 0 | 0 |
| 75% quant | 0 | 0.065083 | 0.0644745 | 0 | 0 | 0.082306 |
| 95% quant | 0.288123 | 0.206541 | 0.215728 | 0.508907 | 0.805806 | 0.369086 |
| Panel B: Vol^SQ |  |  |  |  |  |  |
| Mean | 0.0536678 | 0.0172456 | 0.0175821 | 0.2082778 | 0.2608008 | 0.0436779 |
| Std | 0.4398046 | 0.0654449 | 0.0614795 | 1.0040702 | 1.7365975 | 0.1147294 |
| Kurt | 82256.58 | 5901.34 | 7095.85 | 516.42 | 78042.21 | 2210.22 |
| Skew | 216.23 | 59.3982271 | 59.76 | 14.96 | 230.06 | 25.4568 |
| 5% quant | 0 | 0 | 0 | 0 | 0 | 0 |
| 25% quant | 0 | 0.0006522 | 0.000581 | 0 | 0 | 0.0009081 |
| 50% quant | 0 | 0.0041785 | 0.0041947 | 0 | 0 | 0.0068422 |
| 75% quant | 0.0133805 | 0.0188734 | 0.018502 | 0 | 0.0474652 | 0.0411502 |
| 95% quant | 0.2083128 | 0.0700132 | 0.0743775 | 1.4692834 | 1.2913595 | 0.1969263 |
| Panel C: Vol^GK |  |  |  |  |  |  |
| Mean | 0.0064574 | 0.0230374 | 0.0252609 | 0.0052386 | 0.0115267 | 0.0259776 |
| Std | 0.0121131 | 0.0107706 | 0.0125457 | 0.0184928 | 0.0230601 | 0.0162669 |
| Kurt | 9.75 | 9.16 | 4.06 | 141.37 | 43.15 | -0.0415584 |
| Skew | 2.72 | 1.45 | 1.0734 | 8.48 | 4.76 | 0.5461874 |
| 5% quant | 0 | 0.0073931 | 0.0076231 | 0 | 0 | 0.0034676 |
| 25% quant | 0 | 0.0165241 | 0.0171216 | 0 | 0 | 0.0124797 |
| 50% quant | 0 | 0.0221416 | 0.0234502 | 0 | 0 | 0.0244 |
| 75% quant | 0.0072826 | 0.0284787 | 0.0317613 | 0 | 0.0149993 | 0.0374223 |
| 95% quant | 0.0336807 | 0.041013 | 0.0480681 | 0.0312871 | 0.0538244 | 0.0541242 |
| Panel D: Vol^RS |  |  |  |  |  |  |
| Mean | 0.0054296 | 0.0247651 | 0.0273644 | 0.0015561 | 0.0084784 | 0.0276124 |
| Std | 0.0125796 | 0.0125911 | 0.014309 | 0.014508 | 0.0210822 | 0.0184613 |
| Kurt | 12.79 | 16.75 | 8.43 | 711.29 | 20.74 | 0.1865454 |
| Skew | 3.1 | 2.08 | 1.49 | 19.1 | 3.72 | 0.5839 |
| 5% quant | 0 | 0.00599645 | 0.0070885 | 0 | 0 | 0 |
| 25% quant | 0 | 0.0176513 | 0.0184945 | 0 | 0 | 0.0125471 |
| 50% quant | 0 | 0.02397 | 0.0254553 | 0 | 0 | 0.0257088 |
| 75% quant | 0 | 0.0307562 | 0.0343755 | 0 | 0 | 0.0406122 |
| 95% quant | 0.0345248 | 0.0442156 | 0.0524275 | 0 | 0.0531628 | 0.0592283 |
| Panel E: Volume |  |  |  |  |  |  |
| Mean | 1.1077 | 12.5458 | 15.9085 | 0.0752 | 0.6777 | 10.6456 |
| Std | 3.4527 | 10.8855 | 15.1886 | 0.3649 | 1.9821 | 183.6478 |
| Kurt | 242.87 | 10.64 | 4983.8 | 499.9 | 55.3419 | 40505.6 |
| Skew | 9.87 | 2.45 | 25.95 | 12.31 | 5.8662 | 200.43 |

_(Continued)_

* * *

**Table 3.** _(Continued)_

|  | XPT 2000-2005 | 2005-2010 | 2010-2015 | XPD 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- | --- | --- | --- |
| 5% quant | 0 | 0 | 1 | 0 | 0 | 0 |
| 25% quant | 0 | 5 | 7 | 0 | 0 | 3 |
| 50% quant | 0 | 11 | 13 | 0 | 0 | 7 |
| 75% quant | 1 | 16 | 19 | 0 | 0 | 13 |
| 95% quant | 7 | 32 | 47 | 1 | 4 | 32 |
| Panel F: BAS |  |  |  |  |  |  |
| Mean | 0.006409 | 0.0049555 | 0.0050733 | 0.0267059 | 0.0172727 | 0.0079489 |
| Std | 0.0049016 | 0.0049242 | 0.0049665 | 0.0084668 | 0.0079979 | 0.0069243 |
| Kurt | 17.04 | 151108.09 | 146149.84 | 2.8085356 | 6.83 | 76128.69 |
| Skew | 3.47 | -2.76 | -2.76 | 1.1 | 2.18 | 264.65 |
| 5% quant | 0.0030817 | 0.0028241 | 0.0025684 | 0.0149925 | 0.00907803 | 0.0048251 |
| 25% quant | 0.004008 | 0.0040628 | 0.0041728 | 0.0210526 | 0.01204822 | 0.0070274 |
| 50% quant | 0.004761 | 0.0048997 | 0.0050234 | 0.0254453 | 0.0152091 | 0.0076211 |
| 75% quant | 0.0059701 | 0.0061425 | 0.0063336 | 0.0309598 | 0.01988078 | 0.0085616 |
| 95% quant | 0.0168138 | 0.0071136 | 0.0073651 | 0.0424328 | 0.0322581 | 0.0114811 |
| Obs | 359,727 | 360,180 | 359,902 | 359,606 | 360,180 | 359,902 |

[https://doi.org/10.1371/journal.pone.0174232.t003](https://doi.org/10.1371/journal.pone.0174232.t003)

increase in liquidity over time. Also, the BAS decreased from 0.0064 in the 2000–2005 subsample to 0.0050 in the 2005–2010 subsample. The BAS in the final subsample is slightly higher at
0.0051, indicating that from the first subsample to the final two the BAS has decreased, consistent with an increase in liquidity and efficiency of the platinum market.

The palladium results show that the 2000–2005 and 2010–2015 periods have negative mean
returns, while the 2005–2010 period has a positive mean return. The 2005–2010 period experiences the largest standard deviation of returns and all periods have positive kurtosis and negative skewness. The SQ and RS measures of volatility indicate that the 2005–2010 period has the
highest mean volatility while the GK measure suggests the 2010–2015 period has the highest
volatility. The mean volume of trades increases substantially over time, from 0.08 in the 2000–
2005 subsample to 10.65 in the 2010–2015 subsample. The BAS has decreased over time, from
0.02670 in the 2000–2005 period to 0.00795 in the 2010–2015 period, indicating an increase in
liquidity and efficiency of the palladium market.

The sub-period results show that each precious metal experienced negative mean returns in
the 2010–2015 period and that the number of trades increased substantially over time. Furthermore, the trading volume in the first sub-sample period is very low for each precious metal,
indicating the lack of liquidity at the 5-minute level. Therefore our results show that the behaviour of precious metals has changed substantially over time.

### Intraday stylized facts

Fig 5 reports the intraday mean volume of trades at the 5-minute intervals, all four precious
metals exhibit n-shaped patterns, the number of trades increases until the early afternoon
GMT and then falls away. This is consistent with the opening hours of European markets (9
AM to 5 PM GMT) and North American markets (about 3 PM to 8 PM GMT), where the
highest volume of trades takes place round 11 AM GMT to 5 PM GMT when both markets are
open. These findings suggest the possible presence of a periodic pattern in volume, which is
investigated in more detail on the subsample level.

* * *

**XAU**

| Category | XAU |
| --- | --- |
| 00:00 | 17 |
| 00:20 | 17 |
| 00:40 | 17 |
| 01:00 | 19 |
| 01:20 | 18 |
| 01:40 | 18 |
| 02:00 | 17 |
| 02:20 | 16 |
| 02:40 | 16 |
| 03:00 | 16 |
| 03:20 | 16 |
| 03:40 | 15 |
| 04:00 | 15 |
| 04:20 | 16 |
| 04:40 | 18 |
| 05:00 | 17 |
| 05:20 | 18 |
| 05:40 | 20 |
| 06:00 | 23 |
| 06:20 | 24 |
| 06:40 | 25 |
| 07:00 | 26 |
| 07:20 | 26 |
| 07:40 | 26 |
| 08:00 | 26 |
| 08:20 | 26 |
| 08:40 | 26 |
| 09:00 | 26 |
| 09:20 | 27 |
| 09:40 | 26 |
| 10:00 | 25 |
| 10:20 | 25 |
| 10:40 | 25 |
| 11:00 | 25 |
| 11:20 | 25 |
| 11:40 | 25 |
| 12:00 | 26 |
| 12:20 | 28 |
| 12:40 | 30 |
| 13:00 | 30 |
| 13:20 | 31 |
| 13:40 | 32 |
| 14:00 | 32 |
| 14:20 | 32 |
| 14:40 | 32 |
| 15:00 | 31 |
| 15:20 | 31 |
| 15:40 | 30 |
| 16:00 | 29 |
| 16:20 | 28 |
| 16:40 | 28 |
| 17:00 | 27 |
| 17:20 | 26 |
| 17:40 | 23 |
| 18:00 | 23 |
| 18:20 | 20 |
| 18:40 | 19 |
| 19:00 | 18 |
| 19:20 | 18 |
| 19:40 | 17 |
| 20:00 | 13 |
| 20:20 | 13 |
| 20:40 | 12 |
| 21:00 | 10 |
| 21:20 | 7 |
| 21:40 | 6 |
| 22:00 | 5 |
| 22:20 | 4 |
| 22:40 | 4 |
| 23:00 | 9 |
| 23:20 | 10 |
| 23:40 | 12 |

**XAG**

| Category | XAG |
| --- | --- |
| 00:00 | 8 |
| 00:20 | 8 |
| 00:40 | 8 |
| 01:00 | 13 |
| 01:20 | 10 |
| 01:40 | 10 |
| 02:00 | 9 |
| 02:20 | 8 |
| 02:40 | 9 |
| 03:00 | 8 |
| 03:20 | 8 |
| 03:40 | 7 |
| 04:00 | 7 |
| 04:20 | 8 |
| 04:40 | 12 |
| 05:00 | 9 |
| 05:20 | 9 |
| 05:40 | 12 |
| 06:00 | 13 |
| 06:20 | 14 |
| 06:40 | 14 |
| 07:00 | 15 |
| 07:20 | 16 |
| 07:40 | 16 |
| 08:00 | 15 |
| 08:20 | 16 |
| 08:40 | 15 |
| 09:00 | 15 |
| 09:20 | 15 |
| 09:40 | 15 |
| 10:00 | 14 |
| 10:20 | 14 |
| 10:40 | 14 |
| 11:00 | 15 |
| 11:20 | 15 |
| 11:40 | 15 |
| 12:00 | 17 |
| 12:20 | 19 |
| 12:40 | 20 |
| 13:00 | 19 |
| 13:20 | 21 |
| 13:40 | 21 |
| 14:00 | 20 |
| 14:20 | 20 |
| 14:40 | 20 |
| 15:00 | 19 |
| 15:20 | 19 |
| 15:40 | 18 |
| 16:00 | 17 |
| 16:20 | 17 |
| 16:40 | 16 |
| 17:00 | 16 |
| 17:20 | 17 |
| 17:40 | 13 |
| 18:00 | 14 |
| 18:20 | 12 |
| 18:40 | 11 |
| 19:00 | 10 |
| 19:20 | 10 |
| 19:40 | 9 |
| 20:00 | 8 |
| 20:20 | 6 |
| 20:40 | 6 |
| 21:00 | 4 |
| 21:20 | 3 |
| 21:40 | 3 |
| 22:00 | 3 |
| 22:20 | 3 |
| 22:40 | 4 |
| 23:00 | 5 |
| 23:20 | 5 |
| 23:40 | 6 |

| Category | XAG |
| --- | --- |
| 00:00-00:20 | 8 |
| 00:20-00:40 | 8.5 |
| 00:40-01:00 | 9 |
| 01:00-01:20 | 13 |
| 01:20-01:40 | 10.5 |
| 01:40-02:00 | 10 |
| 02:00-02:20 | 8 |
| 02:20-02:40 | 9 |
| 02:40-03:00 | 9 |
| 03:00-03:20 | 8.5 |
| 03:20-03:40 | 8 |
| 03:40-04:00 | 7 |
| 04:00-04:20 | 7 |
| 04:20-04:40 | 12 |
| 04:40-05:00 | 9.5 |
| 05:00-05:20 | 9.5 |
| 05:20-05:40 | 12 |
| 05:40-06:00 | 13 |
| 06:00-06:20 | 14 |
| 06:20-06:40 | 14 |
| 06:40-07:00 | 15 |
| 07:00-07:20 | 16 |
| 07:20-07:40 | 16 |
| 07:40-08:00 | 16 |
| 08:00-08:20 | 16 |
| 08:20-08:40 | 16 |
| 08:40-09:00 | 15.5 |
| 09:00-09:20 | 15.5 |
| 09:20-09:40 | 15 |
| 09:40-10:00 | 15 |
| 10:00-10:20 | 14 |
| 10:20-10:40 | 14 |
| 10:40-11:00 | 14 |
| 11:00-11:20 | 16 |
| 11:20-11:40 | 15 |
| 11:40-12:00 | 15 |
| 12:00-12:20 | 17 |
| 12:20-12:40 | 20 |
| 12:40-13:00 | 21 |
| 13:00-13:20 | 22 |
| 13:20-13:40 | 22 |
| 13:40-14:00 | 22 |
| 14:00-14:20 | 22 |
| 14:20-14:40 | 21 |
| 14:40-15:00 | 21 |
| 15:00-15:20 | 21 |
| 15:20-15:40 | 20 |
| 15:40-16:00 | 19 |
| 16:00-16:20 | 18 |
| 16:20-16:40 | 17 |
| 16:40-17:00 | 17 |
| 17:00-17:20 | 18 |
| 17:20-17:40 | 14 |
| 17:40-18:00 | 14 |
| 18:00-18:20 | 14 |
| 18:20-18:40 | 11 |
| 18:40-19:00 | 11 |
| 19:00-19:20 | 10 |
| 19:20-19:40 | 10 |
| 19:40-20:00 | 9 |
| 20:00-20:20 | 6 |
| 20:20-20:40 | 6 |
| 20:40-21:00 | 5 |
| 21:00-21:20 | 5 |
| 21:20-21:40 | 3 |
| 21:40-22:00 | 2 |
| 22:00-22:20 | 2 |
| 22:20-22:40 | 2 |
| 22:40-23:00 | 4 |
| 23:00-23:20 | 4 |
| 23:20-23:40 | 5 |

**XPT**

| Category | XPT |
| --- | --- |
| 00:00-00:20 | 8 |
| 00:20-00:40 | 7 |
| 00:40-01:00 | 7 |
| 01:00-01:20 | 8 |
| 01:20-01:40 | 6.5 |
| 01:40-02:00 | 6 |
| 02:00-02:20 | 5 |
| 02:20-02:40 | 4.5 |
| 02:40-03:00 | 4.5 |
| 03:00-03:20 | 4.5 |
| 03:20-03:40 | 5 |
| 03:40-04:00 | 5 |
| 04:00-04:20 | 5 |
| 04:20-04:40 | 5 |
| 04:40-05:00 | 6 |
| 05:00-05:20 | 6 |
| 05:20-05:40 | 7 |
| 05:40-06:00 | 7 |
| 06:00-06:20 | 8 |
| 06:20-06:40 | 6 |
| 06:40-07:00 | 6 |
| 07:00-07:20 | 7 |
| 07:20-07:40 | 7 |
| 07:40-08:00 | 8 |
| 08:00-08:20 | 7 |
| 08:20-08:40 | 7 |
| 08:40-09:00 | 7 |
| 09:00-09:20 | 6.5 |
| 09:20-09:40 | 6.5 |
| 09:40-10:00 | 6 |
| 10:00-10:20 | 6 |
| 10:20-10:40 | 6 |
| 10:40-11:00 | 6 |
| 11:00-11:20 | 6 |
| 11:20-11:40 | 6 |
| 11:40-12:00 | 7 |
| 12:00-12:20 | 8 |
| 12:20-12:40 | 9 |
| 12:40-13:00 | 8 |
| 13:00-13:20 | 9 |
| 13:20-13:40 | 9 |
| 13:40-14:00 | 9 |
| 14:00-14:20 | 9 |
| 14:20-14:40 | 8.5 |
| 14:40-15:00 | 8.5 |
| 15:00-15:20 | 8.5 |
| 15:20-15:40 | 8 |
| 15:40-16:00 | 8 |
| 16:00-16:20 | 7.5 |
| 16:20-16:40 | 7 |
| 16:40-17:00 | 7 |
| 17:00-17:20 | 8 |
| 17:20-17:40 | 6 |
| 17:40-18:00 | 6 |
| 18:00-18:20 | 5 |
| 18:20-18:40 | 4.5 |
| 18:40-19:00 | 4 |
| 19:00-19:20 | 4 |
| 19:20-19:40 | 3.5 |
| 19:40-20:00 | 3.5 |
| 20:00-20:20 | 3 |
| 20:20-20:40 | 2.5 |
| 20:40-21:00 | 2.5 |
| 21:00-21:20 | 2 |
| 21:20-21:40 | 1.5 |
| 21:40-22:00 | 1.5 |
| 22:00-22:20 | 1 |
| 22:20-22:40 | 1 |
| 22:40-23:00 | 2 |
| 23:00-23:20 | 2.5 |
| 23:20-23:40 | 4 |

| Category | XPT |
| --- | --- |
| 00:00 | 8.5 |
| 00:20 | 7.5 |
| 00:40 | 7.5 |
| 01:00 | 8.5 |
| 01:20 | 7.5 |
| 01:40 | 7 |
| 02:00 | 6.5 |
| 02:20 | 5.5 |
| 02:40 | 5 |
| 03:00 | 4.8 |
| 03:20 | 4.8 |
| 03:40 | 5 |
| 04:00 | 5 |
| 04:20 | 5 |
| 04:40 | 5 |
| 05:00 | 5.5 |
| 05:20 | 6 |
| 05:40 | 7 |
| 06:00 | 7.5 |
| 06:20 | 6 |
| 06:40 | 5.5 |
| 07:00 | 6.5 |
| 07:20 | 6.5 |
| 07:40 | 7 |
| 08:00 | 7 |
| 08:20 | 7.5 |
| 08:40 | 7 |
| 09:00 | 7 |
| 09:20 | 6.5 |
| 09:40 | 6.5 |
| 10:00 | 6.5 |
| 10:20 | 6.5 |
| 10:40 | 6.5 |
| 11:00 | 6.5 |
| 11:20 | 6.5 |
| 11:40 | 6.5 |
| 12:00 | 7 |
| 12:20 | 8.5 |
| 12:40 | 9 |
| 13:00 | 8.5 |
| 13:20 | 9 |
| 13:40 | 9 |
| 14:00 | 9.5 |
| 14:20 | 9 |
| 14:40 | 9 |
| 15:00 | 9 |
| 15:20 | 9 |
| 15:40 | 8.5 |
| 16:00 | 8.5 |
| 16:20 | 8 |
| 16:40 | 8 |
| 17:00 | 9.5 |
| 17:20 | 7.5 |
| 17:40 | 7 |
| 18:00 | 6.5 |
| 18:20 | 6 |
| 18:40 | 5 |
| 19:00 | 4.5 |
| 19:20 | 4.5 |
| 19:40 | 4 |
| 20:00 | 4 |
| 20:20 | 3.5 |
| 20:40 | 3 |
| 21:00 | 3 |
| 21:20 | 3 |
| 21:40 | 2.5 |
| 22:00 | 2 |
| 22:20 | 1.5 |
| 22:40 | 1.5 |
| 23:00 | 2 |
| 23:20 | 2.5 |
| 23:40 | 4 |

| Category | XPD |
| --- | --- |
| 00:00 | 3.5 |
| 00:20 | 2.5 |
| 00:40 | 2.5 |
| 01:00 | 3.5 |
| 01:20 | 2.5 |
| 01:40 | 2.5 |
| 02:00 | 2 |
| 02:20 | 2 |
| 02:40 | 1.8 |
| 03:00 | 1.8 |
| 03:20 | 1.8 |
| 03:40 | 1.8 |
| 04:00 | 1.8 |
| 04:20 | 1.8 |
| 04:40 | 1.8 |
| 05:00 | 2 |
| 05:20 | 2.5 |
| 05:40 | 3.5 |
| 06:00 | 3.5 |
| 06:20 | 3.5 |
| 06:40 | 4 |
| 07:00 | 4.5 |
| 07:20 | 4.5 |
| 07:40 | 4.5 |
| 08:00 | 4.5 |
| 08:20 | 4.5 |
| 08:40 | 4.5 |
| 09:00 | 4 |
| 09:20 | 4 |
| 09:40 | 4 |
| 10:00 | 3.8 |
| 10:20 | 3.8 |
| 10:40 | 3.8 |
| 11:00 | 3.8 |
| 11:20 | 4 |
| 11:40 | 4 |
| 12:00 | 4.5 |
| 12:20 | 5.5 |
| 12:40 | 6.5 |
| 13:00 | 6 |
| 13:20 | 6.5 |
| 13:40 | 6.5 |
| 14:00 | 6.5 |
| 14:20 | 6.5 |
| 14:40 | 6.5 |
| 15:00 | 6 |
| 15:20 | 6 |
| 15:40 | 6 |
| 16:00 | 5.8 |
| 16:20 | 5.5 |
| 16:40 | 5 |
| 17:00 | 6.5 |
| 17:20 | 5.5 |
| 17:40 | 4 |
| 18:00 | 4.5 |
| 18:20 | 3.5 |
| 18:40 | 3 |
| 19:00 | 3 |
| 19:20 | 3 |
| 19:40 | 3 |
| 20:00 | 3 |
| 20:20 | 3 |
| 20:40 | 2.5 |
| 21:00 | 2.5 |
| 21:20 | 2.5 |
| 21:40 | 2 |
| 22:00 | 2 |
| 22:20 | 1.5 |
| 22:40 | 1.5 |
| 23:00 | 2 |
| 23:20 | 2 |
| 23:40 | 2.2 |

| 5-minute period | XPD (mean volume of trades) |
| --- | --- |
| 00:00 | 3.0 |
| 00:20 | 2.8 |
| 00:40 | 2.5 |
| 01:00 | 2.8 |
| 01:20 | 2.5 |
| 01:40 | 2.4 |
| 02:00 | 2.3 |
| 02:20 | 2.1 |
| 02:40 | 2.1 |
| 03:00 | 2.0 |
| 03:20 | 2.0 |
| 03:40 | 1.9 |
| 04:00 | 1.9 |
| 04:20 | 1.9 |
| 04:40 | 2.0 |
| 05:00 | 2.1 |
| 05:20 | 2.3 |
| 05:40 | 2.8 |
| 06:00 | 3.8 |
| 06:20 | 3.8 |
| 06:40 | 3.9 |
| 07:00 | 4.2 |
| 07:20 | 4.2 |
| 07:40 | 4.1 |
| 08:00 | 4.0 |
| 08:20 | 4.0 |
| 08:40 | 4.1 |
| 09:00 | 4.0 |
| 09:20 | 3.9 |
| 09:40 | 3.9 |
| 10:00 | 3.8 |
| 10:20 | 3.7 |
| 10:40 | 3.7 |
| 11:00 | 3.7 |
| 11:20 | 3.8 |
| 11:40 | 3.9 |
| 12:00 | 4.2 |
| 12:20 | 5.0 |
| 12:40 | 5.5 |
| 13:00 | 5.5 |
| 13:20 | 6.2 |
| 13:40 | 6.0 |
| 14:00 | 6.2 |
| 14:20 | 6.0 |
| 14:40 | 6.0 |
| 15:00 | 5.9 |
| 15:20 | 5.8 |
| 15:40 | 5.7 |
| 16:00 | 5.5 |
| 16:20 | 5.2 |
| 16:40 | 5.0 |
| 17:00 | 6.0 |
| 17:20 | 5.5 |
| 17:40 | 3.8 |
| 18:00 | 3.5 |
| 18:20 | 3.0 |
| 18:40 | 2.8 |
| 19:00 | 2.6 |
| 19:20 | 2.5 |
| 19:40 | 2.4 |
| 20:00 | 2.4 |
| 20:20 | 2.0 |
| 20:40 | 1.9 |
| 21:00 | 1.9 |
| 21:20 | 1.8 |
| 21:40 | 1.3 |
| 22:00 | 1.2 |
| 22:20 | 1.1 |
| 22:40 | 1.3 |
| 23:00 | 1.6 |
| 23:20 | 1.7 |
| 23:40 | 1.9 |

**Fig 5. The mean volume of trades for each 5-minute period over the full sample of each precious metal.** [https://doi.org/10.1371/journal.pone.0174232.g005](https://doi.org/10.1371/journal.pone.0174232.g005)

The intraday mean BAS at the 5-minute intervals for each precious metal are reported in
Fig 6 and show that the mean BAS for gold and silver is fairly constant throughout the day.
Both markets exhibit a small increase in the BAS around 10 PM GMT, possibly due to the
daily hour closure of the markets from 9 PM GMT to 10 PM GMT. Platinum also shows a
fairly constant BAS throughout the day with some very small fluctuations around 10 PM
GMT. Palladium however exhibits some periodicity, with the BAS largest from midnight
GMT to 6 AM GMT, which then falls and stays fairly constant until the end of the day, which
could be the results of the opening (and anticipation) of European markets. Fig 7 reports the
intraday volatility through the three volatility measures previously discussed and shows that
the volatility for gold is fairly constant up to 12 PM GMT and then increases slightly until 2
PM GMT. After this point, volatility decreases and levels off to the end of the day. Silver’s volatility is fairly constant throughout the day, with again a small increase around 12 PM GMT
which continues until 2 PM GMT. The GK and RS volatility for platinum and palladium are
very similar and fairly constant throughout the day, while the SQ measure of volatility is little
more variable with a few sharp jumps at various points of the day although there is no clear
periodicity.

### Dynamic intraday stylized facts

As we have seen in Tables 2 and 3, the behaviour of the four precious metals has changed substantially over time and so their intraday behaviour may also change, depending on the sub
period examined. Therefore we also study the dynamic intraday stylized facts in three subsamples to examine whether the behaviour of the precious metals markets change depending on
the time period examined.

Fig 8 shows the intraday volume of trades over the three subsamples and shows that each
subsample experiences daily periodicity, albeit at different magnitudes. For instance, the

* * *

**XAU**

| 5-minute period | Mean BAS |
| --- | --- |
| 00:00 | 0.0013 |
| 00:20 | 0.0013 |
| 00:40 | 0.0013 |
| 01:00 | 0.0013 |
| 01:20 | 0.0013 |
| 01:40 | 0.0013 |
| 02:00 | 0.0013 |
| 02:20 | 0.0013 |
| 02:40 | 0.0013 |
| 03:00 | 0.0013 |
| 03:20 | 0.0013 |
| 03:40 | 0.0013 |
| 04:00 | 0.0013 |
| 04:20 | 0.0013 |
| 04:40 | 0.0013 |
| 05:00 | 0.0013 |
| 05:20 | 0.0013 |
| 05:40 | 0.0013 |
| 06:00 | 0.0013 |
| 06:20 | 0.0013 |
| 06:40 | 0.0013 |
| 07:00 | 0.0013 |
| 07:20 | 0.0013 |
| 07:40 | 0.0013 |
| 08:00 | 0.0013 |
| 08:20 | 0.0013 |
| 08:40 | 0.0013 |
| 09:00 | 0.0013 |
| 09:20 | 0.0013 |
| 09:40 | 0.0013 |
| 10:00 | 0.0013 |
| 10:20 | 0.0013 |
| 10:40 | 0.0013 |
| 11:00 | 0.0015 |
| 11:20 | 0.0015 |
| 11:40 | 0.0015 |
| 12:00 | 0.0015 |
| 12:20 | 0.0015 |
| 12:40 | 0.0015 |
| 13:00 | 0.0015 |
| 13:20 | 0.0015 |
| 13:40 | 0.0015 |
| 14:00 | 0.0015 |
| 14:20 | 0.0015 |
| 14:40 | 0.0015 |
| 15:00 | 0.0015 |
| 15:20 | 0.0015 |
| 15:40 | 0.0015 |
| 16:00 | 0.0015 |
| 16:20 | 0.0015 |
| 16:40 | 0.0015 |
| 17:00 | 0.0015 |
| 17:20 | 0.0015 |
| 17:40 | 0.0015 |
| 18:00 | 0.0015 |
| 18:20 | 0.0015 |
| 18:40 | 0.0015 |
| 19:00 | 0.0015 |
| 19:20 | 0.0015 |
| 19:40 | 0.0015 |
| 20:00 | 0.0015 |
| 20:20 | 0.0015 |
| 20:40 | 0.0015 |
| 21:00 | 0.0015 |
| 21:20 | 0.0015 |
| 21:40 | 0.0015 |
| 22:00 | 0.0015 |
| 22:20 | 0.0016 |
| 22:40 | 0.0016 |
| 23:00 | 0.0016 |
| 23:20 | 0.0015 |
| 23:40 | 0.0015 |

**XAG**

| 5-minute period | Mean BAS |
| --- | --- |
| 00:00 | 0.0043 |
| 00:20 | 0.0043 |
| 00:40 | 0.0043 |
| 01:00 | 0.0042 |
| 01:20 | 0.0042 |
| 01:40 | 0.0042 |
| 02:00 | 0.0042 |
| 02:20 | 0.0042 |
| 02:40 | 0.0042 |
| 03:00 | 0.0042 |
| 03:20 | 0.0042 |
| 03:40 | 0.0042 |
| 04:00 | 0.0042 |
| 04:20 | 0.0042 |
| 04:40 | 0.0042 |
| 05:00 | 0.0042 |
| 05:20 | 0.0042 |
| 05:40 | 0.0042 |
| 06:00 | 0.0042 |
| 06:20 | 0.0042 |
| 06:40 | 0.0042 |
| 07:00 | 0.0037 |
| 07:20 | 0.0037 |
| 07:40 | 0.0037 |
| 08:00 | 0.0037 |
| 08:20 | 0.0037 |
| 08:40 | 0.0037 |
| 09:00 | 0.0037 |
| 09:20 | 0.0037 |
| 09:40 | 0.0037 |
| 10:00 | 0.0037 |
| 10:20 | 0.0037 |
| 10:40 | 0.0037 |
| 11:00 | 0.0037 |
| 11:20 | 0.0037 |
| 11:40 | 0.0037 |
| 12:00 | 0.0037 |
| 12:20 | 0.0042 |
| 12:40 | 0.0042 |
| 13:00 | 0.0042 |
| 13:20 | 0.0042 |
| 13:40 | 0.0042 |
| 14:00 | 0.0042 |
| 14:20 | 0.0042 |
| 14:40 | 0.0042 |
| 15:00 | 0.0042 |
| 15:20 | 0.0042 |
| 15:40 | 0.0042 |
| 16:00 | 0.0042 |
| 16:20 | 0.0042 |
| 16:40 | 0.0042 |
| 17:00 | 0.0042 |
| 17:20 | 0.0042 |
| 17:40 | 0.0042 |
| 18:00 | 0.0042 |
| 18:20 | 0.0042 |
| 18:40 | 0.0042 |
| 19:00 | 0.0042 |
| 19:20 | 0.0042 |
| 19:40 | 0.0042 |
| 20:00 | 0.0042 |
| 20:20 | 0.0042 |
| 20:40 | 0.0042 |
| 21:00 | 0.0042 |
| 21:20 | 0.0042 |
| 21:40 | 0.0042 |
| 22:00 | 0.0042 |
| 22:20 | 0.0043 |
| 22:40 | 0.0043 |
| 23:00 | 0.0043 |
| 23:20 | 0.0042 |
| 23:40 | 0.0042 |

**XPT**

| 5-minute period | Mean BAS |
| --- | --- |
| 00:00 | 0.0065 |
| 00:20 | 0.0068 |
| 00:40 | 0.0068 |
| 01:00 | 0.0067 |
| 01:20 | 0.0067 |
| 01:40 | 0.0067 |
| 02:00 | 0.0067 |
| 02:20 | 0.0067 |
| 02:40 | 0.0067 |
| 03:00 | 0.0067 |
| 03:20 | 0.0067 |
| 03:40 | 0.0067 |
| 04:00 | 0.0067 |
| 04:20 | 0.0067 |
| 04:40 | 0.0067 |
| 05:00 | 0.0067 |
| 05:20 | 0.0067 |
| 05:40 | 0.0067 |
| 06:00 | 0.0067 |
| 06:20 | 0.0067 |
| 06:40 | 0.0067 |
| 07:00 | 0.0068 |
| 07:20 | 0.0068 |
| 07:40 | 0.0068 |
| 08:00 | 0.0068 |
| 08:20 | 0.0068 |
| 08:40 | 0.0068 |
| 09:00 | 0.0068 |
| 09:20 | 0.0068 |
| 09:40 | 0.0068 |
| 10:00 | 0.0068 |
| 10:20 | 0.0068 |
| 10:40 | 0.0068 |
| 11:00 | 0.0068 |
| 11:20 | 0.0068 |
| 11:40 | 0.0068 |
| 12:00 | 0.0068 |
| 12:20 | 0.0068 |
| 12:40 | 0.0068 |
| 13:00 | 0.0068 |
| 13:20 | 0.0068 |
| 13:40 | 0.0068 |
| 14:00 | 0.0068 |
| 14:20 | 0.0068 |
| 14:40 | 0.0068 |
| 15:00 | 0.0068 |
| 15:20 | 0.0068 |
| 15:40 | 0.0068 |
| 16:00 | 0.0068 |
| 16:20 | 0.0068 |
| 16:40 | 0.0068 |
| 17:00 | 0.0068 |
| 17:20 | 0.0068 |
| 17:40 | 0.0068 |
| 18:00 | 0.0068 |
| 18:20 | 0.0068 |
| 18:40 | 0.0068 |
| 19:00 | 0.0068 |
| 19:20 | 0.0068 |
| 19:40 | 0.0068 |
| 20:00 | 0.0068 |
| 20:20 | 0.0068 |
| 20:40 | 0.0068 |
| 21:00 | 0.0068 |
| 21:20 | 0.0068 |
| 21:40 | 0.0068 |
| 22:00 | 0.0067 |
| 22:20 | 0.0067 |
| 22:40 | 0.0071 |
| 23:00 | 0.0067 |
| 23:20 | 0.0067 |
| 23:40 | 0.0071 |

**XPD**

| 5-minute period | Mean BAS |
| --- | --- |
| 00:00 | 0.0175 |
| 00:20 | 0.0185 |
| 00:40 | 0.0185 |
| 01:00 | 0.0185 |
| 01:20 | 0.0185 |
| 01:40 | 0.0185 |
| 02:00 | 0.0185 |
| 02:20 | 0.0185 |
| 02:40 | 0.0185 |
| 03:00 | 0.0185 |
| 03:20 | 0.0185 |
| 03:40 | 0.0185 |
| 04:00 | 0.0185 |
| 04:20 | 0.0185 |
| 04:40 | 0.0185 |
| 05:00 | 0.0185 |
| 05:20 | 0.0185 |
| 05:40 | 0.0185 |
| 06:00 | 0.0185 |
| 06:20 | 0.0185 |

**Fig 6. The mean BAS for each 5-minute period over the full sample of each precious metal.**

[https://doi.org/10.1371/journal.pone.0174232.g006](https://doi.org/10.1371/journal.pone.0174232.g006)

| Category | SQ | GK | RS |
| --- | --- | --- | --- |
| 00:00 | 0.018 | 0.004 | 0.004 |
| 00:20 | 0.008 | 0.005 | 0.005 |
| 00:40 | 0.006 | 0.005 | 0.005 |
| 01:00 | 0.006 | 0.005 | 0.005 |
| 01:20 | 0.005 | 0.005 | 0.005 |
| 01:40 | 0.005 | 0.005 | 0.005 |
| 02:00 | 0.004 | 0.004 | 0.004 |
| 02:20 | 0.004 | 0.004 | 0.004 |
| 02:40 | 0.004 | 0.004 | 0.004 |
| 03:00 | 0.004 | 0.004 | 0.004 |
| 03:20 | 0.004 | 0.004 | 0.004 |
| 03:40 | 0.004 | 0.004 | 0.004 |
| 04:00 | 0.004 | 0.004 | 0.004 |
| 04:20 | 0.004 | 0.004 | 0.004 |
| 04:40 | 0.004 | 0.004 | 0.004 |
| 05:00 | 0.004 | 0.004 | 0.004 |
| 05:20 | 0.004 | 0.004 | 0.004 |
| 05:40 | 0.004 | 0.004 | 0.004 |
| 06:00 | 0.005 | 0.004 | 0.004 |
| 06:20 | 0.005 | 0.004 | 0.004 |
| 06:40 | 0.005 | 0.004 | 0.004 |
| 07:00 | 0.006 | 0.004 | 0.004 |
| 07:20 | 0.006 | 0.004 | 0.004 |
| 07:40 | 0.006 | 0.004 | 0.004 |
| 08:00 | 0.006 | 0.004 | 0.004 |
| 08:20 | 0.006 | 0.004 | 0.004 |
| 08:40 | 0.006 | 0.004 | 0.004 |
| 09:00 | 0.006 | 0.004 | 0.004 |
| 09:20 | 0.006 | 0.004 | 0.004 |
| 09:40 | 0.006 | 0.004 | 0.004 |
| 10:00 | 0.006 | 0.004 | 0.004 |
| 10:20 | 0.006 | 0.004 | 0.004 |
| 10:40 | 0.006 | 0.004 | 0.004 |
| 11:00 | 0.006 | 0.004 | 0.004 |
| 11:20 | 0.006 | 0.004 | 0.004 |
| 11:40 | 0.006 | 0.004 | 0.004 |
| 12:00 | 0.006 | 0.004 | 0.004 |
| 12:20 | 0.006 | 0.004 | 0.004 |
| 12:40 | 0.010 | 0.005 | 0.005 |
| 13:00 | 0.011 | 0.005 | 0.005 |
| 13:20 | 0.012 | 0.005 | 0.005 |
| 13:40 | 0.014 | 0.005 | 0.005 |
| 14:00 | 0.014 | 0.005 | 0.005 |
| 14:20 | 0.013 | 0.005 | 0.005 |
| 14:40 | 0.013 | 0.005 | 0.005 |
| 15:00 | 0.013 | 0.005 | 0.005 |
| 15:20 | 0.012 | 0.005 | 0.005 |
| 15:40 | 0.012 | 0.005 | 0.005 |
| 16:00 | 0.011 | 0.005 | 0.005 |
| 16:20 | 0.011 | 0.005 | 0.005 |
| 16:40 | 0.010 | 0.005 | 0.005 |
| 17:00 | 0.010 | 0.005 | 0.005 |
| 17:20 | 0.010 | 0.005 | 0.005 |
| 17:40 | 0.008 | 0.005 | 0.005 |
| 18:00 | 0.007 | 0.005 | 0.005 |
| 18:20 | 0.007 | 0.005 | 0.005 |
| 18:40 | 0.007 | 0.005 | 0.005 |
| 19:00 | 0.006 | 0.005 | 0.005 |
| 19:20 | 0.006 | 0.005 | 0.005 |
| 19:40 | 0.006 | 0.005 | 0.005 |
| 20:00 | 0.005 | 0.005 | 0.005 |
| 20:20 | 0.005 | 0.005 | 0.005 |
| 20:40 | 0.005 | 0.005 | 0.005 |
| 21:00 | 0.005 | 0.005 | 0.005 |
| 21:20 | 0.005 | 0.005 | 0.005 |
| 21:40 | 0.005 | 0.005 | 0.005 |
| 22:00 | 0.005 | 0.005 | 0.005 |
| 22:20 | 0.005 | 0.005 | 0.005 |
| 22:40 | 0.005 | 0.005 | 0.005 |
| 23:00 | 0.005 | 0.005 | 0.005 |
| 23:20 | 0.005 | 0.005 | 0.005 |
| 23:40 | 0.005 | 0.005 | 0.005 |

| Category | SQ | GK | RS |
| --- | --- | --- | --- |
| 00:00 | 0.035 | 0.008 | 0.008 |
| 00:20 | 0.030 | 0.008 | 0.008 |
| 00:40 | 0.028 | 0.008 | 0.008 |
| 01:00 | 0.025 | 0.008 | 0.008 |
| 01:20 | 0.020 | 0.008 | 0.008 |
| 01:40 | 0.020 | 0.008 | 0.008 |
| 02:00 | 0.018 | 0.008 | 0.008 |
| 02:20 | 0.015 | 0.008 | 0.008 |
| 02:40 | 0.015 | 0.008 | 0.008 |
| 03:00 | 0.015 | 0.008 | 0.008 |
| 03:20 | 0.015 | 0.008 | 0.008 |
| 03:40 | 0.015 | 0.008 | 0.008 |
| 04:00 | 0.015 | 0.008 | 0.008 |
| 04:20 | 0.015 | 0.008 | 0.008 |
| 04:40 | 0.015 | 0.008 | 0.008 |
| 05:00 | 0.015 | 0.008 | 0.008 |
| 05:20 | 0.020 | 0.008 | 0.008 |
| 05:40 | 0.020 | 0.008 | 0.008 |
| 06:00 | 0.022 | 0.008 | 0.008 |
| 06:20 | 0.022 | 0.008 | 0.008 |
| 06:40 | 0.022 | 0.008 | 0.008 |
| 07:00 | 0.025 | 0.008 | 0.008 |
| 07:20 | 0.025 | 0.008 | 0.008 |
| 07:40 | 0.025 | 0.008 | 0.008 |
| 08:00 | 0.025 | 0.008 | 0.008 |
| 08:20 | 0.025 | 0.008 | 0.008 |
| 08:40 | 0.025 | 0.008 | 0.008 |
| 09:00 | 0.025 | 0.008 | 0.008 |
| 09:20 | 0.025 | 0.008 | 0.008 |
| 09:40 | 0.025 | 0.008 | 0.008 |
| 10:00 | 0.025 | 0.008 | 0.008 |
| 10:20 | 0.025 | 0.008 | 0.008 |
| 10:40 | 0.025 | 0.008 | 0.008 |
| 11:00 | 0.025 | 0.008 | 0.008 |
| 11:20 | 0.025 | 0.008 | 0.008 |
| 11:40 | 0.025 | 0.008 | 0.008 |
| 12:00 | 0.025 | 0.008 | 0.008 |
| 12:20 | 0.025 | 0.008 | 0.008 |
| 12:40 | 0.030 | 0.008 | 0.008 |
| 13:00 | 0.040 | 0.008 | 0.008 |
| 13:20 | 0.045 | 0.008 | 0.008 |
| 13:40 | 0.050 | 0.008 | 0.008 |
| 14:00 | 0.050 | 0.008 | 0.008 |
| 14:20 | 0.050 | 0.008 | 0.008 |
| 14:40 | 0.050 | 0.008 | 0.008 |
| 15:00 | 0.045 | 0.008 | 0.008 |
| 15:20 | 0.045 | 0.008 | 0.008 |
| 15:40 | 0.045 | 0.008 | 0.008 |
| 16:00 | 0.045 | 0.008 | 0.008 |
| 16:20 | 0.040 | 0.008 | 0.008 |
| 16:40 | 0.040 | 0.008 | 0.008 |
| 17:00 | 0.040 | 0.008 | 0.008 |
| 17:20 | 0.040 | 0.008 | 0.008 |
| 17:40 | 0.035 | 0.008 | 0.008 |
| 18:00 | 0.030 | 0.008 | 0.008 |
| 18:20 | 0.030 | 0.008 | 0.008 |
| 18:40 | 0.025 | 0.008 | 0.008 |
| 19:00 | 0.020 | 0.008 | 0.008 |
| 19:20 | 0.020 | 0.008 | 0.008 |
| 19:40 | 0.020 | 0.008 | 0.008 |
| 20:00 | 0.015 | 0.008 | 0.008 |
| 20:20 | 0.015 | 0.008 | 0.008 |

**Fig 7. The mean volatility for each 5-minute period over the full sample of each precious metal employing**
**the three different measures of volatility.**

[https://doi.org/10.1371/journal.pone.0174232.g007](https://doi.org/10.1371/journal.pone.0174232.g007)

* * *

**XAU**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00:00 | 10 | 12 | 38 |
| 00:20 | 10 | 12 | 36 |
| 00:40 | 10 | 12 | 37 |
| 01:00 | 10 | 12 | 40 |
| 01:20 | 10 | 12 | 40 |
| 01:40 | 10 | 12 | 40 |
| 02:00 | 10 | 12 | 38 |
| 02:20 | 10 | 12 | 36 |
| 02:40 | 10 | 12 | 38 |
| 03:00 | 10 | 12 | 38 |
| 03:20 | 10 | 12 | 36 |
| 03:40 | 10 | 12 | 35 |
| 04:00 | 10 | 12 | 35 |
| 04:20 | 10 | 12 | 38 |
| 04:40 | 10 | 12 | 38 |
| 05:00 | 10 | 12 | 37 |
| 05:20 | 10 | 12 | 38 |
| 05:40 | 10 | 12 | 42 |
| 06:00 | 10 | 12 | 50 |
| 06:20 | 10 | 12 | 52 |
| 06:40 | 10 | 12 | 55 |
| 07:00 | 10 | 12 | 60 |
| 07:20 | 10 | 12 | 60 |
| 07:40 | 10 | 12 | 60 |
| 08:00 | 10 | 12 | 60 |
| 08:20 | 10 | 12 | 60 |
| 08:40 | 10 | 12 | 60 |
| 09:00 | 10 | 12 | 60 |
| 09:20 | 10 | 12 | 60 |
| 09:40 | 10 | 12 | 60 |
| 10:00 | 10 | 12 | 58 |
| 10:20 | 10 | 12 | 55 |
| 10:40 | 10 | 12 | 55 |
| 11:00 | 10 | 12 | 56 |
| 11:20 | 10 | 12 | 56 |
| 11:40 | 10 | 12 | 56 |
| 12:00 | 10 | 12 | 58 |
| 12:20 | 10 | 12 | 62 |
| 12:40 | 10 | 12 | 62 |
| 13:00 | 10 | 12 | 62 |
| 13:20 | 10 | 12 | 62 |
| 13:40 | 10 | 12 | 64 |
| 14:00 | 10 | 12 | 64 |
| 14:20 | 10 | 12 | 64 |
| 14:40 | 10 | 12 | 63 |
| 15:00 | 10 | 12 | 62 |
| 15:20 | 10 | 12 | 61 |
| 15:40 | 10 | 12 | 60 |
| 16:00 | 10 | 12 | 58 |
| 16:20 | 10 | 12 | 57 |
| 16:40 | 10 | 12 | 56 |
| 17:00 | 10 | 12 | 55 |
| 17:20 | 10 | 12 | 50 |
| 17:40 | 10 | 12 | 50 |
| 18:00 | 10 | 12 | 48 |
| 18:20 | 10 | 12 | 48 |
| 18:40 | 10 | 12 | 46 |
| 19:00 | 10 | 12 | 46 |
| 19:20 | 10 | 12 | 45 |
| 19:40 | 10 | 12 | 44 |
| 20:00 | 10 | 12 | 44 |
| 20:20 | 10 | 12 | 32 |
| 20:40 | 10 | 12 | 30 |
| 21:00 | 10 | 12 | 30 |
| 21:20 | 10 | 12 | 20 |
| 21:40 | 10 | 12 | 15 |
| 22:00 | 10 | 12 | 15 |
| 22:20 | 10 | 12 | 15 |
| 22:40 | 10 | 12 | 25 |
| 23:00 | 10 | 12 | 28 |
| 23:20 | 10 | 12 | 28 |
| 23:40 | 10 | 12 | 30 |

**XAG**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00:00 | 5 | 6 | 22 |
| 00:20 | 5 | 6 | 22 |
| 00:40 | 5 | 6 | 22 |
| 01:00 | 5 | 6 | 35 |
| 01:20 | 5 | 6 | 30 |
| 01:40 | 5 | 6 | 28 |
| 02:00 | 5 | 6 | 27 |
| 02:20 | 5 | 6 | 25 |
| 02:40 | 5 | 6 | 22 |
| 03:00 | 5 | 6 | 25 |
| 03:20 | 5 | 6 | 25 |
| 03:40 | 5 | 6 | 25 |
| 04:00 | 5 | 6 | 23 |
| 04:20 | 5 | 6 | 22 |
| 04:40 | 5 | 6 | 22 |
| 05:00 | 5 | 6 | 25 |
| 05:20 | 5 | 6 | 30 |
| 05:40 | 5 | 6 | 35 |
| 06:00 | 5 | 6 | 32 |
| 06:20 | 5 | 6 | 35 |
| 06:40 | 5 | 6 | 38 |
| 07:00 | 5 | 6 | 40 |
| 07:20 | 5 | 6 | 40 |
| 07:40 | 5 | 6 | 40 |
| 08:00 | 5 | 6 | 38 |
| 08:20 | 5 | 6 | 40 |
| 08:40 | 5 | 6 | 38 |
| 09:00 | 5 | 6 | 38 |
| 09:20 | 5 | 6 | 38 |
| 09:40 | 5 | 6 | 38 |
| 10:00 | 5 | 6 | 38 |
| 10:20 | 5 | 6 | 35 |
| 10:40 | 5 | 6 | 35 |
| 11:00 | 5 | 6 | 35 |
| 11:20 | 5 | 6 | 38 |
| 11:40 | 5 | 6 | 38 |
| 12:00 | 5 | 6 | 40 |
| 12:20 | 5 | 6 | 45 |
| 12:40 | 5 | 6 | 45 |
| 13:00 | 5 | 6 | 45 |
| 13:20 | 5 | 6 | 45 |
| 13:40 | 5 | 6 | 45 |
| 14:00 | 5 | 6 | 45 |
| 14:20 | 5 | 6 | 45 |
| 14:40 | 5 | 6 | 45 |
| 15:00 | 5 | 6 | 45 |
| 15:20 | 5 | 6 | 45 |
| 15:40 | 5 | 6 | 42 |
| 16:00 | 5 | 6 | 40 |
| 16:20 | 5 | 6 | 38 |
| 16:40 | 5 | 6 | 38 |
| 17:00 | 5 | 6 | 38 |
| 17:20 | 5 | 6 | 38 |
| 17:40 | 5 | 6 | 35 |
| 18:00 | 5 | 6 | 35 |
| 18:20 | 5 | 6 | 35 |
| 18:40 | 5 | 6 | 30 |
| 19:00 | 5 | 6 | 30 |
| 19:20 | 5 | 6 | 30 |
| 19:40 | 5 | 6 | 28 |
| 20:00 | 5 | 6 | 28 |
| 20:20 | 5 | 6 | 25 |
| 20:40 | 5 | 6 | 22 |
| 21:00 | 5 | 6 | 22 |
| 21:20 | 5 | 6 | 22 |
| 21:40 | 5 | 6 | 15 |
| 22:00 | 5 | 6 | 12 |
| 22:20 | 5 | 6 | 12 |
| 22:40 | 5 | 6 | 12 |
| 23:00 | 5 | 6 | 15 |
| 23:20 | 5 | 6 | 15 |
| 23:40 | 5 | 6 | 15 |

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 0:00-0:20 | 0 | 3 | 20 |
| 0:20-0:40 | 0 | 3 | 20 |
| 0:40-1:00 | 0 | 3 | 20 |
| 1:00-1:20 | 0 | 3 | 35 |
| 1:20-1:40 | 0 | 3 | 28 |
| 1:40-2:00 | 0 | 3 | 27 |
| 2:00-2:20 | 0 | 3 | 25 |
| 2:20-2:40 | 0 | 3 | 20 |
| 2:40-3:00 | 0 | 3 | 23 |
| 3:00-3:20 | 0 | 3 | 23 |
| 3:20-3:40 | 0 | 3 | 23 |
| 3:40-4:00 | 0 | 3 | 20 |
| 4:00-4:20 | 0 | 3 | 20 |
| 4:20-4:40 | 0 | 3 | 20 |
| 4:40-5:00 | 0 | 3 | 28 |
| 5:00-5:20 | 0 | 3 | 23 |
| 5:20-5:40 | 0 | 3 | 23 |
| 5:40-6:00 | 0 | 3 | 35 |
| 6:00-6:20 | 0 | 3 | 28 |
| 6:20-6:40 | 0 | 3 | 32 |
| 6:40-7:00 | 0 | 3 | 32 |
| 7:00-7:20 | 0 | 3 | 35 |
| 7:20-7:40 | 0 | 3 | 35 |
| 7:40-8:00 | 0 | 3 | 35 |
| 8:00-8:20 | 0 | 3 | 32 |
| 8:20-8:40 | 0 | 3 | 32 |
| 8:40-9:00 | 0 | 3 | 32 |
| 9:00-9:20 | 0 | 3 | 32 |
| 9:20-9:40 | 0 | 3 | 32 |
| 9:40-10:00 | 0 | 3 | 30 |
| 10:00-10:20 | 0 | 3 | 30 |
| 10:20-10:40 | 0 | 3 | 30 |
| 10:40-11:00 | 0 | 3 | 28 |
| 11:00-11:20 | 0 | 3 | 28 |
| 11:20-11:40 | 0 | 3 | 30 |
| 11:40-12:00 | 0 | 3 | 32 |
| 12:00-12:20 | 0 | 3 | 35 |
| 12:20-12:40 | 0 | 5 | 40 |
| 12:40-13:00 | 0 | 5 | 40 |
| 13:00-13:20 | 0 | 5 | 45 |
| 13:20-13:40 | 0 | 5 | 40 |
| 13:40-14:00 | 0 | 5 | 45 |
| 14:00-14:20 | 0 | 5 | 45 |
| 14:20-14:40 | 0 | 5 | 45 |
| 14:40-15:00 | 0 | 5 | 45 |
| 15:00-15:20 | 0 | 5 | 45 |
| 15:20-15:40 | 0 | 5 | 40 |
| 15:40-16:00 | 0 | 5 | 40 |
| 16:00-16:20 | 0 | 5 | 35 |
| 16:20-16:40 | 0 | 5 | 35 |
| 16:40-17:00 | 0 | 5 | 35 |
| 17:00-17:20 | 0 | 5 | 35 |
| 17:20-17:40 | 0 | 5 | 30 |
| 17:40-18:00 | 0 | 5 | 30 |
| 18:00-18:20 | 0 | 5 | 30 |
| 18:20-18:40 | 0 | 5 | 30 |
| 18:40-19:00 | 0 | 3 | 28 |
| 19:00-19:20 | 0 | 3 | 28 |
| 19:20-19:40 | 0 | 3 | 28 |
| 19:40-20:00 | 0 | 3 | 25 |
| 20:00-20:20 | 0 | 3 | 25 |
| 20:20-20:40 | 0 | 3 | 20 |
| 20:40-21:00 | 0 | 3 | 20 |
| 21:00-21:20 | 0 | 3 | 20 |
| 21:20-21:40 | 0 | 3 | 15 |
| 21:40-22:00 | 0 | 3 | 15 |
| 22:00-22:20 | 0 | 3 | 15 |
| 22:20-22:40 | 0 | 3 | 15 |
| 22:40-23:00 | 0 | 3 | 15 |
| 23:00-23:20 | 0 | 3 | 15 |
| 23:20-23:40 | 0 | 3 | 15 |

**XPT**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 0:00-0:20 | 0 | 17 | 22 |
| 0:20-0:40 | 0 | 15 | 18 |
| 0:40-1:00 | 0 | 15 | 18 |
| 1:00-1:20 | 0 | 13 | 18 |
| 1:20-1:40 | 0 | 13 | 17 |
| 1:40-2:00 | 0 | 13 | 16 |
| 2:00-2:20 | 0 | 12 | 15 |
| 2:20-2:40 | 0 | 12 | 15 |
| 2:40-3:00 | 0 | 12 | 15 |
| 3:00-3:20 | 0 | 12 | 15 |
| 3:20-3:40 | 0 | 12 | 15 |
| 3:40-4:00 | 0 | 12 | 15 |
| 4:00-4:20 | 0 | 12 | 15 |
| 4:20-4:40 | 0 | 12 | 15 |
| 4:40-5:00 | 0 | 12 | 15 |
| 5:00-5:20 | 0 | 12 | 15 |
| 5:20-5:40 | 0 | 12 | 15 |
| 5:40-6:00 | 0 | 12 | 15 |
| 6:00-6:20 | 0 | 12 | 15 |
| 6:20-6:40 | 0 | 12 | 15 |
| 6:40-7:00 | 0 | 12 | 15 |
| 7:00-7:20 | 0 | 12 | 15 |
| 7:20-7:40 | 0 | 12 | 15 |
| 7:40-8:00 | 0 | 12 | 15 |
| 8:00-8:20 | 0 | 12 | 15 |
| 8:20-8:40 | 0 | 12 | 15 |
| 8:40-9:00 | 0 | 12 | 15 |
| 9:00-9:20 | 0 | 12 | 15 |
| 9:20-9:40 | 0 | 12 | 15 |
| 9:40-10:00 | 0 | 12 | 15 |
| 10:00-10:20 | 0 | 12 | 15 |
| 10:20-10:40 | 0 | 12 | 15 |
| 10:40-11:00 | 0 | 12 | 15 |
| 11:00-11:20 | 0 | 12 | 15 |
| 11:20-11:40 | 0 | 12 | 15 |
| 11:40-12:00 | 0 | 12 | 15 |
| 12:00-12:20 | 0 | 12 | 15 |
| 12:20-12:40 | 0 | 12 | 15 |
| 12:40-13:00 | 0 | 12 | 15 |
| 13:00-13:20 | 0 | 12 | 15 |
| 13:20-13:40 | 0 | 12 | 15 |

| 0 | 10:00 | 20:20 | 30:40 | 40:60 | 50:80 | 60:100 | 70:140 | 80:180 | 90:220 | 100:260 | 110:300 | 120:340 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XPT |  |  |  |  |  |  |  |  |  |  |  |  |
| 0 | 10:00 | 20:20 | 30:40 | 40:60 | 50:80 | 60:100 | 70:140 | 80:180 | 90:220 | 100:260 | 110:300 | 120:340 |
| XPT |  |  |  |  |  |  |  |  |  |  |  |  |
| 0 | 10:00 | 20:20 | 30:40 | 40:60 | 50:80 | 60:100 | 70:140 | 80:180 | 90:220 | 100:260 | 110:300 | 120:340 |

| Category | Mean volume of trades (5-minute period) |
| --- | --- |
| 0-5:00 | 0.5 |
| 5-10:00 | 0.5 |
| 10-15:00 | 0.5 |
| 15-20:00 | 0.5 |
| 20-25:00 | 0.5 |
| 25-30:00 | 0.5 |
| 30-35:00 | 0.5 |
| 35-40:00 | 0.5 |
| 40-45:00 | 0.5 |
| 45-50:00 | 0.5 |
| 50-55:00 | 0.5 |
| 55-60:00 | 0.5 |
| 60-65:00 | 0.5 |
| 65-70:00 | 0.5 |
| 70-75:00 | 0.5 |
| 75-80:00 | 0.5 |
| 80-85:00 | 0.5 |
| 85-90:00 | 0.5 |
| 90-95:00 | 0.5 |
| 95-100:00 | 0.5 |
| 100-105:00 | 0.5 |
| 105-110:00 | 0.5 |
| 110-115:00 | 0.5 |
| 115-120:00 | 0.5 |
| 120-125:00 | 0.5 |
| 125-130:00 | 0.5 |
| 130-135:00 | 0.5 |
| 135-140:00 | 0.5 |
| 140-145:00 | 0.5 |
| 145-150:00 | 0.5 |
| 150-155:00 | 0.5 |
| 155-160:00 | 0.5 |
| 160-165:00 | 0.5 |
| 165-170:00 | 0.5 |
| 170-175:00 | 0.5 |
| 175-180:00 | 0.5 |
| 180-185:00 | 0.5 |
| 185-190:00 | 0.5 |
| 190-195:00 | 0.5 |
| 195-200:00 | 0.5 |
| 200-205:00 | 0.5 |
| 205-210:00 | 0.5 |
| 210-215:00 | 0.5 |
| 215-220:00 | 0.5 |
| 220-225:00 | 0.5 |
| 225-230:00 | 0.5 |
| 230-235:00 | 0.5 |
| 235-240:00 | 0.5 |
| 240-245:00 | 0.5 |
| 245-250:00 | 0.5 |
| 250-255:00 | 0.5 |
| 255-260:00 | 0.5 |
| 260-265:00 | 0.5 |
| 265-270:00 | 0.5 |
| 270-275:00 | 0.5 |
| 275-280:00 | 0.5 |
| 280-285:00 | 0.5 |
| 285-290:00 | 0.5 |
| 290-295:00 | 0.5 |
| 295-300:00 | 0.5 |
| 300-305:00 | 0.5 |
| 305-310:00 | 0.5 |
| 310-315:00 | 0.5 |
| 315-320:00 | 0.5 |
| 320-325:00 | 0.5 |
| 325-330:00 | 0.5 |
| 330-335:00 | 0.5 |
| 335-340:00 | 0.5 |

| Category | 2000-2005 (mean volume of trades, 5-minute period) | 2005-2010 (mean volume of trades, 5-minute period) | 2010-2015 (mean volume of trades, 5-minute period) |
| --- | --- | --- | --- |
| 0-5:00 | 0.5 | 0.5 | 8 |
| 5-10:00 | 0.5 | 0.5 | 7 |
| 10-15:00 | 0.5 | 0.5 | 8 |
| 15-20:00 | 0.5 | 0.5 | 7 |
| 20-25:00 | 0.5 | 0.5 | 6 |
| 25-30:00 | 0.5 | 0.5 | 6 |
| 30-35:00 | 0.5 | 0.5 | 6 |
| 35-40:00 | 0.5 | 0.5 | 6 |
| 40-45:00 | 0.5 | 0.5 | 6 |
| 45-50:00 | 0.5 | 0.5 | 6 |
| 50-55:00 | 0.5 | 0.5 | 6 |
| 55-60:00 | 0.5 | 0.5 | 6 |
| 60-65:00 | 0.5 | 0.5 | 6 |
| 65-70:00 | 0.5 | 0.5 | 6 |
| 70-75:00 | 0.5 | 0.5 | 6 |
| 75-80:00 | 0.5 | 0.5 | 6 |
| 80-85:00 | 0.5 | 0.5 | 6 |
| 85-90:00 | 0.5 | 0.5 | 6 |
| 90-95:00 | 0.5 | 0.5 | 6 |
| 95-100:00 | 0.5 | 0.5 | 6 |
| 100-105:00 | 0.5 | 0.5 | 6 |
| 105-110:00 | 0.5 | 0.5 | 6 |
| 110-115:00 | 0.5 | 0.5 | 6 |
| 115-120:00 | 0.5 | 0.5 | 6 |
| 120-125:00 | 0.5 | 0.5 | 6 |
| 125-130:00 | 0.5 | 0.5 | 6 |
| 130-135:00 | 0.5 | 0.5 | 6 |
| 135-140:00 | 0.5 | 0.5 | 6 |
| 140-145:00 | 0.5 | 0.5 | 6 |
| 145-150:00 | 0.5 | 0.5 | 6 |
| 150-155:00 | 0.5 | 0.5 | 6 |
| 155-160:00 | 0.5 | 0.5 | 6 |
| 160-165:00 | 0.5 | 0.5 | 6 |
| 165-170:00 | 0.5 | 0.5 | 6 |
| 170-175:00 | 0.5 | 0.5 | 6 |
| 175-180:00 | 0.5 | 0.5 | 6 |
| 180-185:00 | 0.5 | 0.5 | 6 |
| 185-190:00 | 0.5 | 0.5 | 6 |
| 190-195:00 | 0.5 | 0.5 | 6 |
| 195-200:00 | 0.5 | 0.5 | 6 |
| 200-205:00 | 0.5 | 0.5 | 6 |
| 205-210:00 | 0.5 | 0.5 | 6 |
| 210-215:00 | 0.5 | 0.5 | 6 |
| 215-220:00 | 0.5 | 0.5 | 6 |
| 220-225:00 | 0.5 | 0.5 | 6 |
| 225-230:00 | 0.5 | 0.5 | 6 |
| 230-235:00 | 0.5 | 0.5 | 6 |
| 235-240:00 | 0.5 | 0.5 | 6 |
| 240-245:00 | 0.5 | 0.5 | 6 |
| 245-250:00 | 0.5 | 0.5 | 6 |
| 250-255:00 | 0.5 | 0.5 | 6 |
| 255-260:00 | 0.5 | 0.5 | 6 |
| 260-265:00 | 0.5 | 0.5 | 6 |
| 265-270:00 | 0.5 | 0.5 | 6 |
| 270-275:00 | 0.5 | 0.5 | 6 |
| 275-280:00 | 0.5 | 0.5 | 6 |
| 280-285:00 | 0.5 | 0.5 | 6 |
| 285-290:00 | 0.5 | 0.5 | 6 |
| 290-295:00 | 0.5 | 0.5 | 6 |
| 295-300:00 | 0.5 | 0.5 | 6 |
| 300-305:00 | 0.5 | 0.5 | 6 |
| 305-310:00 | 0.5 | 0.5 | 6 |
| 310-315:00 | 0.5 | 0.5 | 6 |
| 315-320:00 | 0.5 | 0.5 | 6 |
| 320-325:00 | 0.5 | 0.5 | 6 |
| 325-330:00 | 0.5 | 0.5 | 6 |
| 330-335:00 | 0.5 | 0.5 | 6 |
| 335-340:00 | 0.5 | 0.5 | 6 |

**Fig 8. The mean volume of trades for each 5-minute period over the three subsamples for the four precious**
**metals.**

[https://doi.org/10.1371/journal.pone.0174232.g008](https://doi.org/10.1371/journal.pone.0174232.g008)

volume of trades of gold increases throughout the day and then decreases from around 5 PM
GMT, similar to what was found in Fig 5. For all four precious metals, the increase in the volume of trades is much larger from the second to the third subsample than the first to the second subsample, indicating a much larger increase in trading of precious metals after 2010. The
intraday BAS over the three subsamples is reported in Fig 9 which, similar to the intraday BAS
over the full sample, shows very little pattern throughout the day as the BAS seems to remain
fairly constant in each subsample period. As expected from our previous analysis, the BAS of
each precious metal decreases over time indicating an increase in liquidity and efficiency of
each precious metal market. Fig 10 presents the intraday squared returns measure of volatility
over the three subsamples and for gold and silver, the patterns are very similar. For platinum,
we find that the volatility during the first subsample is much greater throughout the day than
for the most recent subsamples while we find that the most recent subsample for palladium
experiences much less variation throughout the day than the first two subsamples The other
measures of volatility show similar patterns and are not reported to conserve space but available upon request.

### Correlation

A well-known stylised fact in finance is that stock index returns are negatively correlated with
changes in volatility \[26\] and that the relationship is even more pronounced in falling than in
rising markets \[43\]. There has been much evidence of this relationship in stock market indices
but little in precious metals, especially at high-frequency. To examine the lead-lag relationship
between returns and volatility of returns, we calculate the correlation coefficient of the precious metals returns at the 5-minute internal _t_ with VSQ and VGK in 5-minutes internal _t + j,_
where _j_ 2 {-500,...,500}. Calculations are based on all _t_ during the total sample period. The RS

$$
j\\in{-500,\\ldots,500}
$$

* * *

XAU 2000-2005 2005-2010 2010-2015

XAG 2000-2005 2005-2010 2010-2015

XPT 2000-2005 2005-2010 2010-2015

XPD 2000-2005 2005-2010 2010-2015

**Fig 9. The mean BAS for each 5-minute period over the three subsamples for the four precious metals.** [https://doi.org/10.1371/journal.pone.0174232.g009](https://doi.org/10.1371/journal.pone.0174232.g009)

graphs are almost identical to those of the GK and are not included but are available upon
request.

Fig 11 shows the correlation coefficient is near zero for lagged SQ volatility \*(j < 0)\* for all
precious metals. Thus, precious metals return does not seem to be systematically related to the
preceding SQ volatility. However, we find a significantly negative correlation for all four precious metals returns not only with contemporaneous volatility (\*j =\* 0), but also the volatility in
the next few 5-minute periods. This observation supports the hypothesis that volatility is
adjusted to changes in the index level. We also study the GK volatility measure interaction
with returns in Fig 12, which shows similar results to Fig 11, with lagged volatility generating
near zero coefficients and some significant negative correlation coefficients. Again, this is compatible with a return-driven effect. We also study the correlation between volatility and returns
for our three subsamples and find them to be almost identical to ones reported in Figs 11 and
12 and are available upon request. However, correlations computed at lags > 1 could be due to
the correlation at lag _j = 1._ This is why it is necessary to identify causality and the number of
lagged returns which have an impact on contemporaneous volatility.

### Vector autoregression model

To explore the casual relationships between volatility and returns of high-frequency precious
metal data, a vector autoregression (VAR) model is estimated. Granger causality tests are then
conducted to determine the direction of the causal linkages.

We consider a VAR model of order _p_ in which;
X

$$
y\_{t}=c+\\sum\_{t=1}^{p}\\phi\_{t}y\_{t-1}+\\varepsilon\_{t}
$$

ð6Þ

* * *

**XAU**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00-20 | 0.025 | 0.033 | 0.003 |
| 01-20 | 0.008 | 0.006 | 0.003 |
| 02-20 | 0.004 | 0.004 | 0.003 |
| 03-20 | 0.003 | 0.003 | 0.003 |
| 04-20 | 0.004 | 0.004 | 0.003 |
| 05-20 | 0.003 | 0.003 | 0.003 |
| 06-20 | 0.004 | 0.004 | 0.003 |
| 07-20 | 0.005 | 0.005 | 0.003 |
| 08-20 | 0.006 | 0.006 | 0.003 |
| 09-20 | 0.005 | 0.005 | 0.003 |
| 10-20 | 0.005 | 0.005 | 0.003 |
| 11-20 | 0.005 | 0.005 | 0.003 |
| 12-20 | 0.015 | 0.015 | 0.003 |
| 13-20 | 0.012 | 0.012 | 0.003 |
| 14-20 | 0.012 | 0.012 | 0.003 |
| 15-20 | 0.010 | 0.010 | 0.003 |
| 16-20 | 0.009 | 0.009 | 0.003 |
| 17-20 | 0.008 | 0.008 | 0.003 |
| 18-20 | 0.007 | 0.007 | 0.003 |
| 19-20 | 0.005 | 0.005 | 0.003 |
| 20-20 | 0.004 | 0.004 | 0.003 |
| 21-20 | 0.004 | 0.004 | 0.003 |
| 22-20 | 0.003 | 0.003 | 0.003 |
| 23-20 | 0.004 | 0.004 | 0.003 |

**XAG**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00-20 | 0.045 | 0.045 | 0.010 |
| 01-20 | 0.025 | 0.025 | 0.010 |
| 02-20 | 0.015 | 0.015 | 0.010 |
| 03-20 | 0.012 | 0.012 | 0.010 |
| 04-20 | 0.015 | 0.015 | 0.010 |
| 05-20 | 0.015 | 0.015 | 0.010 |
| 06-20 | 0.018 | 0.018 | 0.010 |
| 07-20 | 0.022 | 0.022 | 0.010 |
| 08-20 | 0.025 | 0.025 | 0.010 |
| 09-20 | 0.022 | 0.022 | 0.010 |
| 10-20 | 0.020 | 0.020 | 0.010 |
| 11-20 | 0.020 | 0.020 | 0.010 |
| 12-20 | 0.035 | 0.035 | 0.010 |
| 13-20 | 0.055 | 0.055 | 0.010 |
| 14-20 | 0.050 | 0.050 | 0.010 |
| 15-20 | 0.045 | 0.045 | 0.010 |
| 16-20 | 0.040 | 0.040 | 0.010 |
| 17-20 | 0.035 | 0.035 | 0.010 |
| 18-20 | 0.025 | 0.025 | 0.010 |
| 19-20 | 0.015 | 0.015 | 0.010 |
| 20-20 | 0.012 | 0.012 | 0.010 |
| 21-20 | 0.012 | 0.012 | 0.010 |
| 22-20 | 0.015 | 0.015 | 0.010 |
| 23-20 | 0.015 | 0.015 | 0.010 |

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00-20 | 0.045 | 0.025 | 0.015 |
| 00-40 | 0.035 | 0.025 | 0.015 |
| 01-00 | 0.03 | 0.025 | 0.015 |
| 01-20 | 0.025 | 0.025 | 0.015 |
| 02-00 | 0.02 | 0.025 | 0.01 |
| 02-20 | 0.015 | 0.025 | 0.01 |
| 03-00 | 0.015 | 0.025 | 0.01 |
| 03-20 | 0.02 | 0.025 | 0.01 |
| 04-00 | 0.02 | 0.025 | 0.01 |
| 04-20 | 0.02 | 0.025 | 0.01 |
| 05-00 | 0.02 | 0.025 | 0.01 |
| 05-20 | 0.02 | 0.025 | 0.01 |
| 06-00 | 0.02 | 0.025 | 0.01 |
| 06-20 | 0.02 | 0.025 | 0.01 |
| 07-00 | 0.025 | 0.025 | 0.01 |
| 07-20 | 0.025 | 0.025 | 0.01 |
| 08-00 | 0.025 | 0.025 | 0.01 |
| 08-20 | 0.025 | 0.025 | 0.01 |
| 09-00 | 0.025 | 0.025 | 0.01 |
| 09-20 | 0.025 | 0.025 | 0.01 |
| 10-00 | 0.025 | 0.025 | 0.01 |
| 10-20 | 0.025 | 0.025 | 0.01 |
| 11-00 | 0.025 | 0.025 | 0.01 |
| 11-20 | 0.025 | 0.025 | 0.01 |
| 12-00 | 0.025 | 0.025 | 0.01 |
| 12-20 | 0.08 | 0.05 | 0.03 |
| 12-40 | 0.06 | 0.05 | 0.03 |
| 13-00 | 0.05 | 0.05 | 0.03 |
| 13-20 | 0.06 | 0.05 | 0.03 |
| 13-40 | 0.06 | 0.05 | 0.03 |
| 14-00 | 0.05 | 0.05 | 0.03 |
| 14-20 | 0.05 | 0.05 | 0.03 |
| 14-40 | 0.05 | 0.05 | 0.03 |
| 15-00 | 0.05 | 0.05 | 0.03 |
| 15-20 | 0.05 | 0.05 | 0.03 |
| 15-40 | 0.05 | 0.05 | 0.03 |
| 16-00 | 0.05 | 0.05 | 0.03 |
| 16-20 | 0.05 | 0.05 | 0.03 |
| 16-40 | 0.05 | 0.05 | 0.03 |
| 17-00 | 0.05 | 0.05 | 0.03 |
| 17-20 | 0.05 | 0.05 | 0.03 |
| 17-40 | 0.05 | 0.05 | 0.03 |
| 18-00 | 0.03 | 0.03 | 0.02 |
| 18-20 | 0.03 | 0.03 | 0.02 |
| 18-40 | 0.03 | 0.03 | 0.02 |
| 19-00 | 0.02 | 0.02 | 0.01 |
| 19-20 | 0.02 | 0.02 | 0.01 |
| 19-40 | 0.02 | 0.02 | 0.01 |
| 20-00 | 0.02 | 0.02 | 0.01 |
| 20-20 | 0.02 | 0.02 | 0.01 |
| 20-40 | 0.02 | 0.02 | 0.01 |
| 21-00 | 0.02 | 0.02 | 0.01 |
| 21-20 | 0.02 | 0.02 | 0.01 |
| 21-40 | 0.02 | 0.02 | 0.01 |
| 22-00 | 0.02 | 0.02 | 0.01 |
| 22-20 | 0.02 | 0.02 | 0.01 |
| 22-40 | 0.02 | 0.02 | 0.01 |
| 23-00 | 0.02 | 0.02 | 0.01 |
| 23-20 | 0.02 | 0.02 | 0.01 |
| 23-40 | 0.02 | 0.02 | 0.01 |

**XPT**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00-20 | 0.12 | 0.02 | 0.01 |
| 00-40 | 0.08 | 0.02 | 0.01 |
| 01-00 | 0.07 | 0.02 | 0.01 |
| 01-20 | 0.07 | 0.02 | 0.01 |
| 02-00 | 0.06 | 0.02 | 0.01 |
| 02-20 | 0.04 | 0.02 | 0.01 |
| 03-00 | 0.05 | 0.02 | 0.01 |
| 03-20 | 0.07 | 0.02 | 0.01 |
| 04-00 | 0.07 | 0.02 | 0.01 |
| 04-20 | 0.07 | 0.02 | 0.01 |
| 05-00 | 0.07 | 0.02 | 0.01 |
| 05-20 | 0.07 | 0.02 | 0.01 |
| 06-00 | 0.07 | 0.02 | 0.01 |
| 06-20 | 0.07 | 0.02 | 0.01 |
| 07-00 | 0.06 | 0.02 | 0.01 |
| 07-20 | 0.06 | 0.02 | 0.01 |
| 08-00 | 0.05 | 0.02 | 0.01 |
| 08-20 | 0.05 | 0.02 | 0.01 |
| 09-00 | 0.06 | 0.02 | 0.01 |
| 09-20 | 0.06 | 0.02 | 0.01 |
| 10-00 | 0.06 | 0.02 | 0.01 |
| 10-20 | 0.06 | 0.02 | 0.01 |
| 11-00 | 0.06 | 0.02 | 0.01 |
| 11-20 | 0.06 | 0.02 | 0.01 |
| 12-00 | 0.06 | 0.02 | 0.01 |
| 12-20 | 0.05 | 0.02 | 0.01 |
| 12-40 | 0.05 | 0.02 | 0.01 |
| 13-00 | 0.05 | 0.02 | 0.01 |
| 13-20 | 0.05 | 0.02 | 0.01 |
| 13-40 | 0.05 | 0.02 | 0.01 |
| 14-00 | 0.05 | 0.02 | 0.01 |
| 14-20 | 0.04 | 0.02 | 0.01 |
| 14-40 | 0.04 | 0.02 | 0.01 |
| 15-00 | 0.04 | 0.02 | 0.01 |
| 15-20 | 0.04 | 0.02 | 0.01 |
| 15-40 | 0.04 | 0.02 | 0.01 |
| 16-00 | 0.04 | 0.02 | 0.01 |
| 16-20 | 0.04 | 0.02 | 0.01 |
| 16-40 | 0.04 | 0.02 | 0.01 |
| 17-00 | 0.04 | 0.02 | 0.01 |
| 17-20 | 0.04 | 0.02 | 0.01 |
| 17-40 | 0.04 | 0.02 | 0.01 |
| 18-00 | 0.04 | 0.02 | 0.01 |
| 18-20 | 0.04 | 0.02 | 0.01 |
| 18-40 | 0.04 | 0.02 | 0.01 |
| 19-00 | 0.04 | 0.02 | 0.01 |
| 19-20 | 0.04 | 0.02 | 0.01 |
| 19-40 | 0.04 | 0.02 | 0.01 |
| 20-00 | 0.04 | 0.02 | 0.01 |
| 20-20 | 0.04 | 0.02 | 0.01 |
| 20-40 | 0.04 | 0.02 | 0.01 |
| 21-00 | 0.04 | 0.02 | 0.01 |
| 21-20 | 0.04 | 0.02 | 0.01 |
| 21-40 | 0.04 | 0.02 | 0.01 |
| 22-00 | 0.04 | 0.02 | 0.01 |
| 22-20 | 0.04 | 0.02 | 0.01 |
| 22-40 | 0.04 | 0.02 | 0.01 |
| 23-00 | 0.04 | 0.02 | 0.01 |
| 23-20 | 0.04 | 0.02 | 0.01 |
| 23-40 | 0.04 | 0.02 | 0.01 |

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 00:00 | 0.05 | 0.025 | 0.02 |
| 00:20 | 0.12 | 0.02 | 0.02 |
| 00:40 | 0.08 | 0.02 | 0.02 |
| 01:00 | 0.075 | 0.02 | 0.02 |
| 01:20 | 0.075 | 0.02 | 0.02 |
| 01:40 | 0.07 | 0.02 | 0.02 |
| 02:00 | 0.07 | 0.02 | 0.02 |
| 02:20 | 0.045 | 0.02 | 0.02 |
| 02:40 | 0.04 | 0.02 | 0.02 |
| 03:00 | 0.04 | 0.02 | 0.02 |
| 03:20 | 0.07 | 0.02 | 0.02 |
| 03:40 | 0.07 | 0.02 | 0.02 |
| 04:00 | 0.07 | 0.02 | 0.02 |
| 04:20 | 0.07 | 0.02 | 0.02 |
| 04:40 | 0.07 | 0.02 | 0.02 |
| 05:00 | 0.07 | 0.02 | 0.02 |
| 05:20 | 0.065 | 0.02 | 0.02 |
| 05:40 | 0.07 | 0.02 | 0.02 |
| 06:00 | 0.07 | 0.02 | 0.02 |
| 06:20 | 0.07 | 0.02 | 0.02 |
| 06:40 | 0.1 | 0.02 | 0.02 |
| 07:00 | 0.06 | 0.02 | 0.02 |
| 07:20 | 0.06 | 0.02 | 0.02 |
| 07:40 | 0.055 | 0.02 | 0.02 |
| 08:00 | 0.055 | 0.02 | 0.02 |
| 08:20 | 0.055 | 0.02 | 0.02 |
| 08:40 | 0.06 | 0.02 | 0.02 |
| 09:00 | 0.07 | 0.02 | 0.02 |
| 09:20 | 0.06 | 0.02 | 0.02 |
| 09:40 | 0.06 | 0.02 | 0.02 |
| 10:00 | 0.06 | 0.02 | 0.02 |
| 10:20 | 0.06 | 0.02 | 0.02 |
| 10:40 | 0.06 | 0.02 | 0.02 |
| 11:00 | 0.06 | 0.02 | 0.02 |
| 11:20 | 0.06 | 0.02 | 0.02 |
| 11:40 | 0.06 | 0.02 | 0.02 |
| 12:00 | 0.06 | 0.02 | 0.02 |
| 12:20 | 0.055 | 0.02 | 0.02 |
| 12:40 | 0.05 | 0.02 | 0.02 |
| 13:00 | 0.05 | 0.02 | 0.02 |
| 13:20 | 0.045 | 0.02 | 0.02 |
| 13:40 | 0.045 | 0.02 | 0.02 |
| 14:00 | 0.045 | 0.02 | 0.02 |
| 14:20 | 0.04 | 0.02 | 0.02 |
| 14:40 | 0.04 | 0.02 | 0.02 |
| 15:00 | 0.04 | 0.02 | 0.02 |
| 15:20 | 0.04 | 0.02 | 0.02 |
| 15:40 | 0.04 | 0.02 | 0.02 |
| 16:00 | 0.04 | 0.02 | 0.02 |
| 16:20 | 0.04 | 0.02 | 0.02 |
| 16:40 | 0.04 | 0.02 | 0.02 |
| 17:00 | 0.04 | 0.02 | 0.02 |
| 17:20 | 0.04 | 0.02 | 0.02 |
| 17:40 | 0.04 | 0.02 | 0.02 |
| 18:00 | 0.04 | 0.02 | 0.02 |
| 18:20 | 0.04 | 0.02 | 0.02 |
| 18:40 | 0.04 | 0.02 | 0.02 |
| 19:00 | 0.04 | 0.02 | 0.02 |
| 19:20 | 0.04 | 0.02 | 0.02 |
| 19:40 | 0.04 | 0.02 | 0.02 |
| 20:00 | 0.04 | 0.02 | 0.02 |
| 20:20 | 0.04 | 0.02 | 0.02 |
| 20:40 | 0.04 | 0.02 | 0.02 |
| 21:00 | 0.04 | 0.02 | 0.02 |
| 21:20 | 0.04 | 0.02 | 0.02 |
| 21:40 | 0.04 | 0.02 | 0.02 |
| 22:00 | 0.04 | 0.02 | 0.02 |
| 22:20 | 0.03 | 0.02 | 0.02 |
| 22:40 | 0.03 | 0.02 | 0.02 |
| 23:00 | 0.03 | 0.02 | 0.02 |
| 23:20 | 0.03 | 0.02 | 0.02 |
| 23:40 | 0.04 | 0.02 | 0.02 |

**XPD**

| Category | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 30:00 | 0.8 | 0.6 | 0.05 |
| 30:20 | 0.4 | 0.3 | 0.05 |
| 30:40 | 0.2 | 0.25 | 0.05 |
| 31:00 | 0.15 | 0.2 | 0.05 |
| 31:20 | 0.1 | 0.2 | 0.05 |
| 31:40 | 0.1 | 0.2 | 0.05 |
| 32:00 | 0.08 | 0.15 | 0.05 |
| 32:20 | 0.05 | 0.1 | 0.05 |
| 32:40 | 0.05 | 0.1 | 0.05 |
| 33:00 | 0.05 | 0.1 | 0.05 |
| 33:20 | 0.05 | 0.1 | 0.05 |
| 33:40 | 0.05 | 0.1 | 0.05 |
| 34:00 | 0.1 | 0.2 | 0.05 |
| 34:20 | 0.1 | 0.2 | 0.05 |
| 34:40 | 0.1 | 0.2 | 0.05 |
| 35:00 | 0.1 | 0.2 | 0.05 |
| 35:20 | 0.1 | 0.2 | 0.05 |
| 35:40 | 0.2 | 0.3 | 0.05 |
| 36:00 | 0.3 | 0.35 | 0.05 |
| 36:20 | 0.4 | 0.4 | 0.05 |
| 36:40 | 0.5 | 0.45 | 0.05 |
| 37:00 | 0.45 | 0.4 | 0.05 |
| 37:20 | 0.4 | 0.4 | 0.05 |
| 37:40 | 0.4 | 0.4 | 0.05 |
| 38:00 | 0.3 | 0.35 | 0.05 |
| 38:20 | 0.2 | 0.3 | 0.05 |
| 38:40 | 0.3 | 0.35 | 0.05 |
| 39:00 | 0.8 | 0.4 | 0.05 |
| 39:20 | 0.3 | 0.3 | 0.05 |
| 39:40 | 0.2 | 0.25 | 0.05 |
| 40:00 | 0.1 | 0.2 | 0.05 |
| 40:20 | 0.1 | 0.2 | 0.05 |
| 40:40 | 0.1 | 0.2 | 0.05 |
| 41:00 | 0.1 | 0.2 | 0.05 |
| 41:20 | 0.1 | 0.2 | 0.05 |
| 41:40 | 0.1 | 0.2 | 0.05 |
| 42:00 | 0.1 | 0.2 | 0.05 |
| 42:20 | 0.2 | 0.25 | 0.05 |
| 42:40 | 0.3 | 0.3 | 0.05 |
| 43:00 | 0.3 | 0.3 | 0.05 |
| 43:20 | 0.2 | 0.25 | 0.05 |
| 43:40 | 0.15 | 0.2 | 0.05 |
| 44:00 | 0.1 | 0.2 | 0.05 |
| 44:20 | 0.1 | 0.2 | 0.05 |
| 44:40 | 0.1 | 0.2 | 0.05 |
| 45:00 | 0.1 | 0.2 | 0.05 |
| 45:20 | 0.1 | 0.2 | 0.05 |
| 45:40 | 0.1 | 0.2 | 0.05 |
| 46:00 | 0.1 | 0.2 | 0.05 |
| 46:20 | 0.1 | 0.2 | 0.05 |
| 46:40 | 0.1 | 0.2 | 0.05 |
| 47:00 | 0.1 | 0.2 | 0.05 |
| 47:20 | 0.1 | 0.2 | 0.05 |
| 47:40 | 0.1 | 0.2 | 0.05 |
| 48:00 | 0.1 | 0.2 | 0.05 |
| 48:20 | 0.1 | 0.2 | 0.05 |
| 48:40 | 0.1 | 0.2 | 0.05 |
| 49:00 | 0.1 | 0.2 | 0.05 |
| 49:20 | 0.1 | 0.2 | 0.05 |
| 49:40 | 0.1 | 0.2 | 0.05 |
| 50:00 | 0.1 | 0.2 | 0.05 |
| 50:20 | 0.1 | 0.2 | 0.05 |
| 50:40 | 0.1 | 0.2 | 0.05 |
| 51:00 | 0.1 | 0.2 | 0.05 |
| 51:20 | 0.1 | 0.2 | 0.05 |
| 51:40 | 0.1 | 0.2 | 0.05 |
| 52:00 | 0.1 | 0.2 | 0.05 |
| 52:20 | 0.1 | 0.2 | 0.05 |
| 52:40 | 0.1 | 0.2 | 0.05 |
| 53:00 | 0.1 | 0.2 | 0.05 |
| 53:20 | 0.1 | 0.2 | 0.05 |
| 53:40 | 0.1 | 0.2 | 0.05 |

| 5-minute period | 2000-2005 | 2005-2010 | 2010-2015 |
| --- | --- | --- | --- |
| 20:00-20:20 | 0.15 | 0.25 | 0.02 |
| 20:20-20:40 | 0.85 | 0.75 | 0.02 |
| 20:40-21:00 | 0.35 | 0.35 | 0.02 |
| 21:00-21:20 | 0.3 | 0.3 | 0.02 |
| 21:20-21:40 | 0.2 | 0.25 | 0.02 |
| 21:40-22:00 | 0.15 | 0.2 | 0.02 |
| 22:00-22:20 | 0.1 | 0.15 | 0.02 |
| 22:20-22:40 | 0.05 | 0.1 | 0.02 |
| 22:40-23:00 | 0.05 | 0.05 | 0.02 |
| 23:00-23:20 | 0.05 | 0.05 | 0.02 |
| 23:20-23:40 | 0.05 | 0.05 | 0.02 |
| 23:40-24:00 | 0.1 | 0.2 | 0.02 |
| 24:00-24:20 | 0.15 | 0.15 | 0.02 |
| 24:20-24:40 | 0.1 | 0.15 | 0.02 |
| 24:40-25:00 | 0.1 | 0.15 | 0.02 |
| 25:00-25:20 | 0.1 | 0.15 | 0.02 |
| 25:20-25:40 | 0.1 | 0.15 | 0.02 |
| 25:40-26:00 | 0.2 | 0.2 | 0.02 |
| 26:00-26:20 | 0.3 | 0.3 | 0.02 |
| 26:20-26:40 | 0.4 | 0.35 | 0.02 |
| 26:40-27:00 | 0.55 | 0.4 | 0.02 |
| 27:00-27:20 | 0.45 | 0.4 | 0.02 |
| 27:20-27:40 | 0.4 | 0.4 | 0.02 |
| 27:40-28:00 | 0.45 | 0.45 | 0.02 |
| 28:00-28:20 | 0.35 | 0.35 | 0.02 |
| 28:20-28:40 | 0.25 | 0.3 | 0.02 |
| 28:40-29:00 | 0.2 | 0.25 | 0.02 |
| 29:00-29:20 | 0.3 | 0.3 | 0.02 |
| 29:20-29:40 | 0.8 | 0.7 | 0.02 |
| 29:40-30:00 | 0.2 | 0.25 | 0.02 |
| 30:00-30:20 | 0.2 | 0.2 | 0.02 |
| 30:20-30:40 | 0.4 | 0.4 | 0.02 |
| 30:40-31:00 | 0.2 | 0.2 | 0.02 |
| 31:00-31:20 | 0.15 | 0.15 | 0.02 |
| 31:20-31:40 | 0.15 | 0.15 | 0.02 |
| 31:40-32:00 | 0.1 | 0.1 | 0.02 |
| 32:00-32:20 | 0.1 | 0.1 | 0.02 |
| 32:20-32:40 | 0.1 | 0.1 | 0.02 |
| 32:40-33:00 | 0.1 | 0.1 | 0.02 |
| 33:00-33:20 | 0.1 | 0.1 | 0.02 |
| 33:20-33:40 | 0.1 | 0.1 | 0.02 |
| 33:40-34:00 | 0.1 | 0.1 | 0.02 |
| 34:00-34:20 | 0.1 | 0.1 | 0.02 |
| 34:20-34:40 | 0.1 | 0.1 | 0.02 |
| 34:40-35:00 | 0.1 | 0.1 | 0.02 |
| 35:00-35:20 | 0.1 | 0.1 | 0.02 |
| 35:20-35:40 | 0.1 | 0.1 | 0.02 |
| 35:40-36:00 | 0.1 | 0.1 | 0.02 |
| 36:00-36:20 | 0.1 | 0.1 | 0.02 |
| 36:20-36:40 | 0.1 | 0.1 | 0.02 |
| 36:40-37:00 | 0.1 | 0.1 | 0.02 |
| 37:00-37:20 | 0.1 | 0.1 | 0.02 |
| 37:20-37:40 | 0.1 | 0.1 | 0.02 |
| 37:40-38:00 | 0.1 | 0.1 | 0.02 |
| 38:00-38:20 | 0.1 | 0.1 | 0.02 |
| 38:20-38:40 | 0.1 | 0.1 | 0.02 |
| 38:40-39:00 | 0.1 | 0.1 | 0.02 |
| 39:00-39:20 | 0.1 | 0.1 | 0.02 |
| 39:20-39:40 | 0.1 | 0.1 | 0.02 |
| 39:40-40:00 | 0.1 | 0.1 | 0.02 |
| 40:00-40:20 | 0.1 | 0.1 | 0.02 |
| 40:20-40:40 | 0.1 | 0.1 | 0.02 |
| 40:40-41:00 | 0.1 | 0.1 | 0.02 |
| 41:00-41:20 | 0.1 | 0.1 | 0.02 |
| 41:20-41:40 | 0.1 | 0.1 | 0.02 |
| 41:40-42:00 | 0.1 | 0.1 | 0.02 |
| 42:00-42:20 | 0.1 | 0.1 | 0.02 |
| 42:20-42:40 | 0.1 | 0.1 | 0.02 |
| 42:40-43:00 | 0.1 | 0.1 | 0.02 |
| 43:00-43:20 | 0.1 | 0.1 | 0.02 |
| 43:20-43:40 | 0.1 | 0.1 | 0.02 |
| 43:40-44:00 | 0.1 | 0.1 | 0.02 |
| 44:00-44:20 | 0.1 | 0.1 | 0.02 |
| 44:20-44:40 | 0.1 | 0.1 | 0.02 |
| 44:40-45:00 | 0.1 | 0.1 | 0.02 |
| 45:00-45:20 | 0.1 | 0.1 | 0.02 |
| 45:20-45:40 | 0.1 | 0.1 | 0.02 |
| 45:40-46:00 | 0.1 | 0.1 | 0.02 |
| 46:00-46:20 | 0.1 | 0.1 | 0.02 |
| 46:20-46:40 | 0.1 | 0.1 | 0.02 |
| 46:40-47:00 | 0.1 | 0.1 | 0.02 |
| 47:00-47:20 | 0.1 | 0.1 | 0.02 |
| 47:20-47:40 | 0.1 | 0.1 | 0.02 |
| 47:40-48:00 | 0.1 | 0.1 | 0.02 |
| 48:00-48:20 | 0.1 | 0.1 | 0.02 |
| 48:20-48:40 | 0.1 | 0.1 | 0.02 |
| 48:40-49:00 | 0.1 | 0.1 | 0.02 |
| 49:00-49:20 | 0.1 | 0.1 | 0.02 |
| 49:20-49:40 | 0.1 | 0.1 | 0.02 |
| 49:40-50:00 | 0.1 | 0.1 | 0.02 |
| 50:00-50:20 | 0.1 | 0.1 | 0.02 |
| 50:20-50:40 | 0.1 | 0.1 | 0.02 |
| 50:40-51:00 | 0.1 | 0.1 | 0.02 |
| 51:00-51:20 | 0.1 | 0.1 | 0.02 |
| 51:20-51:40 | 0.1 | 0.1 | 0.02 |
| 51:40-52:00 | 0.1 | 0.1 | 0.02 |
| 52:00-52:20 | 0.1 | 0.1 | 0.02 |
| 52:20-52:40 | 0.1 | 0.1 | 0.02 |
| 52:40-53:00 | 0.1 | 0.1 | 0.02 |
| 53:00-53:20 | 0.1 | 0.1 | 0.02 |
| 53:20-53:40 | 0.1 | 0.1 | 0.02 |
| 53:40-54:00 | 0.1 | 0.1 | 0.02 |
| 54:00-54:20 | 0.1 | 0.1 | 0.02 |
| 54:20-54:40 | 0.1 | 0.1 | 0.02 |
| 54:40-55:00 | 0.1 | 0.1 | 0.02 |
| 55:00-55:20 | 0.1 | 0.1 | 0.02 |
| 55:20-55:40 | 0.1 | 0.1 | 0.02 |
| 55:40-56:00 | 0.1 | 0.1 | 0.02 |
| 56:00-56:20 | 0.1 | 0.1 | 0.02 |
| 56:20-56:40 | 0.1 | 0.1 | 0.02 |
| 56:40-57:00 | 0.1 | 0.1 | 0.02 |
| 57:00-57:20 | 0.1 | 0.1 | 0.02 |
| 57:20-57:40 | 0.1 | 0.1 | 0.02 |
| 57:40-58:00 | 0.1 | 0.1 | 0.02 |
| 58:00-58:20 | 0.1 | 0.1 | 0.02 |
| 58:20-58:40 | 0.1 | 0.1 | 0.02 |
| 58:40-59:00 | 0.1 | 0.1 | 0.02 |
| 59:00-59:20 | 0.1 | 0.1 | 0.02 |
| 59:20-59:40 | 0.1 | 0.1 | 0.02 |
| 59:40-60:00 | 0.1 | 0.1 | 0.02 |

**Fig 10. The mean squared returns measure of volatility for each 5-minute period over the three subsamples**
**for the four precious metals.**

[https://doi.org/10.1371/journal.pone.0174232.g010](https://doi.org/10.1371/journal.pone.0174232.g010)

| Category | Mean squared returns measure of volatility |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | 0 |
| -425 | 0 |
| -400 | 0 |
| -375 | 0 |
| -350 | 0 |
| -325 | 0 |
| -300 | 0 |
| -275 | 0 |
| -250 | 0 |
| -225 | 0 |
| -200 | 0 |
| -175 | 0 |
| -150 | 0 |
| -125 | 0 |
| -100 | 0 |
| -75 | 0 |
| -50 | 0 |
| -25 | 0 |
| 0 | -0.055 |
| 25 | 0 |
| 50 | 0 |
| 75 | 0 |
| 100 | 0 |
| 125 | 0 |
| 150 | 0 |
| 175 | 0 |
| 200 | 0 |
| 225 | 0 |
| 250 | 0 |
| 275 | 0 |
| 300 | 0 |
| 325 | 0 |
| 350 | 0 |
| 375 | 0 |
| 400 | 0 |
| 425 | 0 |
| 450 | 0 |
| 475 | 0 |
| 500 | 0 |

| Category | Mean squared returns measure of volatility |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | 0 |
| -425 | 0 |
| -400 | 0 |
| -375 | 0 |
| -350 | 0 |
| -325 | 0 |
| -300 | 0 |
| -275 | 0 |
| -250 | 0 |
| -225 | 0 |
| -200 | 0 |
| -175 | 0 |
| -150 | 0 |
| -125 | 0 |
| -100 | 0 |
| -75 | 0 |
| -50 | 0 |
| -25 | 0 |
| 0 | -0.055 |
| 25 | 0 |
| 50 | 0 |
| 75 | 0 |
| 100 | 0 |
| 125 | 0 |
| 150 | 0 |
| 175 | 0 |
| 200 | 0 |
| 225 | 0 |
| 250 | 0 |
| 275 | 0 |
| 300 | 0 |
| 325 | 0 |
| 350 | 0 |
| 375 | 0 |
| 400 | 0 |
| 425 | 0 |
| 450 | 0 |
| 475 | 0 |
| 500 | 0 |

| Category | Mean squared returns measure of volatility |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | 0 |
| -425 | 0 |
| -400 | 0 |
| -375 | 0 |
| -350 | 0 |
| -325 | 0 |
| -300 | 0 |
| -275 | 0 |
| -250 | 0 |
| -225 | 0 |
| -200 | 0 |
| -175 | 0 |
| -150 | 0 |
| -125 | 0 |
| -100 | 0 |
| -75 | 0 |
| -50 | 0 |
| -25 | 0 |
| 0 | -0.055 |
| 25 | 0 |
| 50 | 0 |
| 75 | 0 |
| 100 | 0 |
| 125 | 0 |
| 150 | 0 |
| 175 | 0 |
| 200 | 0 |
| 225 | 0 |
| 250 | 0 |
| 275 | 0 |
| 300 | 0 |
| 325 | 0 |
| 350 | 0 |
| 375 | 0 |
| 400 | 0 |
| 425 | 0 |
| 450 | 0 |
| 475 | 0 |
| 500 | 0 |

| Category | Mean squared returns measure of volatility |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | 0 |
| -425 | 0 |
| -400 | 0 |
| -375 | 0 |
| -350 | 0 |
| -325 | 0 |
| -300 | 0 |
| -275 | 0 |
| -250 | 0 |
| -225 | 0 |
| -200 | 0 |
| -175 | 0 |
| -150 | 0 |
| -125 | 0 |
| -100 | 0 |
| -75 | 0 |
| -50 | 0 |
| -25 | 0 |
| 0 | -0.055 |
| 25 | 0 |
| 50 | 0 |
| 75 | 0 |
| 100 | 0 |
| 125 | 0 |
| 150 | 0 |
| 175 | 0 |
| 200 | 0 |
| 225 | 0 |
| 250 | 0 |
| 275 | 0 |
| 300 | 0 |
| 325 | 0 |
| 350 | 0 |
| 375 | 0 |
| 400 | 0 |
| 425 | 0 |
| 450 | 0 |
| 475 | 0 |
| 500 | 0 |

**Fig 11. The correlation between returns and volatility, measured by squared returns over the full sample**
**period for different lead and lag intervals.**

[https://doi.org/10.1371/journal.pone.0174232.g011](https://doi.org/10.1371/journal.pone.0174232.g011)

* * *

**XAU**

| Category | XAU |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | 0.001 |
| -425 | 0.001 |
| -400 | 0.001 |
| -375 | 0 |
| -350 | 0 |
| -325 | 0.002 |
| -300 | 0.001 |
| -275 | 0.001 |
| -250 | 0 |
| -225 | 0 |
| -200 | 0 |
| -175 | 0 |
| -150 | 0 |
| -125 | -0.001 |
| -100 | -0.001 |
| -75 | 0 |
| -50 | 0.003 |
| -25 | 0.002 |
| 0 | -0.002 |
| 25 | -0.003 |
| 50 | -0.002 |
| 75 | -0.002 |
| 100 | -0.001 |
| 125 | -0.001 |
| 150 | 0 |
| 175 | 0.002 |
| 200 | 0 |
| 225 | 0.001 |
| 250 | 0.002 |
| 275 | -0.001 |
| 300 | -0.001 |
| 325 | 0 |
| 350 | -0.001 |
| 375 | 0 |
| 400 | 0.001 |
| 425 | 0 |
| 450 | 0 |
| 475 | 0.001 |
| 500 | 0.001 |

**XAG**

| Category | XAG |
| --- | --- |
| -500 | -0.001 |
| -475 | -0.001 |
| -450 | -0.001 |
| -425 | -0.001 |
| -400 | 0.001 |
| -375 | 0.001 |
| -350 | 0 |
| -325 | 0.001 |
| -300 | 0 |
| -275 | 0.001 |
| -250 | 0 |
| -225 | -0.001 |
| -200 | -0.001 |
| -175 | -0.001 |
| -150 | -0.001 |
| -125 | 0 |
| -100 | -0.001 |
| -75 | 0 |
| -50 | 0.001 |
| -25 | 0.001 |
| 0 | 0.001 |
| 25 | -0.003 |
| 50 | -0.002 |
| 75 | -0.002 |
| 100 | -0.002 |
| 125 | -0.002 |
| 150 | -0.002 |
| 175 | -0.001 |
| 200 | -0.001 |
| 225 | -0.001 |
| 250 | -0.001 |
| 275 | -0.001 |
| 300 | -0.002 |
| 325 | -0.002 |
| 350 | -0.002 |
| 375 | -0.001 |
| 400 | -0.001 |
| 425 | 0 |
| 450 | -0.001 |
| 475 | 0 |
| 500 | 0 |

| Category | XAG | XPT |
| --- | --- | --- |
| -500 | -0.001 | -0.002 |
| -475 | -0.001 | -0.002 |
| -450 | -0.001 | -0.002 |
| -425 | -0.001 | -0.002 |
| -400 | 0.001 | -0.001 |
| -375 | 0.000 | -0.001 |
| -350 | 0.000 | -0.001 |
| -325 | 0.000 | -0.001 |
| -300 | 0.000 | -0.001 |
| -275 | 0.000 | -0.001 |
| -250 | -0.001 | -0.002 |
| -225 | -0.001 | -0.002 |
| -200 | -0.001 | -0.002 |
| -175 | -0.001 | -0.002 |
| -150 | -0.001 | -0.002 |
| -125 | -0.001 | -0.002 |
| -100 | -0.001 | -0.002 |
| -75 | -0.001 | -0.002 |
| -50 | 0.000 | -0.001 |
| -25 | 0.000 | -0.001 |
| 0 | 0.000 | -0.001 |
| 25 | -0.003 | -0.007 |
| 50 | -0.002 | -0.003 |
| 75 | -0.002 | -0.003 |
| 100 | -0.002 | -0.003 |
| 125 | -0.002 | -0.003 |
| 150 | -0.002 | -0.003 |
| 175 | -0.002 | -0.003 |
| 200 | -0.002 | -0.003 |
| 225 | -0.002 | -0.003 |
| 250 | -0.002 | -0.003 |
| 275 | -0.002 | -0.003 |
| 300 | -0.002 | -0.003 |
| 325 | -0.002 | -0.003 |
| 350 | -0.002 | -0.003 |
| 375 | -0.002 | -0.003 |
| 400 | -0.001 | -0.003 |
| 425 | -0.001 | -0.003 |
| 450 | -0.001 | -0.003 |
| 475 | -0.001 | -0.003 |
| 500 | -0.001 | -0.003 |

| Category | XPT | XPD |
| --- | --- | --- |
| -500 | -0.002 | -0.001 |
| -475 | -0.002 | -0.001 |
| -450 | -0.002 | -0.001 |
| -425 | -0.002 | -0.001 |
| -400 | -0.002 | -0.001 |
| -375 | -0.002 | -0.001 |
| -350 | -0.002 | -0.001 |
| -325 | -0.002 | -0.001 |
| -300 | -0.001 | -0.001 |
| -275 | 0.001 | 0.001 |
| -250 | -0.002 | -0.001 |
| -225 | -0.002 | -0.001 |
| -200 | -0.002 | -0.001 |
| -175 | -0.002 | -0.001 |
| -150 | -0.002 | -0.001 |
| -125 | -0.001 | -0.001 |
| -100 | -0.001 | -0.001 |
| -75 | -0.001 | -0.001 |
| -50 | -0.001 | -0.001 |
| -25 | 0.001 | 0.001 |
| 0 | 0.003 | 0.003 |
| 25 | -0.007 | -0.008 |
| 50 | -0.003 | -0.004 |
| 75 | -0.002 | -0.003 |
| 100 | -0.002 | -0.003 |
| 125 | -0.002 | -0.003 |
| 150 | -0.002 | -0.003 |
| 175 | -0.002 | -0.003 |
| 200 | -0.002 | -0.003 |
| 225 | -0.002 | -0.003 |
| 250 | -0.001 | -0.002 |
| 275 | 0.001 | 0.001 |
| 300 | -0.003 | -0.004 |
| 325 | -0.002 | -0.003 |
| 350 | -0.002 | -0.003 |
| 375 | -0.002 | -0.003 |
| 400 | -0.002 | -0.003 |
| 425 | -0.001 | -0.002 |
| 450 | -0.001 | -0.002 |
| 475 | -0.001 | -0.002 |
| 500 | -0.001 | -0.002 |

| Category | XPD |
| --- | --- |
| -500 | 0 |
| -475 | 0 |
| -450 | -0.001 |
| -425 | -0.001 |
| -400 | 0.001 |
| -375 | 0.002 |
| -350 | 0.001 |
| -325 | 0.001 |
| -300 | 0 |
| -275 | 0.001 |
| -250 | -0.001 |
| -225 | -0.001 |
| -200 | -0.002 |
| -175 | -0.002 |
| -150 | -0.001 |
| -125 | 0 |
| -100 | 0.001 |
| -75 | 0.001 |
| -50 | 0.001 |
| -25 | 0.002 |
| 0 | 0.008 |
| 25 | -0.004 |
| 50 | -0.003 |
| 75 | -0.003 |
| 100 | -0.003 |
| 125 | -0.002 |
| 150 | -0.001 |
| 175 | 0 |
| 200 | 0 |
| 225 | -0.001 |
| 250 | -0.001 |
| 275 | -0.001 |
| 300 | -0.003 |
| 325 | -0.003 |
| 350 | -0.002 |
| 375 | -0.003 |
| 400 | -0.002 |
| 425 | 0 |
| 450 | 0.001 |
| 475 | 0.002 |
| 500 | 0.001 |

**Fig 12. The correlation between returns and volatility, measured by the Garman and Klass (1980) measure**
**over the full sample period for different lead and lag intervals.**

[https://doi.org/10.1371/journal.pone.0174232.g012](https://doi.org/10.1371/journal.pone.0174232.g012)

where yt is a (n × 1) vector of endogenous variables, c = (c1,... cn) is the (n × 1) intercept vector
of the VAR,ϕi is the ith (n × n) matrix of autoregressive coefficients for i = 1,2,. . ., p, and
εt = (ε1t,...εnt) is the (n × 1) generalization of a white noise process. We model the return
volatility relationships across the four precious metals where the models are estimated up to a
maximum lag of 12 and the optimal lag length is selected by using the Akaike information criterion (AIC), similar to \[44\].

$$
y\_{t}
$$

$$
c=(c\_{1},\\cdots c\_{n})
$$

$$
\\left(n\\times I\\right)
$$

$$
i=1,2,\\ldots,p,
$$

$$
\\boldsymbol{\\varepsilon} _{t}=(\\boldsymbol{\\varepsilon}_{1t},\\ldots\\boldsymbol{\\varepsilon}\_{n t})
$$

After estimating the VAR model, the Granger causality test is conducted, this is a popular
way to test if there is any temporal statistical relationship with a predictive value between the
two time series \[45\]. This test indicates any possible short-run predictive interrelationships
among the series. When ‘X Granger causes Y’, it does not mean that Y is the effect or the result
of X. Granger causality measures precedence and information content and thus ‘causality’ is
defined in terms of predictability, hence variable X causes variable Y if present Y can be better
predicted by using past values of X than by not doing so, with respect to a given information
set that includes X and Y.

Table 4 summaries the results of the Granger causality test for the full sample period as well
as the three subsample periods for the return-driven relationship in Panel A and the volatilitydriven relationship in Panel B. The results clearly show strong evidence of a return-driven relationship across all sample periods and all three measures of volatility for platinum and palladium. For gold we find significant evidence of a return-driven relationship at the 5% level for
all measures and sample periods except the GK and RS measures in the 2005–2010 period,
where the return-driven relationship is only significant at the 7% level. For silver, we find significant evidence of a return-driven relationship for all sample periods for all SQ and RS volatility measures but find insignificant evidence for the GK measure in the 2000–2015, 2000–
2005 and 2010–2015 periods. We also find significant evidence of a volatility-driven relationship since all p-values are significant at the 5% level. That means that past volatility does add

* * *

**Table 4. The Granger causality test result p-values for the full sample and three subsamples of the return-volatility relationships.** ‘SQ’ denotes the
squared returns measure of volatility, ‘GK’ denotes the Garman-Klass measure and ‘RS’ denotes the Rogers-Satchell measure of volatility.

|  | 2000-2015 |  |  | 2000-2005 |  |  | 2005-2010 |  |  | 2010-2015 |  |  | RS |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | SQ | GK | RS | SQ | GK | RS | SQ | GK | RS | 2010-2015 |  |  | RS | SQ | GK |
| Panel A: Return-driven relationship |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| XAU | 0 | 0.02 | 0.02 | 0 | 0 | 0 | 0 | 0 | 0.07 | 0.07 | 0 | 0.04 | 0.01 |  |  |
| XAG | 0 | 0.72 | 0 | 0 | 0.12 | 0 | 0 | 0 | 0.03 | 0.01 | 0 | 0.78 | 0 |  |  |
| XPT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.01 | 0 | 0 |  |  |
| XPD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |
| Panel B: Volatility-driven relationship |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| XAU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.04 | 0.05 | 0 | 0 | 0 |  |  |
| XAG | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |
| XPT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |
| XPD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |

[https://doi.org/10.1371/journal.pone.0174232.t004](https://doi.org/10.1371/journal.pone.0174232.t004)

significant explanatory power of past returns in explaining current returns. This relationship is
consistent across sample periods and across measures for volatility. Therefore we provide evidence of a bi-lateral relationship between returns and volatility of precious metals, in that
returns and volatility both have strong explanatory power in explaining current volatility and
current returns.

### Discussion and conclusions

This study investigates the intraday periodicity, correlation and volatility interaction of
returns, volatility, volume and BAS that occur in 5-minute data for the key precious metals:
gold, silver, platinum and palladium. We study the intraday periodicity as well as the relationship between returns and volatility from 2000 to 2015, as well as in three subsamples to determine how the precious metals stylized facts have developed over time. These precious metals
are some of the most traded assets worldwide and they also play an important role for investors
as well as comprising an important asset for central banks. Given the increased attention
precious metals have received in the literature, the intraday dynamics are of great interest.

Initially, we show that the volume of trades of precious metals has increased substantially
over the last 15 years’ while the bid-ask spread has decreased indicating the increase in efficiency and liquidity of precious metal markets. We also show strong evidence of intraday periodicity of precious metals volume of trades and volatility. The intraday volume has increased
over time, while the intraday bid-ask spread has decreased over time. The narrowing of bid-ask
spreads and increased trading volume could partially be attributed to the global financial crisis
of 2007–2009 and the subsequent European sovereign debt crisis since market participants
may have chosen to gold as a safe haven or risk-hedging tool during this period (see \[46\] for
more details). We also study the interaction between volatility and returns of each precious
metal and our correlation analysis shows that returns are negatively correlated with the contemporaneous volatility and the previous 5-minute volatility. Furthermore, we find bi-directional Granger causality between volatility and returns suggesting that past volatility (returns)
offers significant explanatory power in explaining current returns (volatility).

### Author Contributions

**Conceptualization:** JB FM BL AU MP.

**Data curation:** MP AU.

* * *

**Formal analysis:** JB FM BL AU MP.

**Investigation:** JB FM BL AU MP.

**Methodology:** JB FM BL AU MP.

**Resources:** MP AU.

**Software:** AU.

**Supervision:** JB FM BL AU MP.

**Validation:** JB FM BL AU MP.

**Writing – original draft:** JB FM BL AU MP.

**Writing – review & editing:** JB FM BL AU MP.

### References

**1.** World Federation of Exchanges 2011 Annual Report. [http://www.world-exchanges.org/files/statistics/](http://www.world-exchanges.org/files/statistics/)
pdf/2011\_WFE\_AR.pdf

**2.** Report on global foreign exchange market activity in 2010. [http://www.bis.org/publ/rpfxf10t.pdf](http://www.bis.org/publ/rpfxf10t.pdf)

**3.** Hauptfleisch M., Putniņš T. J., & Lucey B. (2016). Who sets the price of gold? London or New York.
Journal of Futures Markets, 36(6), 564–586.

**4.** Lockwood L.J., Linn S. C. (1990). An examination of stock market return volatility during overnight and
intraday periods, 1964–1989. _Journal of Finance,_ 45, 591–601.

**5.** McInish T. H., Wood R. A., (1992). An analysis of intraday patterns in bid/ask spreads for NYSE stocks.
_Journal of Finance,_ 47(2), 753–764.

**6.** Evans K. P., Speight A. E. H. (2010). Intraday periodicity, calendar and announcement effects in Euro
exchange rate volatility. _Research in International Business and Finance,_ 24, 82–101.

**7.** Heston S. L., Korajczyk R. A., Sadka R. (2010). Intraday patterns in the cross-section of stock returns.
_The Journal of Finance,_ 65, 1369–1408.

**8.** Broussard J. P., Nikiforov A. (2014). Intraday periodicity in algorithmic trading. _Journal of International_
_Financial Markets, Institutions and Money,_ 30, 196–204.

**9.** Baillie R. T., Bollerslev T. (1991). Intra Day and Inter Market Volatility in Foreign Exchange Rates.
_Review of Economic Studies,_ 58, 565–585.

**10.** Ranaldo A. (2009). Segmentation and Time-of-Day Patterns in Foreign Exchange Markets. _Journal of_
_Banking and Finance,_ 33, 2199–2206.

**11.** Breedon F., Ranaldo A. (2013). Intraday Patterns in FX Returns and Order Flow. _Journal of Money,_
_Credit and Banking,_ 45(5), 953–965.

**12.** Chelley-Steeley P., Park K. (2011). Intraday patterns in London listed Exchange Traded Funds. _International Review of Financial Analysis,_ 20(5), 244–251.

**13.** McInish T. H., Wood R. A. (1990a). An analysis of transactions data for the Toronto Stock Exchange.
_Journal of Banking and Finance,_ 14, 441–458.

**14.** Brock W. A., Kleidon A. W. (1992). Periodic market closure and trading volume: A model of intra-day
bids and asks. _Journal of Economic Dynamics and Control,_ 16, 451–489.

**15.** Hamao Y., Hasbrouck J. (1993). Securities trading in the absence of dealers: Trades and quotes on the
Tokyo Stock Exchange. _The Review of Financial Studies,_ 8, 849–878.

**16.** Ellul, A., Shin, H. S., Tonks, I. (2002). Towards deep and liquid markets: Lessons from open and close
at the London Stock Exchange. LSE Financial Markets Group working Paper.

**17.** Cai X., Hudson R., Keasey K. (2004). Intraday bid-ask spreads, trading volume and volatility: Recent
empirical evidence from the London Stock Exchange. _Journal of Business Finance and Accounting,_
31, 647–676.

**18.** Naik, N., Yadav, P. K. (1999). The effects of market reform on trading costs of public investors: Evidence from the London Stock Exchange. Working paper, London Business School.

**19.** Wood A. R., McInish H. T., Ord K. (1985). An investigation of transactions data for NYSE stocks. _Journal of Finance,_ 40, 723–739.

* * *

**20.** McInish T. H., Wood R. A. (1990b). A transaction data analysis of the variability of common stock
returns during 1980–1984. _Journal of Banking and Finance,_ 14, 99–112.

**21.** Madhavan A., Richardson M., Roomans M. (1997). Why do security prices change? A transactions
level analysis of NYSE stocks. _Review of Financial Studies,_ 10, 1035–1064.

**22.** Caporin M., Ranaldo A., Velo G. (2015). Precious metals under the microscope: a high-frequency analysis. _Quantitative Finance,_ 15(5), 743–759.

**23.** Cai J., Cheung Y., Wong M. C. S. (2001). What moves the gold market? _Journal of Futures Markets,_
21, 257–278.

**24.** Baillie R. T., Han Y. Myers R. J., Song J. (2007). Long-memory models for daily and high-frequency
commodity future markets. _Journal of Futures Markets,_ 27(7), 643–668.

**25.** Khalifa A. A. A., Miao H., Ramchander S. (2011). Return distribution and volatility forecasting in metal
futures markets: Evidence from gold, silver and copper. _Journal of Futures Markets,_ 31(1), 55–80.

**26.** Black, F. (1976). Studies of stock price volatility changes, Proceedings of the meetings of the American
Statistical Association, Business and Economics Section, Chicago, 177–181.

**27.** Bekaert G., Wu G. (2000). Asymmetric volatility and risk in equity markets. _Review of Financial Studies,_
13, 1–42.

**28.** Bollerslev T., Litvinova J., Tauchen G. (2006). Leverage and volatility feedback effects in high-frequency data. _Journal of Financial Econometrics,_ 4, 353–384.

**29.** Dennis P., Mayhew S., Stivers C. (2006). Stock returns, implied volatility innovations, and the asymmetric volatility phenomenon. _Journal of Financial and Quantitative Analysis,_ 41, 381–406.

**30.** Giot P. (2005). On the relationships between implied volatility and stock index returns. _Journal of Portfolio Management,_ 26, 12–17.

**31.** Hafner R., Wallmeier M. (2007). Volatility as an asset class: European evidence. _European Journal of_
_Finance,_ 1, 1–27.

**32.** Chai E. F. L., Lee A. D., & Wang J. (2015). Global information distribution in the gold OTC markets.
_International Review of Financial Analysis,_ 41, 206–217.

**33.** Edwards A. K., Harris L. E., & Piwowar M. S. (2007). Corporate bond market transaction costs and
transparency. _Journal of Finance,_ 62(3), 1421–1451.

**34.** Loon Y. C., & Zhong Z. K. (2016). Does Dodd-Frank affect OTC transaction costs and liquidity? evidence from real-time CDS trade reports. _Journal of Financial Economics,_ 119(3), 645–672.

**35.** Murray S. (2011). Loco London Liquidity Survey. _The Alchemist,_ 63, 9–10.

**36.** Goodhart C. A. E., O’Hara M. (1997). High frequency data in financial markets: Issues and applications.
_Journal of Empirical Finance,_ 4, 73–114.

**37.** Anderson T. G., Bollerslev T., Cai J. (2000). Intraday and interday volatility in the Japanese stock market. _Journal of International Financial Markets, Institutions and Money,_ 10, 107–130.

**38.** Hol, R., Koopman, J. (2002). Stock index volatility forecasting with high frequency data. Tinbergen Institute Discussion Papers. 02-068/4.

**39.** Koutmos G., Martin A. D. (2011). Currency bid-ask spread dynamics and the Asian crisis: Evidence
across currency regimes. _Journal of International Money and Finance,_ 30, 62–73.

**40.** Garman M., Klass M. (1980). On the estimation of security price volatiles from historical data. _Journal of_
_Business,_ 53, 67–78.

**41.** Rogers L., Satchell S. (1991). Estimating variance from high, low, and closing prices. _Annuals of Applied_
_Probabilities,_ 1, 500, 512.

**42.** Rogers L., Satchell S., Yoon Y. (1994). Estimating the volatility of stock prices: a comparison of methods that use high and low prices. _Applied Financial Economics,_ 4, 241–247.

**43.** Figlewski, S., Wang, X. (2000). Is the Leverage Effect still a Leverage Effect? Working Paper Series
00–37 (New York University).

**44.** Jain A., Biswal P. C., Ghosh S. (2016). Volatility-volume causality across single stock spot-futures markets in India. _Applied Economics,_ 48(34), 3228–3243.

**45.** Granger C. W. J. (1969). Investigating causal relations by econometric models and cross-spectral methods. _Econometrica,_ 37(3), 424–438.

**46.** Wang G. J., Xie C., Jiang Z. Q., Stanley H. E. (2016). Extreme risk spillover effects in world gold markets and the global financial crisis. _International Review of Economics & Finance,_ 46, 55–77.