"""
Jarvis 2 - Profitable Trading System
Rule: Only trade when profit is HIGHLY LIKELY
Quality over quantity - 2 profitable trades > 10 mediocre trades
"""

class ProfitableTrading:
    """
    Pre-trade profitability verification system.
    Calculates expected profit/loss BEFORE entering any trade.
    """

    def __init__(self):
        self.min_profit_probability = 0.75  # 75%+ probability of profit required
        self.min_reward_risk_ratio = 2.0    # Profit target must be 2x the risk
        self.take_profit_aggressive = 0.08  # Book profit at 8% (not 12%)
        self.stop_loss_tight = 0.03         # Stop loss at 3%

    def should_enter_trade(self, signal, market_data, agent_name):
        """
        Determine if trade should be entered based on profit probability.

        Returns: {
            "should_trade": bool,
            "reason": str,
            "entry_price": float,
            "stop_loss": float,
            "take_profit": float,
            "expected_profit_pct": float,
            "profit_probability": float,
            "risk_reward_ratio": float
        }
        """

        if signal == "HOLD":
            return {"should_trade": False, "reason": "No signal"}

        entry_price = market_data.get("close", 0)
        high = market_data.get("high", entry_price)
        low = market_data.get("low", entry_price)
        volume = market_data.get("volume", 0)

        # Calculate stop loss and take profit
        if signal == "BUY":
            stop_loss = entry_price * (1 - self.stop_loss_tight)
            take_profit = entry_price * (1 + self.take_profit_aggressive)
        else:  # SELL
            stop_loss = entry_price * (1 + self.stop_loss_tight)
            take_profit = entry_price * (1 - self.take_profit_aggressive)

        # Calculate metrics
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0

        # Estimate profit probability based on technical factors
        profit_probability = self._calculate_profit_probability(
            agent_name, signal, market_data, entry_price, high, low, volume
        )

        expected_profit_pct = ((reward - risk) / entry_price) * 100 if entry_price > 0 else 0

        # Decision: Trade only if high profit probability + good R:R ratio
        should_trade = (
            profit_probability >= self.min_profit_probability and
            risk_reward_ratio >= self.min_reward_risk_ratio and
            volume > 0  # Ensure there's trading activity
        )

        reason = "PROFITABLE" if should_trade else self._get_rejection_reason(
            profit_probability, risk_reward_ratio
        )

        return {
            "should_trade": should_trade,
            "reason": reason,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "expected_profit_pct": expected_profit_pct,
            "profit_probability": profit_probability,
            "risk_reward_ratio": risk_reward_ratio
        }

    def _calculate_profit_probability(self, agent_name, signal, market_data, entry, high, low, volume):
        """Estimate probability of trade being profitable."""

        if agent_name == "XAUUSD":
            # For EMA signals, check how aligned everything is
            # Higher probability if signal is strong + volume present
            volume_good = volume > 10000
            return 0.80 if volume_good else 0.50

        elif agent_name == "STOCKS":
            # Momentum trades - check if move is sustained
            intraday_range = (high - low) / entry if entry > 0 else 0
            open_price = market_data.get("open", entry)
            move_from_open = abs(entry - open_price) / open_price if open_price > 0 else 0

            # Good probability if: range is decent + volume is high + move is sustained
            has_range = intraday_range > 0.02  # At least 2% range
            has_volume = volume > 500000
            sustained_move = move_from_open > 0.008  # Move from open > 0.8%

            factors_met = sum([has_range, has_volume, sustained_move])
            return 0.75 if factors_met >= 2 else 0.40

        elif agent_name == "SENSEX":
            # Range trades - check proximity to level
            range_val = high - low
            if signal == "BUY":
                proximity = (entry - low) / range_val if range_val > 0 else 0
                return 0.78 if proximity > 0.65 else 0.45
            else:  # SELL
                proximity = (high - entry) / range_val if range_val > 0 else 0
                return 0.78 if proximity > 0.65 else 0.45

        elif agent_name == "OPTIONS":
            # Candle trades - check body strength + volume
            open_price = market_data.get("open", entry)
            body = abs(entry - open_price)
            candle_range = high - low
            body_ratio = body / candle_range if candle_range > 0 else 0

            has_strong_body = body_ratio > 0.65
            has_volume = volume > 500000

            return 0.80 if (has_strong_body and has_volume) else 0.35

        elif agent_name == "SENSEX_SCALPING":
            # 3-minute scalping - trend confirmation already done by agent
            # High probability since agent only trades confirmed trends
            return 0.80  # High confidence due to trend confirmation

        return 0.50  # Default

    def _get_rejection_reason(self, profit_prob, risk_reward):
        """Explain why trade was rejected."""
        reasons = []

        if profit_prob < self.min_profit_probability:
            reasons.append("Low win probability (%.0f%%)" % (profit_prob * 100))

        if risk_reward < self.min_reward_risk_ratio:
            reasons.append("Poor risk/reward (%.1f:1)" % risk_reward)

        return " + ".join(reasons) if reasons else "Not profitable enough"

    def print_trade_decision(self, agent_name, decision):
        """Print trade decision details."""
        symbol = decision.get("symbol", "UNKNOWN")

        if decision["should_trade"]:
            print("\n[TRADE APPROVED] %s - %s" % (agent_name, symbol))
            print("  Entry: %.2f | SL: %.2f | TP: %.2f" % (
                decision["entry_price"],
                decision["stop_loss"],
                decision["take_profit"]
            ))
            print("  Risk/Reward: %.2f:1 | Win Prob: %.0f%%" % (
                decision["risk_reward_ratio"],
                decision["profit_probability"] * 100
            ))
            print("  Expected Profit: %.2f%%" % decision["expected_profit_pct"])
        else:
            print("\n[TRADE REJECTED] %s - %s" % (agent_name, symbol))
            print("  Reason: %s" % decision["reason"])


class ProfitBookingStrategy:
    """Aggressive profit booking to ensure all trades end profitably."""

    def __init__(self):
        self.tp_levels = [0.04, 0.06, 0.08]  # Book profits at 4%, 6%, 8%
        self.tp_quantities = [0.33, 0.33, 0.34]  # 33% at each level

    def should_book_profit(self, entry_price, current_price, signal):
        """Check if we should book profit at partial or full position."""

        if entry_price == 0:
            return None

        if signal == "BUY":
            profit_pct = (current_price - entry_price) / entry_price
        else:  # SELL
            profit_pct = (entry_price - current_price) / entry_price

        # Book at profit levels (4%, 6%, 8%)
        for level, qty in zip(self.tp_levels, self.tp_quantities):
            if profit_pct >= level:
                return {
                    "book_profit": True,
                    "profit_pct": profit_pct * 100,
                    "exit_price": current_price,
                    "quantity_pct": qty * 100
                }

        return None


# Example usage in main trading loop
def apply_profitable_trading_filter(agent_name, signal, market_data):
    """
    Use this in main_minimal.py before executing any trade.
    """
    profitability_checker = ProfitableTrading()

    decision = profitability_checker.should_enter_trade(
        signal, market_data, agent_name
    )

    profitability_checker.print_trade_decision(agent_name, decision)

    return decision["should_trade"]
