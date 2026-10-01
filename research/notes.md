# Research Notes: Evidence-led XAUUSD strategy development

**Status:** synthesis complete; research not validated; London RSI/Bollinger is a forward-paper hypothesis only
**Depth:** Deep
**Date:** 2026-10-01

## Plan

- **Question:** Which reproducible gold-trading hypotheses might improve success rate without disguising losses, costs, or overfitting?
- **Scope:** Academic and primary-provider evidence; gold intraday entry filters, regime selection, bid/ask execution, and validation. No real orders or guaranteed returns.
- **Audience:** Trading-dashboard owner seeking tested improvement.
- **Deliverable:** `research/xauusd-strategy-research.md` (plain-English synthesis, results, limitations, and cited source/evidence map).
- **Instrument:** OANDA practice XAU_USD / XAUUSD only. Fixed 100 units = 100 troy ounces (one lot); modeled trades and risk in USD. INR is a consolidated reporting reference only, not the strategy's P&L currency.
- **Existing evidence:** Frozen baseline: 3 closed trades, 1 win/2 losses, 33.33%, +$200 modeled; zero holdout trades. Earlier bounded 24-configuration EMA family: no eligible candidate; top validation win rate 48.78% (20/41), −$625; validation best net −$450.
- **Phase 6 synthesis:** Evidence differs by venue, frequency, horizon, and method. Gold futures or ETFs do not establish OANDA spot performance. A few technical-rule papers find gold-specific predictability after parameter searches; standard moving-average settings and after-cost OOS findings are less encouraging. Venue, cost, full-text, and cumulative selection-bias limits are recorded.
- **Phase 7 report:** Complete, with a follow-on fixed-window session comparison. 28 numbered source entries remain mapped to registry keys and saved evidence. Distinguishes source facts from applicability/limitations and records contradictions/data gaps.
- **Testing controls:** Chronological fit → inner validation → untouched final holdout, with the holdout evaluated only after all training gates pass. No 90% guarantee, no oversizing/stops engineered to inflate win rate, and no historical result described as an actual broker fill.

## Focus Areas

| Area | Status | Sources |
|---|---|---|
| Gold mean-reversion evidence and selective entry rules | synthesized; transfer uncertain | gold-mean-reversion-1–9; gap-33; gap-36 |
| Trend-pullback and market-regime filters | synthesized; no validated XAUUSD edge | gold-regime-pullback-10–14; gap-34–35 |
| Session, breakout, and announcement effects | session windows compared; all fail gates; London hypothesis is paper-only; no authentic news alignment | gold-session-breakout-15–20; `jarvis2/evidence/xauusd_session_study.json` |
| Win-rate, trading-cost, and overfitting controls | synthesized; historical non-spread charges unverified | gold-validation-risk-21–26 |
| OANDA data resolution and realistic execution | modeled conservatively; not broker-fill validated | gold-provider-execution-27–32 |

## Coverage Checklist

- [x] Identify entry hypotheses with credible evidence, not promotional accuracy claims.
- [x] Distinguish futures, other gold markets, and XAUUSD spot/practice applicability.
- [x] Document bounded causal entry/exit rules and unsuccessful searches.
- [x] Assess why win rate alone can conceal negative expectancy.
- [x] Specify spread, intrabar ambiguity, and unavailable cost limitations.
- [x] Establish chronological validation safeguards, sample uncertainty, and untouched holdout.
- [x] Test a bounded new family on genuine saved data and report rejected candidates.

## Findings Log

The numbered report source map links each citation to its existing registry key, saved URL, local evidence path, supported fact, and limitation. Registry/evidence files were not modified.

### Reproducible study outcomes

- Data: saved, complete OANDA practice bid/ask M1 OHLC, XAU_USD only; 87,672 candles (2026-07-03 through 2026-10-01). User chart screenshots were not inputs.
- Earlier EMA search: 24 finite, predeclared settings; all failed eligibility; 48.78% (20/41) top validation win rate with −$625, best validation net −$450. No holdout evaluation.
- New RSI/Bollinger family: 32 predeclared settings; zero training-eligible candidates. Its most frequent/coverage-focused rejected candidate reached 2.62 proposed review calls and 2.15 modeled entries per eligible active validation day, but made 4 wins/24 losses (14.29%), −$2,100, PF 0.4167; fit −$3,189. Best observed validation win rate was 50% (8/16) and +$1,068, while its fit was −$3,216 and its validation count missed the 20-trade rule.
- Final holdout: zero evaluations for either study; the only valid claim is that no candidate cleared training gates. Do not substitute the failed validation values with a fabricated/zero-valued holdout.
- Quote-side OHLC simulation is not actual broker execution. Commission, financing/swap, slippage beyond sampled quotes, and execution quality remain unknown. Intrabar ambiguity is stop-first; adverse gaps exit at next observed exit-side open.

### Follow-on fixed-strategy session screen

