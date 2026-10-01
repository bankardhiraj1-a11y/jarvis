Source: https://www.diva-portal.org/smash/get/diva2:845497/FULLTEXT01.pdf
Title: Microsoft Word - thesis remake 12.06.docx
Fetched: 2026-10-01T11:48:36.049Z

!

# INTRADAY MOMENTUM

## Day trading on the gold futures market using Opening Range Breakouts and GARCH

### Tobias Sönnert

**Umeå School of Business and Economics** Autumn senester 2014/2015 Bachelor thesis, 15 ECTS Bachelors Program of Business and Economics !

---

# ACKNOWLEDGEMENTS

! I want to show my gratitude to my supervisors and to the people who has been helping me along this work. Firstly, Tomas Sjögren, for his help and proficiency in guiding me in the right direction. Secondly, Christian Lundström especially for his useful tips and insights taken from his previous occupational experience within asset management Thirdly, Priyantha Wijayatunga for his support regarding the statistical-modelling. Lastly, I would also like to acknowledge the product specialists and the customer support of Thomson Reuters concerning their assistance.

! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !

---

# ABSTRACT

Are financial markets always efficient, or do securities show signs of deviating from a random walk? In this paper we investigate the occurrence of intraday momentum by backtesting profitability of the Opening Range Breakout (ORB) strategy. The study is based on gold futures time series data from! 2009-05-15 to 2014-11-11. The dataset is compiled of historical daily High, Low, Open and Close price data from the New York Mercantile Exchange. The ORB strategy utilizes predetermined upper and lower bound thresholds. Within these thresholds the ORB trader does not get any trading signals and no positions are considered. When the price breaks a threshold, a trading signal is issued. The hypothesis states that when the upper (lower) threshold is crossed the price is likely to continue upwards (downwards) signalling to the trader to enter a long (short) position. The ORB trader faces the query of when the intraday momentum is supposed to occur and hence how to set the thresholds. Additionally we want to investigate whether or not a flexible threshold, dependent on volatility forecasting from a GARCH model, will yield better results than a fixed threshold strategy. The results suggest that an application of Opening Range Breakouts could be profitable with the use of narrow thresholds. The specific strategy developed shows considerably higher returns than zero as well as significantly higher returns relative to the underlying asset. Comparing the Sharpe ratio of the developed strategy and the underlying asset showed that the ORB strategy also performed better than the underlying asset measured in risk adjusted terms. Further, the results imply that gold futures are affected by momentum and can deviate from a random walk. Still, no indications of momentum being affected by volatility were found since the strategy of ORB with volatility adjusted thresholds did not yield any better results than the “regular” ORB.

! !

! **Keywords:*** *Momentum,) volatility,) ORB,) GARCH,) Efficient) market) hypothesis,) random) walk,) Gold)* *futures,)intraday)trading,)technical)analysis,)VaR,)Sharpe)ratio)*

---

# TABLE OF CONTENTS)

## 1. INTRODUCTION…………………………………………….1

1.1 BACKGROUND……………………………………………… 1
## 2. THEORY…………………………………………………………. 6

2.1 THEORETICAL FOUNDATION……………………………. 6
## 3. METHODOLOGY…………………………………………... 8

3.1 OPENING RANGE BREAKOUTS………………………….. 8
3.2 GARCH………………………………………………………	12
3.3 THE SHARP RATIO………………………………………...	16
3.4 VALUE AT RISK……………………………………………	17
3.5 STATISTICAL TESTING…………………………………... 18

## 4. DATA……………………………………………………………. 19

4.1 FINANCIAL INSTRUMENTS……………………………... 19
4.2 GOLD FUTURES CONTRACTS…………………………... 20
4.3 TIME PERIOD………………………………………………. 21
4.4 OPEN-HIGH-LOW-CLOSE………………………………… 23
## 5. RESULTS AND ANALYSIS………………………….24

5.1 THE ORB STRATEGY…………………………………….. 24
5.2 THE VOLATILITY ADJUSTED ORB STRATEGY……… 29
5.3 POSSIBLE ERRORS……………………………………….. 31
## 6. DISCUSSION……………………………………………… ... 33

6.1 CONCLUSIONS……………………………………………. 33
6.2 SUGGESTIONS FOR FURTHER RESEARCH….…..… ... 34
## 7. REFERENCES………………………………………………. 35

---



---

# 1. INTRODUCTION

1.1 BACKGROUND Asset prices follow a random walk and mechanical trading rules are useless as predictions of future price movements. These are the implications of The Efficient Market Hypothesis (EMH) (Fama, 1965, 1970), but are they accurate? The question of market efficiency has been a major debate topic among both researchers and investors for decades. During these years, studies showing both support (e.g., Malkiel
1973), and reject (e.g., Jegadeesh and Titman, 1993) of the hypothesis has been found. Despite comprehensive research within the field there is still no consensus. A random walk implies that asset prices evolve at random. Any returns generated are therefore also random. An investor who is continuously generating profits can thus be seen as a contradiction of EMH. Whether you are a long-term investor, a professional
1 day trader or a fund manager your primary objective should be to beat the market. The risk averseness deviates among these different market participants, hence the definition of beating the market deviates as well. Beating the market can be defined as generating higher profits at the same risk or the same profits at lower risk than a market benchmark.

Consequently, predicting movements of financial assets prices in order to beat the market would only be possible if deviations from a random walk actually occur. According to the theory of efficient markets the price of an asset will only fluctuate around an equilibrium price whereby new market-relevant information is the only thing that should change the equilibrium price itself. Accordingly, an investment strategy based on historical price movements can be seen as a comprehensive way of testing EMH. In previous papers of this kind we find the already mentioned Jegadeesh and Titman (1993) who introduces the concept of momentum with an application to the financial markets. Their method used to test for momentum was develop a strategy based on technical analysis.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !The expression of beating the market is often referred to achieving greater results than a benchmark (e.g. a stock index).!

! 1! !

---

The short version of momentum can be explained  by the,  to industry people wellknown expression; “let the winners ride and cut the losses short”. The expression is 
taken from  the pioneering technical analyst and speculator Jesse Livermore. What 
Livermore implies is that an investor can gain profits by selling non-profitable assets 
and keeping the profitable once. A momentum-investor seeks to pinpoint significant 
movements in asset prices. An occurrence of momentum would imply that rising 
prices tends to continue to rise and falling prices to keep falling. Analogous with 
Holmberg, Lönnbark and Lundström (2013) this paper aims to study the profitability 
2
of an intraday momentum strategy. With the use of technical trading rules the 
intraday strategy will be developed. The study is limited to the commodity futures 
3
market by applying backtesting of gold futures during 2009-05-15 and 2014-11-11. 
4
The approach here is to enter both long and short trades on an intraday basis. To 
evaluate the overall performance of the strategy not only returns will be analysed but 
also the risk associated with the strategy. The structure of a futures contract is what
makes it possible for the investor to not only earn profits from price-increases but also 
from price-decreases. The specifics of futures contracts in general and gold futures in 
particular will be explained in chapter 4.2.

Even though an investor would accept the existence of momentum, the difficulty of 
localizing it remains. For the ORB investor this implies that the placement of 
thresholds is an issue that has to be dealt with. In this paper we investigate the

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
2!An intraday-strategy implies a strategy where the trader uses the price-fluctuations during a day!
3!Backtesting is the process of applying a strategy back in time to see how the outcome would have 
been!
4!Long trades refers to trades where and investor tries to make money by buying low and selling high,

