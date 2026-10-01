import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PAPER_TRADING = True
RISK_PER_TRADE = 0.01
DAILY_DRAWDOWN_LIMIT = 0.02
STARTING_CAPITAL = 500000.0
POLLING_INTERVAL = 300  # 5 minutes to avoid rate limits

class IngestionAgent:
    def __init__(self):
        self.rate_limit_cooldowns = {}
        self.last_successful_fetch = {}

    async def fetch_nse_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch NSE data with intelligent rate limit handling."""
        try:
            import requests

            # Check cooldown
            if symbol in self.rate_limit_cooldowns:
                if time.time() < self.rate_limit_cooldowns[symbol]:
                    logger.debug(f"Cooldown active for {symbol}")
                    return None
                del self.rate_limit_cooldowns[symbol]

            client_id = os.getenv('DHAN_CLIENT_ID')
            access_token = os.getenv('DHAN_ACCESS_TOKEN')

            if not client_id or not access_token:
                return None

            url = "https://api.dhan.co/v2/marketfeed/ltp"
            payload = {"mode": "LTP", "exchangeTokens": {"NSE": [symbol]}}
            headers = {
                "access-token": access_token,
                "client-id": client_id,
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=5)

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 120))
                self.rate_limit_cooldowns[symbol] = time.time() + retry_after
                logger.info(f"Rate limited: {symbol} cooldown {retry_after}s")
                return None

            response.raise_for_status()
            data = response.json()

            if data.get('status') == 200 and data.get('data'):
                quote = data['data'].get('NSE', {}).get(symbol, {})
                if quote and quote.get('ltp'):
                    ltp = float(quote.get('ltp', 0))
                    df = pd.DataFrame([{
                        'timestamp': datetime.now(),
                        'open': float(quote.get('open', ltp)),
                        'high': float(quote.get('high', ltp)),
                        'low': float(quote.get('low', ltp)),
                        'close': ltp,
                        'volume': max(1, int(quote.get('volume', 1)))
                    }])
                    df['vwap'] = df['close']
                    self.last_successful_fetch[symbol] = datetime.now()
                    logger.info(f"NSE {symbol}: {ltp}")
                    return df
            return None

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout: {symbol}")
            return None
        except Exception as e:
            logger.debug(f"Error {symbol}: {str(e)[:50]}")
            return None

    async def fetch_xau_usd_data(self) -> Optional[pd.DataFrame]:
        """Fetch XAU/USD with robust parsing."""
        try:
            df = yf.download('GC=F', period='5d', interval='15m', progress=False)
            if df.empty:
                return None

            df = df.reset_index()

            # Normalize column names robustly
            cols_lower = {col: str(col).lower().replace(' ', '') for col in df.columns}
            df.rename(columns=cols_lower, inplace=True)

            # Map possible column names
            rename_map = {
                'datetime': 'timestamp',
                'date': 'timestamp',
                'index': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'adjclose': 'close',
                'volume': 'volume'
            }

            actual_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=actual_cols, inplace=True)

            required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            available = [c for c in required if c in df.columns]

            if len(available) < 5:
                logger.warning(f"XAU/USD missing cols: {set(required) - set(available)}")
                return None

            df = df[available].copy()
            df = df.dropna()

            if len(df) == 0:
                return None

            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(1).astype(int)
            df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

            logger.info(f"XAU/USD: {len(df)} bars, last={df['close'].iloc[-1]:.2f}")
            return df

        except Exception as e:
            logger.debug(f"XAU/USD error: {str(e)[:50]}")
            return None

class StrategyAgent:
    def trend_momentum_strategy(self, df: pd.DataFrame, symbol: str) -> Optional[str]:
        """VWAP + EMA(9/21) for NSE."""
        if df is None or len(df) < 21:
            return None

        df = df.copy()
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

        last_close = df['close'].iloc[-1]
        last_vwap = df['vwap'].iloc[-1]
        last_ema9 = df['ema9'].iloc[-1]
        last_ema21 = df['ema21'].iloc[-1]

        if len(df) >= 2:
            prev_ema9 = df['ema9'].iloc[-2]
            prev_ema21 = df['ema21'].iloc[-2]

            if prev_ema9 <= prev_ema21 and last_ema9 > last_ema21 and last_close > last_vwap:
                return "BUY"
            elif prev_ema9 >= prev_ema21 and last_ema9 < last_ema21 and last_close < last_vwap:
                return "SELL"

        return None

    def liquidity_mean_reversion_strategy(self, df: pd.DataFrame) -> Optional[str]:
        """Bollinger Sweep (2.2 SD) for XAU/USD."""
        if df is None or len(df) < 20:
            return None

        df = df.copy()
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['sma20'] + (2.2 * df['std20'])
        df['bb_lower'] = df['sma20'] - (2.2 * df['std20'])

        last_close = df['close'].iloc[-1]
        last_upper = df['bb_upper'].iloc[-1]
        last_lower = df['bb_lower'].iloc[-1]

        if last_close > last_upper:
            return "SELL"
        elif last_close < last_lower:
            return "BUY"

        return None

class RiskExecutionAgent:
    def __init__(self):
        self.trade_book = []
        self.open_positions = {}
        self.daily_pnl = 0.0
        self.max_daily_loss = STARTING_CAPITAL * DAILY_DRAWDOWN_LIMIT
        self.load_trade_book()

    def load_trade_book(self):
        if os.path.exists('trade_book.json'):
            try:
                with open('trade_book.json', 'r') as f:
                    data = json.load(f)
                    self.trade_book = data.get('trades', [])
                    self.open_positions = data.get('positions', {})
            except:
                pass

    def save_trade_book(self):
        with open('trade_book.json', 'w') as f:
            json.dump({
                'trades': self.trade_book,
                'positions': self.open_positions,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)

    def calculate_position_size(self, symbol: str, current_price: float, atr: float) -> int:
        risk_amount = STARTING_CAPITAL * RISK_PER_TRADE
        stop_loss_distance = max(atr * 1.5, current_price * 0.02)
        quantity = int(risk_amount / stop_loss_distance)
        return max(1, quantity)

    async def execute_trade(self, symbol: str, signal: str, df: pd.DataFrame) -> bool:
        if signal == "HOLD":
            return False

        if not PAPER_TRADING:
            logger.error("Live trading disabled")
            return False

        current_price = df['close'].iloc[-1]
        atr = (df['high'] - df['low']).tail(14).mean() if len(df) >= 14 else current_price * 0.01

        if abs(self.daily_pnl) >= self.max_daily_loss:
            logger.warning("Circuit breaker ACTIVE")
            return False

        position_size = self.calculate_position_size(symbol, current_price, atr)
        stop_loss = current_price * (0.98 if signal == "BUY" else 1.02)
        take_profit = current_price * (1.02 if signal == "BUY" else 0.98)

        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'signal': signal,
            'entry_price': float(current_price),
            'quantity': position_size,
            'stop_loss': float(stop_loss),
            'take_profit': float(take_profit),
            'mode': 'PAPER',
            'status': 'OPEN'
        }

        self.trade_book.append(trade_record)
        self.open_positions[symbol] = trade_record
        self.save_trade_book()

        logger.info(f"EXECUTED: {signal} {symbol} @ {current_price:.2f} | {position_size} units | SL={stop_loss:.2f} TP={take_profit:.2f}")
        return True

class AgentOrchestrator:
    def __init__(self):
        self.ingestion = IngestionAgent()
        self.strategy = StrategyAgent()
        self.execution = RiskExecutionAgent()
        self.symbols_nse = ['RELIANCE', 'TCS', 'INFY']
        self.symbols_fo = ['NIFTY']
        self.running = False

    def update_agent_status(self, agent_name: str, status: str, signal: str = None):
        try:
            if os.path.exists('agent_status.json'):
                with open('agent_status.json', 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            data[agent_name] = {
                'status': status,
                'last_signal': signal,
                'last_update': datetime.now().isoformat()
            }

            with open('agent_status.json', 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

    async def run_cycle(self):
        self.update_agent_status('STOCKS', 'SCANNING')
        self.update_agent_status('XAUUSD', 'SCANNING')

        tasks = []
        for symbol in self.symbols_nse + self.symbols_fo:
            tasks.append(self.ingestion.fetch_nse_data(symbol))
        tasks.append(self.ingestion.fetch_xau_usd_data())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        stocks_signal = False
        for i, symbol in enumerate(self.symbols_nse + self.symbols_fo):
            df = results[i]
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                signal = self.strategy.trend_momentum_strategy(df, symbol)
                if signal and signal != "HOLD":
                    await self.execution.execute_trade(symbol, signal, df)
                    self.update_agent_status('STOCKS', 'WORKING', signal)
                    stocks_signal = True

        if not stocks_signal:
            self.update_agent_status('STOCKS', 'IDLE')

        xau_df = results[-1]
        xau_signal = False
        if isinstance(xau_df, pd.DataFrame) and len(xau_df) > 0:
            signal = self.strategy.liquidity_mean_reversion_strategy(xau_df)
            if signal and signal != "HOLD":
                await self.execution.execute_trade('XAUUSD', signal, xau_df)
                self.update_agent_status('XAUUSD', 'WORKING', signal)
                xau_signal = True

        if not xau_signal:
            self.update_agent_status('XAUUSD', 'IDLE')

        logger.info(f"Cycle complete. Positions: {len(self.execution.open_positions)}")

    async def start(self):
        self.running = True
        logger.info("[LIVE] Quant Engine PRODUCTION MODE. Paper Trading ENFORCED. Polling every 5 minutes.")

        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                logger.info(f"[CYCLE {cycle_count}] Starting market analysis...")
                await self.run_cycle()
                await asyncio.sleep(POLLING_INTERVAL)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(30)

    def stop(self):
        self.running = False

async def main():
    orchestrator = AgentOrchestrator()
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        orchestrator.stop()
        logger.info("Orchestrator stopped.")

if __name__ == '__main__':
    asyncio.run(main())