- Predeclared comparison: 12 pairings of two fixed models (EMA12/26 and training-only best-coverage RSI/Bollinger) with six clock windows. Data: same saved OANDA practice XAU_USD bid/ask M1 set, 87,672 bars from 2026-07-03 11:05 UTC to 2026-10-01 11:05 UTC; fit 44,503 bars, inner validation 17,772. Zero fit/validation-eligible candidates; final holdout zero evaluations and uninspected. Raw study result, candidate rows, and preregistration are in `jarvis2/evidence/xauusd_session_study.json`, `jarvis2/evidence/xauusd_session_study_candidates.csv`, and `jarvis2/evidence/xauusd_session_study_preregistered.json`.
- Fit→validation table values below are quote-side P&L in USD / closed trades, before unverified commissions and financing:

| Window | EMA12/26 fit → validation | Fixed RSI/BB fit → validation |
|---|---:|---:|
| Tokyo 09–18 | −$5,309/96 → −$3,794/39 | −$3,915/63 → −$2,325/26 |
| London 08–17 | −$6,521/99 → −$3,250/39 | −$3,217/86 → **−$300/30** |
| New York 08–17 | −$2,138/99 → −$3,250/39 | −$3,528/84 → −$1,275/33 |
| EU/US overlap | −$2,138/99 → −$3,250/39 | −$2,400/37 → +$375/8 |
| EU/US union | −$6,521/99 → −$3,250/39 | −$4,342/97 → −$825/37 |
| Original UTC 16–23 | −$328/99 → −$2,600/39 | −$2,333/68 → −$1,875/30 |

- **Tentative forward-paper hypothesis only:** use RSI7/re-entry20, Bollinger20/2σ, EMA20/50 regime filter with $1.50 stop, $3.75 target, 25-minute maximum hold, no overnight, and London 08:00–17:00 Europe/London. Validation: −$300 over 30 trades, 8 wins/22 losses (26.67%, PF 0.9091); fit −$3,217/86. Selected only as least-negative sufficiently sampled RSI/BB window; fails positive-P&L/PF eligibility. Overlap +$375 came from only 8 trades (<20). This is not an edge or a validated winner.
- DST-aware clock conversion for 2026-10-01; these are study conventions, not OANDA contract trading hours:

| Window | UTC | IST |
|---|---:|---:|
| Tokyo 09–18 Asia/Tokyo | 00–09 | 05:30–14:30 |
| London 08–17 Europe/London (BST) | 07–16 | 12:30–21:30 |
| New York 08–17 America/New_York (EDT) | 12–21 | 17:30–02:30 (+1 day) |
| EU/US overlap | 12–16 | 17:30–21:30 |
| EU/US union | 07–21 | 12:30–02:30 (+1 day) |
| Original UTC 16–23 | 16–23 | 21:30–04:30 (+1 day) |

- NY17 no-carry guard is DST-aware `America/New_York`: maximum 25-minute hold plus one-minute exit buffer must fit before 16:59 NY and before session close; no overnight holding. Same-day construction avoids planned financing but does not make financing zero. OANDA unfiltered annual-instruments metadata returned HTTP 200 without `XAU_USD`; filtered lookup returned 404, so commission and financing/swap are **unknown**, not zero.
- This session screen reused earlier indicator families across six windows; reporting London after comparison compounds selection bias and is not fresh independent proof. User explicitly approved experimental paper learning. The study has `paper_configuration_switched=false` and `paper_entries_enabled_by_this_study=false`; separately, the forward-paper runtime now uses the exact London candidate, with negative historical evidence exposed. No real orders or 90% guarantee.

## Conflicts & Open Questions

- Academic findings conflict because the evaluated market, frequency, period, selection process and cost assumptions differ. In particular, standard moving-average parameter results versus searched longer-parameter gold results are not evidence of a reliable broker-executable edge; one 2018 accessible record also says no standard-parameter predictive power while a parameter-universe search finds some gold predictability.
- A 90% win rate and 2–3 daily calls remain aspirations; neither the OANDA tests nor cited literature validates them. Calls/trades are never forced to meet a quota.
- Batten et al. (2018) accessible records conflict on sample end (detailed content says 2014; introduction says 2015). Use the conflict as an open source-data issue, not an inferred correction.
- Academic gold research reports both market-specific intraday reversals/momentum and weak/illusory persistence after data-snooping and cost controls in other venues. Neither result directly settles OANDA XAUUSD.
- User authorized EXPERIMENTAL PAPER LEARNING. London RSI/Bollinger is only a forward-paper hypothesis, chosen as a least-loss diagnostic. Runtime was restarted and verified on 2026-10-01: Gold and Sensex experimental paper permissions true; other new-entry permissions false; live broker orders false. The focused suite passed 96 tests, and the Charges desktop flow and contained mobile layout were checked. This is not strategy validation, real-order authorization or evidence of a 90% win rate.

## Gaps

- Historical commissions, financing/swap, margin, actual broker fills, and slippage beyond observed sampled quotes are unavailable and must not be invented.
- One-minute OHLC cannot establish intrabar ordering or validate historical stop fills. OANDA streaming is sampled, capped at four updates/second, and may omit prices.
- OANDA candle “volume” counts created prices, not authentic traded volume; it cannot support spot VWAP.
- No authentic timestamped historical economic-news dataset was aligned with the study.
- Small samples have broad uncertainty; low/zero-opportunity active days and drawdowns matter alongside mean coverage or win rate.
- INR consolidation needs a documented reporting FX conversion source/date. Strategy outcomes remain USD; no conversion is implied in this study.