4!Long trades refers to trades where and investor tries to make money by buying low and selling high, 
short trades works in the opposite way where the investor speculates in falling prices!

---

possible improvement of adjusting the thresholds to the expected price fluctuation (volatility) of a day compared to the “regular” ORB strategy. The hypothesis here is that the volatility will affect the random walk of a day. The reasoning behind this is that days with higher volatility imply larger natural fluctuations in a random walk. With the stated hypothesis in mind, the application will be to use larger thresholds when higher volatility is expected. Even though the method used here is very specific, there is recent research confirming the importance of being able to incorporate price fluctuations (Pindyck R.S. 2004).

The justification of the momentum-effect is often linked to the field of behavioural finance. A selected few of the various different theories included within the area will be clarified in chapter 2.1, but for now, we are content with a quotation:

*"!Economics seeks to be a science. Science is supposed to be objective and it is* *difficult to be scientific when the subject matter, the participant in the economic* *process, lacks objectivity." – George Soros*

By this quotation Soros refers to the, to him irrational reasoning behind EMH, stating that EMH could have been true if it was not to all the irrational investors. Irrationality of other investors would open up a gap in the random walk and make room for e.g. a momentum-investor to make money. By evaluating the profitability of the ORB strategy, the potential momentum effect and thereby the efficiency of gold futures will be tested. To pin down the purpose of the study we state two questions. We will answer question (i) by evaluating the performance of the ORB strategy whereas question (ii) will be answered by evaluating the performance of implementing volatility-adjusted thresholds to the ORB strategy (modelled by GARCH).

(i) Can we find indications of intraday momentum in the gold futures market? (ii) Can we find indications of intraday momentum being influenced by the forecasted volatility? In addition to the questions stated above, we wish to frame the prerequisite and alternatives of a short-term investor, acting on a commodities market. ! 3!
!

---

As stated earlier, previous research has shown empirical evidence of momentum in 
financial markets (see e.g. Jegadeesh and Titman, 1993; Daniel et al. 1998). In a more 
recent paper, researchers find a linkage between abnormal returns and the skilfulness 
of an investor (Coval et al, 2005), rationalizing the relatively small group of investors 
being able to continuously beat the market. EMH believers on the other hand
rationalise the group of successful investors as lucky investors that can be seen as 
5
outliers since the group is still relatively small (Malkiel 1996; Statman, 2002).

One of the most recent papers investigating the profitability of ORB is focusing on
crude-oil futures during 2001 and 2011 (Holmberg, Lönnbark and Lundström 2013). 
In this paper we investigate the profitability and risk associated with an ORB strategy 
applied to gold futures during  2009 and 2014, which makes this work contribute to 
research within this area. The link between profitability of a strategy and the ability to 
forecast volatility is not a new one (see Merton 1980; French, Schwert, and 
Stambaugh, 1987). The choice of model used to forecast the volatility could of course 
be essential to the final results of the ORB strategy with volatility-adjusted ranges, 
since the alternatives are many.

In derivatives forecasting the estimation of volatility is essential since it is used  to 
determine a theoretical price. In the options market the Black-Scholes Model, 
originally developed by Black and Scholes (1973) is the most common one. Looking 
at the futures market there are a variant where you price options on futures contracts 
called  The Black-76 Model (Black, 1976). The inventive trader can find usage of 
these models (Black-Scholes in particular) in reverse to calculate the implied 
6
volatility . These calculations can then be used to forecast future volatility given the 
derivatives present price. Analogous to a volatility-comparable study from 1992 we 
choose the GARCH model over the Black-Scholes, which in that particular paper is 
stated to be the superior model for forecasting (Day and Lewis 1992). A specific 
linkage between the ORB strategy and intraday volatility is shown in a recent paper 
(Lundström 2013). The sub question testing the possible improvement of letting 
volatility decide the thresholds of the ORB strategy can be seen as an extension of

5!An outlier is a statistical term described as an observation with large deviation of others in the same 
set of data. Few outliers is said to not affect the comprehensive picture when analysing the data!
6!The implied volatility is the estimated volatility regarding the price of a security that paper. By the use of GARCH modelling we will investigate if the trader can profit from this linkage found.

The outline for the paper is the following: Chapter 2 gives a brief introduction to some of the most substantial theories connected to the paper. Chapter 3 will go 7 through the two trading tools used to develop the model (ORB, GARCH) and further explain how the strategy has been developed. In chapter 4 the data, time period and choice of financial instrument will be declared. In Chapter 5 the results and analysis to the results will be displayed. Finally, chapter 6 will include a concluding discussion and give suggestions for further research.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !The conception of trading-tools is what navigates the trader to different decisions. In the example above tools used to create the strategy are shown!

! 5! !

---

# 2. THEORY

2.1 THEORETICAL FOUNDATION The concept of market-efficiency and the theory of Efficient Market Hypothesis have already been introduced. However, the underlying assumptions of EMH are much more elaborate than what has previously been declared. Given an efficient market, price movements would be completely random, evolving in so-called martingales. A martingale process is a sequence of independent variables where the next variable over time is estimated to be the same as the current, plus/minus an error term, regardless of any previous variables. This implies that the error term is the only determining factor of the next variable. Per definition the error term cannot be calculated meaning the process is random. Despite the theory of the efficient market, investors constantly seek to find opportunities where profits can be made. If the market were to deviate from the martingale process, investors would see this as an
8 opportunity for profit. The potentially mispriced assets would therefore be eliminated keeping the market “correctly priced” and impossible to forecast.

9 A market without information bias is unpredictable (Fama, 1979). There are, however, three different levels of efficiency. The Weak form of efficiency is characterized by a climate where all historical market relevant information is fully reflected in the market price. The semi-strong form of efficiency requires that not only the weak form holds but also that the price effect of all publicly announced news, such as economical and geopolitical news is considered. The strong form of efficiency requires that earlier information criteria’s are fulfilled but also that no information bias in the form of sector- and/or insider information is present.

As previously stated the efficiency of gold futures is tested through a trading strategy. The substance of the strategy is what determines what form of efficiency is tested for. Since the strategy is only based on historical price changes, the weak form of efficiency is what is tested for. The assumption of market efficiency is a requirement for many asset-pricing theories found within financial economics. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !Mismatching!the!intrinsic!value!of!an!asset! !One part possess more relevant information than the other, creating an evident advantage

! 6! !

---

One of these theories is the modern portfolio theory (MPT). This theory implies that there is a clear relationship between risk and expected return (Markowitz, 1952). Through his book, Markowitz explains how an investor can abate risk by creating a diversified portfolio with various assets. As a further development of MPT the Capital Asset Pricing Model (CAPM) was created by Jack Treynor (1961,1962), William Sharpe (1964), John Lintner (1965) and Jan Mossin (1966). CAPM is supposed to visualize to an investor what the rate of return of an asset should be considering its 10 systematic risk and can also be used to estimate the price of a certain asset. The CAPM model is based on assumptions of rational investors and perfect market conditions. In most cases the CAPM model does provide a decent estimate of asset prices, however deviations from the CAPM model do occur. These deviations are most likely due to behavioural finance. Behavioural finance seeks to explain the seemingly irrational movements observed in financial markets.

