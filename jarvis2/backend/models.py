from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from datetime import datetime
import enum
import uuid
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
    data_source = Column(String(16), nullable=True)
    entry_data_timestamp = Column(String(40), nullable=True)
    exit_data_timestamp = Column(String(40), nullable=True)

class PaperLimitOrder(Base):
    __tablename__ = "paper_limit_orders"

    id = Column(Integer, primary_key=True)
    client_order_id = Column(String(80), nullable=False, unique=True, index=True)
    origin = Column(String(32), nullable=False, default="paper_manual")
    symbol = Column(String(20), nullable=False, default="XAUUSD")
    side = Column(String(8), nullable=False, default="SELL")
    manual_order = Column(Boolean, nullable=False, default=True)
    session_override = Column(Boolean, nullable=False, default=True)
    limit_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    quantity_troy_ounces = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)
    fill_price = Column(Float, nullable=True)
    first_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    second_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    last_reason = Column(String(500), nullable=True)
    state_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": state_version}

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


class ManualPaperOrder(Base):
    """Durable parent for user-created, provider-quoted paper orders."""

    __tablename__ = "manual_paper_orders"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version_id}
    client_order_id = Column(
        String(80), nullable=False, unique=True, index=True,
        default=lambda: str(uuid.uuid4()),
    )
    market = Column(String(16), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(8), nullable=False)
    order_type = Column(String(8), nullable=False)
    limit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    quantity_troy_ounces = Column(Float, nullable=True)
    quantity_lots = Column(Integer, nullable=True)
    option_lot_size = Column(Integer, nullable=True)
    option_type = Column(String(2), nullable=True)
    strike = Column(Float, nullable=True)
    expiry = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    filled_at = Column(DateTime, nullable=True)
    fill_price = Column(Float, nullable=True)
    first_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    second_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    max_hold_minutes = Column(Integer, nullable=False)
    manual_order = Column(Boolean, nullable=False, default=True)
    session_override = Column(Boolean, nullable=False, default=True)
    allow_overnight = Column(Boolean, nullable=False, default=False)
    last_reason = Column(String(500), nullable=True)
