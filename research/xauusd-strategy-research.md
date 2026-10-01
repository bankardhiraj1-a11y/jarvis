# XAUUSD strategy research: evidence, bounded tests, and decision

**Status:** Research not validated; London RSI/Bollinger is a forward-paper hypothesis only. The user-authorized paper runtime was restarted and its data, charge and permission endpoints verified on 2026-10-01. Real broker orders remain disabled.  
**Research date:** 2026-10-01  
**Market:** OANDA practice Gold Spot / U.S. Dollar, instrument `XAU_USD` only.  
**Decision:** No tested candidate passed the prespecified fit/validation gates or demonstrated a 90% win rate. London 08:00–17:00 Europe/London with the fixed RSI/Bollinger rule is the selected forward-paper hypothesis only—not a validated winner or authorization for real orders.

## Executive summary and study report

### Bottom line

The evidence does not support promising a 90% win rate, a fixed number of daily opportunities, or a profitable strategy. The earlier 24-setting EMA and 32-setting RSI/Bollinger searches, plus a new 12-case fixed-model/session screen on saved OANDA practice quotes, found no candidate eligible under the gates. The final chronological holdout remains untouched. London RSI/Bollinger is carried forward only as a paper-learning hypothesis because it had the least-negative validation P&L among adequately sampled session comparisons—not because it was profitable or passed training.

The fixed research position was 100 units, treated as 100 troy ounces (one lot). P&L is USD. At this size a $3-per-ounce stop corresponds to $300 of modeled price risk before a gap, slippage, or unavailable fees. INR belongs only in a consolidated display: translate a USD result using a separately recorded, dated USD/INR reporting conversion. It is not the strategy's trading currency or a return measured in INR. OANDA describes this product as a USD-quoted gold CFD measured in troy ounces; product terms can differ by OANDA entity and jurisdiction.[23]

### What published research can—and cannot—say

Gold results depend on venue and design. COMEX patterns are not an OANDA entry rule,[1] and five-minute spot/futures studies do not validate fixed-risk trading on this feed.[2] A real-time monthly gold forecast did not necessarily beat buy-and-hold after costs,[3] while monthly futures research reports some macro-predictability.[4] Neither tests minute-level indicators; ETF evidence also differs from OTC spot.[5]

Technical evidence is mixed. A five-minute precious-metals study finds intraday periodicity and lower wholesale spreads in European hours—not necessarily here.[6] Batten et al.'s 2018 five-minute spot study finds no predictability for standard moving averages but some gold results after a large parameter search. Accessible text describes Thomson Reuters Tick History and in/out-of-sample/bootstrap analysis, but not a reproducible OANDA rule, broker costs or 90% accuracy. Sample end conflicts (detailed text: 2014; introduction: 2015).[7]

RSI research varies: a 2022 paper reports optimized RSI/Keltner futures excess returns but does not establish OANDA results or broker-cost-adjusted 90% accuracy.[8] A Shanghai futures study finds persistent attractive out-of-sample technical performance unlikely after data-snooping/cost controls.[9] Chinese futures session momentum/reversal[10] and wholesale OTC periodicity[11] do not establish a strategy on this feed.

Scheduled U.S. announcements relate to COMEX gold volatility and costs,[12] and a snippet associates some futures/ETF jumps with news, not trade accuracy.[13] No authentic news history was aligned to OANDA candles; a gold-futures breakout thesis is not XAUUSD validation.[14]

### Bounded test and results

The source was saved OANDA practice bid/ask OHLC: 87,672 one-minute bars, 2026-07-03 to 2026-10-01; chart screenshots were not price inputs. Chronologically, 61,370 bars formed development and 26,302 the final 30% holdout; development split into 43,126 inner-fit and 18,244 inner-validation bars. Eligibility required at least 30 fit and 20 validation trades, positive P&L in both, profit factor ≥1.10 and drawdown ≤$3,000; holdout was eligible for one evaluation only after all gates passed. Multiple-testing research explains why searches can produce misleading winners; proposed controls include Deflated Sharpe and false-discovery/persistence tests.[15][16][17][18]

| Study | Best descriptive validation result | Fit / eligibility and decision |
|---|---|---|
| Earlier 24-setting EMA family | Highest validation win rate: 48.78% (20 wins/41 trades), net −$625. Best validation net was −$450. | No candidate met minimum sample, positive-P&L, profit-factor and drawdown rules. No holdout evaluation. |
| New 32-setting Wilder RSI/Bollinger re-entry family | Coverage-focused rejected setting: 2.62 proposed review calls and 2.15 modeled entries per eligible active validation day (13 days), but only 4 wins/24 losses (14.29%), net −$2,100, profit factor 0.4167. | This setting's fit was −$3,189. Zero candidates eligible for selection. |
| Highest validation win rate within the new family | 50% (8/16), net +$1,068. | Fit was −$3,216; 16 validation trades fell short of the 20-trade minimum. It is a small, rejected diagnostic, not a selected strategy. |
| Frozen baseline, for context | 1 win/2 losses (33.33%), +$200 over 3 closed trades. | Too few trades; zero holdout trades. Not a 90% claim. |

