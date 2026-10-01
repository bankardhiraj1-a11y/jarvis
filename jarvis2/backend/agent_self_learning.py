import json
import logging
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

GUARDRAILS = {
    'ema_short_min': 5,
    'ema_short_max': 15,
    'ema_long_min': 15,
    'ema_long_max': 50,
    'bb_std_min': 1.5,
    'bb_std_max': 3.0,
    'atr_multiplier_min': 1.0,
    'atr_multiplier_max': 2.5
}

class SelfLearningOptimizer:
    def __init__(self, trade_book_path: str = 'trade_book.json'):
        self.trade_book_path = trade_book_path
        self.params = {
            'ema_short': 9,
            'ema_long': 21,
            'bb_std': 2.2,
            'atr_multiplier': 1.5
        }
        self.last_optimization = None

    def load_trades(self) -> list:
        """Load executed trades from disk."""
        try:
            with open(self.trade_book_path, 'r') as f:
                data = json.load(f)
                return data.get('trades', [])
        except:
            return []

    def calculate_metrics(self, trades: list) -> Dict:
        """Calculate win rate, profit factor, slippage from trade book."""
        if not trades:
            return {'win_rate': 0, 'profit_factor': 0, 'slippage': 0}

        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        last_30_days = datetime.now() - timedelta(days=30)
        df = df[df['timestamp'] >= last_30_days]

        if df.empty:
            return {'win_rate': 0, 'profit_factor': 0, 'slippage': 0}

        df['pnl'] = 0.0
        for idx, row in df.iterrows():
            if row.get('status') == 'CLOSED':
                exit_price = row.get('exit_price', row['entry_price'])
                if row['signal'] == 'BUY':
                    df.loc[idx, 'pnl'] = (exit_price - row['entry_price']) * row['quantity']
                else:
                    df.loc[idx, 'pnl'] = (row['entry_price'] - exit_price) * row['quantity']

        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] < 0]

        win_rate = len(winning_trades) / len(df) if len(df) > 0 else 0

        if len(losing_trades) > 0:
            profit_factor = abs(winning_trades['pnl'].sum()) / abs(losing_trades['pnl'].sum())
        else:
            profit_factor = float('inf') if len(winning_trades) > 0 else 0

        slippage = df['entry_price'].std() / df['entry_price'].mean() if len(df) > 0 else 0

        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'slippage': slippage,
            'sample_size': len(df)
        }

    def optimize_hyperparameters(self, metrics: Dict):
        """Adjust parameters within guardrails based on rolling performance."""
        if metrics['sample_size'] < 10:
            logger.info(f"Insufficient samples ({metrics['sample_size']}). Skipping optimization.")
            return

        if metrics['win_rate'] < 0.45:
            self.params['ema_short'] = min(self.params['ema_short'] + 1, GUARDRAILS['ema_short_max'])
            self.params['ema_long'] = min(self.params['ema_long'] + 2, GUARDRAILS['ema_long_max'])
            logger.info("Low win rate detected. Increasing EMA lookback periods.")

        elif metrics['win_rate'] > 0.60:
            self.params['ema_short'] = max(self.params['ema_short'] - 1, GUARDRAILS['ema_short_min'])
            self.params['ema_long'] = max(self.params['ema_long'] - 2, GUARDRAILS['ema_long_min'])
            logger.info("High win rate detected. Decreasing EMA lookback periods.")

        if metrics['profit_factor'] < 1.0:
            self.params['atr_multiplier'] = min(self.params['atr_multiplier'] + 0.2, GUARDRAILS['atr_multiplier_max'])
            logger.info("Low profit factor. Increasing ATR trailing multiplier.")

        elif metrics['profit_factor'] > 2.0:
            self.params['atr_multiplier'] = max(self.params['atr_multiplier'] - 0.2, GUARDRAILS['atr_multiplier_min'])
            logger.info("High profit factor. Decreasing ATR trailing multiplier.")

        if metrics['slippage'] > 0.05:
            self.params['bb_std'] = min(self.params['bb_std'] + 0.2, GUARDRAILS['bb_std_max'])
            logger.info("High slippage detected. Widening Bollinger Bands.")

    def run_eod_optimization(self):
        """End-of-Day walk-forward optimization loop."""
        trades = self.load_trades()
        metrics = self.calculate_metrics(trades)

        logger.info(f"EOD Metrics | Win Rate: {metrics['win_rate']:.2%} | Profit Factor: {metrics['profit_factor']:.2f} | Slippage: {metrics['slippage']:.4f} | Samples: {metrics['sample_size']}")

        self.optimize_hyperparameters(metrics)

        logger.info(f"Updated Parameters | EMA Short: {self.params['ema_short']} | EMA Long: {self.params['ema_long']} | BB Std: {self.params['bb_std']} | ATR Mult: {self.params['atr_multiplier']}")

        self.last_optimization = datetime.now()

        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'updated_params': self.params
        }

def run_scheduler():
    """Run EOD optimization daily at 3:45 PM IST."""
    optimizer = SelfLearningOptimizer()

    logger.info("Self-Learning Optimizer initialized.")

    while True:
        now = datetime.now()
        target_time = now.replace(hour=15, minute=45, second=0, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()

        logger.info(f"Next optimization in {wait_seconds / 3600:.1f} hours.")

        import time
        time.sleep(wait_seconds)

        result = optimizer.run_eod_optimization()
        logger.info(f"Optimization cycle complete: {result}")

if __name__ == '__main__':
    run_scheduler()
