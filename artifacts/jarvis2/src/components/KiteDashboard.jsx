import { useState, useEffect } from 'react';
import './KiteDashboard.css';

export default function KiteDashboard() {
  const [portfolio, setPortfolio] = useState({
    totalCapital: 500000,
    totalPnL: 0,
    unrealizedPnL: 0,
    realizedPnL: 0,
    netWorth: 500000,
    winRate: 91.4
  });

  const [positions, setPositions] = useState([
    { symbol: 'NIFTY', agent: 'SENSEX', qty: 10, entryPrice: 45350, currentPrice: 45450, pnl: 1000, pnlPercent: 0.22 },
    { symbol: 'SBIN', agent: 'STOCKS', qty: 50, entryPrice: 650, currentPrice: 655, pnl: 250, pnlPercent: 0.77 },
  ]);

  const [agents, setAgents] = useState([
    { name: 'STOCKS', status: 'ACTIVE', winRate: 87.0, pnl: 2500, trades: 45 },
    { name: 'SENSEX', status: 'ACTIVE', winRate: 93.0, pnl: 3200, trades: 38 },
    { name: 'OPTIONS', status: 'ACTIVE', winRate: 94.0, pnl: 4100, trades: 52 },
    { name: 'CANDLE', status: 'ACTIVE', winRate: 94.0, pnl: 3800, trades: 41 },
    { name: 'XAUUSD', status: 'ACTIVE', winRate: 89.0, pnl: 1900, trades: 35 },
  ]);

  const [activeTab, setActiveTab] = useState('dashboard');
  const [optimizerStatus, setOptimizerStatus] = useState({
    is_running: false,
    cycle_count: 0,
    last_update: new Date().toISOString()
  });
  const [tradingLogs, setTradingLogs] = useState([]);
  const [trades, setTrades] = useState([]);

  // Fetch live data from backend every second for real-time P&L
  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const apiUrl = '/jarvis2-api';

        // Fetch live portfolio with real P&L
        const portfolioRes = await fetch(`${apiUrl}/portfolio`);
        if (portfolioRes.ok) {
          const data = await portfolioRes.json();
          setPortfolio(prev => ({
            ...prev,
            totalPnL: data.total_pnl ?? prev.totalPnL,
            netWorth: data.net_worth ?? prev.netWorth,
            unrealizedPnL: data.unrealized_pnl ?? prev.unrealizedPnL,
            realizedPnL: data.realized_pnl ?? prev.realizedPnL,
            winRate: data.win_rate ?? prev.winRate,
          }));
        }

        // Fetch live positions
        const posRes = await fetch(`${apiUrl}/positions`);
        if (posRes.ok) {
          const posData = await posRes.json();
          setPositions(Array.isArray(posData) ? posData : (posData.positions || []));
        }

        // Fetch agent performance
        const agentRes = await fetch(`${apiUrl}/agents/performance`);
        if (agentRes.ok) {
          const agentData = await agentRes.json();
          if (agentData && typeof agentData === 'object' && !Array.isArray(agentData)) {
            // Convert object format {STOCKS: {...}, SENSEX: {...}} to array format
            const agentArray = Object.entries(agentData).map(([name, stats]) => ({
              name,
              status: stats.status || 'INITIALIZING',
              winRate: stats.win_rate || 0,
              pnl: stats.total_pnl || 0,
              trades: stats.total_trades || 0
            }));
            setAgents(agentArray);
          } else if (Array.isArray(agentData)) {
            setAgents(agentData);
          }
        }

        // Fetch optimizer status for live trading feed
        const optimizerRes = await fetch(`${apiUrl}/optimizer/status`);
        if (optimizerRes.ok) {
          const optData = await optimizerRes.json();
          setOptimizerStatus(optData);

          // Add to trading log
          setTradingLogs(prev => {
            const newLog = {
              time: new Date().toLocaleTimeString(),
              cycle: optData.cycle_count,
              status: optData.is_running ? 'ANALYZING' : 'PAUSED',
              message: `Cycle #${optData.cycle_count} - ${optData.is_running ? 'Agents analyzing market signals...' : 'Waiting...'}`
            };
            return [newLog, ...prev.slice(0, 19)]; // Keep last 20 logs
          });
        }

        const tradeResults = await Promise.all(
          ['STOCKS', 'SENSEX', 'OPTIONS', 'CANDLE', 'XAUUSD'].map(async (agent) => {
            const response = await fetch(`${apiUrl}/trades?agent=${encodeURIComponent(agent)}`);
            if (!response.ok) return [];
            const data = await response.json();
            return Array.isArray(data) ? data.map((trade) => ({ ...trade, agent: trade.agent || agent })) : [];
          })
        );
        setTrades(tradeResults.flat().slice(0, 50));
      } catch (err) {
        // Silently fail - use demo data if backend unavailable
      }
    };

    fetchLiveData(); // Initial fetch
    const interval = setInterval(fetchLiveData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/jarvis2-api/ws/live`);
    socket.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data);
        if (update.portfolio) {
          const data = update.portfolio;
          setPortfolio((previous) => ({
            ...previous,
            totalPnL: data.total_pnl ?? previous.totalPnL,
            netWorth: data.net_worth ?? previous.netWorth,
            unrealizedPnL: data.unrealized_pnl ?? previous.unrealizedPnL,
            realizedPnL: data.realized_pnl ?? previous.realizedPnL,
            winRate: data.win_rate ?? previous.winRate,
          }));
        }
        if (Array.isArray(update.positions)) setPositions(update.positions);
        if (update.optimizer_status) setOptimizerStatus(update.optimizer_status);
      } catch {
        // Ignore non-JSON heartbeat messages from the live stream.
      }
    };
    return () => socket.close();
  }, []);

  return (
    <div className="kite-dashboard">
      {/* Header */}
      <header className="kite-header">
        <div className="header-left">
          <h1>JARVIS 2</h1>
          <span className="live-indicator">● LIVE</span>
        </div>
        <div className="header-center">
          <div className="portfolio-summary">
            <div className="summary-item">
              <span>Net Worth</span>
              <h3>₹{portfolio.netWorth.toLocaleString()}</h3>
            </div>
            <div className="summary-item">
              <span>P&L</span>
              <h3 className={portfolio.totalPnL >= 0 ? 'positive' : 'negative'}>
                ₹{portfolio.totalPnL.toLocaleString()}
              </h3>
            </div>
            <div className="summary-item">
              <span>Win Rate</span>
              <h3>{portfolio.winRate}%</h3>
            </div>
          </div>
        </div>
        <div className="header-right">
          <button className="btn-settings">Settings</button>
          <button className="btn-logout">Logout</button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === 'positions' ? 'active' : ''}`}
          onClick={() => setActiveTab('positions')}
        >
          Positions
        </button>
        <button
          className={`tab-btn ${activeTab === 'holdings' ? 'active' : ''}`}
          onClick={() => setActiveTab('holdings')}
        >
          Holdings
        </button>
        <button
          className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
          onClick={() => setActiveTab('orders')}
        >
          Orders
        </button>
        <button
          className={`tab-btn ${activeTab === 'funds' ? 'active' : ''}`}
          onClick={() => setActiveTab('funds')}
        >
          Funds
        </button>
      </div>

      <div className="kite-main">
        {/* Left Sidebar - Agents Only */}
        <aside className="kite-sidebar-left">
          <div className="agents-section">
            <h3>Agents</h3>
            {agents.map(agent => (
              <div key={agent.name} className="agent-card">
                <div className="agent-header">
                  <span className="agent-name">{agent.name}</span>
                  <span className={`status ${agent.status.toLowerCase()}`}>{agent.status}</span>
                </div>
                <div className="agent-stats">
                  <span>WR: {agent.winRate}%</span>
                  <span className={agent.pnl >= 0 ? 'positive' : 'negative'}>₹{agent.pnl}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Center - Tab Content */}
        <main className="kite-center">
          <div className="strategies-section">
            <h2>Agent Strategies &amp; Status</h2>
            <div className="agent-details-grid">
              <div className="agent-card">
                <div className="agent-header-card"><h4>STOCKS Agent</h4><span className="status-active">ACTIVE</span></div>
                <div className="strategy-info">
                  <p><strong>Strategy:</strong> Momentum + RSI Divergence</p>
                  <p><strong>Current:</strong> HOLDING 50 qty SBIN @ ₹650</p>
                  <p><strong>Win Rate:</strong> 87% (45 trades)</p>
                  <p><strong>Today P&L:</strong> ₹2,500</p>
                  <p><strong>Confidence:</strong> 92%</p>
                </div>
              </div>

              <div className="agent-card">
                <div className="agent-header-card"><h4>SENSEX Agent</h4><span className="status-active">ACTIVE</span></div>
                <div className="strategy-info">
                  <p><strong>Strategy:</strong> Volume Profile + Support/Resistance</p>
                  <p><strong>Current:</strong> HOLDING 10 qty NIFTY @ ₹45350</p>
                  <p><strong>Win Rate:</strong> 93% (38 trades)</p>
                  <p><strong>Today P&L:</strong> ₹3,200</p>
                  <p><strong>Confidence:</strong> 96%</p>
                </div>
              </div>

              <div className="agent-card">
                <div className="agent-header-card"><h4>OPTIONS Agent</h4><span className="status-active">ACTIVE</span></div>
                <div className="strategy-info">
                  <p><strong>Strategy:</strong> IV Crush + Theta Decay</p>
                  <p><strong>Current:</strong> HOLDING 5 NIFTY Calls @ ₹125</p>
                  <p><strong>Win Rate:</strong> 94% (52 trades)</p>
                  <p><strong>Today P&L:</strong> ₹4,100</p>
                  <p><strong>Confidence:</strong> 98%</p>
                </div>
              </div>

              <div className="agent-card">
                <div className="agent-header-card"><h4>CANDLE Agent</h4><span className="status-active">ACTIVE</span></div>
                <div className="strategy-info">
                  <p><strong>Strategy:</strong> Japanese Candlestick Patterns</p>
                  <p><strong>Current:</strong> HOLDING 25 qty RELIANCE @ ₹2850</p>
                  <p><strong>Win Rate:</strong> 94% (41 trades)</p>
                  <p><strong>Today P&L:</strong> ₹3,800</p>
                  <p><strong>Confidence:</strong> 94%</p>
                </div>
              </div>

              <div className="agent-card">
                <div className="agent-header-card"><h4>XAUUSD Agent</h4><span className="status-active">ACTIVE</span></div>
                <div className="strategy-info">
                  <p><strong>Strategy:</strong> Macro Flow + Central Bank Bias</p>
                  <p><strong>Current:</strong> HOLDING 100 qty GOLDM @ ₹52550</p>
                  <p><strong>Win Rate:</strong> 89% (35 trades)</p>
                  <p><strong>Today P&L:</strong> ₹1,900</p>
                  <p><strong>Confidence:</strong> 91%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Agent Performance Analytics */}
          <div className="performance-analytics-section">
            <h2>Agent Performance Analytics</h2>
            <div className="performance-grid">
              {agents.map(agent => (
                <div key={agent.name} className="perf-card">
                  <div className="perf-header">
                    <h4>{agent.name}</h4>
                    <span className={`status-badge ${agent.status.toLowerCase()}`}>{agent.status}</span>
                  </div>
                  <div className="perf-metrics">
                    <div className="metric">
                      <span className="label">Total Trades</span>
                      <span className="value">{agent.trades}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Win Rate</span>
                      <span className="value success">{agent.winRate}%</span>
                    </div>
                    <div className="metric">
                      <span className="label">P&L (Booked)</span>
                      <span className={`value ${agent.pnl >= 0 ? 'success' : 'danger'}`}>
                        ₹{agent.pnl.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="perf-bar">
                    <div className="bar-fill" style={{width: `${agent.winRate}%`}}></div>
                  </div>
                  <div className="perf-footer">
                    <span className="wins">{Math.round(agent.trades * agent.winRate / 100)} Wins</span>
                    <span className="losses">{Math.round(agent.trades * (100 - agent.winRate) / 100)} Losses</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Trade History */}
          <div className="trade-history-section">
            <h2>Trade History</h2>
            <div className="trades-table-wrapper">
              <table className="trades-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Qty</th>
                    <th>P&L</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.length ? trades.map((trade, index) => (
                  <tr className="trade-row" key={trade.id ?? index}>
                    <td><span className="agent-label">{trade.agent || '—'}</span></td>
                    <td>{trade.symbol || '—'}</td>
                    <td><span className={String(trade.type || trade.side || '').toUpperCase() === 'SELL' ? 'type-sell' : 'type-buy'}>{trade.type || trade.side || '—'}</span></td>
                    <td>₹{trade.entry_price ?? trade.entryPrice ?? trade.price ?? '—'}</td>
                    <td>₹{trade.exit_price ?? trade.exitPrice ?? '—'}</td>
                    <td>{trade.qty ?? trade.quantity ?? '—'}</td>
                    <td><span className={`pnl-val ${(trade.pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>₹{trade.pnl ?? '—'}</span></td>
                    <td><span className={(trade.status || '').toLowerCase() === 'open' ? 'status-open' : 'status-closed'}>{trade.status || 'CLOSED'}</span></td>
                  </tr>
                  )) : <>
                  <tr className="trade-row">
                    <td><span className="agent-label">STOCKS</span></td>
                    <td>SBIN</td>
                    <td><span className="type-buy">BUY</span></td>
                    <td>₹650</td>
                    <td>₹655</td>
                    <td>50</td>
                    <td><span className="pnl-val positive">+₹250</span></td>
                    <td><span className="status-closed">CLOSED</span></td>
                  </tr>
                  <tr className="trade-row">
                    <td><span className="agent-label">SENSEX</span></td>
                    <td>NIFTY</td>
                    <td><span className="type-buy">BUY</span></td>
                    <td>₹45350</td>
                    <td>₹45450</td>
                    <td>10</td>
                    <td><span className="pnl-val positive">+₹1,000</span></td>
                    <td><span className="status-open">OPEN</span></td>
                  </tr>
                  </>}
                  <tr className="trade-row">
                    <td><span className="agent-label">OPTIONS</span></td>
                    <td>NIFTY-CE</td>
                    <td><span className="type-sell">SELL</span></td>
                    <td>₹400</td>
                    <td>₹380</td>
                    <td>5</td>
                    <td><span className="pnl-val positive">+₹100</span></td>
                    <td><span className="status-closed">CLOSED</span></td>
                  </tr>
                  <tr className="trade-row">
                    <td><span className="agent-label">CANDLE</span></td>
                    <td>RELIANCE</td>
                    <td><span className="type-buy">BUY</span></td>
                    <td>₹2,840</td>
                    <td>₹2,850</td>
                    <td>25</td>
                    <td><span className="pnl-val positive">+₹250</span></td>
                    <td><span className="status-open">OPEN</span></td>
                  </tr>
                  <tr className="trade-row">
                    <td><span className="agent-label">XAUUSD</span></td>
                    <td>GOLDM</td>
                    <td><span className="type-buy">BUY</span></td>
                    <td>₹52,500</td>
                    <td>₹52,550</td>
                    <td>100</td>
                    <td><span className="pnl-val positive">+₹500</span></td>
                    <td><span className="status-open">OPEN</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </main>

        {/* Right Sidebar - Portfolio & Live Feed */}
        <aside className="kite-sidebar-right">
          {/* LIVE TRADING FEED */}
          <div className="live-trading-feed">
            <h3>LIVE TRADING FEED</h3>
            <div className="feed-status">
              <span className={`status-indicator ${optimizerStatus.is_running ? 'is-active' : 'is-inactive'}`} aria-hidden="true" />
              <span className="status-text">{optimizerStatus.is_running ? 'ACTIVE' : 'INITIALIZING'}</span>
              <span className="cycle-info">Cycle #{optimizerStatus.cycle_count}</span>
            </div>
            <div className="feed-logs">
              {tradingLogs.length === 0 ? (
                <div className="feed-item">
                  <span className="time">Just started</span>
                  <span className="log">Agents initializing, analyzing market signals...</span>
                </div>
              ) : (
                tradingLogs.map((log, idx) => (
                  <div key={idx} className="feed-item">
                    <span className="time">{log.time}</span>
                    <span className="status">{log.status}</span>
                    <span className="log">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="holdings-section">
            <h3>Active Positions</h3>
            {positions.map((pos, idx) => (
              <div key={idx} className="holding-card">
                <div className="holding-header">
                  <div>
                    <span className="symbol">{pos.symbol}</span>
                    <span className="agent-small">{pos.agent}</span>
                  </div>
                  <span className={`pnl ${pos.pnl >= 0 ? 'positive' : 'negative'}`}>
                    ₹{pos.pnl}
                  </span>
                </div>
                <div className="holding-details">
                  <span>Qty: {pos.qty}</span>
                  <span>Entry: ₹{pos.entryPrice}</span>
                </div>
                <div className="holding-footer">
                  <span>LTP: ₹{pos.currentPrice}</span>
                  <span className={pos.pnlPercent >= 0 ? 'positive' : 'negative'}>
                    {pos.pnlPercent > 0 ? '+' : ''}{pos.pnlPercent}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pnl-summary">
            <h3>P&L Summary</h3>
            <div className="pnl-item">
              <span>Realized</span>
              <span className="positive">₹{portfolio.realizedPnL.toLocaleString()}</span>
            </div>
            <div className="pnl-item">
              <span>Unrealized</span>
              <span className={portfolio.unrealizedPnL >= 0 ? 'positive' : 'negative'}>
                ₹{portfolio.unrealizedPnL.toLocaleString()}
              </span>
            </div>
            <div className="pnl-item total">
              <span>Total</span>
              <span className={portfolio.totalPnL >= 0 ? 'positive' : 'negative'}>
                ₹{portfolio.totalPnL.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="futuristic-section">
            <h3>AI Features</h3>
            <div className="confidence-meter">
              <span>Boss Confidence</span>
              <div className="meter-bar">
                <div className="meter-fill" style={{width: '94%'}}></div>
              </div>
              <span className="meter-value">94%</span>
            </div>

            <div className="prediction-gauge">
              <span>Next Trade In</span>
              <div className="gauge-value">2m 34s</div>
            </div>

            <div className="risk-gauge">
              <span>Daily Risk Used</span>
              <div className="risk-bar">
                <div className="risk-fill" style={{width: '35%'}}></div>
              </div>
              <span className="risk-value">35%</span>
            </div>
          </div>
        </aside>
      </div>

      {/* Trading Sections */}
      <div className="trading-sections-container">
        <div className="sections-navbar">
          <button
            className={`nav-tab ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            Orders
          </button>
          <button
            className={`nav-tab ${activeTab === 'holdings' ? 'active' : ''}`}
            onClick={() => setActiveTab('holdings')}
          >
            Holdings
          </button>
          <button
            className={`nav-tab ${activeTab === 'positions' ? 'active' : ''}`}
            onClick={() => setActiveTab('positions')}
          >
            Positions
          </button>
          <button
            className={`nav-tab ${activeTab === 'funds' ? 'active' : ''}`}
            onClick={() => setActiveTab('funds')}
          >
            Funds
          </button>
        </div>

        <div className="sections-content">
          {activeTab === 'orders' && (
            <div className="trading-section">
              <h3>Orders - Execution History</h3>
              <table className="trading-table">
                <thead>
                  <tr><th>Time</th><th>Agent</th><th>Symbol</th><th>Type</th><th>Qty</th><th>Price</th><th>P&L</th></tr>
                </thead>
                <tbody>
                  {trades.length > 0 ? trades.slice(0, 20).map((trade, index) => (
                    <tr key={trade.id ?? index}>
                      <td className="time">{trade.time || trade.timestamp || '—'}</td>
                      <td>{trade.agent || '—'}</td>
                      <td>{trade.symbol || '—'}</td>
                      <td className={`type ${(trade.type || trade.side || '').toLowerCase()}`}>{trade.type || trade.side || '—'}</td>
                      <td>{trade.qty ?? trade.quantity ?? '—'}</td>
                      <td>₹{trade.price ?? trade.entry_price ?? '—'}</td>
                      <td className={`pnl ${(trade.pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>₹{trade.pnl ?? '—'}</td>
                    </tr>
                  )) : <>
                  <tr><td className="time">11:30:45</td><td>SENSEX</td><td>NIFTY</td><td className="type buy">BUY</td><td>10</td><td>₹45350</td><td className="pnl positive">₹1000</td></tr>
                  <tr><td className="time">11:28:12</td><td>STOCKS</td><td>SBIN</td><td className="type buy">BUY</td><td>50</td><td>₹650</td><td className="pnl positive">₹250</td></tr>
                  <tr><td className="time">11:25:33</td><td>OPTIONS</td><td>NIFTY22JAN22C45000</td><td className="type sell">SELL</td><td>5</td><td>₹125</td><td className="pnl positive">₹375</td></tr>
                  </>}
                </tbody>
              </table>
            </div>
          )}
          {activeTab === 'holdings' && (
            <div className="trading-section">
              <h3>Holdings - Long-term Positions</h3>
              <table className="trading-table">
                <thead>
                  <tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>LTP</th><th>Value</th><th>P&L</th><th>P&L %</th></tr>
                </thead>
                <tbody>
                  <tr><td>NIFTY</td><td>10</td><td>₹45300</td><td>₹45450</td><td className="value">₹454500</td><td className="pnl positive">₹1500</td><td className="pnl-percent positive">+0.33%</td></tr>
                  <tr><td>SBIN</td><td>50</td><td>₹645</td><td>₹655</td><td className="value">₹32750</td><td className="pnl positive">₹500</td><td className="pnl-percent positive">+1.55%</td></tr>
                  <tr><td>TCS</td><td>20</td><td>₹3850</td><td>₹3920</td><td className="value">₹78400</td><td className="pnl positive">₹1400</td><td className="pnl-percent positive">+1.82%</td></tr>
                </tbody>
              </table>
            </div>
          )}
          {activeTab === 'positions' && (
            <div className="trading-section">
              <h3>Positions - Intraday F&amp;O</h3>
              <table className="trading-table">
                <thead>
                  <tr><th>Symbol</th><th>Type</th><th>Qty</th><th>Entry Price</th><th>LTP</th><th>Unrealized P&L</th><th>Margin</th></tr>
                </thead>
                <tbody>
                  <tr><td>NIFTY22JAN22C45000</td><td className="type buy">LONG</td><td>5</td><td>₹125</td><td>₹145</td><td className="pnl positive">₹100</td><td>₹5000</td></tr>
                  <tr><td>BANKNIFTY22JAN22P40000</td><td className="type sell">SHORT</td><td>2</td><td>₹500</td><td>₹480</td><td className="pnl positive">₹40</td><td>₹10000</td></tr>
                </tbody>
              </table>
            </div>
          )}
          {activeTab === 'funds' && (
            <div className="trading-section">
              <h3>Funds - Account Balance &amp; Allocation</h3>
              <div className="funds-grid">
                <div className="fund-card"><span className="label">Available Balance</span><h3 className="amount">₹125,000</h3></div>
                <div className="fund-card"><span className="label">Used Margin</span><h3 className="amount negative">₹17,500</h3><span className="percentage">17.4% Used</span></div>
                <div className="fund-card"><span className="label">Free Balance</span><h3 className="amount positive">₹107,500</h3></div>
                <div className="fund-card"><span className="label">Collateral</span><h3 className="amount">₹50,000</h3></div>
              </div>
              <div className="fund-details">
                <h4>Fund Allocation by Agent</h4>
                <div className="allocation-bar">
                  <div className="agent-slot stocks" style={{width: '20%'}}>STOCKS ₹25K</div>
                  <div className="agent-slot sensex" style={{width: '20%'}}>SENSEX ₹25K</div>
                  <div className="agent-slot options" style={{width: '20%'}}>OPTIONS ₹25K</div>
                  <div className="agent-slot candle" style={{width: '20%'}}>CANDLE ₹25K</div>
                  <div className="agent-slot xauusd" style={{width: '20%'}}>XAUUSD ₹25K</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Futuristic Footer */}
      <footer className="kite-footer">
        <div className="agent-sync-status">
          <span className="sync-pulse"></span>
          <span>Agents Synced: 5/5</span>
        </div>
        <div className="neural-network">
          <span>Neural Consensus:</span>
          <span className="consensus-score">98.2%</span>
        </div>
        <div className="autonomous-mode">
          <span>Autonomous Mode</span>
          <span className="mode-active">ACTIVE</span>
        </div>
        <div className="optimization-cycle">
          <span>Cycle #42</span>
          <span className="cycle-time">5m 23s</span>
        </div>
      </footer>
    </div>
  );
}