The 32-setting RSI/Bollinger family used 1/5-minute bars, RSI7/14 and thresholds20/30, 20-bar/2σ bands, EMA20/50 limits, stops ≤$3/oz, 25-minute maximum holds, no overnight trades and three UTC-day entries maximum. The rejected coverage setting used M1 RSI7/re-entry20, Bollinger20/2σ, EMA20/50 separation ≤$2, $1.50 stop/$3.75 target. It reached desired call frequency but failed validation. The separate 50% diagnostic (8/16) has a broad 95% Wilson interval (28%–72%); coverage's 14.29% (4/28) interval is 5.7%–31.49%. 90% remains aspirational.

### Follow-on fixed-strategy session screen

A predeclared screen compared two frozen rules across six session schedules (12 combinations), changing windows only. It used saved OANDA practice `XAU_USD` bid/ask M1 data from 2026-07-03 11:05 to 2026-10-01 11:05 UTC (87,672 bars; no new provider request or screenshot prices). Development contained 44,503 fit and 17,772 validation bars. All 12 failed a gate; final holdout evaluation count was zero, and it was not inspected.

The local result and row-level evidence are `jarvis2/evidence/xauusd_session_study.json` and `jarvis2/evidence/xauusd_session_study_candidates.csv`; the locked plan is `jarvis2/evidence/xauusd_session_study_preregistered.json`.

| Session convention | UTC, 1 Oct 2026 | IST, 1 Oct 2026 |
|---|---:|---:|
| Tokyo 09:00–18:00 Asia/Tokyo | 00:00–09:00 | 05:30–14:30 |
| London 08:00–17:00 Europe/London (BST) | 07:00–16:00 | 12:30–21:30 |
| New York 08:00–17:00 America/New_York (EDT) | 12:00–21:00 | 17:30–02:30 (+1 day) |
| EU/US overlap | 12:00–16:00 | 17:30–21:30 |
| EU/US union | 07:00–21:00 | 12:30–02:30 (+1 day) |
| Original UTC 16:00–23:00 | 16:00–23:00 | 21:30–04:30 (+1 day) |

These are research session-clock conventions using IANA time zones and DST, not OANDA contract or provider trading hours.

The table below reports gross executable-side quote P&L before unknown commission/financing; each cell is `P&L / closed trades` for fit → validation. The models were fixed EMA-12/26 continuation and the training-only best-coverage RSI/Bollinger rule (RSI-7 re-entry at 20, 20-bar/2σ bands, EMA20/50 regime filter); quantity was 100 units. None qualified, including the least-negative observed validation rows:

| Session | EMA fit | EMA validation | RSI/BB fit | RSI/BB validation |
|---|---:|---:|---:|---:|
| Tokyo | −$5,309 / 96 | −$3,794 / 39 | −$3,915 / 63 | −$2,325 / 26 |
| London | −$6,521 / 99 | −$3,250 / 39 | −$3,217 / 86 | **−$300 / 30** |
| New York | −$2,138 / 99 | −$3,250 / 39 | −$3,528 / 84 | −$1,275 / 33 |
| EU/US overlap | −$2,138 / 99 | −$3,250 / 39 | −$2,400 / 37 | +$375 / 8 |
| EU/US union | −$6,521 / 99 | −$3,250 / 39 | −$4,342 / 97 | −$825 / 37 |
| Original UTC window | −$328 / 99 | −$2,600 / 39 | −$2,333 / 68 | −$1,875 / 30 |

**Forward-paper hypothesis:** use the fixed RSI/Bollinger rule only during London 08:00–17:00. Fit lost $3,217/86; validation lost $300/30 (8 wins, 22 losses; 26.67%, PF 0.9091), so it fails positive-P&L/PF gates. Overlap gained $375 but had only 8 trades (<20 minimum); other adequately sampled RSI/BB sessions lost more. London is a least-loss diagnostic, not an edge. The common no-carry guard requires a 25-minute hold plus one-minute exit buffer to finish by 16:59 America/New_York and before session close; no overnight holds.

