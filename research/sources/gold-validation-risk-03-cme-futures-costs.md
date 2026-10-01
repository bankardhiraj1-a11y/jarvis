Source: https://www.cmegroup.com/content/dam/cmegroup/education/files/TCA-4.pdf
Title: Futures Industry Template
Fetched: 2026-10-01T11:48:32.082Z

Transaction Cost Analysis for Futures
By Greg Wood

A futures broker sits down with his pension fund client for a quarterly review of their recent trading activity. The conversation starts off in the usual way with a brief discussion of market conditions, but soon turns to topics such as "shortfall," "negative trend," "trading alpha" and "reversion." A trader writes a complicated formula on the back of a napkin, confers with his boss and sits across the table. "This is how you calculate the impact of our order on the market, isn't it?"

This isn't a conversation about trading equities, where such terms are used frequently. This is a main reason for about trading futures—indices, bonds, commodities, the full spectrum of products available electronically—and the subject is being discussed more often as the buy-side evaluates more efficient execution.

There are two main reasons for this. First, clients rely less on brokers to manage futures of the market. As futures markets have become electronic, customers can now use algorithms to the use of the market brokers traditionally done for them.

Second, hedge funds, commodity trading advisors and real money managers are consolidating their trading desks, so it is now common for individual traders to execute across multiple asset classes. When this happens, they expect to use the same toolkit regardless of asset class. Tools include execution management systems that provide routing to multiple brokers as well as the execution algorithms that the brokers provide.

Another reason is that the provide trading alpha—broadly defined as a return in excess of the market during the execution timeframe. Execution algorithms are not designed to generate routing decisions—the "what," "why" and "when"—but rather the "how" so as to minimize execution risk that could require any trading alpha identified with the trade idea.

Measuring Market Impact

Every trade has an impact on the market. Regardless of the size of it, it is going to incur a cost simply by its presence in the marketplace and how it accesses liquidity. It is also possible to signal intentions and pay more for a trade than intended. This is especially true in the futures markets where there is no concept of trading in the dark. For example, an order to buy 1,000 contracts of Conex Gold futures, shown in the central limit book on Globex, will influence the market. The offer will rise as market participants become aware of an order that is larger than normal. This increase in the offer represents a cost to the trade. Liquid markets can impair the impact of trade without the cost of example until the trade also becomes noticeably large relative to other orders in the market. Less liquid markets will not absorb the impact so easily, which can leave a lasting effect by moving the market from its prior level. To minimize this impact a trader needs to reduce any signalling of intent.

The trader can choose to schedule the execution of the 1,000 contracts over a period of time with VWAP or TWAP, or use a mechanical algorithm such as an iceberg. Algorithms that target VWAP (volume-weighted average price) will lead more orders to the market during high volume periods such as the open and close and work less at quarter periods such as lunch time. An average discussion with the market weighted average price) will feed orders to the market even over a designated period of time.

Another approach to use an intelligent stealth algorithm that minimizes signalling risk by never posting to the central limit book. Instead it takes prices that are within range and works hard to blind in with other participants' activity in the market.

Another type of algorithm is designed to reduce implementation shortfall (also known as "slippage"). Implementation shortfall is a measure of performance versus the "arrival price" or the price at which the order entered the market. For future markets, typically defined as the first risk of the market because spreads are often just one tick wider. A trader who buys at the offer "pays" the spread (the difference between the bid and the offer) to trade; his shortfall is zero. If they buy at a tick above the arrival price, then the shortfall is negative since the market has moved away from the bid, but they actually "captured" the spread and incurved positive shortfall. An example of an algorithm that seeks to reduce implementation shortfall is one that has the expectation that prices are mean-reverting, or will typically fluctuate within a small range. This will become more aggressive when the market is favorable compared to the arrival price.

---

Alpha Profile
A sample trade profile for a buy order demonstrating the concepts of implementation shortfall and erosion in graphical form.

more passive when the market is moving away. The danger here is that the algorithm may not be able to complete the order if the market continues trending away from the arrival price.

The concepts of shortfall and reversion apply to any type of financial market. Because these concepts can be quantified, algorithms can be used to attempt to mini-

mize any of these factors, and their performance measured.

Implementation Shortfall
Implementation shortfall is a well established industry standard approach to measuring transaction costs. It includes anything that has an effect on a financial instrument's

price—notably trend and impact, amongst other factors.

If the underlying trend during your trade is negative (i.e. a rising market when buying, a falling market when selling) then part of shortfall will be a cost attributable to trend. Similarly, if the trend is positive (i.e. a falling market when buying, a rising market when selling) then this part of shortfall will be a saving.

