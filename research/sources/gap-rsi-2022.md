Source: https://www.sciencedirect.com/science/article/pii/S0960077921010304
Title: Intraday Trading of Precious Metals Futures Using Algorithmic Systems - ScienceDirect
Fetched: 2026-10-01T12:01:28.189Z

[Skip to main content](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#main) [Skip to article](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#article)

[![Chaos, Solitons & Fractals](https://ars.els-cdn.com/content/image/1-s2.0-S0960077921X00136-cov200h.gif)](https://www.sciencedirect.com/journal/chaos-solitons-and-fractals/vol/154/suppl/C)

## [Chaos, Solitons & Fractals](https://www.sciencedirect.com/journal/chaos-solitons-and-fractals "Go to Chaos, Solitons & Fractals on ScienceDirect")

Date:January 2022

Article:111676

Volume:[Volume 154](https://www.sciencedirect.com/journal/chaos-solitons-and-fractals/vol/154/suppl/C "Go to table of contents for this volume/issue")

View accessibility information

## Published by:Elsevier

### Published by

[![Elsevier](https://www.sciencedirect.com/us-east-1/prod/08bcf77e921828c5a59334cdb2949dd973632719/image/elsevier-non-solus.svg)](https://www.sciencedirect.com/journal/chaos-solitons-and-fractals "Go to Chaos, Solitons & Fractals on ScienceDirect")

Show more

Research article

[Get rights and content](https://s100.copyright.com/AppDispatchServlet?publisherName=ELS&contentID=S0960077921010304&orderBeanReset=true)

# Intraday Trading of Precious Metals Futures Using Algorithmic Systems

Author links open overlay panelCohenGil

Show more

Cite

Add to Mendeley

Share

[10.1016/j.chaos.2021.111676](https://doi.org/10.1016/j.chaos.2021.111676)

[Access through **your organization**](https://www.sciencedirect.com/user/institution/login?targetUrl=%2Fscience%2Farticle%2Fpii%2FS0960077921010304) [Purchase PDF](https://www.sciencedirect.com/getaccess/pii/S0960077921010304/purchase)

More actions

## Article preview

- [Abstract](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#abstracts)
- [Introduction](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#introduction)
- [Section snippets](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#section-snippets)
- [References (27)](https://www.sciencedirect.com/science/article/abs/pii/S0960077921010304#references)

## Highlights

- •
In this research we designed and optimized artificial intelligence (AI) trading systems for intraday trading of five precious metals.

- •
We adopt two technical tools that are known to be useful trading stocks, to short term commodities price trends detecting. Relative strength index and keltner channels.

- •
We optimized the setting of our system using particle swam optimization (PSO) which helped us to conduct complex optimization with multiple objectives and under many constraints' variables.

- •
We find that the RSI system outperformed the B&H returns for Gold, Silver, platinum and palladium and was beaten by the B&H returns for copper trades. The system has delivered 106.2%, 63.7%, 22.4% and 326.3% excess returns for Gold, Silver, platinum and palladium.

- •
Both RSI and KC AI systems have been proven to be able to trade profitably precious metals with both long and short positions, in most cases the system performed better in for long trades than for short trades.


## Abstract

In this research we designed and optimized Artificial Intelligence (AI) trading systems for intraday trading of five precious metals. We used data from the beginning of 2020 till the end of September 2021 to design and optimize trading systems using Relative Strength Index (RSI) and Keltner Channels (KC) oscillators. Our prime optimization tool was Particle Swam Optimization (PSO) which helped us to conduct complex optimization with multiple objectives and under many constraints' variables. We find that the RSI system outperformed the B&H returns for Gold, Silver, Platinum and Palladium and was beaten by the B&H returns for Copper trades. The system has delivered 106.2%, 63.7%, 22.4% and 326.3% excess returns for Gold, Silver, Platinum and Palladium. Sixty minutes bars with 1.5 Average True rang Multiplier (MATR) have been found to be a fruitful configuration for the KC system trading Gold, Silver and Palladium providing better trading returns than the B&H strategy, by 64.72%, 58.5% and 310.25%, respectively. Both RSI and KC AI systems have been proven to be able to trade profitably precious metals with both long and short positions, in most cases the system performed better in for long trades than for short trades.

## Keywords

Precious Metals

;

Gold

;

Silver

;

Algorithmic Trading

;

Futures

- [Previous article in this issue](https://www.sciencedirect.com/science/article/pii/S096007792101002X)
- [Next article in this issue](https://www.sciencedirect.com/science/article/pii/S0960077921010419)

## Introduction

The global precious metal market value was valued at 193.3$ billion in 2020 and is expected to grow at a compound annual growth rate of 9% in terms of revenue from 2020 to 2027.1 Gold and Silver are the leaders of that market followed by Copper, Platinum and Palladium. Precious metals were traditionally considered as inflation hedging tools and they also served as \`\`safe haven'' against stocks market crash. And as such their link to inflation and other hazards have been thoroughly investigated (see for example: Chebbi, 2020). Past researchers have use Artificial Intelegence (AI) systems to try to predict precious metals price trends. However, not much evidence has been gathered concerning algorithmic trading systems designed for intraday futures in general and particularly precious metals futures. The main objectives of the following research is to fill that gap of knowledge and examine whether short term price of precious metals can be predicted and which tools should be used for that process. The short term precious metals price prediction is important not only to precious metals traders but also to managers of stocks and currencies portfolios. Moreover, the short term price movment of precious metals can indicate on general economic imbalance concernig other risky assets such as stocks, bonds and real estate.

The following research uses Machin Learning (ML) algorithmic trading strategies that use the Relative Strength Index (RSI) oscilator and Keltner Channels (KC) as our primary technical tool. We utilize different setups of these tools to achieve best preformance of the AI systems. In recent years investors have realized that AI systems are a necessary tools to process efficiently huge amount of financial data and replace many hours of human analysis. That data is consisted of financial market data and social media data. Researchers have realized that the financial markets are highly responsive to social media influences and therefore developed deep learning models that can be used to extract incredible information that buried in a Big Data.

Intraday In the financial world describe securities that trade on the markets during regular business hours. Traders pay close attention to intraday price movements by using real-time charts to benefit from short-term price fluctuations. The advantage of intraday trading is that it is not exposed to afterhours news that can change price direction dramatically. Such news includes vital economic and earnings reports, as well as broker upgrades and downgrades that occur either before the market opens or after the market closes. Intraday trading relies heavily on algorithmic trading and AI machine learning since speed and accuracy is essential in such fast dynamic environment. Not many researches have analysed different trading strategies suitable to precious metal trading systems. Chinn and Coibion \[1\] documented a significant differences both across and within commodity groups. Precious metals fail most tests of unbiasedness and are poor predictors of subsequent price changes but energy and agricultural futures fare much better. These finding of Chin and Coibion motivated us to search for algorithmic systems that will be able to predict intraday prices of precious metals. For that reason, we designed and optimize three algorithmic trading systems suitable for precious metal futures trading. Our system is based on advanced trading startegies that have never been examined before for intraday metals price prediction.

The Relative Strength Index (RSI) is a momentum indicator developed by Welles Wilder \[2\], which compares the magnitude of recent gains and losses over a specified period to measure speed and change of price movements of a security. This technical oscillator was proven to be an effective tool for stocks trading for different time frame. For example, Bhargavi et al. \[3\] concluded that the RSI can be effectively used in the construction of portfolio. It can be used both for short term investment and long-term investment. It accurately predicts the buy and sells signals for different stocks. The Keltner Channel (KC) strategy was first introduced by Chester Keltner in the 1960s. The original formula used simple moving averages (SMA) and the high-low price range to calculate the bands. In the 1980s, a new formula was introduced that used Average True Range (ATR), as measures of volatility. KC formulate graphic channels that enable AI system to recognize and preform actual trading. However, because of its optimization complexity it is seldomly used by AI systems for intraday trading tasks. We designed two trading systems using RSI and KC algorithms and optimized their setups using Particle Swarm Optimization (PSO) for best trading performances and tested their ability to forecast intraday price trends of five major precious metals: Gold, Silver, Copper, Platinum and Palladium.

## Organizational access

Get full-text access by signing in with your organisation [Access through **your organization**](https://www.sciencedirect.com/user/institution/login?targetUrl=%2Fscience%2Farticle%2Fpii%2FS0960077921010304)

### Other access options

[Purchase PDF](https://www.sciencedirect.com/getaccess/pii/S0960077921010304/purchase)

[Need help with access?](https://service.elsevier.com/app/answers/list/c/10543/supporthub/sciencedirect/)

## Section snippets

### Literature review

ML and Big Data has become popular research tool for locating and trading securities. Those algorithms usually but not exclusively combine financial data that were extracted from the financial markets with social media data. Liu \[4\] investigate whether content from social media has differential impacts on stock performance. They collected a large dataset of 84 million tweets and 8 years of stock data for 407 companies from the S&P500 index and found that while consumers' positive sentiment does

### Data and methodologies

In the following research we construct and optimize two intraday algorithmic trading systems that are based on RSI and KC. Our data is consisted of minute-by-minute price data of five major precious metals futures: Gold, Silver, Copper, Platinum and Palladium from the beginning of 2020 till the end of September 2021. The data base is set in different time frames bars2

### Results

We start the result section by looking at descriptive statistic of the five precious metals from the beginning of 2020 till the end of September 2021 (Table 1).

Table 1 show that the highest B&H return from the beginning of January 2020 till the end of September 2021 was recorded for copper (47.75%) while the lowest was for palladium (−14%). The B&H returns will be compared to the returns to our AI systems returns. We also record that silver has the highest daily volatility while gold has the

### Conclusions and implications

In this research we designed and optimized AI trading systems for intraday trading of precious metals. We used minute by minute data from the beginning of 2020 till the end of September 2021 to design and optimize trading systems using RSI and KC oscillators. Our prime optimization tool was PSO which helped us to conduct complex optimization with multiple objectives and under many constraints' variables. We start the optimization process using the setups that are usually used to trade stocks

## Declaration of Competing Interest

There are no competing interests financial or non-financial associated with this paper. No financial funder to be reported.

## References (27)

- X. Liu

### [Target and position article - Analyzing the impact of user-generated content on B2B Firms' stock performance: big data analysis with machine learning methods](https://www.sciencedirect.com/science/article/pii/S0019850118305029)




### Indust Mark Manag



(2020)

- J.A. Batten _et al._

### [The macroeconomics determinants of volatility in precious metals markets](https://www.sciencedirect.com/science/article/pii/S0301420709000543)




### Resour Policy



(2010)

- Y. Zheng

### [The linkage between aggregate investor sentiment and metal futures returns: a nonlinear approach](https://www.sciencedirect.com/science/article/pii/S1062976915000277)




### Q Rev Econ Finance



(2015)

- J. Elder _et al._

### [Impact of macroeconomic news on metal futures](https://www.sciencedirect.com/science/article/pii/S0378426611001968)




### J Bank Financ



(2012)

- D. Bosch _et al._

### [The impact of speculation on precious metals futures markets](https://www.sciencedirect.com/science/article/pii/S0301420715000227)




### Resour Policy



(2015)

- S.H. Kang _et al._

### [Dynamic spillover effects among crude oil, precious metal, and agricultural commodity futures markets](https://www.sciencedirect.com/science/article/pii/S0140988316303577)




### Energ Eco



(2017)

- S. Lyócsa _et al._

### [Exploiting dependence: day-ahead volatility forecasting for crude oil and natural gas exchange-traded funds](https://www.sciencedirect.com/science/article/pii/S0360544218308193)




### Energy



(2018)

- S. Torbat _et al._

### [A hybrid probabilistic fuzzy ARIMA model for consumption forecasting in commodity markets](https://www.sciencedirect.com/science/article/pii/S031359261730067X)




### Econ Anal Policy



(2018)

- J. Wang _et al._

### [Crude oil price forecasting based on internet concern using an extreme learning machine](https://www.sciencedirect.com/science/article/pii/S0169207018300748)




### Int J Forecast



(2018)

- M.D. Chinn _et al._

### The predictive content of commodety futures




### J Futures Mark



(2013)


J.W. Wilder

### New concept of Technical Trading Systems

### Trend Res

(1978)

Gumparathi S BhargaviR _et al._

### Relative Strength Index for Developing Effective Trading Strategies in Constructing Optimal Portfolio

### Int J App Eng Res

(2017)

S. Sohangir _et al._

### Big Data: deep Learning for financial sentiment analysis

### J Big Data

(2018)

View more references

[View full text](https://www.sciencedirect.com/science/article/pii/S0960077921010304)

## Recommended articles

### Based on reading popularity

- Research article



[Calendar effect and in-sample forecasting](https://www.sciencedirect.com/science/article/pii/S0167668720301359)

EnnoMammen, …, MichaelVogt

Insurance: Mathematics and Economics • Volume 96 • 2021 • Pages 31-52

- Research article



[Bollinger bands approach on boosting ABC algorithm and its variants](https://www.sciencedirect.com/science/article/pii/S1568494616304173)

BarışKoçer

Applied Soft Computing • Volume 49 • 2016 • Pages 292-312

- Research article



[Dynamic impact of China's stock market on the international commodity market](https://www.sciencedirect.com/science/article/pii/S0301420717305858)

ShaoboWen, …, XueyongLiu

Resources Policy • Volume 61 • 2019 • Pages 564-571

- Research article



[Do precious metal spot prices influence each other? Evidence from a nonparametric causality-in-quantiles approach](https://www.sciencedirect.com/science/article/pii/S0301420717302477)

VaneetBhatia, …, Haslifah M.Hasim

Resources Policy • Volume 55 • 2018 • Pages 244-252

- Research articleOpen access



[Modelling time varying volatility spillovers and conditional correlations across commodity metal futures](https://www.sciencedirect.com/science/article/pii/S105752191730176X)

MenelaosKaranasos, …, RajatNath

International Review of Financial Analysis • Volume 57 • 2018 • Pages 246-256

- Short communication



[Hybrid models for intraday stock price forecasting based on artificial neural networks and metaheuristic algorithms](https://www.sciencedirect.com/science/article/pii/S0167865521001239)

Kumar ChandarS

Pattern Recognition Letters • Volume 147 • 2021 • Pages 124-133


## Cited by (10)

- Research article



[A non-ferrous metal price ensemble prediction system based on innovative combined kernel extreme learning machine and chaos theory](https://www.sciencedirect.com/science/article/pii/S0301420722004184)

Guo H., …, Zhang L.

Resources Policy • Volume 79 • 2022 • Article 102975





Citation Excerpt:



In this paper, the historical data of metal price is used for modeling, but the metal price is often affected by other factors such as exchange rate (Pincheira Brown and Hardy, 2019; Pincheira-Brown et al., 2022) and oil price (Jain and Ghosh, 2013; Ciner, 2017). In the future, we can introduce multivariable and multifactor into the machine learning model to predict the metal price, and reasonably solve the error accumulation caused by the multivariable model, which will be the direction Sresting research direction to analyze how accurate metal price prediction will be transformed into trading strategy and what impact it will have on investors' buying and shorting (Gil, 2022; Auer, 2016). Accurate and timely non-ferrous metal price prediction is very essential for financial investors, futures researchers and decision makers to make informed decisions.




Show abstract




Non-ferrous metal futures, as a significant component of the financial market, are complementary and coordinated with other financial elements, which has been a key area of research in recent years. However, given the apparent volatility and chaotic nature of the non-ferrous metal price sequence, forecasting it remains a difficult challenge. While prior research employed a variety of methodologies to forecast metal prices, they overlooked the critical role of chaos feature analysis and the necessity of error analysis, severely limiting prediction accuracy. This paper designs a novel non-ferrous metal price ensemble prediction system that incorporates data decomposition, phase space reconstruction, multi-objective optimization, point prediction, and interval prediction. A combined kernel extreme learning machine based on the improved multi-objective lion swarm optimization algorithm is developed and theoretically explained to improve prediction accuracy and reliability. Additionally, the appropriate creation of the prediction interval based on the best-fit distribution of the point prediction error enabled the examination of various levels of uncertainty. In an empirical experiment using copper and aluminum prices from the London Metal Exchange, the proposed system demonstrated benefits in point and interval prediction, providing decision makers with useful prediction references.

- [Enhancing Trading Strategies: A Multi-indicator Analysis for Profitable Algorithmic Trading](http://www.scopus.com/scopus/inward/record.url?partnerID=10&rel=3.0.0&view=basic&eid=2-s2.0-85200333155&md5=56d23b26ad4cee12427be3ef998f7)

Sukma N., Namahoot C.S.

Computational Economics • Volume 65 • 2025 • Article 111676

- [An Algorithmic Trading Approach Merging Machine Learning With Multi-Indicator Strategies for Optimal Performance](http://www.scopus.com/scopus/inward/record.url?partnerID=10&rel=3.0.0&view=basic&eid=2-s2.0-85212314418&md5=f29bfc09b89367429798082c1fca52c)

Sukma N., Namahoot C.S.

IEEE Access • Volume 12 • 2024

- [Technical Analysis in Investing](http://www.scopus.com/scopus/inward/record.url?partnerID=10&rel=3.0.0&view=basic&eid=2-s2.0-85162795101&md5=188adfab89596bf9375a71bcab435f)

Cohen G.

Review of Pacific Basin Financial Markets and Policies • Volume 26 • 2023 • Article 2350013

- [Portfolio Hedging Strategy-Metals and Commodities](http://www.scopus.com/scopus/inward/record.url?partnerID=10&rel=3.0.0&view=basic&eid=2-s2.0-85172315342&md5=77bfb435557ef41982a40f9ecb839b1)

Užík M., …, Dizaye H.

Acta Montanistica Slovaca • Volume 28 • 2023

- [Algorithmic Trading and Financial Forecasting Using Advanced Artificial Intelligence Methodologies](http://www.scopus.com/scopus/inward/record.url?partnerID=10&rel=3.0.0&view=basic&eid=2-s2.0-85138617969&md5=44f6e57658d2549124a32c231a947ad)

Cohen G.

Mathematics • Volume 10 • 2022 • Article 3302


[View all citing articles on Scopus](http://www.scopus.com/scopus/inward/citedby.url?partnerID=10&rel=3.0.0&eid=2-s2.0-85120712653&md5=c029ed0e9e7749787a79120242f68f6)

## Metrics

### Citations

- Citation Indexes10

### Captures

- Mendeley Readers25

![PlumX Metrics Logo](https://cdn.plu.mx/3ba727faf225e19d2c759f6ebffc511d/plumx-logo.png)[View details](https://plu.mx/plum/a/?doi=10.1016%2Fj.chaos.2021.111676&theme=plum-sciencedirect-theme&hideUsage=true)

© 2021 Elsevier Ltd. All rights reserved.

Persistent link using digital object identifier (DOI)

The Identity Selector: Persistence Service