One of the major theories of behavioural finance is overreaction. Overreaction states that price movements of financial assets tend to be exaggerated, creating momentum before finding balance (Daniel et al., 1998). The reasoning behind overreaction can be linked to a weak point of an investor called herd instinct. Herd instinct, is when an investor acts without the use of own reasoning. A significant example of this is the dot-com bubble, which had its peak during the year of 2000. During this time many investors were buying highly overvalued telecom-stocks with no actual value simply because a majority of the market was doing the same thing. In an intraday view, a behavioural economist would link daily positive momentum to herd instinct as well. While negative momentum could be linked to frightened investors ending their positions, increasing the price-fall. As the appearance of overreaction and herd instinct indicates irrational behaviour, it is a clear violation of EMH. Other researchers mean that the occurrence of momentum is due to imperfect information (Crombez, 2001), this, also a clear contradiction of EMH. Despite behavioural finance, many unexplained phenomenon of financial markets still remain. These phenomenon are known as anomalies. A common example of an anomaly is the January effect; the fact that securities not performing well before the end of the year tend to outperform the market in January. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !Often referred to as market risk or undiversifiable risk since it is the underlying risk of a market, which one cannot escape. In econometric terms denoted as beta!

! 7! !

---

# 3. METHODOLOGY

3.1 OPENING RANGE BREAKOUTS The theoretical background of Opening range breakouts (ORB) can be derived back to 1990 when the instigator of ORB; Toby Crabel first presented this concept. Crabel demonstrated a new approach of how to gain profits trading futures on an intraday basis. An ORB strategy can be seen as a type of Long/short strategy, a concept often used by hedge funds. A long/short strategy is a strategy, which typically implicates to take long positions in securities expected to increase and short positions in securities expected to decrease. Here we focus on gold futures entering long positions when the price is expected to increase and short positions when a price decrease is expected. The specific use of ORB can deviate between investors concerning the placement of thresholds but also regarding timespan, despite this the framework of the strategy stays the same (Crabel 1990). As long as the price does not break a threshold we let the price fluctuate without acting but when the upper (lower) threshold is broken a long (short) position is taken (Crabel, 1990). As stated earlier we aim to develop a strategy encouraging to hold positions with a favourable outcome and to quickly end positions with an unfavourable outcome (remember; “ride your winners, sell your losers”). As a consequence of this, the thresholds are placed with a relatively narrow distance from each other. The placements of the thresholds are determined by the opening price of a given day and a symmetric upper and lower threshold is set subsequently. So, in the beginning of a day we will use the observed opening price to place a 10
11 basis points (bp) upper and lower range threshold respectively. As said we will enter a position as soon as a threshold breaks but we will only consider taking one short position and one long position a day. For the purpose of this study we will assume to end positions at the very end of each day, implicating that the difference between the crossed threshold and the closing price is equal to the daily profit/ loss. Since we assume to take equally large positions at all time, a further implication of !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !A!hundredth!of!1!percentage!

! 8! !

---

the strategy is that maximum two trades will be generated and at days when we go 
both long and short we will limit losses to the range between the thresholds (20 bp).
The compiled price data consists of the opening price (!!!), the highest price (!!!), 
the lowest price (!!!) and the closing price of a given day, t. From !!!the symmetric 
!!
upper and lower threshold is placed, these are denoted as ! and ! respectively.

(P_{t}^{h})

\left(P_{t}^{l}\right)

P_{t}^{o}

\cdot\psi^{l}

\psi^{h}

Different possible outcomes of a day are displayed below:

A “profitable bullish day” refers to a day where the price has crossed the upper 
threshold from below and closed above it. A “profitable bearish day” refers to a day 
where the price has crossed the lower threshold from above and closed below it. A 
“non-profit bullish day” refers to a day where the price has crossed the upper 
threshold from below and closed below it. A “non-profit bearish day” refers to a 
day where the price has crossed the lower threshold from above and closed above 
it. The arrow of the profitable days shows the size of the profit (rather small in this example. The arrow of the non-profit days shows the size of negative profit that day 
(in this example maximized, equal to the range between threshold high and low).
We can view the placement of the upper and lower threshold as following:

\begin{array}{l l l}{{P_{t}^{o}(1+b p)=\psi^{h}}}&{{\qquad\qquad}}&{{W hbegin r}\ {{w:}}\\ {{\psi^{h}=\ u p p r r\ t h r e s h o l d}}\\ {{\qquad^{h}=\ u u w e e r\ t h e s h o l d}}\\ {{\qquad\qquad}}&&{{{\psi^{h}=u\ o r e r\ t h e s h o l d}}}\\ {{\qquad^{h}=\ u u t e e r\\theta h h e s s o l l s}}\\ {{\qquad\qquad}}&{{\qquad\^{h p}=u u a l e r\ o f a s i i s\\ o r i s s\ }}\\ {{\qquad\qquad}}&{{b\qquad p}=u u m b e r\ o f b a s i s\ p o i n s}}\\end{}\end{array}

Here, the thresholds functions as a indicators, indicating to enter a long position 
!"#$
(!) when the upper threshold is crossed from below while taking a short 
!!!"#!
position (!) when the lower threshold (!) is crossed from above:

(\psi^{l})

(\vartheta^{l o n g})

(\vartheta^{s h o r t})

\ {\begin{array}{l l}{{\theta^{l o n g}\mid P_{t+\delta}\geq\psi^{h}\quad\quad\quad\quad\quad

\Longrightarrow\vartheta^{l o n g}\,\&\,\vartheta^{s h o r t}\,\mid\,P_{t+\delta}\geq\varPsi^{h}\,\cup\,P_{t+\delta}\geq\varPsi^{l}

We use; “!!” to denote the profit of a day. Given that this strategy is strictly followed, 
there are two possible scenarios in which positive profits are generated in a trading 
day. The first eventuality is if the price in some point during a day rises above the 
upper threshold and  closes above it (!!!). The other possibility is that the price in 
some point of the day declines below the lower threshold and closes below it (!!!).

^mathfrak\\varsigma}{R_{t}}^{\circ\mathfrak varsigma

Consequently, Negative profits will be generated if one of the following three 
scenarios occurs. (1) The price breaks threshold high and then closes below. (2) The

(R_{t}^{-})

R_{t}^{+}=\,P_{t+\delta}\geq\varPsi^{h}\;a n d\;P^{c}>\varPsi^{h}

(R_{t}^{+})

---

price breaks threshold low and closes above it. (3) The price breaks both threshold 
high and threshold low during the same day.

(1)\,P_{t+\delta}\geq\varPsi^{h}\,a n d\,P^{c}<\varPsi^{h}

(2)\ P_{t+\delta}\leq\varPsi^{h}\,a n d\,P^{c}>\varPsi^{l}

(3)\,P_{t+\delta}\geq\varPsi^{h}\cup\,P_{t+\delta}\leq\varPsi^{h}

Since it lies within the purpose of this study to investigate if there is any significant 
difference between a Buy&hold strategy (the evolvement of the underlying asset) and 
the ORB strategy this evolvement was calculated:

\frac{P_{t}^{C}}{P_{t-1}^{C}}-1

We denote the returns of days where a long trade is taken as !!and returns where a 
short trade is taken as !!. The calculations were made as follows:

R_{L}

R_{S}

R_{L}=\cfrac{P^{c}}{\psi^{h}}-1

R_{S}=1-\frac\{P{}}^c{\psi^{l}}

Consequently we have shown how the negative profit of a day has been limited to the 
!!
range between the thresholds (! − !) and shown why this situation always will 
occur on days where both a long and a short trade is taken.

R_{L,S}

(\psi^{h}-\psi^{l})

---

We use “n” as an expression for the number of days traded and show the sum of the returns gained by the strategy by following function:

! (!!,!+ !!+ !!) !!!

3.2 GARCH To test the profitability of using volatility-based thresholds the tactic is to model the financial time series with the use of GARCH. The specific application of GARCH will be explained but first a background of the model is in order. The Generalized autoregressive heteroscedasticity model, mostly known as the GARCH model follows as a result of early research findings of volatility clustering (Mandelbrot, 1963). When financial time series indicate behaviour of volatility clustering it implies that large (small) price-changes tend to follow by further large (small) changes. The concept of conditional heteroscedaticity was first introduced by Engle (1982) making it possible for an investor to account for volatility clustering and nonlinearity in the modelling of series. Since 1982 an abundance of conditional heteroscedaticity models has been generated, it was not until a few years later that the final GARCH model was developed (Bollerslev, 1986). Recent research suggests that GARCH models the features of financial markets in a convenient way (Enders, 2010). Various models have been used as attempts to forecast future price movements of financial markets. Among the many papers discussing features of different time series models we find Bera and Higgins (1993), stating the importance of using a model that incorporates for nonlinear dependence, suggesting GARCH to be a possible tool. With the use of GARCH the forecasting is based on historically forecasted volatility and returns of days in the past. In this thesis the rather simple but heavily used GARCH(1,1) is the version that will be used. This implies that only the returns (AR- term) and the forecasted volatility (CH-term) of the previous period, t-1 will be considered. This study is unique in its application of GARCH. The hypothesis is that the volatility affects the zone of where the momentum effect augments. This implies
## ! 12!

---

that a consideration  of volatility could improve an ORB strategy by better locating
12
momentum and improve the timing during trading sessions. The implementation 
will be to let the forecasted volatility regulate the thresholds. To anticipate for larger 
unforeseeable price fluctuations in a day where the forecasted volatility is large, wider 
thresholds will be considered. If the link between volatility and ORB profitability 
acknowledged by Lundström (2013) would apply to this time series, not only could 
the timing be improved but also the number of false breakouts could be greatly 
reduced.

The graphical illustrations above display how the thresholds will be adjusted 
according to the forecasted volatility. The  application will be to let the thresholds 
remain with the same range in days where the volatility is not expected to be 
abnormally high. Days categorized as normal volatility days will be determined by a 
concept called  long-term variance, (explained in section 5.2). In days where the 
forecasted variance (squared volatility) is expected to be 10% higher than the long-

12
A trading session is a sequence where the underlying market is open and hence, trades could be 
considered term variance measure threshold high and threshold low will be expand by 10% 
respectively. This procedure follows in ten steps, where 100% increase of both
thresholds is the maximum.

Given the number of observations, n, variables of daily returns are created and 
transformed into log-returns to follow an exponential increase. All variables; X1, 
X2,…, Xnare assumed to be independent and identically distributed (iid) and are 
calculated as;

\mathbf{X}_{1}

\mathrm{X_{2},...,X_{n}}

X_{t}=\,\log{\left(\frac{P_{t}^{C}}{P_{t-1}^{C}}-1\right)}

Given the iid assumption log-returns can be seen to evolve somewhat like a random 
walk.

Since the distribution of returns is assumed to follow a Gaussian distribution we use 
the method of maximum likelihood estimation (MLE) to estimate parameters. The 
idea is to deliberate the probability of observing a certain value of !!. We denote 
!"#(!) as the likelihood of a function of n variables:

x_{i}

l i k(\theta)

l i k(\theta)=f(x_{1},x_{2},\ldots,x_{n}|\theta)

This function can be maximized by the use of log likelihood, which is equal to the 
sum of all logarithmic functions. The log likelihood function can then be shown as 
follows:

l(\theta)=\sum_{i=1}^{n}\log\left(f(x_{i}\,|\,\theta)\right)

---

The model as a whole is written like following:

\sigma_{n}^{2}=\omega\,+\alpha_{1}u_{n-1}^{2}+\beta_{1}\sigma_{n-1}^{2},\ldots,+\alpha_{i}u_{n-i}^{2}+\beta_{i}\sigma_{n-j}^{2}

!!!
!!Is the natural logarithm of the squared return of period n-i and !!!!!is the 
forecasted volatility of period n-j

u_{n-i}^{2}

\sigma_{n-j}^{2}

The estimation of parameters refers to !, !!, !!, …, !!and !!!, !!, …, !!. ω = the 
extent to which the long-term variance affects the volatility estimate. α!= The extent 
to which the squared log returns affects the volatility estimate. β!= The extent to
which the squared volatility affects the volatility estimate.

\omega,\alpha_{1},\alpha_{2},\ldots,\alpha_{n}

\beta_{1},\beta_{2},\ldots,\beta_{n},\ 0\ ==\\,

\alpha_{n}=\

\beta_{n}=

\sigma_{t}^{2}=\omega+\sum_{i=1}^{p}\alpha_{i}u_{n-i}^{2}+\sum_{j=1}^{q}\beta_{i}\sigma_{n-j}^{2}

Where “i” represent the number of lags for the p component and “j” represent the 
number of lags for the q component.

^66\ 1{{\ }\beta}

To fulfil the stationary assumption it needs to hold that:

c j^{2,}

\omega>0,\alpha\geq0\;\mathrm{a n d}\;\beta\geq0

\sigma_{n}^{2}=\,\gamma\mathbb{V}_{\mathrm{L}}+\alpha u_{n-1}^{2}+\beta\sigma_{n-1}^{2}

The GARCH(1,1) process is a model that only include lag-1 of both p-and q 
components respectively which implies that it can be written as following:

\mathrm{V_{L}}

\gamma\mathrm{V}_{\mathrm{L}}

\omega

---

## We calculate !!by following function:

! !!= 1 − ! − ! ! Since the estimated weights of γ, !!and!! must sum to 1 it is easy to retrieve γ once ! and ! has been calculated. ! γ + ! + ! = 1 ⟹ !γ = 1 − ! − !! ! The variance is expected to be finite which indirectly implies that there will also be a finite weight assigned to γ. This can be shown by: ! ! !!!< ∞ ⟹ ! + ! < 1 → !γ > 0! ! !

3.3 THE SHARPE RATIO To be able to evaluate the risk adjusted performance of an investor the widely used Sharpe ratio will be calculated. The Sharpe ratio can be derived back to 1966 when William F. Sharpe created this tool of measurement. The measurement was named The Sharpe ratio and considers an investors performance given the undertaken risk (standard deviation). There are several ways to perform the calculations of the Sharpe ratio; the one used here is called the ex-post ratio (Sharpe, 1966). Due to the fact that the strategy only includes one asset, the calculations will be relatively simple since neither correlation nor covariance of assets will have to be taken into account.
! !− !!!! !!!!!! ⟹ !!!!! !!!!

13 The first (left) calculation shows the risk-free return, !!subtracted from the return of the specific asset !!.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! !Since no assets can be defined as totally risk-free, a good estimator has been chosen Used throughout this thesis is a Swedish three-month treasury bill!

## ! 16!

---

In the right calculation !!stands for the average excess return and !!for the underlying standard deviation of the asset.

3.4 VALUE AT RISK To get a full review of the riskiness of an asset or portfolio it is important to look at a worst-case scenario. To survey the worst-case scenario of the strategy executed in this paper, Value at risk (vaR) was used. VaR looks at the size of amount of money that is risked to lose and the statistical probability of doing it within a certain time period, which gives a fair view of the risk management of a strategy. The calculation is based on the statistical probability of a particular outcome. VaR is based on two parameters; confidence interval (1-α) and time horizon T. We display the probability of a certain loss, α as:
! = ![!"## > !"# !, ! ]

α Is the significance level while VaR(α,T) are the value at risk for the two stated parameters. The VaR method used in this thesis is called the analytical VaR and is calculated through a standard transformation:

! − ! ! = ! !

Where Z = −Var!and ! = −!. By the use of the transformation we can write the vaR calculation used to acquire the value at risk:

## !"# = −! + !"

Where: ! is the daily mean return, ! the chosen confidence interval (absolute value terms) and ! is the standard deviation regarding the strategy.

## ! 17!

---

## 3.5 STATISTICAL TESTING

The hypothesis below are the once that will be statistically verified by tests. Apart from these hypothesis we will, as stated earlier, also examine the ORB strategy to the Buy&hold in terms of the Sharpe ratio. Further, the profitability of using volatility- adjusted ranges will be tested.

**Hypothesis 1** H0: R = 0 (The returns of the ORB-strategy during do not exceed the returns of a Buy&hold strategy) HA: R ≠ 0 (The returns of the ORB-strategy significantly differs from a Buy&hold strategy) **Hypothesis 2** H0: R = 0 (The returns of the ORB-strategy during do not exceed the returns of a Buy&hold strategy) HA: R ≠ 0 (The returns of the ORB-strategy significantly differs from a Buy&hold strategy)

To see if hypothesises can be accepted or rejected, the following significance test are made. Hypothesis 1 was tested by the use of a one-sample t test, since we only have one sample that we want to compare to a predetermined value. Hypothesis 2 was tested by the use of a two-sample t test since we have two different samples, comparing ORB to buy and hold. The calculation concerning the one sample t test is shown below to the left whereby the two-sample t test is shown to the right.

! − !!!!− !! ! =!!!!!!!!!!!!!!!!!!!! =!! !/! !! ! !!! + !!!!

!! Represents the mean profit of a day, !!is the comparable expectation of the strategy, which in this case is zero. Here, s stands for the known standard deviation and n indicates the number of observations. The indexation of 1 and 2 in the two- sample t test stands for the two different samples (strategies). The level of 14 significance, α, will determine the probability of type 1 error as follows: α = P(type 1 error) = P(reject H0|H0true). The choice of α will in extension be determining the 15 power of the test P(reject H0|H0false). Since we in this paper will use a confidence interval of 95 percentages, the probability of type 1 error will be 5 percentages.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! The probability of incorrectly rejecting the null hypothesis The probability of correctly reject the null hypothesis given it is false

## ! 18!

---

4. DATA

4.1 FINANCIAL INSTRUMENTS

As described in the introduction-part, a minor purpose of the study was to discuss the 
choice of financial product. The reasoning behind this is that the supply of financial 
products is ever changing and along with this, we have seen an increase in complexity 
16
of the products the last years, making this important decision hard for the investor.

To choose the most effective product of commerce, an investor has to consider their 
specific needs. In this strategy intraday movements are considered and hence many 
positions will be taken. Firstly, we want to act in a product with low transaction costs. 
Secondly, there should be high liquidity, making it easy to find buyers and sellers. 
Apart from this the possibility of going both long and short is a must for the ORB 
investor. We suggest the short-term investor to obligate a two dimensional criteria. 
17
The two dimensional criterion is supposed to prevent slippage to the extent possible.
To fulfil the criteria we have to be in section 4 represented below; with high liquidity 
and low transactions costs.

Looking back in time, the genesis of derivatives can be derived from a time where 
farmers were able to reduce risk by using contracts and ensuring the price of their 
commodities such as wheat and corn in beforehand by using contracts. This represents

Figure 3: Slippage Matrix Picturing how transactions costs and liquidity affects the total 
slippage.

16!Source:!http://www.finAfsa.fi/en/Financial_customer/Financial_products/Pages/Default.aspx!
17
Trading-related costs, due to commission-fees and/ or market illiquidity one of two ways of one can use derivatives. It is called hedging and is used to reduce risk. The other approach is to speculate in price changes of an asset rather than to assure it, which is what is done in this study.

Today, the usage of derivatives has been broadened and hence gotten utilized. In todays financial climate there is a great selection of financial instruments to consider as a trader. Exchange traded funds (ETFs) and Exchange traded commodities (ETCs) but also exchange traded certificates (often denoted as bull/ bear certificates) and contracts for difference (CFDs) are examples of alternatives to futures contracts. The structure of these different products varies but there are common denominators. Regardless if it is in the form of courtage, spreads or other administrative fees, they all come with a commission to an external part. The issuer of the financial products often does the structuring, using futures contracts as an component to replicate the underlying products of use.

There are a few crucial differences between the futures contract and the closely related forward contract. Firstly, forwards are not as standardized as futures and therefore not exchange traded. Secondly, the settlement for a forward occurs at the time of maturity 18 and not by marking to market. Thirdly, futures in general have a higher volume of 19 trade compared to forwards.

4.2 GOLD FUTURES CONTRACTS A futures contract is a type of derivative, an agreement between two parties where a buyer (seller) agrees to buy (sell) the underlying asset to a given price at a pre- determined specific date in the future. All futures are exchange traded which means that the deal is conducted by a regulating intermediary exchange. Profits and losses are accounted by the method of marking to market (MTM) at a daily basis. The MTM process is on going until a sell-point is reached. A sell-point can be reached in three different ways: (i) The holder of the futures contract decides to sell before final settlement date (ii) The predetermined end date of the contract (final settlement date) !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Regularly accounting of a securities market value The number of futures contract in motion (bought and sold) during a specific period of time!
## ! 20!

---

20
is reached (iii) A sell is forced to be made due to a margin call At the time where the 
final settlement date of a futures contract is reached two possible occurrences of 
settlement can be expected,  physical delivery; the seller delivers the underlying asset 
to the buyer at the predetermined price or cash settlement; the parties settle by paying 
(receiving) the loss (gain) of the contract in cash.

The financial instrument traded throughout this study is a gold future. Gold in itself is 
an interesting commodity (precious metal), in more than one sense. Gold was for a 
long time used as intermediate and today it is a backup standard for money (gold 
standard). Many people see it as the safest investment possible over time. Most 
importantly for this study, gold is a very frequently traded future., providing high 
21
liquidity and minimizing the bid/ ask spread. It has a physical delivery at the end 
settlement day. The future is denoted in US Dollar and Cent per troy ounce whereas 
the minimum fluctuation of it is 0,10 Dollar/ troy ounce. The size of one contract 
corresponds to 100 troy ounces. The Future is traded on New York Mercantile 
Exchange  (NYMEX),  a  part  of  CME  Group,  the  worlds  leading  derivatives 
marketplace. The combination of high liquidity together with low transactions costs 
places the gold future in a desired part of the slippage matrix. Using  ORB as an
intraday strategy, we will only hold the position during the day; this takes away the 
22
risk of overnight gaps.

The raw data has been retrieved from Thomson Reuters DataStream. The database in 
turn extracts all of it´s data directly from CME Group. When analysing financial time 
series it is common to split up the data into different sections. In this study the time 
period is limited to a relatively short sequence of data and will therefore be looked 
upon as a whole. Within this time period we can observe periods where the price tends 
to move in trends, due to the development of the underlying asset. One could roughly 
23
view the first third of the time period as a bull market period, the second third as a

20
A point where your investment are forced to be closed, due to big decrease in value
21
The difference between the price buyers are prepared to buy for and the price that sellers are 
prepared to sell for
22
The difference (gap) between the opening price of a day and the closing price of the day before!

22
The difference (gap) between the opening price of a day and the closing price of the day before!
23A period of where a particular market is upward-trending

---

24 25
bear market period and the  final one as a  non-trending period. This makes it 
possible for us to evaluate a strategy during different market-climates. Using a twosided momentum strategy makes it possible to go both long and short. Since this is 
done within an intraday timeframe the underlying long-term market-trend is not 
interesting. Hence, one should gain similar returns during a bull or a bear market as 
during a non-trending market more influenced day-by-day. The time series period is 
from 2009-05-15 to 2014-11-11, denoted as τ and the current period includes 1386 
potential trading days.

Figure)4:)The)development)of)the)daily)open)price)of)US)Gold)futures)adjusted)for)rollMover)
effects)during)time)period:)!.)Source:)Thomson)Reuters)DataStream.)