Reusing prior indicator families across six windows and choosing London afterward compounds selection bias; this is not independent confirmation. The study itself did not switch the paper configuration or enable entries. Separately, the authorized forward-paper runtime now uses the exact London RSI/Bollinger candidate and exposes its negative fit/validation results and unvalidated status. OANDA unfiltered account-instruments metadata returned HTTP 200 without `XAU_USD`; the filtered lookup returned 404. Commission and financing/swap remain **unknown**, not zero; no fees were fabricated. No real-order authorization follows.

### Execution, costs and limits

Quote-side historical simulation is not actual broker fills. OANDA candles provide bid/ask/mid OHLC and define volume as created prices—not traded quantity.[21] The pricing stream is capped at four updates/second and may omit prices; it is sampled, not full tick history.[22] Entries use next complete bar open (buy ask/sell bid), exits the executable side; ambiguous stop/target bars are stop-first, adverse gaps exit next observed open. OANDA warns stops may execute worse than specified.[24]

Gross quote-side P&L includes observed bid/ask, but historical commission, swap, margin, extra slippage and broker fills are unverified. CME execution-cost and alpha-decay work explains general futures cost concepts, not OANDA fees.[19][20] OANDA policies/specifications are entity-specific and do not establish this account's costs or fills.[25][26]

OANDA volume is not authentic traded volume, so a volume-weighted-average-price filter cannot be built from this candle field. Thin samples, missing candles, zero-opportunity days and unmeasured fees leave meaningful residual uncertainty. Average calls, win rate and closed-trade P&L should be accompanied by active-day coverage, no-signal days, sample size, drawdown and post-cost expectancy whenever evidence improves.

### Decision and next evidence threshold

The research outcome is **failed validation**, not “strategy found.” The user has explicitly approved **EXPERIMENTAL PAPER LEARNING**; the London window is a forward-paper hypothesis only. Runtime permission checks confirm that only Gold and Sensex options scalping can accept experimental paper entries, subject to genuine data and risk/holding gates. The study itself did not change the runtime. No real orders are authorized. Any paper phase must log accepted entries separately from review calls, retain USD accounting and dated INR conversion metadata, freeze rules before fresh chronological data, verify actual costs/fills, and require an unseen holdout with adequate sample, positive net expectancy and acceptable drawdown. Do not retune the reserved holdout or force a 90% metric. Monitoring and reviews depend on the API process remaining running.

For the optional Charges tab only: Zerodha's schedule retrieved 2026-10-01 lists India-market brokerage and statutory fees; a 2026 amendment raises specified securities transaction tax rates from 2026-04-01.[27][28] These estimates are not OANDA XAUUSD CFD fees and should not be mixed into this strategy's USD quote-side results.

## Numbered source map and evidence appendix

Each entry gives the registry key, source and local saved evidence path, followed by the fact actually used and its transfer limitation. Academic publisher pages and snippets are cited only for what their accessible text establishes; full PDFs were not available in every case.

| No. | Registry key; source | Saved evidence | Supported fact and limitation |
|---|---|---|---|
| **[1]** | `gold-mean-reversion-2` — Cai et al., “What moves the gold market?” (2001), [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1002/1096-9934(200103)21:3%3C257::AID-FUT4%3E3.0.CO;2-W) | `research/sources/gold-mean-reversion-snippets.md` | Describes intraday return/volatility in COMEX gold futures; not an OANDA entry/exit result. Evidence here is a search snippet. |
| **[2]** | `gold-mean-reversion-3` — “The timing of the flight to gold,” [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1544612319301448) | `research/sources/gold-mean-reversion-snippets.md` | Five-minute intraday gold spot/futures and S&P 500 analysis; no broker-specific strategy validation. Snippet only. |
| **[3]** | `gold-mean-reversion-5` — Pierdzioch, Risse & Rohloff, “On the efficiency of the gold market” (2014), [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521914000209) | `research/sources/gold-mean-reversion-02-gold-efficiency.md` | Accessible abstract says a real-time monthly gold forecast rule does not necessarily outperform buy-and-hold after costs; not minute-level spot XAUUSD. |
| **[4]** | `gold-mean-reversion-7` — Tharann, “Return predictability in metal futures markets” (2019), [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6587048) | `research/sources/gold-mean-reversion-01-metal-futures-predictability.md` | Full-text article reports monthly futures out-of-sample predictability and utility results; predictors/horizon differ from intraday OANDA. |
| **[5]** | `gold-mean-reversion-8` — “Intraday return predictability: Evidence from commodity ETFs,” [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S030142072030862X) | `research/sources/gold-mean-reversion-snippets.md` | Study concerns commodity ETFs including gold; ETF market structure is not OTC XAUUSD. Accessible snippet only. |

