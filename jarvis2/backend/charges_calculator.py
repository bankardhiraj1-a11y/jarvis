"""
Charges Calculator - Segment-Specific Broker Fee Calculation
Zerodha rates verified and implemented
"""

class ChargesCalculator:
    """Calculate all trading charges by segment"""

    # Zerodha Rates (Verified from user's calculation)
    # Both STOCKS and FNO use 0.178% per side (from Zerodha: ₹149.52 on ₹84,000 = 0.178%)
    STOCKS_CHARGE_RATE = 0.00178  # 0.178% per side (STOCKS segment)
    FNO_CHARGE_RATE = 0.00178     # 0.178% per side (FNO segment - same as STOCKS for this broker)
    CURRENCY_FLAT_CHARGE = 25     # ₹25 per trade

    # Segment identification
    STOCKS_SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICI", "LT", "SUNPHARMA",
                      "WIPRO", "MARUTI", "BAJAJFINSV"]
    FNO_SYMBOLS = ["SENSEX", "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]
    CURRENCY_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]

    @staticmethod
    def get_segment(symbol):
        """Identify trading segment"""
        if symbol in ChargesCalculator.STOCKS_SYMBOLS:
            return "STOCKS"
        elif symbol in ChargesCalculator.FNO_SYMBOLS:
            return "FNO"
        elif symbol in ChargesCalculator.CURRENCY_SYMBOLS:
            return "CURRENCY"
        else:
            return "STOCKS"  # Default

    @staticmethod
    def calculate_charges(symbol, entry_price, exit_price, quantity, lot_size=1):
        """
        Calculate all charges for a trade.

        Args:
            symbol: Trading symbol
            entry_price: Entry price per unit
            exit_price: Exit price per unit
            quantity: Quantity traded (50 for FNO, shares for stocks)
            lot_size: Lot multiplier (20 for SENSEX, 1 for stocks)

        Returns:
            {
                'segment': 'STOCKS' | 'FNO' | 'CURRENCY',
                'entry_turnover': float,
                'exit_turnover': float,
                'entry_charges': float,
                'exit_charges': float,
                'total_charges': float,
                'charge_ratio_pct': float,
                'breakeven_points': float,
                'charge_breakdown': dict
            }
        """

        segment = ChargesCalculator.get_segment(symbol)

        if segment == "STOCKS":
            return ChargesCalculator._calculate_stocks_charges(
                symbol, entry_price, exit_price, quantity
            )
        elif segment == "FNO":
            return ChargesCalculator._calculate_fno_charges(
                symbol, entry_price, exit_price, quantity, lot_size
            )
        else:  # CURRENCY
            return ChargesCalculator._calculate_currency_charges(
                symbol, entry_price, exit_price, quantity
            )

    @staticmethod
    def _calculate_stocks_charges(symbol, entry_price, exit_price, quantity):
        """Calculate charges for STOCKS segment"""

        entry_turnover = entry_price * quantity
        exit_turnover = exit_price * quantity

        # Entry charges
        entry_charges = entry_turnover * ChargesCalculator.STOCKS_CHARGE_RATE

        # Exit charges
        exit_charges = exit_turnover * ChargesCalculator.STOCKS_CHARGE_RATE

        # Total charges
        total_charges = entry_charges + exit_charges

        # Charge ratio
        avg_turnover = (entry_turnover + exit_turnover) / 2
        charge_ratio_pct = (total_charges / avg_turnover) * 100 if avg_turnover > 0 else 0

        # Breakeven points (percentage move needed to cover charges)
        breakeven_pct = (total_charges / entry_turnover) * 100 if entry_turnover > 0 else 0

        return {
            'segment': 'STOCKS',
            'entry_turnover': round(entry_turnover, 2),
            'exit_turnover': round(exit_turnover, 2),
            'entry_charges': round(entry_charges, 2),
            'exit_charges': round(exit_charges, 2),
            'total_charges': round(total_charges, 2),
            'charge_ratio_pct': round(charge_ratio_pct, 3),
            'breakeven_pct': round(breakeven_pct, 3),
            'charge_breakdown': {
                'brokerage_entry': round(entry_charges, 2),
                'brokerage_exit': round(exit_charges, 2),
                'stt': 0,  # Included in rate
                'gst': 0,  # Included in rate
                'exchange_fees': 0,  # Included in rate
                'total': round(total_charges, 2)
            }
        }

    @staticmethod
    def _calculate_fno_charges(symbol, entry_price, exit_price, quantity, lot_size):
        """Calculate charges for FNO segment (SENSEX, NIFTY, etc.)

        For index futures like SENSEX: 1 point = ₹1 notional value (NOT multiplied by quantity)
        Charges are calculated on point value, not on position size.
        """

        # For SENSEX/NIFTY: notional = price level in rupees (1 point = 1 rupee notional)
        # Charges apply to the contract price, not the position quantity
        entry_notional = entry_price  # Price level in rupees (1 point = 1 rupee)
        exit_notional = exit_price    # Price level in rupees (1 point = 1 rupee)

        # Apply charge rate to notional value
        entry_charges = entry_notional * ChargesCalculator.FNO_CHARGE_RATE
        exit_charges = exit_notional * ChargesCalculator.FNO_CHARGE_RATE

        # Total charges
        total_charges = entry_charges + exit_charges

        # Charge ratio
        avg_notional = (entry_notional + exit_notional) / 2
        charge_ratio_pct = (total_charges / avg_notional) * 100 if avg_notional > 0 else 0

        # Breakeven points (points move needed to cover charges)
        total_units = quantity * lot_size
        breakeven_points = (total_charges / total_units) if total_units > 0 else 0

        return {
            'segment': 'FNO',
            'entry_notional': round(entry_notional, 2),
            'exit_notional': round(exit_notional, 2),
            'entry_charges': round(entry_charges, 2),
            'exit_charges': round(exit_charges, 2),
            'total_charges': round(total_charges, 2),
            'charge_ratio_pct': round(charge_ratio_pct, 3),
            'breakeven_points': round(breakeven_points, 2),
            'charge_breakdown': {
                'brokerage_entry': round(entry_charges, 2),
                'brokerage_exit': round(exit_charges, 2),
                'stt': 0,  # Included in rate for FNO
                'gst': 0,  # Included in rate
                'exchange_fees': 0,  # Included in rate
                'total': round(total_charges, 2)
            }
        }

    @staticmethod
    def _calculate_currency_charges(symbol, entry_price, exit_price, quantity):
        """
        Calculate charges for XAUUSD (Gold spot).

        Lot size mapping:
        - 0.01 lot (1 oz): $0.06 per side = $0.12 round-trip
        - 0.10 lot (10 oz): $0.60 per side = $1.20 round-trip
        - 1.00 lot (100 oz): $6.00 per side = $12.00 round-trip

        Linear interpolation between lot sizes.
        """

        # Determine charges based on lot size
        if quantity <= 0.01:
            # 1 oz: $0.06 per side
            entry_charges = 0.06
            exit_charges = 0.06
        elif quantity <= 0.10:
            # Interpolate between 0.01 ($0.06) and 0.10 ($0.60)
            ratio = (quantity - 0.01) / (0.10 - 0.01)
            entry_charges = 0.06 + (0.60 - 0.06) * ratio
            exit_charges = entry_charges
        elif quantity <= 1.00:
            # Interpolate between 0.10 ($0.60) and 1.00 ($6.00)
            ratio = (quantity - 0.10) / (1.00 - 0.10)
            entry_charges = 0.60 + (6.00 - 0.60) * ratio
            exit_charges = entry_charges
        else:
            # > 1.00 lot: scale from $6.00 per 100 oz
            entry_charges = (quantity / 1.00) * 6.00
            exit_charges = entry_charges

        total_charges = entry_charges + exit_charges
        entry_turnover = entry_price * quantity * 100  # Convert oz to cents
        charge_ratio_pct = (total_charges / entry_turnover) * 100 if entry_turnover > 0 else 0

        return {
            'segment': 'CURRENCY',
            'entry_turnover': round(entry_turnover, 2),
            'exit_turnover': round(entry_price * quantity * 100, 2),
            'entry_charges': round(entry_charges, 4),
            'exit_charges': round(exit_charges, 4),
            'total_charges': round(total_charges, 4),
            'charge_ratio_pct': round(charge_ratio_pct, 3),
            'breakeven_points': round(total_charges / quantity, 4) if quantity > 0 else 0,
            'charge_breakdown': {
                'spread_entry': round(entry_charges, 4),
                'spread_exit': round(exit_charges, 4),
                'commissions': 0,
                'fees': 0,
                'total': round(total_charges, 4)
            }
        }

    @staticmethod
    def calculate_net_pnl(gross_pnl, total_charges):
        """
        Calculate net P&L after charges.

        Args:
            gross_pnl: Profit before charges
            total_charges: Total charges amount

        Returns:
            {
                'gross_pnl': float,
                'total_charges': float,
                'net_pnl': float,
                'charge_impact_pct': float
            }
        """

        net_pnl = gross_pnl - total_charges
        charge_impact_pct = (total_charges / abs(gross_pnl)) * 100 if gross_pnl != 0 else 0

        return {
            'gross_pnl': round(gross_pnl, 2),
            'total_charges': round(total_charges, 2),
            'net_pnl': round(net_pnl, 2),
            'charge_impact_pct': round(charge_impact_pct, 2)
        }


