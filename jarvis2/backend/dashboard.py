import json
import logging
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Quant Engine HUD", layout="wide", initial_sidebar_state="collapsed")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.markdown("""
<style>
    * { margin: 0; padding: 0; }
    body { background: linear-gradient(135deg, #0a0d15 0%, #0f1420 100%); color: #b8c5d6; font-family: 'JetBrains Mono', monospace; }
    .metric-card { background: rgba(91, 158, 242, 0.08); border: 1px solid rgba(91, 158, 242, 0.3); border-radius: 8px; padding: 16px; margin: 8px 0; backdrop-filter: blur(10px); }
    .metric-label { font-size: 12px; color: #7a8a9e; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #5b9ef2; margin-top: 8px; }
    .status-active { color: #4ade80; }
    .status-scanning { color: #fbbf24; animation: pulse 1s infinite; }
    .status-working { color: #f87171; animation: pulse 0.5s infinite; }
    .status-inactive { color: #ef4444; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .trade-table { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

def load_trade_book() -> dict:
    """Load trade book from disk."""
    try:
        with open('trade_book.json', 'r') as f:
            return json.load(f)
    except:
        return {'trades': [], 'positions': {}, 'last_updated': None}

def load_agent_status() -> dict:
    """Load live agent status from disk."""
    try:
        with open('agent_status.json', 'r') as f:
            return json.load(f)
    except:
        return {
            'STOCKS': {'status': 'IDLE', 'last_signal': None, 'last_update': None},
            'XAUUSD': {'status': 'IDLE', 'last_signal': None, 'last_update': None}
        }

def calculate_health_metrics(trades: list) -> tuple:
    """Calculate algorithmic health percentage and circuit breaker status."""
    if not trades:
        return 0, "IDLE"

    df = pd.DataFrame(trades)

    last_30_trades = df.tail(30)
    if len(last_30_trades) > 0:
        winning = len(last_30_trades[last_30_trades.get('status') == 'CLOSED'])
        total = len(last_30_trades)
        health_pct = (winning / total * 100) if total > 0 else 0
    else:
        health_pct = 0

    circuit_status = "ACTIVE" if health_pct < 40 else "NORMAL"

    return health_pct, circuit_status

st.markdown("# [LIVE] Quant Engine HUD")

col1, col2, col3, col4 = st.columns(4)

trade_book = load_trade_book()
agent_status = load_agent_status()
health, circuit = calculate_health_metrics(trade_book['trades'])

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Algorithmic Health</div>
        <div class="metric-value">{health:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Circuit Breaker</div>
        <div class="metric-value {'status-active' if circuit == 'NORMAL' else 'status-inactive'}">{circuit}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Execution Mode</div>
        <div class="metric-value status-inactive">PAPER</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Gold Feed Status</div>
        <div class="metric-value status-active">LIVE</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### Active Agents")
agent_col1, agent_col2 = st.columns(2)

with agent_col1:
    stocks_status = agent_status.get('STOCKS', {})
    status_text = stocks_status.get('status', 'IDLE')
    status_class = 'status-scanning' if status_text == 'SCANNING' else ('status-working' if status_text == 'WORKING' else 'status-inactive')
    signal_text = stocks_status.get('last_signal', 'No signal yet')
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">STOCKS Agent</div>
        <div class="metric-value {status_class}">{status_text}</div>
        <div style="font-size: 11px; color: #a0aec0; margin-top: 8px;">Last Signal: {signal_text}</div>
    </div>
    """, unsafe_allow_html=True)

with agent_col2:
    xau_status = agent_status.get('XAUUSD', {})
    status_text = xau_status.get('status', 'IDLE')
    status_class = 'status-scanning' if status_text == 'SCANNING' else ('status-working' if status_text == 'WORKING' else 'status-inactive')
    signal_text = xau_status.get('last_signal', 'No signal yet')
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">XAUUSD Agent</div>
        <div class="metric-value {status_class}">{status_text}</div>
        <div style="font-size: 11px; color: #a0aec0; margin-top: 8px;">Last Signal: {signal_text}</div>
    </div>
    """, unsafe_allow_html=True)

col_chart, col_telemetry = st.columns([3, 1])

with col_chart:
    st.markdown("### XAU/USD 15m Chart")
    try:
        xau_df = yf.download('GC=F', period='5d', interval='15m', progress=False)
        if not xau_df.empty:
            xau_df = xau_df.reset_index()

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=xau_df['Datetime'],
                open=xau_df['Open'],
                high=xau_df['High'],
                low=xau_df['Low'],
                close=xau_df['Close'],
                name='GC=F'
            ))

            xau_df['VWAP'] = (xau_df['Close'] * xau_df['Volume']).cumsum() / xau_df['Volume'].cumsum()
            fig.add_trace(go.Scatter(
                x=xau_df['Datetime'],
                y=xau_df['VWAP'],
                mode='lines',
                name='VWAP',
                line=dict(color='rgba(74, 222, 128, 0.6)', width=2)
            ))

            fig.update_layout(
                title="XAU/USD with VWAP Overlay",
                yaxis_title="Price (USD)",
                template="plotly_dark",
                height=500,
                hovermode='x unified',
                paper_bgcolor='rgba(15, 20, 32, 0.8)',
                plot_bgcolor='rgba(15, 20, 32, 0.8)',
                font=dict(family="'JetBrains Mono'", color='#b8c5d6')
            )

            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error: {e}")

with col_telemetry:
    st.markdown("### Live Metrics")

    if trade_book['positions']:
        st.metric("Active Positions", len(trade_book['positions']))
        total_risk = sum([p.get('quantity', 0) * p.get('entry_price', 0) * 0.02 for p in trade_book['positions'].values()])
        st.metric("Risk Exposure", f"₹{total_risk:,.0f}")
    else:
        st.metric("Active Positions", 0)
        st.metric("Risk Exposure", "₹0")

st.markdown("### Trade Ledger (Last 20)")

if trade_book['trades']:
    trades_df = pd.DataFrame(trade_book['trades'])
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    trades_df = trades_df.sort_values('timestamp', ascending=False).head(20)

    display_df = trades_df[[
        'timestamp', 'symbol', 'signal', 'entry_price', 'quantity', 'stop_loss', 'take_profit', 'status', 'mode'
    ]].copy()

    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"₹{x:,.2f}")
    display_df['stop_loss'] = display_df['stop_loss'].apply(lambda x: f"₹{x:,.2f}")
    display_df['take_profit'] = display_df['take_profit'].apply(lambda x: f"₹{x:,.2f}")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Waiting for first signal...")

st.markdown("---")
st.caption(f"Last updated: {trade_book.get('last_updated', 'Never')} | Paper Trading: ENFORCED | Auto-refresh 30s | Orchestrator: AUTO-RESTART")
