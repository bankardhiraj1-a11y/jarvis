# Zerodha fee schedule evidence (reference estimate)

**Retrieved:** 2026-10-01  
**Primary source:** [Zerodha charges](https://zerodha.com/charges/)  
**Calculator source:** [Zerodha brokerage calculator](https://zerodha.com/brokerage-calculator/#tab-equities)  
**Use:** Broker-reference estimates only. These are not a Zerodha invoice, the user's account schedule, or advice.

The live charges page retrieved on 2026-10-01 listed:

| Charge | Equity intraday | Equity delivery | Index options |
| --- | --- | --- | --- |
| Brokerage | 0.03% per executed order or ₹20, whichever is lower | ₹0 for regular resident equity delivery | ₹20 per executed options order |
| STT | 0.025% on sell side | 0.10% on buy and sell sides | 0.15% on sell-side premium; 0.15% of intrinsic value when a bought option is exercised |
| Transaction charge | NSE 0.00307%; BSE 0.00375% published baseline | NSE 0.00307%; BSE 0.00375% published baseline | NSE 0.03553% of premium; BSE 0.0325% of premium |
| GST | 18% of brokerage + SEBI charges + transaction charges | Same base | Same base |
| SEBI turnover charge | ₹10 per crore | ₹10 per crore | ₹10 per crore |
| Stamp duty | 0.003% on buy side | 0.015% on buy side | NSE 0.002% / BSE 0.003%, buy side |

The charges page also states that BSE transaction charges vary by scrip group, with published separate group rates. As the calculate request has no BSE scrip-group field, the implementation leaves BSE equity exchange fees unknown instead of silently applying the baseline. The charges page describes ₹15.34 DP charge per scrip sold; the generic calculator request lacks the delivered ISIN and settlement context, so delivery-sell DP is an explicit unknown. The calculator's stamp-duty line is displayed rounded to the nearest whole rupee; other modeled monetary lines are rounded to paise.

## Captured calculator sample

The repository's contemporaneous saved extraction is [`zerodha-calculator-fees.md`](zerodha-calculator-fees.md), captured 2026-10-01. The displayed examples are:

* Intraday equity: turnover ₹840,000; brokerage ₹40; STT ₹110; exchange ₹25.79; GST ₹11.99; SEBI ₹0.84; stamp ₹12; total ₹200.62.
* Delivery equity: turnover ₹840,000; brokerage ₹0; STT ₹840; exchange ₹25.79; GST ₹4.79; SEBI ₹0.84; stamp ₹60; total ₹931.42.
* Options: turnover ₹84,000; brokerage ₹40; STT ₹66; exchange ₹29.85; GST ₹12.59; SEBI ₹0.08; stamp ₹1; total ₹149.52.

These calculator lines are included as regression fixtures, while actual user fees can differ due to BSE groups, broker/account class, scrip, execution/order count, DP context, and final contract-note rounding.