There is a catch 22 to how to choose a suitable time period. Firstly, we, as statisticians 
want as many observations possible, providing a more reliable result. Secondly, we, as 
a financial analysts know that price patterns and fluctuations of financial assets 
changes over time and the actors on the market does that as well, therefore you want 
fresh information. When the period was chosen another parameter was considered; the 
development of the underlying asset. By using this particular period, both upward and 
downward long-term trends are embraced.

25!A period of where a particular market is not trending upwards nor downwards!

---

4.4 OPEN-HIGH-LOW-CLOSE

The retrieved price data consists of four different parts, including; opening price (Po), 
high price (PH), low price (PL) and closing price (Pc).

\left(\mathrm{P}_{0}\right)

(\mathrm{P}_{\mathrm{H}})

(\mathrm{P}_{\mathrm{L}})

(\mathrm{P}_{\mathrm{c}})

|  | Bearish day | Bullish day |
| --- | --- | --- |
| Opening price-The first trade of the day | PH | PH |
| High price-The highest price of the day | PO | PC |
| Low price-The lowest price of the day | PC | PO |
| Closing price*-The last trade of the day | PL | PL |

\mathbf{P_{H}}

\mathrm{P\__{H}}

Figure 5: OHLC data visualized in candlesticks such as an analyst views it

