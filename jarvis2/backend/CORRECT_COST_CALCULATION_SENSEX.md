# CORRECT CALCULATION: SENSEX SCALPING ACTUAL PROFITABILITY
**Accurate Cost Breakdown with Real Broker Rates**  
**Date:** 2025-09-22  

---

## CORRECT CALCULATION (User Corrected)

### Input Parameters (SENSEX_SCALPING)
- **Quantity:** 50 lots
- **Lot Size:** 20 units per lot
- **Total Units:** 50 × 20 = **1,000 units**
- **Entry:** SENSEX 74,500 points
- **Target Profit:** 15 points
- **Exit:** SENSEX 74,515 points

---

## STEP 1: GROSS PROFIT CALCULATION

```
Gross Profit = (Exit Price - Entry Price) × Total Units
            = (74,515 - 74,500) × 1,000
            = 15 × 1,000
            = ₹15,000
```

✓ **Gross Profit: ₹15,000** (NOT ₹150)

---

## STEP 2: BROKER CHARGES

**Broker:** ₹20 per trade (entry + exit)

```
Entry Charge:  ₹20
Exit Charge:   ₹20
Total Broker:  ₹40
```

---

## STEP 3: PERCENTAGE-BASED COSTS

### Notional Value for Calculation
- Entry price: 74,500 points
- Units: 1,000
- Notional value = 74,500 × 1,000 = ₹7,45,00,000

### Cost Breakdown

**A. Brokerage (% of turnover)**
- Typical NSE broker: 0.03% per side
- Entry brokerage: ₹7,45,00,000 × 0.03% = ₹22,350
- Exit brokerage: ₹7,45,00,000 × 0.03% = ₹22,350
- **Total brokerage:** ₹44,700

**B. GST on Brokerage (18%)**
- GST = ₹44,700 × 18% = ₹8,046

**C. STT (Securities Transaction Tax)**
- Intraday equity: 0.025%
- Applied on exit side: ₹7,45,00,000 × 0.025% = ₹18,625

**D. Exchange & SEBI Charges**
- Typically 0.000039%
- Amount: ₹7,45,00,000 × 0.000039% = ₹29
- **Negligible, can ignore**

**E. Slippage (Realistic for 3-min candle)**
- Entry slippage: 1-2 ticks = ₹1,000-₹2,000
- Exit slippage: 1-2 ticks = ₹1,000-₹2,000
- **Average slippage: ₹2,000**

---

## TOTAL COST CALCULATION

| Component | Amount |
|-----------|--------|
| Broker charge (flat) | ₹40 |
| Entry brokerage (0.03%) | ₹22,350 |
| Exit brokerage (0.03%) | ₹22,350 |
| GST (18% on brokerage) | ₹8,046 |
| STT (0.025% on exit) | ₹18,625 |
| Exchange/SEBI | ₹29 |
| Slippage (1-2 ticks avg) | ₹2,000 |
| **TOTAL COSTS** | **₹73,440** |

---

## NET P&L CALCULATION

```
Gross Profit:      ₹15,000
Total Costs:      -₹73,440
─────────────────────────
NET P&L:          -₹58,440 (LOSS)
```

**RESULT: ❌ TRADING AT A LOSS OF ₹58,440**

---

## THE PROBLEM: PERCENTAGE COSTS ARE HUGE

Your broker charges **0.03% on both entry and exit** on a notional of ₹7,45,00,000.

- That's ₹44,700 just in brokerage
- Plus ₹18,625 STT
- Plus ₹8,046 GST
- = **₹71,400 in just these three items**

**Your ₹15,000 profit can't cover ₹71,400 in costs!**

---

## COMPARISON: WHAT IF BROKER CHARGES ARE FLAT ONLY?

**Assumption: Flat ₹20 per trade (no percentage fees)**

Some brokers offer flat fees for high-volume traders. Let's calculate with that:

| Component | Amount |
|-----------|--------|
| Broker charge (flat only) | ₹40 |
| Slippage (1-2 ticks) | ₹2,000 |
| **TOTAL COSTS** | **₹2,040** |

```
Gross Profit:      ₹15,000
Total Costs:       -₹2,040
─────────────────────────
NET P&L:           ₹12,960 ✓ PROFIT!
```

**Result: ✓ Profitable by ₹12,960 per trade**

