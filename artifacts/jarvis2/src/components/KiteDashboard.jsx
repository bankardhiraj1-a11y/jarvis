import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Archive,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Download,
  Receipt,
  RefreshCw,
  Search,
  UsersRound,
} from 'lucide-react';
import ChargesTab from './ChargesTab.jsx';
import './KiteDashboard.css';

const API_ROOT = '/jarvis2-api';
const COMMON_AGENTS = ['STOCKS', 'SENSEX', 'OPTIONS', 'XAUUSD', 'SENSEX_OPTIONS_SCALPING'];
const AGENT_ORDER = ['STOCKS', 'SENSEX', 'OPTIONS', 'XAUUSD', 'SENSEX_OPTIONS_SCALPING', 'CANDLE'];
const emptyPortfolio = null;

function currency(value, code = 'INR') {
  if (value === null || value === undefined || value === '') return '—';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '—';
  const formatted = amount.toLocaleString(code === 'USD' ? 'en-US' : 'en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${code === 'USD' ? '$' : '₹'}${formatted}`;
}

function timeLabel(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('en-GB', {
    timeZone: 'UTC',
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).replace(',', '');
}

function signedCurrency(value, code = 'INR') {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '—';
  return `${amount > 0 ? '+' : ''}${currency(amount, code)}`;
}

function tradeQuantity(trade) {
  if (trade.agent !== 'XAUUSD') return trade.quantity ?? '—';
  const ounces = Number(trade.quantity_troy_ounces ?? trade.quantity);
  if (!Number.isFinite(ounces) || ounces <= 0) return '—';
  const lots = Number(trade.quantity_lots ?? ounces / 100);
  return `${Number(lots.toFixed(2))} lot · ${Number(ounces.toFixed(2))} oz`;
}

function formatAgent(agent) {
  return agent === 'SENSEX_OPTIONS_SCALPING' ? 'SENSEX SCALPING' : agent || '—';
}

function csvCell(value) {
  let text = value === null || value === undefined ? '' : String(value);
  if (typeof value === 'string' && /^[\t\r ]*[=+\-@]/.test(text)) {
    text = `'${text}`;
  }
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadCsv(filename, headers, rows) {
  const contents = [headers, ...rows]
    .map((row) => row.map(csvCell).join(','))
    .join('\r\n');
  const blob = new Blob([`\uFEFF${contents}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export default function KiteDashboard() {
  const [portfolio, setPortfolio] = useState(emptyPortfolio);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState({});
  const [activeTab, setActiveTab] = useState('active');
  const [agentFilter, setAgentFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('time');
  const [sortDirection, setSortDirection] = useState('desc');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [clock, setClock] = useState(() => new Date());
  const inFlight = useRef(false);
  const hasLoaded = useRef(false);

  const refresh = useCallback(async (manual = false) => {
    if (inFlight.current) return;
    inFlight.current = true;
    if (manual && hasLoaded.current) setRefreshing(true);
    try {
      const endpoints = [
        fetch(`${API_ROOT}/portfolio`, { credentials: 'include' }),
        fetch(`${API_ROOT}/trades`, { credentials: 'include' }),
        fetch(`${API_ROOT}/agents/performance`, { credentials: 'include' }),
      ];
      const responses = await Promise.allSettled(endpoints);
      const failed = [];
      const payloads = await Promise.all(responses.map(async (result, index) => {
        const names = ['portfolio', 'trades', 'agent performance'];
        if (result.status === 'rejected') {
          failed.push(names[index]);
          return null;
        }
        if (!result.value.ok) {
          failed.push(names[index]);
          return null;
        }
        try {
          return await result.value.json();
        } catch {
          failed.push(names[index]);
          return null;
        }
      }));

      if (payloads[0] && typeof payloads[0] === 'object') setPortfolio(payloads[0]);
      if (Array.isArray(payloads[1])) setTrades(payloads[1]);
      else if (payloads[1] !== null) failed.push('trades response');
      if (payloads[2] && typeof payloads[2] === 'object' && !Array.isArray(payloads[2])) {
        setPerformance(payloads[2]);
      }
      setError(failed.length ? `Unable to refresh ${[...new Set(failed)].join(', ')}. Showing the latest available data.` : '');
      if (!failed.length) setLastUpdated(new Date());
      hasLoaded.current = true;
    } catch {
      setError('Could not reach the paper-trading service. Check the connection and try again.');
    } finally {
      inFlight.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const poll = window.setInterval(() => refresh(), 5000);
    const ticker = window.setInterval(() => setClock(new Date()), 1000);
    return () => {
      window.clearInterval(poll);
      window.clearInterval(ticker);
    };
  }, [refresh]);

  const openTrades = useMemo(() => trades.filter((trade) => String(trade.status || '').toUpperCase() === 'OPEN'), [trades]);
  const closedTrades = useMemo(() => trades.filter((trade) => String(trade.status || '').toUpperCase() === 'CLOSED'), [trades]);

  const agentNames = useMemo(() => {
    const names = new Set([
      ...Object.keys(performance || {}),
      ...trades.map((trade) => trade.agent).filter(Boolean),
    ]);
    if (!names.size) return COMMON_AGENTS;
    return [...names].sort((left, right) => {
      const leftRank = AGENT_ORDER.indexOf(left);
      const rightRank = AGENT_ORDER.indexOf(right);
      const normalizedLeftRank = leftRank === -1 ? AGENT_ORDER.length : leftRank;
      const normalizedRightRank = rightRank === -1 ? AGENT_ORDER.length : rightRank;
      return normalizedLeftRank - normalizedRightRank || left.localeCompare(right);
    });
  }, [performance, trades]);

  const usdPortfolioPnl = portfolio?.pnl_by_currency?.total?.USD;
  const needsUnavailableFx = usdPortfolioPnl !== null
    && usdPortfolioPnl !== undefined
    && usdPortfolioPnl !== ''
    && Number(usdPortfolioPnl) !== 0
    && portfolio?.usd_inr_conversion?.status !== 'available';
  const totalPnl = !needsUnavailableFx
    && portfolio?.total_pnl !== null
    && portfolio?.total_pnl !== undefined
    && portfolio?.total_pnl !== ''
    && Number.isFinite(Number(portfolio.total_pnl))
    ? Number(portfolio.total_pnl)
    : null;
  const activeCount = openTrades.length;
  const closedWins = closedTrades.filter((trade) => Number(trade.pnl) > 0).length;
  const winRate = closedTrades.length
    ? (closedWins / closedTrades.length) * 100
    : null;
  const summary = [
    { label: 'Total P&L (INR)', value: currency(totalPnl), tone: totalPnl > 0 ? 'positive' : totalPnl < 0 ? 'negative' : '', id: 'pnl' },
    { label: 'Active Positions', value: String(activeCount), tone: '', id: 'active' },
    { label: 'Total Trades', value: String(trades.length), tone: '', id: 'trades' },
    { label: 'Win Rate', value: winRate === null ? '—' : `${winRate.toFixed(1)}%`, tone: '', id: 'win-rate' },
  ];

  const tabs = [
    { id: 'active', label: 'Active Positions', Icon: BriefcaseBusiness },
    { id: 'closed', label: 'Closed Trades', Icon: Archive },
    { id: 'agents', label: 'By Agent', Icon: UsersRound },
    { id: 'charges', label: 'Charges', Icon: Receipt },
  ];

  const resetFilterForTab = (tab) => {
    setActiveTab(tab);
    setAgentFilter('ALL');
  };

  const filteredRows = useMemo(() => {
    const source = activeTab === 'closed' ? closedTrades : openTrades;
    const query = searchTerm.trim().toLocaleLowerCase();
    return source.filter((trade) => {
      if (agentFilter !== 'ALL' && trade.agent !== agentFilter) return false;
      if (!query) return true;
      return [trade.symbol, trade.agent, formatAgent(trade.agent), trade.signal, trade.type, trade.status]
        .some((value) => String(value || '').toLocaleLowerCase().includes(query));
    });
  }, [activeTab, agentFilter, closedTrades, openTrades, searchTerm]);

  const sortedRows = useMemo(() => {
    const timestamp = (trade) => activeTab === 'closed'
      ? (trade.exit_time || trade.entry_time || trade.created_at)
      : (trade.entry_time || trade.created_at);
    const sortValue = (trade) => {
      switch (sortBy) {
        case 'symbol': return trade.symbol;
        case 'agent': return formatAgent(trade.agent);
        case 'signal': return trade.signal || trade.type;
        case 'quantity': return trade.quantity;
        case 'entry': return trade.entry_price;
        case 'price': return activeTab === 'closed' ? (trade.exit_price ?? trade.current_price) : trade.current_price;
        case 'pnl': return trade.pnl;
        case 'stop': return trade.stop_loss;
        case 'target': return trade.take_profit;
        case 'time': return timestamp(trade);
        default: return timestamp(trade);
      }
    };
    const valueForCompare = (value) => {
      if (value === null || value === undefined || value === '') return null;
      if (sortBy === 'time') {
        const dateValue = new Date(value).getTime();
        return Number.isFinite(dateValue) ? dateValue : null;
      }
      const numericValue = Number(value);
      return Number.isFinite(numericValue) && String(value).trim() !== '' ? numericValue : String(value);
    };
    return [...filteredRows].sort((left, right) => {
      const leftValue = valueForCompare(sortValue(left));
      const rightValue = valueForCompare(sortValue(right));
      if (leftValue === null) return rightValue === null ? 0 : 1;
      if (rightValue === null) return -1;
      const comparison = typeof leftValue === 'number' && typeof rightValue === 'number'
        ? leftValue - rightValue
        : String(leftValue).localeCompare(String(rightValue), undefined, { numeric: true, sensitivity: 'base' });
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [activeTab, filteredRows, sortBy, sortDirection]);

  const filteredAgentEntries = useMemo(() => {
    const query = searchTerm.trim().toLocaleLowerCase();
    return Object.entries(performance).filter(([agent, stats]) => {
      if (!query) return true;
      return [agent, formatAgent(agent), stats.status]
        .some((value) => String(value || '').toLocaleLowerCase().includes(query));
    });
  }, [performance, searchTerm]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortDirection((direction) => direction === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortDirection(['symbol', 'agent', 'signal'].includes(column) ? 'asc' : 'desc');
    }
  };

  const handleExport = () => {
    const dateStamp = new Date().toISOString().replace(/[:.]/g, '-');
    if (activeTab === 'agents') {
      const rows = filteredAgentEntries.map(([agent, stats]) => [
        agent,
        stats.status,
        stats.total_trades,
        stats.winning_trades,
        stats.losing_trades,
        stats.win_rate,
        stats.total_pnl,
        stats.currency,
        stats.confidence,
      ]);
      downloadCsv(`jarvis2-agent-performance-${dateStamp}.csv`, [
        'agent', 'status', 'total_trades', 'wins', 'losses', 'win_rate', 'total_pnl', 'currency', 'confidence',
      ], rows);
      return;
    }

    const rows = sortedRows.map((trade) => [
      trade.status,
      trade.symbol,
      trade.agent,
      trade.signal || trade.type,
      trade.quantity,
      trade.entry_price,
      activeTab === 'closed' ? (trade.exit_price ?? trade.current_price) : trade.current_price,
      trade.pnl,
      trade.pnl_percent,
      trade.currency,
      trade.stop_loss,
      trade.take_profit,
      trade.entry_time || trade.created_at,
      trade.exit_time,
    ]);
    downloadCsv(`jarvis2-${activeTab}-${dateStamp}.csv`, [
      'status', 'symbol', 'agent', 'side', 'quantity', 'entry_price', activeTab === 'closed' ? 'exit_price' : 'current_price',
      'pnl', 'pnl_percent', 'currency', 'stop_loss', 'take_profit', 'entry_time', 'exit_time',
    ], rows);
  };

  const visibleCount = activeTab === 'agents' ? filteredAgentEntries.length : sortedRows.length;

  return (
    <div className="kite-dashboard" data-testid="screen-jarvis-dashboard">
      <header className="kite-topbar">
        <div className="brand-cluster">
          <span
            className={`connection-dot${error ? ' is-offline' : loading ? ' is-connecting' : ''}`}
            role="status"
            aria-label={error ? 'Paper backend disconnected' : loading ? 'Connecting to paper backend' : 'Paper backend connected'}
            title={error ? 'Paper backend disconnected' : loading ? 'Connecting to paper backend' : 'Paper backend connected'}
          />
          <span className="brand-name">JARVIS 2 POSITIONS &amp; HISTORY</span>
          <span className="paper-badge" data-testid="badge-paper-mode">PAPER</span>
        </div>
        <div className="topbar-right">
          <span className="utc-clock" data-testid="text-utc-clock">{clock.toISOString().slice(11, 19)} UTC</span>
        </div>
      </header>

      <main className="dashboard-content">
        <section className="overview" aria-labelledby="page-title">
          <div className="title-line">
            <div>
              <h1 id="page-title">Live Positions &amp; Trade History</h1>
            </div>
          </div>
          <div className="summary-grid" data-testid="summary-metrics">
            {summary.map((item) => (
              <div className="summary-cell" key={item.id} data-testid={`metric-${item.id}`}>
                <strong className={item.tone}>{item.value}</strong>
                <span>{item.label}</span>
                {item.id === 'pnl' && portfolio?.usd_inr_conversion?.status === 'available' && (
                  <span>{`USD/INR ECB reference · ${portfolio.usd_inr_conversion.source_date}`}</span>
                )}
                {item.id === 'pnl' && portfolio?.usd_inr_conversion?.status === 'stale' && (
                  <span>{`USD/INR rate stale; total not reported · ${portfolio.usd_inr_conversion.source_date}`}</span>
                )}
                {item.id === 'pnl' && portfolio?.usd_inr_conversion?.total_pnl_conversion === 'fx_rate_unavailable_or_stale' && (
                  <span>USD/INR rate unavailable; total not reported</span>
                )}
                {item.id === 'pnl' && portfolio?.usd_inr_conversion?.total_pnl_conversion === 'not_required' && (
                  <span>No USD P&amp;L to convert</span>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="trade-browser">
          <nav className="tabs" aria-label="Trade views" data-testid="navigation-trade-tabs">
            {tabs.map(({ id, label, Icon }) => (
              <button
                className={`tab-button ${activeTab === id ? 'selected' : ''}`}
                key={id}
                type="button"
                onClick={() => resetFilterForTab(id)}
                aria-current={activeTab === id ? 'page' : undefined}
                data-testid={`tab-${id}`}
              >
                <Icon size={13} strokeWidth={2.2} />
                {label}
              </button>
            ))}
          </nav>

          {activeTab === 'charges' ? <ChargesTab /> : (<>
          {activeTab !== 'agents' && (
            <div className="filter-strip" role="group" aria-label="Filter trades by agent" data-testid="filters-agents">
              <button
                type="button"
                className={`filter-chip ${agentFilter === 'ALL' ? 'active' : ''}`}
                onClick={() => setAgentFilter('ALL')}
                data-testid="filter-agent-all"
              >
                All Agents
              </button>
              {agentNames.map((agent) => (
                <button
                  type="button"
                  className={`filter-chip ${agentFilter === agent ? 'active' : ''}`}
                  key={agent}
                  onClick={() => setAgentFilter(agent)}
                  data-testid={`filter-agent-${agent.toLowerCase()}`}
                >
                  {formatAgent(agent)}
                </button>
              ))}
            </div>
          )}

          <div className="table-toolbar" data-testid="toolbar-trades">
            <label className="search-field">
              <Search size={14} aria-hidden="true" />
              <input
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder={activeTab === 'agents' ? 'Search agents or status…' : 'Search symbol, agent, or side…'}
                aria-label={activeTab === 'agents' ? 'Search agents or status' : 'Search trades'}
                data-testid="input-search-trades"
              />
            </label>
            <div className="toolbar-actions">
              <span className="result-count" data-testid="text-result-count">
                {visibleCount} {activeTab === 'agents' ? 'agents' : activeTab === 'closed' ? 'trades' : 'positions'}
              </span>
              <span className="last-updated" data-testid="text-last-updated">
                {lastUpdated ? `Updated ${lastUpdated.toISOString().slice(11, 19)} UTC` : 'Waiting for data'}
              </span>
              <button
                className="toolbar-button"
                type="button"
                onClick={() => refresh(true)}
                disabled={loading || refreshing}
                aria-label="Refresh paper-trading data"
                data-testid="button-refresh-data"
              >
                <RefreshCw className={refreshing ? 'is-refreshing' : ''} size={13} />
                {refreshing ? 'Refreshing' : 'Refresh'}
              </button>
              <button
                className="toolbar-button export-button"
                type="button"
                onClick={handleExport}
                disabled={visibleCount === 0}
                data-testid="button-export-csv"
              >
                <Download size={13} />
                Export CSV
              </button>
            </div>
          </div>

          {error && (
            <div className="error-notice" role="status" data-testid="status-api-error">
              <span>{error}</span>
              <button type="button" onClick={() => refresh(true)} data-testid="button-retry">
                <RefreshCw className={refreshing ? 'is-refreshing' : ''} size={13} />
                {refreshing ? 'Retrying' : 'Retry'}
              </button>
            </div>
          )}

          {activeTab === 'agents' ? (
            <div className="agent-table-wrap" data-testid="table-agent-performance">
              <table className="trades-table agent-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Total Trades</th>
                    <th>Wins</th>
                    <th>Losses</th>
                    <th>Win Rate</th>
                    <th>Total P&amp;L</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && Object.keys(performance).length === 0 ? (
                    <tr><td colSpan="7"><div className="loading-state"><span className="skeleton-line" /><span className="skeleton-line short" /></div></td></tr>
                  ) : filteredAgentEntries.length ? filteredAgentEntries.map(([agent, stats]) => (
                    <tr key={agent} data-testid={`row-agent-${agent.toLowerCase()}`}>
                      <td className="symbol-cell">{formatAgent(agent)}</td>
                      <td><span className="status-label">{stats.status || '—'}</span>{stats.analyzing ? <span className="analyzing-label">ANALYZING</span> : null}</td>
                      <td>{stats.total_trades ?? '—'}</td>
                      <td>{stats.winning_trades ?? '—'}</td>
                      <td>{stats.losing_trades ?? '—'}</td>
                      <td>{stats.win_rate == null ? '—' : `${Number(stats.win_rate).toFixed(1)}%`}</td>
                      <td className={Number(stats.total_pnl) < 0 ? 'negative' : 'positive'}>
                        {stats.total_pnl == null ? '—' : signedCurrency(stats.total_pnl, stats.currency || 'INR')}
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan="7"><EmptyState
                      title={Object.keys(performance).length ? 'No matching agents' : 'No agent performance yet'}
                      detail={Object.keys(performance).length
                        ? `No agents match “${searchTerm.trim()}”.`
                        : 'Agent summaries will appear when the paper backend has recorded performance data.'}
                    /></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="trades-table-wrap" data-testid="table-trades-scroll">
              <table className="trades-table" data-testid="table-trades">
                <thead>
                  <tr>
                    <SortHeader column="symbol" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>Symbol / Contract</SortHeader>
                    <SortHeader column="agent" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>Agent</SortHeader>
                    <SortHeader column="signal" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>Signal</SortHeader>
                    <SortHeader column="quantity" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>Qty</SortHeader>
                    <SortHeader column="entry" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>Entry Price</SortHeader>
                    <SortHeader column="price" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>{activeTab === 'closed' ? 'Exit Price' : 'Current Price'}</SortHeader>
                    <SortHeader column="pnl" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>P&amp;L</SortHeader>
                    <SortHeader column="stop" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>SL</SortHeader>
                    <SortHeader column="target" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>TP</SortHeader>
                    <SortHeader column="time" sortBy={sortBy} sortDirection={sortDirection} onSort={handleSort}>{activeTab === 'closed' ? 'Exit Time' : 'Entry Time'}</SortHeader>
                  </tr>
                </thead>
                <tbody>
                  {loading && trades.length === 0 ? (
                    <tr><td colSpan="10"><div className="loading-state"><span className="skeleton-line" /><span className="skeleton-line" /><span className="skeleton-line short" /></div></td></tr>
                  ) : sortedRows.length ? sortedRows.map((trade) => {
                    const code = trade.currency || 'INR';
                    const isUnpricedOpen = activeTab !== 'closed'
                      && trade.current_price == null
                      && String(trade.status || '').toUpperCase() === 'OPEN';
                    const pnl = Number(trade.pnl);
                    const hasPnl = !isUnpricedOpen
                      && trade.pnl !== null
                      && trade.pnl !== undefined
                      && Number.isFinite(pnl);
                    const shownPrice = activeTab === 'closed'
                      ? (trade.exit_price ?? trade.current_price)
                      : trade.current_price;
                    return (
                      <tr key={trade.id} data-testid={`row-trade-${trade.id}`}>
                        <td className="symbol-cell" data-testid={`text-symbol-${trade.id}`}>{trade.symbol || '—'}</td>
                        <td><span className="agent-name-cell">{formatAgent(trade.agent)}</span></td>
                        <td><span className={`signal-label ${(trade.signal || trade.type || '').toUpperCase() === 'SELL' ? 'sell' : 'buy'}`}>{trade.signal || trade.type || '—'}</span></td>
                        <td>{tradeQuantity(trade)}</td>
                        <td>{currency(trade.entry_price, code)}</td>
                        <td>{currency(shownPrice, code)}</td>
                        <td className={hasPnl ? (pnl < 0 ? 'negative' : 'positive') : 'muted'} data-testid={`text-pnl-${trade.id}`}>
                          {hasPnl ? <>{signedCurrency(pnl, code)}{trade.pnl_percent != null ? <small className="pnl-percent">({Number(trade.pnl_percent).toFixed(2)}%)</small> : null}</> : '—'}
                        </td>
                        <td>{currency(trade.stop_loss, code)}</td>
                        <td>{currency(trade.take_profit, code)}</td>
                        <td className="time-cell">{timeLabel(activeTab === 'closed' ? (trade.exit_time || trade.entry_time || trade.created_at) : (trade.entry_time || trade.created_at))}</td>
                      </tr>
                    );
                  }) : (
                    <tr>
                      <td colSpan="10">
                        <EmptyState
                          title={searchTerm.trim() ? 'No matching trades' : activeTab === 'closed' ? 'No closed trades' : 'No active positions'}
                          detail={searchTerm.trim()
                            ? `No trades match “${searchTerm.trim()}”.`
                            : agentFilter === 'ALL'
                              ? 'The paper backend has not recorded any trades in this view.'
                              : `No ${activeTab === 'closed' ? 'closed trades' : 'open positions'} recorded for ${formatAgent(agentFilter)}.`}
                        />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          </>)}
        </section>
      </main>
    </div>
  );
}

function EmptyState({ title, detail }) {
  return (
    <div className="empty-state" data-testid="state-empty">
      <ChartNoAxesCombined size={18} aria-hidden="true" />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

function SortHeader({ column, sortBy, sortDirection, onSort, children }) {
  const active = sortBy === column;
  return (
    <th aria-sort={active ? (sortDirection === 'asc' ? 'ascending' : 'descending') : undefined}>
      <button className={`sort-header${active ? ' active' : ''}`} type="button" onClick={() => onSort(column)}>
        {children}
        <span className="sort-indicator" aria-hidden="true">{active ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}</span>
      </button>
    </th>
  );
}