*In the derivatives market, the industry standard is to use daily settlement price 
equivalent to the closing price. The settlement price is set by the volume-weighted 
average price (VWAP), rounded to the nearest tradable tick. This is done between 
13:29:00 and 13:30:00. This makes the settlement price reasonable to consider as the 
price where the trades of a day are ended.

---

5. RESULTS AND ANALYSIS

5.1 THE ORB STRATEGY

Down below we look at the descriptive statistics of holding the underlying asset itself 
(equal to a buy&hold strategy) compared to ORB. This comparison is interesting for 
hypothesis testing as well as from a money management perspective.

Table 1: descriptive statistics of the buy&hold strategy - 2009-05-15 to 2014-11-11

| Obs. | Daily Mean | Std. Dev. | Min | Max | Skewness | Kurtosis |
| --- | --- | --- | --- | --- | --- | --- |
| 1386 | 0.02% | 1.14% | -9.00% | 5.15% | -0.90 | 5.79 |

Table 2: Descriptive statistics of the ORB strategy - 2009-05-15 to 2014-11-11

| Obs. | Mean | Std. Dev. | Min | Max | Skewness | Kurtosis |
| --- | --- | --- | --- | --- | --- | --- |
| 1386 | 0.04% | 0.58% | -0.21% | 4.64% | 3,18 | 12,60 |

Other than that the daily mean return is about twice as high using the ORB strategy 
compared to own the underlying asset during the same period of time, it is remarkable 
how the minimal loss (Min) gets limited using ORB. The deviation of daily returns is 
visualized in Figure 6 below.

Figure 6: Comparasion of daily returns of ORB vs buy&hold

---

Figure 6 clearly shows how the losses gests limited using the ORB strategy. We can 
also see that during some days  Buy&hold had highly negative profits while it was a 
very profitable day for ORB, due to short-selling. The statistics displays different 
types of days. We Divide days when we go long (Long days), from days when we go 
short (short days) from days when we go both long and short (Long/short days).

Table 3: Comparison between long, short and long/ short days

| Position taking | # Trading days | Total return | Average return |
| --- | --- | --- | --- |
| Long days: | 155 | 132.82% | 0.86% |
| Short days: | 146 | 140.35% | 0.96% |
| Long/short-days: | 1083 | -216.60% | -0.20% |
| Total: | 1384 | 56.57% | 0.58% |

Total:

We observe that long days occur a fairly similar amount of times as short days (155 
VS 146). The majority of days is constituted by “Long/ short  days” which  sums to
78,25% of the days. In contrast, the long days occur 11,20% and “Short days” 10,55%. 
Due to the strategy all “Long/ short days” are losing days but the relatively  narrow
threshold limits the loss of a day to -0,21% with a mean of -0,20%. The average daily 
return on “Long Days” (0,86%) and “Short days” (0,96%) deviates a lot on the plusside compared to what the Long/ short days does on the minus-side. This deviation is 
what in turn makes the total mean profit during this period positive (0,58%) even 
though there are so few winning days.

We can observe Figure 7 and see the ORB strategy to outperform a Buy&hold strategy 
in the long run. Looking at earlier sections of the period the ORB-strategy does not 
seem to generate the same returns ad hence follow the underlying asset in a bullmarket.  The large deviation between the two strategies indicates a large tracking 
26
error of underlying asset, and a highly active strategy.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
26
The difference between the price evolvement of a benchmark compared to a portfolio or specific 
asset

---

Looking at figure 8, we see that the long/ short strategy gives a hedging effect, which 
can be seen through the negative correlation between long and short trades. Linked to 
Markowitz modern portfolio theory we receive the benefits of a well-diversified 
portfolio, being active in only one asset.

Figure 7: accumulated returns of the ORB versus the buy&hold strategy

Figure 8: accumulated returns of log versus short trades

The  significance  tests  regarding  the  state  hypothesis  are  displayed  in  table  4 
(difference in returns ORB deviating from zero) and 5 (difference in returns between 
ORB and buy&hold)