---

## KEY INSIGHT

**The difference: ₹71,400 in percentage fees**

- Standard NSE broker (0.03% brokerage): **LOSS ₹58,440**
- Flat-fee broker (₹20 per trade): **PROFIT ₹12,960**

**You NEED a flat-fee or ultra-low-cost broker for this to work!**

---

## RECALCULATED SENSEX_SCALPING BACKTEST

### Scenario A: Standard Broker (0.03% fees) ❌

```
Total Trades: 280
Win Rate: 99.64%
Gross Profit/Trade: ₹15,000 × 280 = ₹42,00,000

Total Costs/Trade: ₹73,440 × 280 = ₹2,05,63,200

NET P&L: ₹42,00,000 - ₹2,05,63,200 = -₹1,63,63,200 (MASSIVE LOSS!)

Result: ❌ Strategy is TERRIBLE at standard rates
```

**Win rate means nothing if costs exceed gross profit.**

### Scenario B: Flat-Fee Broker (₹20 per trade) ✓

```
Total Trades: 280
Win Rate: 99.64%
Gross Profit/Trade: ₹15,000 × 280 = ₹42,00,000

Total Costs/Trade: ₹2,040 × 280 = ₹57,120

NET P&L: ₹42,00,000 - ₹57,120 = ₹41,42,880 (EXCELLENT!)

Result: ✓ Strategy is HIGHLY PROFITABLE
```

**With flat fees, you make ₹41+ lakhs on 280 trades!**

---

## RECOMMENDATION

### You MUST verify your broker's actual charges:

**Ask Dhan / Your Broker:**
1. "What is the actual brokerage % for NSE index options?"
   - Standard: 0.03% each way (total 0.06%)
   - You need: Flat ₹20 per trade (or negotiate!)

2. "Is there a flat fee option for high-volume scalping?"
   - Many brokers offer flat fees for active traders
   - Could save you ₹200,000+ per month

3. "What about STT, GST, and exchange fees?"
   - Are these included in brokerage or separate?
   - Can they be reduced with volume?

---

## CORRECTED WIN-RATE ANALYSIS

### With Standard Broker (0.03%):
- Gross profit per trade: ₹15,000
- Costs per trade: ₹73,440
- Net loss per trade: -₹58,440
- Even 99.64% win rate = UNPROFITABLE
- **Status: DO NOT TRADE** ❌

### With Flat-Fee Broker (₹20):
- Gross profit per trade: ₹15,000
- Costs per trade: ₹2,040
- Net profit per trade: ₹12,960
- At 99.64% win rate = ₹41,42,880 for 280 trades
- **Status: HIGHLY PROFITABLE** ✓

---

## ACTION ITEMS

### BEFORE LIVE TRADING:

1. **☐ Contact Dhan/Broker and get exact charge structure**
   - Ask for flat-fee option
   - Negotiate if possible
   
2. **☐ If using percentage fees (0.03%), STOP**
   - This makes 15-point scalping impossible
   - Costs exceed profits
   
3. **☐ If using flat fees (₹20), PROCEED**
   - Strategy is profitable
   - Can trade live with confidence
   
4. **☐ Request cost breakdown from broker**
   - Confirm all charges are accounted for
   - No hidden fees

---

## SUMMARY

| Broker Type | Brokerage | Total Cost/Trade | Gross Profit | Net Profit | 280 Trade Result |
|------------|-----------|-----------------|-------------|-----------|-----------------|
| **Standard (0.03%)** | ₹44,700 | ₹73,440 | ₹15,000 | **-₹58,440** | **-₹1,63,63,200** ❌ |
| **Flat-Fee (₹20)** | ₹40 | ₹2,040 | ₹15,000 | **+₹12,960** | **+₹41,42,880** ✓ |
| **Difference** | -₹44,660 | -₹71,400 | Same | +₹71,400 | +₹2,05,06,080 |

---

## CONCLUSION

**Your strategy (15-point TP, 1,000 units, 99.64% win rate) is:**

- **❌ UNPROFITABLE with standard 0.03% broker fees**
- **✓ HIGHLY PROFITABLE with ₹20 flat-fee broker**

**The ENTIRE profitability depends on your broker's fee structure, not the strategy itself.**

Check your broker charges TODAY before running backtest with wrong assumptions.