### Intraday rules, session effects and news

| No. | Registry key; source | Saved evidence | Supported fact and limitation |
|---|---|---|---|
| **[6]** | `gold-regime-pullback-10` — Batten et al., “Stylized facts of intraday precious metals” (2017), [PLOS One](https://pmc.ncbi.nlm.nih.gov/articles/PMC5407636) | `research/sources/gold-regime-pullback-1-intraday-facts.md` | Five-minute stylized-facts study; reports intraday periodicity. It is market description, not a winning trade rule. |
| **[7]** | `gap-34` — Batten et al., “Does intraday technical trading have predictive power in precious metal markets?” (2018), [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1042443117301087) | `research/sources/gap-rsi-2018-alt.md` | Publisher preview verifies spot-metal moving-average study, five-minute data, standard parameters without predictive power and gold results among searched parameters. Accessible full text unavailable; venue/feed execution details, costs and sample-end discrepancy remain unresolved. |
| **[8]** | `gap-33` — Gil, “Intraday Trading of Precious Metals Futures Using Algorithmic Systems” (2022), [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0960077921010304) | `research/sources/gap-rsi-2022.md` | Publisher abstract reports PSO-optimized RSI/Keltner futures results on 2020–Sep 2021 data; exact reproducible signals, OOS protocol and costs are not established in accessible text. |
| **[9]** | `gap-36` — Jin, “Performance of intraday technical trading in China’s gold market” (2022), [RePEc](https://ideas.repec.org/a/eee/intfin/v76y2022ics1042443121001876.html) | `research/sources/gap-session-02-china-futures-2022.md` | Abstract specifies five-minute SHFE futures, 2018–2021, and says persistent attractive OOS technical-rule results are unlikely after data-snooping/cost controls; not OTC spot. |
| **[10]** | `gold-mean-reversion-4` — Ma et al., “The night effect of intraday trading” (2025), [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1044028325000110) | `research/sources/gold-mean-reversion-03-chinese-futures.md` | Finds Chinese gold/silver futures momentum and reversal patterns changed with night trading; different exchange and sessions. |
| **[11]** | `gold-session-breakout-15` — Batten et al., “Stylized facts of intraday precious metals” (2017), [Reading repository PDF](https://centaur.reading.ac.uk/79175/1/BattenLuceyMcGroartyPeatUrquhart2017.pdf) | `research/sources/gold-session-breakout-04-reading-intraday-stylized-facts.md` | Full text reports five-minute wholesale precious-metals data from Thomson Reuters Tick History, May 2000–April 2015, intraday periodicity and relatively low spreads in European hours; no OANDA execution guarantee or strategy. |
| **[12]** | `gold-session-breakout-16` — Smales, O’Grady & Yang, “Examining the impact of macroeconomic announcements on gold futures” (2015), [UWA repository](https://research-repository.uwa.edu.au/en/publications/examining-the-impact-of-macroeconomic-announcements-on-gold-futur) | `research/sources/gold-session-breakout-02-uwa-macro-announcements.md` | Abstract links scheduled U.S. announcements to COMEX volatility, trading costs and activity; not a validated news filter for spot. |
| **[13]** | `gold-session-breakout-20` — “What triggers intraday price jumps and co-jumps in gold?” [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521925004673) | `research/sources/gold-session-breakout-snippets.md` | Search snippet reports U.S. news association with some futures/ETF jumps; the full result and an XAUUSD event study were not verified. |
| **[14]** | `gold-session-breakout-17` — Sönnert, “Day trading on the gold futures market using Opening Range Breakouts and GARCH” (2014/15 thesis), [DiVA PDF](https://www.diva-portal.org/smash/get/diva2:845497/FULLTEXT01.pdf) | `research/sources/gold-session-breakout-03-diva-gold-orb-thesis.md` | Thesis tests NYMEX futures ORB historically; not peer-reviewed broker replication and costs are incompletely quantified. |

### Validation, multiple testing and execution-cost methods

| No. | Registry key; source | Saved evidence | Supported fact and limitation |
|---|---|---|---|
| **[15]** | `gold-validation-risk-21` — Bailey et al., “The Probability of Backtest Overfitting,” [author-hosted paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | `research/sources/gold-validation-risk-01-backtest-overfitting.md` | Presents CSCV for assessing backtest overfitting; methodology guidance, not gold performance evidence. |
| **[16]** | `gold-validation-risk-22` — Bailey & López de Prado, “Pseudo-Mathematics and Financial Charlatanism,” [SSRN](http://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2308659) | `research/sources/gold-validation-risk-snippets.md` | Search excerpt warns that trying more configurations raises backtest-overfit risk; snippet, not instrument evidence. |
| **[17]** | `gold-validation-risk-23` — Bailey & López de Prado, “The Deflated Sharpe Ratio” (2014), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) | `research/sources/gold-validation-risk-02-deflated-sharpe.md` | Describes adjustment for selection bias/multiple testing and non-normality; does not validate these test returns. |
| **[18]** | `gold-validation-risk-26` — Bajgrowicz & Scaillet, “Technical trading revisited: False discoveries, persistence tests, and transaction costs” (2012), [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0304405X1200116X) | `research/sources/gold-validation-risk-snippets.md` | Supports persistence/false-discovery caution; accessible snippet discusses futures, not OANDA spot costs. |
| **[19]** | `gold-validation-risk-24` — CME Group, “Transaction Cost Analysis for Futures,” [CME PDF](https://www.cmegroup.com/content/dam/cmegroup/education/files/TCA-4.pdf) | `research/sources/gold-validation-risk-03-cme-futures-costs.md` | Explains spread, implementation shortfall, impact and execution analysis for futures; no transferable CFD fee schedule. |
| **[20]** | `gold-validation-risk-25` — “Dynamic Trading with Predictable Returns and Transaction Costs,” [NBER working paper](https://www.nber.org/system/files/working_papers/w15205/revisions/w15205.rev0.pdf) | `research/sources/gold-validation-risk-snippets.md` | Search snippet supports signal-decay/cost tradeoff; not a specific XAUUSD commission/slippage estimate. |

### OANDA data/execution and optional INR-market fee references

| No. | Registry key; source | Saved evidence | Supported fact and limitation |
|---|---|---|---|
| **[21]** | `gold-provider-execution-27` — OANDA v20 API, “Instrument,” [documentation](https://developer.oanda.com/rest-live-v20/instrument-df/) | `research/sources/gold-provider-execution-01-oanda-instrument-candles.md` | Official schema gives bid/ask/mid candle OHLC, completeness and volume as number of created prices; not exchange traded volume. |
| **[22]** | `gold-provider-execution-28` — OANDA v20 API, “Pricing,” [documentation](https://developer.oanda.com/rest-live-v20/pricing-ep/) | `research/sources/gold-provider-execution-02-oanda-pricing-api.md` | Official pricing-stream limit is four updates/sec/instrument and intervening prices may be omitted; not complete tick history. |
| **[23]** | `gold-provider-execution-29` — OANDA Global Markets, XAU/USD product page, [OANDA](https://www.oanda.com/bvi-en/cfds/instruments/xau-usd) | `research/sources/gold-provider-execution-03-oanda-gold-product.md` | Page describes CFD gold quoted in USD and measured in troy ounces; jurisdiction-specific terms must be checked. |
| **[24]** | `gold-provider-execution-30` — OANDA US, “Beginners guide to order types,” [OANDA](https://www.oanda.com/us-en/skills-and-insights/education/introduction-trading/basics/order-types-explained) | `research/sources/gold-provider-execution-snippets.md` | OANDA warns stops can execute worse than the specified price; retrieved evidence is a snippet and does not quantify this study's slippage. |
| **[25]** | `gold-provider-execution-31` — OANDA TMS Brokers S.A., Best Execution Policy, [OANDA EU](https://www.oanda.com/eu-en/document/31) | `research/sources/gold-provider-execution-snippets.md` | Policy snippet defines symmetric slippage; entity-specific, not generalized as a universal OANDA outcome. |
| **[26]** | `gold-provider-execution-32` — OANDA Financial Instruments Specification, [OANDA](https://www.oanda.com/eu-en/instruments-specification) | `research/sources/gold-provider-execution-snippets.md` | Snippet points to contract, swap and historical-spread resources; no account-specific values were retrieved or verified. |
| **[27]** | `charges-zerodha-official` — Zerodha charges page, [Zerodha](https://zerodha.com/charges/) | `research/sources/charges-zerodha-official.md` | Retrieved 2026-10-01 fee schedule for Indian exchange products; broker-reference only, not OANDA CFD fees or user invoice. |
| **[28]** | `charges-stt-2026-04` — Government of India, Finance Act 2026, [Finance Bill](https://www.indiabudget.gov.in/doc/Finance_Bill.pdf) | `research/sources/charges-stt-2026-04.md` | Clause 143 raises specified options STT rates effective 2026-04-01; unrelated to XAUUSD spot CFD trading. |

**Citation count:** 28 distinct numbered source entries; all are mapped to existing keys in `research/sources.json`. This report uses only saved source evidence and makes no new web requests.