| Type of trade | Long | Short | Long, Short &amp; Long/ short |
| --- | --- | --- | --- |
| P-values: | &lt;0.001 | &lt;0.001 | 0.0086 |
| 95% C.I | [0.42%;0.05%] | [0.16%;0.17%] | [0.0001%;0.0007%] |

---

The p-values states significant returns on both long, short and  Long, Short & Long/ 
short days. The significance would still be valid throughout a 99% indicating high 
robustness.

Table 5: difference in returns between ORB and buy&hold:

| Type of trade | Long, Short &amp; Long/ short |
| --- | --- |
| P-values: | &lt;0.001 |
| 95% C.I | [0.4420%; 0.4227%] |

The occurrence of highly significant returns is seen when comparing with buy&hold 
as well. As seen below, the Sharpe ratio of the ORB-strategy easily outperforms the 
Buy&hold strategy. This states that the ORB-strategy does not only outperform the 
Buy&hold strategy in absolute terms but in risk-adjusted terms.

Table 6: Sharpe ratio comparison

| Measurement | ORB | Buy&hold |
| --- | --- | --- |
| Standard deviation | 0.58 | 1.14 |
| Mean excess return | 0.04 | 0.02 |
| Sharpe ratio | 1.28 | 0.34 |

Table 7: Results regarding historical value at risk calculation

| Mean | Std.Dev | C.I% | C.I | VaR(%) | VaR(100M$) |
| --- | --- | --- | --- | --- | --- |
| 0.04% | 0.58% | 95% | 1,645 | 0.91% | 910547 |

27
To avoid the risk of data snooping and for the purpose of keeping a high 
objectiveness of the study various thresholds for the strategy has been tested. We 
examine how the daily returns and standard deviation deviates as we changes the 
thresholds.

$ ^{27} $ When a systematic selection of tests can be made, showing fallacious results

---

Figure 9: The variation of daily mean returns, using different thresholds

Figure 9 shows how the daily mean returns fluctuate depending on how the thresholds 
are set. A clear negative correlation of daily mean returns and tighter thresholds can be
seen, starting on a breaking point around 0,40%.

*
Figure 10: The variation of the standard deviation of the daily returns, using different 
thresholds

One can observe that the standard deviation for daily returns is rising with lower 
threshold-levels. This process takes a big turn around 0,2% when it is instead starting 
to diminish.

---

One can observe that the maximum value of daily returns is remotely increasing until 
reaching approximately 1% thresholds where it lies more constant. The minimum 
daily returns have an even more clearly diminishing behaviour as we go down to lower 
levels thresholds.

5.2 THE VOLATILITY ADJUSTED ORB STRATEGY

To fit a GARCH model one has to calculate the log returns, since returns are expected 
to grow exponentially. The log returns are then squared to eliminate non-positive 
values and to show consideration to the variance.

[Image: Im5]Figure 12: The evolvement of the logged returns during time period !

The estimation of the GARCH(1,1) parameters !, !, ! done by the use of Maximum 
likelihood estimation (MLE) is seen in Table 8.

Table 8: estimated parameters:
!

| $\omega$ | $\alpha$ | $\beta$ |
| --- | --- | --- |
| 0.00000378 | 0.0589323 | 0.9134991 |

By plugging in the parameters to the GARCH(1,1) it resulted in the following model:

V_{L}=\frac{\omega}{1-\alpha-\beta}=\frac{0.00000378}{0.027569}=0.000137

---

Since the long-term variance average variance (!!) is the long-term volatility squared, 
it follows that:  V!= !0, 000137! ↔ Volatility!= 0, 000137 = 0,011709505 ≈
1,17%.  Figure 13 shows an illustration of the day-to-day forecasted conditional 
variance. The patterns of volatility clustering is obvious, indicating a GARCH model 
as a fairly good estimator of the financial time series.

\left(V_{L}\right)

:\mathrm{~v_{L}=~0,000137~\leftrightarrow~V o l a t i t t__{L L}=\sqrt{0,000137}=00,011709505~}\approx0.01001307\ \approx

Figure)13:DayMtoMday)forecasted)conditional)variance)during)the)time)period;)!)

In Table 9 the results pertaining to the strategy regarding volatility-adjusted ranges are 
shown. We will denote the originally developed ORB-strategy as the “regular ORBstrategy” and the adjusted ORB-strategy as the “flexible ORB-strategy.

Table 9: descriptive statistics from 2009-05-15 to 2014-11-11 (Flexible ORB):

| Strategy | Mean | Std. Dev. | Min | Max | Skew. | Kurt. |
| --- | --- | --- | --- | --- | --- | --- |
| Flexible | 0.03% | 0.59% | -0.41% | 4.64% | 3.06 | 11.69 |
| Regular | 0.04% | 0.58% | -0.21% | 4.64% | 3.18 | 12.60 |

With the test of different thresholds in mind, we observe that the flexible ORBstrategy is still a profitable one. The plotted returns of these two strategies reveals a 
high correlation where the regular ORB-strategy proves to “win the race” at the end.

---

Figure!14:!accumulated!returns;!ORB!strategy!versus!Flexible!ORB!strategy!

5.3 POSSIBLE ERRORS

There is always a drawback to the method of evaluating a strategy using backtesting. 
In section 3.4 certain assumptions were made, if these were to start staggering, it 
could make a difference to the results.

Since we assume perfect market liquidity, this could implicate problems with 
slippage. The problem of filling market orders increases as we intend to execute 
larger amounts of money. Apart from a potential filling problem there is also a chance 
that we could face problems regarding the timing. The use of relatively tight 
thresholds increases the hurdle to get the prices the strategy suggests. We can reduce 
the  risk of this by putting abeyant orders to the market-book as we observe the 
opening price. By doing this we reduce the necessity of constantly being compelled to 
monitor our screens, waiting for a threshold to be crossed. In most cases we do not
know the effect of not getting the exact prices as planned since it could result in a 
missed profit as well as a missed loss.

---

results. Since we never hold positions over night we do not expose ourselves to overnight-gaps, though. Noticeable is that; if this strategy would be result in a hedge fund the amount of money afloat could affect the market itself. The assumption of normally distributed returns could be violated concerning the kurtosis and skewness observed. With this in mind, properties like excessively high kurtosis and skewness is not new, but rather common when examining financial data.

In the structuring of GARCH and the implementation of volatility-adjusted ranges, a very specific approach is taken. The theory is that volatility affects the random walk, and the signals of momentum should be modified subsequently. Due to restricted time, only a narrow approach to test this theory is made. Hence, one could argue that the result of this particular approach is not representative for the question as a whole.

## ! 32!

---

# 6. DISCUSSION

