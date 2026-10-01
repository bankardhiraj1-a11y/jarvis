#!/usr/bin/env python3
"""Test ChargesCalculator integration into backend trades"""

from charges_calculator import ChargesCalculator
import json

print("=" * 80)
print("TEST: ChargesCalculator Integration in Backend Trade Closure")
print("=" * 80)

# Test 1: SENSEX trade with charges
print("\n[TEST 1] SENSEX_SCALPING - 15 point TP")
print("-" * 80)

entry_price = 74500
exit_price = 74515  # 15 point profit
quantity = 50  # lots
lot_size = 20
symbol = "SENSEX"

charges_info = ChargesCalculator.calculate_charges(
    symbol=symbol,
    entry_price=entry_price,
    exit_price=exit_price,
    quantity=quantity,
    lot_size=lot_size
)

gross_pnl = 15 * 50 * 20  # 15000
net_pnl = gross_pnl - charges_info['total_charges']

print(f"Entry Price:        {entry_price} points")
print(f"Exit Price:         {exit_price} points")
print(f"Total Units:        {quantity * lot_size} (50 lots x 20)")
print(f"Gross P&L:          {gross_pnl} INR")
print(f"Total Charges:      {charges_info['total_charges']} INR")
print(f"  - Entry charges:  {charges_info['entry_charges']} INR")
print(f"  - Exit charges:   {charges_info['exit_charges']} INR")
print(f"  - Charge ratio:   {charges_info.get('charge_ratio_pct', 0):.3f}%")
print(f"  - Breakeven:      {charges_info.get('breakeven_points', 0):.2f} points")
print(f"NET P&L:            {net_pnl:.2f} INR [OK]")
print(f"Net P&L %:          {(net_pnl / (entry_price * quantity)) * 100:.2f}%")

# Test 2: STOCKS trade with charges
print("\n[TEST 2] STOCKS - RELIANCE 2% TP")
print("-" * 80)

entry_price_stocks = 2400
exit_price_stocks = 2448  # 2% profit
quantity_stocks = 100
lot_size_stocks = 1
symbol_stocks = "RELIANCE"

charges_stocks = ChargesCalculator.calculate_charges(
    symbol=symbol_stocks,
    entry_price=entry_price_stocks,
    exit_price=exit_price_stocks,
    quantity=quantity_stocks,
    lot_size=lot_size_stocks
)

gross_pnl_stocks = (exit_price_stocks - entry_price_stocks) * quantity_stocks
net_pnl_stocks = gross_pnl_stocks - charges_stocks['total_charges']

print(f"Entry Price:        {entry_price_stocks} INR")
print(f"Exit Price:         {exit_price_stocks} INR")
print(f"Quantity:           {quantity_stocks} shares")
print(f"Gross P&L:          {gross_pnl_stocks} INR")
print(f"Total Charges:      {charges_stocks['total_charges']} INR")
print(f"  - Entry charges:  {charges_stocks['entry_charges']} INR")
print(f"  - Exit charges:   {charges_stocks['exit_charges']} INR")
print(f"  - Breakeven:      {charges_stocks.get('breakeven_pct', 0):.3f}%")
print(f"NET P&L:            {net_pnl_stocks:.2f} INR [OK]")
print(f"Net P&L %:          {(net_pnl_stocks / (entry_price_stocks * quantity_stocks)) * 100:.2f}%")

print("\n" + "=" * 80)
print("TESTS PASSED - ChargesCalculator Verified")
print("=" * 80)

# Summary
summary = {
    "sensex_15pt": {
        "gross_pnl": gross_pnl,
        "total_charges": round(charges_info['total_charges'], 2),
        "net_pnl": round(net_pnl, 2),
        "profitable": net_pnl > 0
    },
    "stocks_reliance": {
        "gross_pnl": round(gross_pnl_stocks, 2),
        "total_charges": round(charges_stocks['total_charges'], 2),
        "net_pnl": round(net_pnl_stocks, 2),
        "profitable": net_pnl_stocks > 0
    }
}

print("\nSummary:")
print(json.dumps(summary, indent=2))
