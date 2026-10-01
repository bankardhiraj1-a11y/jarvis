from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum as SQLEnum
from datetime import datetime
import enum
from database import Base

class TradeType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class AgentName(str, enum.Enum):
    STOCKS = "STOCKS"
    SENSEX = "SENSEX"
    OPTIONS = "OPTIONS"
    CANDLE = "CANDLE"
    XAUUSD = "XAUUSD"
    SENSEX_SCALPING = "SENSEX_SCALPING"
    SENSEX_OPTIONS_SCALPING = "SENSEX_OPTIONS_SCALPING"

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    agent = Column(SQLEnum(AgentName), nullable=False)
    symbol = Column(String(20), nullable=False)
    trade_type = Column(SQLEnum(TradeType), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True, default=0.0)
    take_profit = Column(Float, nullable=True, default=0.0)
    pnl = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    option_strike = Column(String(20), nullable=True)
    option_price = Column(Float, nullable=True)

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    agent = Column(SQLEnum(AgentName), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AgentMetrics(Base):
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True)
    agent = Column(SQLEnum(AgentName), unique=True, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