6.1 CONCLUSIONS In this study we have studied market inefficiency through testing the profitability of the momentum-based strategy Opening Range Breakouts with application is on gold futures contracts during 2009-05-15- 2014-11-11. As a complement, the effectiveness of adding forecasted volatility into the decisions in the strategy has been tested. Through the opening range breakouts strategy, we analogus to Holmberg, Lönnbark and Lundström (2013) have achieved returns significantly larger than zero. This significance holds for both short and for long trades as well as for the total result. Moreover, the strategy showed significantly higher returns than its underlying asset, which acted as benchmark. Looking at the risk-adjusted returns we found that the ORB-strategy produced a better result despite a higher Sharpe ratio. The risk management of ORB can in the shorter time horizon be considered as robust since the losses of a trading-day are limited to less than 1 %. Viewing this in a longer perspective, the robustness declines since the strategy showed a whole 78 % of the days to be losing days. The effectiveness of the strategy given this large percentage of losing days can be explained by the remarkably high mean profits throughout the profitable days. In a subjective view the results could indicate short-term intraday inefficiencies of the gold-futures market. As for the secondary question regarding the volatility estimation we estimated a GARCH (1,1) model. With the long-term average volatility working as a starting point, theoretically fitted ranges were implemented to fit the fluctuations of a daily random walk. The strategy of volatility adjusted ranges showed no improvement of the originally development, on the contrary, slightly worsened results were observed. The overall result of the ORB strategy is in line with Jegadeesh and Titman (1993) suggesting that intraday momentum is a real occurrence in the gold futures market. This, indicating drawbacks in EHM, contradicting Fama (1965).
## ! 33!

---

6.2 SUGGESTIONS FOR FURTHER RESEARCH

The  significant  results  concerning  the  ORB-strategy  opens  up  for  additional
questions. Does this apply only to this particular derivative during this specific time 
period? Is the relation; smaller thresholds, higher profit a re-occurring phenomenon?
Performing simulations of random variables, (e.g. by the use of Monte Carlo) to this 
particular strategy could strengthen the results. Further it would be interesting to split 
up the data and perform tests for different underlying trends. By applying the strategy 
on other securities we could see if the results are significant only to gold futures or if 
it seems too be a re-appearing event. As the substance of the ORB-strategy is 
presently viewed, the big flaw is the number of losing days. A study with an entire 
focus of tracking down and reducing the losing days would be highly interesting.

In the  implementing of volatility-adjusted flexible ranges the approach is very 
specific. As stated, the biggest flaw of the ORB-strategy is the quantity of losing days. 
It could be interesting to do a follow-up study,  which would aim to determine what 
distinguishes a good trading-day from a bad. If one would find a correlation between 
a day with bad outcome and the forecasted volatility, one could possibly eliminate
many of these days.  The limitation of data (open-high-low-close) opens up for the 
possibilities for the fully informed trader. With knowledge of the whole development 
of the asset during a day one could adjust the rules of going long/ short. One could 
test the profitability of entering more  trades during the same trading session. One 
could also lock in profits and (hopefully) reduce the number of losing days, by the use 
28
of a trailing stop-loss.  In order to reduce the number of bull- and bear-traps an 
additional momentum indicator could be convenient. A study regarding the strength 
of momentum and how it could be tracked would be highly interesting. One approach 
would be to look at increasing liquidity since it is said to increase the strength of a 
movement. In the current strategy no type of money management is considered. If one 
would follow the expression; “buy more when you are sure” it could result in larger 
profits measured in monetary terms. Lastly, a practical implementation of the strategy 
could be helpful in order to see how it functions in reality. The results of this could be 
considered to make some final adjustments if needed.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

28
A stop-loss is a tool that generates automated sell-orders in order to avoid turning profits into losses. 
The trailing version automatically tracks the security and sells within a certain deviation from the 
current market price

---

# REFERENCES

Baraldi, A.N., & Enders, C.K. (2010): “An introduction to modern missing data analyses” Journal of *School Psychology, 48, 5-37.* Black.F (1976): “The pricing of commodity contracts”: Journal of Financial Economics, vol.3, *January/March 1976, pp.167-179* Black.F and Scholes.M, (1973): “The Pricing of Options and Corporate Liabilities” Bollerslev, T Chou Y.R, Kroner F.K (1992): Journal of Econometrics 52 5-59 North-Holland Bollerslev, T. (1986): “Generalized autoregressive conditional heteroskedasticity” *Journal of* *Econometrics 31, 307-327.* Bollerslev, T., R. Y. Chou, and K. F. Kroner (1992): “ARCH modelling in finance: a Bollerslev.T (1986): “Generalized autoregressive conditional heteroskedaticity” Conditions of Risk” The Journal of Finance, Vol. 19, No. 3 pp. 425-442 Coval, J.D., D.A. Hirshleifer, and T. Shumway (2005): “Can Individual Investors Beat the Market?” Working Paper No. 04-025. School of Finance, Harvard University Crabel, T. (1990): Day Trading With Short Term Price Patterns Day Trading With Short Term Price Patterns and Opening Range Breakout, Greenville, S.C.: Traders Press. Crombez, J. (2001): “Momentum, Rational Agents and Efficient Markets," Journal of Psychology and *Financial Markets, 2, 190-200.* Daniel, K., Hirshleifer, D., Subrahmanyam, A., (1998): “A theory of overconfidence, self-attribution, and security market under- and over-reactions” Journal of Finance 53, in press. Day.T.E and Lewis.C.M (1992): ”Stock market volatility and the information content of stock index options” Journal of Econometrics 52 (1992) 267-287. Engle, R. F. (1982): “Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation". Econometrica, Vol. 50, No. 4. (Jul., 1982), pp. 987-1007. Engle.R.F (1982): “Autoregressive conditional heteroskedaticity with estimates of the variance of United Kingdom inflation” Econometrica, Vol. 50, No. 4. pp. 987-1007 Exploratory Investigation NBER Working Paper No. 444 Fama, E. (1965): “The Behavior of Stock Market Prices,” Journal of Business, 38, 34–105. Fama.E, (1979): "Inflation, Interest, and Relative Prices." Journal of Business, 52(2), pp. 183-209 French.K.R, Schwert.W.G, and Stambaugh.R.F (1987): “Expected stock returns and Holmberg, U., C. Lonnbark, and C. Lundstrom (2013): ”Assessing the Profitability of Intraday Opening Range Breakout Strategies,” Finance Research Letters, 10, 27-33. Implications for Market Efficiency”, Journal of Finance 48, 65-91. Jegadeesh, N., Titman, S., (1993): “Returns to Buying Winner and Selling Loser: *Journal of Econometrics 31 (1986) 307-327* Lintner.J (1965): “The Valuation of Risk Assets and the Selection of Risky Investments in Stock Portfolios and Capital Budgets” A review of Economics and Statistics, 47, 13-37

## ! 35!

---

Lundström.C (2013): “Day Trading Profitability across Volatility States: Evidence of Intraday Momentum and Mean Reversion” Malkiel, B. G. (1996): A Random Walk Down Wall Street, W. W. Norton Mandelbrot.B, (1963): “The Variation of Certain Speculative Prices” The Journal of Business, Vol. 36, *No. 4 pp. 394-419* Merton. R.C (1980): On Estimating the Expected Return on the Market: An Mossin.J (1966): “Equilibrium in a Capital Asset Market” Econometrica, Vol. 34, No. 4 pp. 768-783 Pindyck R.S. (2004): “Volatility and Commodity Price Dynamics.” The Journal of Futures Markets *24:1029–1047* selective review of the theory and empirical evidence”. Journal of Econometrics 52, 5–59 Sharp.W.F (1964): “Capital Asset Prices: A Theory of Market Equilibrium under Statman, M. (2002): “Lottery Players / Stock Traders,” Financial Analysts Journal Vol. 58 1, pp 14-21 *The Journal of Political Economy, Vol. 81, No. 3 (May-Jun., 1973), pp. 637-654* Volatility” vol. 19, issue 1, pages 3-29

## ! 36!

---

! 37!