Impact is always a cost created by a trade's presence in the market. An example of how impact can be defined would be the difference between the trade's arrival price and the sum of all other trades on the market—a relatively straightforward formula that could be written on a napkin.

Different types of algorithms approach trend and impact in different ways. For example, an algorithm can be instructed to avoid crossing the spread or to be a very small part of the overall volume traded on the market.

This stretches out the duration of the order, minimizes impact and increases trading lightness, but even if the not be completed in time. If it is imperative to complete the order then you may need to risk higher impact by using a more aggressive algorithm or instead select a WVAP or TWAP algorithm that will trade when the market is unfavourable just to remain on

Test-Driving an Algo

Transaction Cost Analysis, commonly known as TCA, is spreading from equities across all asset classes. The idea of being able to quantify execution and measure how it performed against the market is not new, but the tools to provide such quantification are now becoming common in all asset classes. Here is a hypothetical example to show how a customer might apply TCA to futures trading.

You call your broker and ask about the algorithms it provides. They sound enticing but easy. How do I know which to use? Won't there be bad press last year about algorithms during the Flash Crash? How do I know that my trade is safe and won't cause some major impact on the market?

Your broker runs through the algo available, what they are supposed to do, and in which markets they work best. Then comes the dealer—you can review the performance on a TCA report. Start off with some smaller orders, look at the reports, learn what parameters work best and build confidence.

Back at the trading desk, you place some small orders through the system, but soon the results with the market. Then it time to really give it a trial. You need to sell a few thousand long gilt futures on Life from the open. It is a languish price, but too large, just to be safe to sell it over a few hours and ensure that it is never more than 20% of the market. Let's see how this works. While the order is in motion you're wondering whether it is doing what you want it to be. Is it selling the highs and avoiding those temporary dips in the market? Is it participating when there's more volume? Is it sitting what you're trying to do? What will it do if the market trends away?

The following day you get an email from your broker with the TCA report. The report is normalized so as to allow ready comparison across different markets. Values are quoted in basis points, monetary amounts in U.S. dollars.

The average bid/skew spread on the long gilt futures contract is shown as 1.09 basis points of the notional. Makes sense—you do the math and it comes out as 1 tick, or £10. You look at the other values. Implementation shortfall is shown as -5.1 bps—that's the measure of execution versus the arrival price (the price at the start of the trade which in this case was the opening print of the day). Your shortfall is made up of trend, impact and trading alghit. The market provided down immediately after the order, you down it, so that explains the large negative value. I was expecting that, you think.

Here's the clincher though. How did you compare to the volume-weighted average price over the duration of the TCA? It shows that you sold at a price 0.5 basis points lower than the WVAP benchmark.

Hmm. It don't expected that. Let's take a closer look. You choose a WVAP algorithm for your trade because you wanted to stretch out the order, guarantee completion but never more than 20% of the market. An increased market pressure after the order, you down it, so that explains the large negative value. I was expecting that, you think.

Your broker walks you through what the market did during your trade. You can see the overall trend down across the duration of your order, with a little bit of chopiness here and there. The volume profile on the day of your order was comparable with other days, so the WVAP algorithm was not disaccented by any unusual value at the time it participated fairly evenly across the entire duration according to the expected volume profile, but was never more than 2% of the traded volume because of the lengthy duration of the order.

---

schedule. Such an algorithm, however, will not look to minimize implementation shortfall (see "Test-Driving an Algo" below).

Reversion
An interesting measure of the impact of a trade on the market is how the market reverts afterwards. Reversion can be measured over different periods of time or identify if the impact of a trade was temporary or permanent.

If the price after a finite period remains the same as the price at completion of the trade, then impact can be considered permanent if a period of time is identified if absorbed by market supply and demand, or because it was trading too aggressively by crossing the spread and pushing the price away.

If the price after a finite period remains the same as the price at completion of the trade, then impact can be considered permanent if a period of time is identified if absorbed by market supply and demand, or because it was trading too aggressively by crossing the spread and pushing the price away.

If the price after a finite period remains the same as the price at completion of the trade, then impact can be considered permanent if a period of time is identified if absorbed by market supply and demand, or because it was trading too aggressively by crossing the spread and pushing the price away.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept of measuring execution is not new and traders have been applying these principles for many years. The ability to quantify a trade compared with the market below, during and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

In doing and after its time in the market is an extraordinarily powerful tool. It can provide insight for the buy-side on how they are trading and whether they are using the right approach for their objectives, i.e., whether they are using the best type of algorithm for a particular trade.

Putting It into Practice
The concept