# Test the calculator
if __name__ == "__main__":
    print("=" * 80)
    print("CHARGES CALCULATOR TEST")
    print("=" * 80)

    # Test 1: STOCKS (RELIANCE)
    print("\n[TEST 1] STOCKS - RELIANCE")
    charges_stocks = ChargesCalculator.calculate_charges(
        symbol="RELIANCE",
        entry_price=2400,
        exit_price=2448,
        quantity=100,
        lot_size=1
    )
    print(f"Segment: {charges_stocks['segment']}")
    print(f"Entry Turnover: ₹{charges_stocks['entry_turnover']}")
    print(f"Exit Turnover: ₹{charges_stocks['exit_turnover']}")
    print(f"Total Charges: ₹{charges_stocks['total_charges']}")
    print(f"Charge Ratio: {charges_stocks['charge_ratio_pct']}%")
    print(f"Breakeven: {charges_stocks['breakeven_pct']}%")

    # Calculate net P&L
    gross_pnl_stocks = (2448 - 2400) * 100  # ₹4,800
    pnl_stocks = ChargesCalculator.calculate_net_pnl(gross_pnl_stocks, charges_stocks['total_charges'])
    print(f"Gross P&L: ₹{pnl_stocks['gross_pnl']}")
    print(f"Net P&L: ₹{pnl_stocks['net_pnl']}")

    # Test 2: FNO (SENSEX)
    print("\n[TEST 2] FNO - SENSEX")
    charges_fno = ChargesCalculator.calculate_charges(
        symbol="SENSEX",
        entry_price=74500,
        exit_price=74515,
        quantity=50,
        lot_size=20
    )
    print(f"Segment: {charges_fno['segment']}")
    print(f"Entry Notional: ₹{charges_fno['entry_notional']}")
    print(f"Exit Notional: ₹{charges_fno['exit_notional']}")
    print(f"Total Charges: ₹{charges_fno['total_charges']}")
    print(f"Charge Ratio: {charges_fno['charge_ratio_pct']}%")
    print(f"Breakeven: {charges_fno['breakeven_points']} points")

    # Calculate net P&L
    gross_pnl_fno = 15 * 50 * 20  # ₹15,000
    pnl_fno = ChargesCalculator.calculate_net_pnl(gross_pnl_fno, charges_fno['total_charges'])
    print(f"Gross P&L: ₹{pnl_fno['gross_pnl']}")
    print(f"Net P&L: ₹{pnl_fno['net_pnl']}")

    # Test 3: CURRENCY (XAUUSD)
    print("\n[TEST 3] CURRENCY - XAUUSD")
    charges_currency = ChargesCalculator.calculate_charges(
        symbol="XAUUSD",
        entry_price=4355,
        exit_price=4365,
        quantity=1,
        lot_size=1
    )
    print(f"Segment: {charges_currency['segment']}")
    print(f"Total Charges: ₹{charges_currency['total_charges']}")
    print(f"Charge Ratio: {charges_currency['charge_ratio_pct']}%")

    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)
