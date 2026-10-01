import { useCallback, useEffect, useState } from 'react';
import { Calculator, ExternalLink, RefreshCw } from 'lucide-react';
import './ChargesTab.css';

const API_ROOT = '/jarvis2-api';
const sym = (c) => (c === 'USD' ? '$' : '₹');

function money(v, c = 'INR') {
  if (v === null || v === undefined || !Number.isFinite(Number(v))) return 'Unknown';
  return `${sym(c)}${Number(v).toLocaleString(c === 'USD' ? 'en-US' : 'en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

async function getJson(path, options) {
  const res = await fetch(`${API_ROOT}${path}`, { credentials: 'include', ...options });
  if (!res.ok) {
    let detail = '';
    try { const b = await res.json(); detail = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail || ''); } catch { /* ignore */ }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function calculateCharges(payload) {
  return getJson('/charges/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function Breakdown({ result, hypothetical }) {
  const c = result.currency;
  return (
    <div className="ch-result" data-testid="charges-breakdown">
      {hypothetical && <div className="ch-flag">Hypothetical preview. Prices are a manual or cached snapshot; not an actual trade and not saved.</div>}
      <div className="ch-table-wrap"><table className="trades-table ch-table">
        <thead><tr><th>Component</th><th>Amount</th><th>Basis</th><th>Type</th></tr></thead>
        <tbody>
          {result.components.map((x) => (
            <tr key={x.code}>
              <td className="symbol-cell">{x.label}</td>
              <td className={x.amount === null ? 'muted' : ''}>{x.amount === null ? 'Unknown' : money(x.amount, x.currency || c)}</td>
              <td className="ch-basis">{x.basis || '—'}</td>
              <td>{x.additional ? 'Additional' : 'Embedded'}</td>
            </tr>
          ))}
          {!result.components.length && <tr><td colSpan="4" className="muted">No components returned.</td></tr>}
        </tbody>
      </table></div>
      <div className="ch-totals">
        <div><span>Embedded spread (already in price)</span><strong>{money(result.embedded_spread_cost, c)}</strong></div>
        <div><span>Known additional charges</span><strong>{money(result.known_additional_charges, c)}</strong></div>
        <div><span>Total additional charges</span><strong>{result.total_additional_charges === null ? 'Unknown' : money(result.total_additional_charges, c)}</strong></div>
        <div><span>Price P&amp;L before additional fees</span><strong>{money(result.price_pnl_before_additional_fees, c)}</strong></div>
        <div><span>{result.complete ? 'Net P&L (complete)' : 'Net P&L'}</span><strong>{result.net_pnl === null ? 'Unknown' : money(result.net_pnl, c)}</strong></div>
        <div><span>Net after known charges only</span><strong>{money(result.net_pnl_after_known_charges, c)}</strong></div>
      </div>
      <div className={`ch-status ${result.complete ? 'ok' : 'warn'}`}>
        {result.complete ? 'Complete estimate' : 'Partial estimate: at least one fee is unknown, so net P&L is not reported as final.'}
      </div>
      {(result.notes || []).map((n, i) => <p className="ch-note" key={i}>{n}</p>)}
      <SourceLinks sources={result.sources} />
    </div>
  );
}

function SourceLinks({ sources }) {
  if (!Array.isArray(sources) || !sources.length) return null;
  return (
    <div className="ch-sources">
      {sources.map((s, i) => {
        const url = s.url;
        const label = s.name || url || `Source ${i + 1}`;
        return url ? (
          <a key={i} href={url} target="_blank" rel="noreferrer noopener">{label}{s.as_of ? ` · ${s.as_of}` : ''}<ExternalLink size={11} /></a>
        ) : <span key={i}>{label}</span>;
      })}
    </div>
  );
}

const QUOTE_MAX_AGE_S = 20;
function quoteAge(q, now) {
  const t = q && Date.parse(q.timestamp);
  return Number.isFinite(t) ? (now - t) / 1000 : null;
}
function freshQuote(q, now) {
  if (!q || !(Number(q.bid) > 0) || !(Number(q.ask) > 0)) return false;
  const a = quoteAge(q, now);
  return a !== null && a >= -2 && a <= QUOTE_MAX_AGE_S;
}

function Row({ k, v }) {
  return <div className="ch-row"><span>{k}</span><strong>{v}</strong></div>;
}

function GoldRules({ gold, now, onRefresh }) {
  const q = gold?.quote;
  const m = gold?.cost_metadata || {};
  return (
    <div className="ch-card" data-testid="card-gold-rules">
      <h3>XAUUSD · OANDA XAU_USD · USD</h3>
      <Row k="Contract" v={`${gold?.lot_size_troy_ounces || 100} oz = 1 lot`} />
      {q ? (
        <>
          <Row k="Cached bid" v={money(q.bid, 'USD')} />
          <Row k="Cached ask" v={money(q.ask, 'USD')} />
          <Row k="Provider timestamp" v={`${q.timestamp} (${Math.max(0, Math.round(quoteAge(q, now)))}s old)`} />
          <Row k="Autofill" v={freshQuote(q, now) ? 'Fresh; BUY uses ask, SELL uses bid' : `Stale (over ${QUOTE_MAX_AGE_S}s); manual snapshot only`} />
        </>
      ) : <Row k="Cached quote" v="Unavailable; enter prices manually" />}
      <Row k="Fee metadata" v={m.status || 'unknown'} />
      <Row k="Commission" v={m.commission || 'unknown'} />
      <Row k="Financing" v={m.financing || 'unknown'} />
      {gold?.weekday_charges != null && <Row k="Weekday charges" v={typeof gold.weekday_charges === 'object' ? Object.entries(gold.weekday_charges).map(([k, x]) => `${k} ${x}`).join(' · ') : String(gold.weekday_charges)} />}
      {gold?.schedule != null && <Row k="Schedule" v={typeof gold.schedule === 'object' ? Object.entries(gold.schedule).map(([k, x]) => `${k} ${typeof x === 'object' ? JSON.stringify(x) : x}`).join(' · ') : String(gold.schedule)} />}
      {m.as_of && <Row k="Metadata as of" v={m.as_of} />}
      <button className="toolbar-button" type="button" onClick={onRefresh} data-testid="button-refresh-quote"><RefreshCw size={13} />Refresh quote</button>
      <p className="ch-note">Unknown fees stay unknown and are never counted as zero.</p>
    </div>
  );
}

function IndiaRules({ rules, asOf }) {
  if (!rules) return null;
  const text = (v) => (typeof v === 'string' ? v : Object.entries(v || {}).map(([k, x]) => `${k} ${x}`).join(' · '));
  const products = ['equity_intraday', 'equity_delivery', 'index_options'];
  return (
    <div className="ch-card" data-testid="card-india-rules">
      <h3>India · Zerodha reference · INR</h3>
      <Row k="As of" v={asOf || 'unknown'} />
      <p className="ch-note">{rules.broker_reference}</p>
      {products.map((p) => (
        <div key={p} className="ch-rule-group">
          <h4>{p.replace('_', ' ')}</h4>
          <Row k="Brokerage" v={text(rules.brokerage?.[p])} />
          {Object.entries(rules[p] || {}).map(([k, v]) => <Row key={k} k={k.replace(/_/g, ' ')} v={text(v)} />)}
        </div>
      ))}
      <div className="ch-rule-group">
        <h4>common</h4>
        {Object.entries(rules.common || {}).map(([k, v]) => <Row key={k} k={k} v={text(v)} />)}
      </div>
      {(rules.limitations || []).map((n, i) => <p className="ch-note" key={i}>{n}</p>)}
    </div>
  );
}

export default function ChargesTab() {
  const [rules, setRules] = useState(null);
  const [tradeData, setTradeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(() => Date.now());
  const [error, setError] = useState('');
  const [form, setForm] = useState({ market: 'INDIA', product: 'equity_intraday', exchange: 'NSE', quantity: '', entry_price: '', exit_price: '', side: 'BUY', entry_orders: '1', exit_orders: '1', entry_time: '', exit_time: '', dp: false });
  const [preview, setPreview] = useState(null);
  const [calcError, setCalcError] = useState('');
  const [calcBusy, setCalcBusy] = useState(false);

  const load = useCallback(async (background = false) => {
    if (!background) setLoading(true);
    try {
      const [r, t] = await Promise.all([getJson('/charges/rules'), getJson('/charges/trades')]);
      setRules(r);
      setTradeData(t);
      setError('');
      setNow(Date.now());
      const q = freshQuote(r?.gold?.quote, Date.now()) ? r.gold.quote : null;
      const lt = r?.gold?.lot_size_troy_ounces || 100;
      setForm((f) => {
        if (f.market !== 'XAUUSD' || f.entry_price || !q) return f;
        const px = f.side === 'SELL' ? q.bid : q.ask;
        return { ...f, quantity: String(lt), entry_price: px > 0 ? String(px) : '' };
      });
    } catch (e) {
      setError(e.message || 'Could not load charges data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const poll = window.setInterval(() => load(true), 45000);
    const tick = window.setInterval(() => setNow(Date.now()), 5000);
    return () => { window.clearInterval(poll); window.clearInterval(tick); };
  }, [load]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const lot = rules?.gold?.lot_size_troy_ounces || 100;
  const quote = rules?.gold?.quote;
  const hasQuote = freshQuote(quote, now);
  const entrySidePrice = (side) => (hasQuote ? String(side === 'SELL' ? quote.bid : quote.ask) : '');
  const exitSidePrice = (side) => (hasQuote ? String(side === 'SELL' ? quote.ask : quote.bid) : '');
  const changeSide = (side) => setForm((f) => (f.market === 'XAUUSD' && hasQuote
    ? { ...f, side, entry_price: entrySidePrice(side), exit_price: '' } : { ...f, side }));

  const switchMarket = (market) => {
    setPreview(null); setCalcError('');
    if (market === 'XAUUSD') {
      setForm((f) => ({ ...f, market, product: '', exchange: '', quantity: String(lot), entry_price: entrySidePrice(f.side), exit_price: '', entry_time: '', exit_time: '' }));
    } else {
      setForm((f) => ({ ...f, market, product: 'equity_intraday', exchange: 'NSE', quantity: '', entry_price: '', exit_price: '' }));
    }
  };

  const validate = () => {
    const q = Number(form.quantity), e = Number(form.entry_price);
    if (!(q > 0)) return 'Quantity must be greater than zero.';
    if (!(e > 0)) return 'Entry price must be greater than zero.';
    if (form.exit_price !== '' && !(Number(form.exit_price) > 0)) return 'Exit price must be positive when provided.';
    if (form.entry_time && form.exit_time && new Date(form.exit_time) <= new Date(form.entry_time)) return 'Exit time must be after entry time.';
    if (form.market === 'INDIA') {
      if (!['equity_intraday', 'equity_delivery', 'index_options'].includes(form.product)) return 'Choose a product.';
      if (!['NSE', 'BSE'].includes(form.exchange)) return 'Choose an exchange.';
      if (!Number.isInteger(q)) return 'Indian quantity must be a whole number.';
      for (const k of ['entry_orders', 'exit_orders']) {
        const n = Number(form[k]);
        if (!Number.isInteger(n) || n < 1) return 'Order counts must be whole numbers of at least 1.';
      }
    }
    return '';
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const problem = validate();
    setCalcError(problem);
    if (problem) return;
    const body = { market: form.market, quantity: Number(form.quantity), entry_price: Number(form.entry_price), side: form.side,
      entry_orders: Number(form.entry_orders), exit_orders: Number(form.exit_orders) };
    if (form.market === 'INDIA') { body.product = form.product; body.exchange = form.exchange; }
    if (form.market === 'INDIA' && form.product === 'equity_delivery' && form.dp) body.dp_scrips = 1;
    if (form.exit_price !== '') body.exit_price = Number(form.exit_price);
    if (form.market === 'XAUUSD') {
      for (const k of ['entry_time', 'exit_time']) {
        if (form[k]) { const d = new Date(form[k]); if (!Number.isNaN(d.getTime())) body[k] = d.toISOString(); }
      }
    }
    setCalcBusy(true);
    try { setPreview(await calculateCharges(body)); } catch (e) { setPreview(null); setCalcError(e.message); } finally { setCalcBusy(false); }
  };

  const trades = tradeData?.trades || [];
  const gold = form.market === 'XAUUSD';

  return (
    <div className="charges-tab" data-testid="panel-charges">
      {error && (
        <div className="error-notice" role="status" data-testid="status-charges-error">
          <span>{error}</span>
          <button type="button" onClick={() => load()} data-testid="button-charges-retry"><RefreshCw size={13} />Retry</button>
        </div>
      )}
      <div className="ch-policy" data-testid="text-charges-policy">
        Policy: options and Sensex run same-day intraday only, flat by 15:20 IST. Stocks run a hold strategy; the backend sizes entries after fees and requires positive expected net profit. Gold is traded only when the strategy needs it, max 25 min, not held overnight by default.
      </div>

      {loading && !rules ? (
        <div className="loading-state"><span className="skeleton-line" /><span className="skeleton-line" /><span className="skeleton-line short" /></div>
      ) : rules && (
        <section className="ch-section" data-testid="section-charge-rules">
          <h2>Rules</h2>
          <div className="ch-grid">
            <GoldRules gold={rules.gold} now={now} onRefresh={() => load(true)} />
            <IndiaRules rules={rules.indian_rules} asOf={rules.as_of} />
          </div>
          <SourceLinks sources={rules.sources} />
          {(rules.notes || []).map((n, i) => <p className="ch-note" key={i}>{n}</p>)}
        </section>
      )}

      <section className="ch-section" data-testid="section-charge-calculator">
        <h2>Calculator <span className="ch-tag">Hypothetical preview</span></h2>
        <form className="ch-form" onSubmit={submit} noValidate>
          <label>Market
            <select value={form.market} onChange={(e) => switchMarket(e.target.value)} data-testid="select-charges-market">
              <option value="INDIA">India (INR)</option>
              <option value="XAUUSD">XAUUSD (USD)</option>
            </select>
          </label>
          {!gold && (
            <>
              <label>Product
                <select value={form.product} onChange={(e) => set('product', e.target.value)} data-testid="select-charges-product">
                  <option value="equity_intraday">Equity intraday</option>
                  <option value="equity_delivery">Equity delivery</option>
                  <option value="index_options">Index options</option>
                </select>
              </label>
              <label>Exchange
                <select value={form.exchange} onChange={(e) => set('exchange', e.target.value)} data-testid="select-charges-exchange">
                  <option value="NSE">NSE</option><option value="BSE">BSE</option>
                </select>
              </label>
            </>
          )}
          <label>Side
            <select value={form.side} onChange={(e) => changeSide(e.target.value)} data-testid="select-charges-side">
              <option value="BUY">BUY</option><option value="SELL">SELL</option>
            </select>
          </label>
          <label>{gold ? `Quantity (oz, ${lot} = 1 lot)` : 'Quantity'}
            <input type="number" min="0" step="any" value={form.quantity} onChange={(e) => set('quantity', e.target.value)} data-testid="input-charges-quantity" />
          </label>
          <label>Entry price
            <input type="number" min="0" step="any" value={form.entry_price} onChange={(e) => set('entry_price', e.target.value)} placeholder={gold && !hasQuote ? 'No fresh quote: enter manually' : ''} data-testid="input-charges-entry" />
          </label>
          <label>Exit price (optional)
            <input type="number" min="0" step="any" value={form.exit_price} onChange={(e) => set('exit_price', e.target.value)} data-testid="input-charges-exit" />
          </label>
          <label>Entry orders
            <input type="number" min="1" step="1" value={form.entry_orders} onChange={(e) => set('entry_orders', e.target.value)} data-testid="input-charges-entry-orders" />
          </label>
          <label>Exit orders
            <input type="number" min="1" step="1" value={form.exit_orders} onChange={(e) => set('exit_orders', e.target.value)} data-testid="input-charges-exit-orders" />
          </label>
          {gold && (
            <>
              <label>Entry time (optional, local)
                <input type="datetime-local" value={form.entry_time} onChange={(e) => set('entry_time', e.target.value)} data-testid="input-charges-entry-time" />
              </label>
              <label>Exit time (optional, local)
                <input type="datetime-local" value={form.exit_time} onChange={(e) => set('exit_time', e.target.value)} data-testid="input-charges-exit-time" />
              </label>
              <div className="ch-actions">
                <button className="toolbar-button" type="button" disabled={!hasQuote} onClick={() => set('exit_price', exitSidePrice(form.side))} data-testid="button-charges-cached-exit">
                  Use cached {form.side === 'SELL' ? 'ask' : 'bid'} for exit preview
                </button>
              </div>
            </>
          )}
          {!gold && form.product === 'equity_delivery' && (
            <label className="ch-check">
              <span><input type="checkbox" checked={form.dp} onChange={(e) => set('dp', e.target.checked)} data-testid="checkbox-charges-dp" /> Estimate published DP fee for one scrip (₹15.34)</span>
              <small>{form.dp ? 'Assumption: published standard DP fee for one scrip. Not verified against an actual account invoice, ISIN or same-day duplicates.' : 'Off: DP fee stays unknown, so net P&L is not reported as final.'}</small>
            </label>
          )}
          <div className="ch-actions">
            <button className="toolbar-button" type="submit" disabled={calcBusy} data-testid="button-charges-calculate"><Calculator size={13} />{calcBusy ? 'Calculating' : preview ? 'Recompute' : 'Calculate'}</button>
          </div>
        </form>
        {calcError && <div className="error-notice" role="status" data-testid="status-calc-error"><span>{calcError}</span></div>}
        {preview && <Breakdown result={preview} hypothetical />}
      </section>

      <section className="ch-section" data-testid="section-charge-trades">
        <h2>Actual trades</h2>
        {loading && !tradeData ? null : trades.length === 0 ? (
          <div className="empty-state" data-testid="state-charges-empty">
            <strong>No actual trades to show charges for</strong>
            <span>Charges appear here once the paper backend records trades. Calculator previews are never saved as trades.</span>
          </div>
        ) : trades.map((t) => (
          <details className="ch-trade" key={t.trade_id} data-testid={`row-charge-trade-${t.trade_id}`}>
            <summary>
              <span className="symbol-cell">{t.symbol}</span>
              <span>{t.agent}</span>
              <span>{t.status}</span>
              <span>{t.charges?.net_pnl == null ? 'Net unknown' : `Net ${money(t.charges.net_pnl, t.currency)}`}</span>
            </summary>
            {t.charges && <Breakdown result={t.charges} />}
          </details>
        ))}
        {tradeData?.limit != null && <p className="ch-note">Showing up to {tradeData.limit} trades.</p>}
        {tradeData?.fees_basis && <p className="ch-note">Fees basis: {typeof tradeData.fees_basis === 'string' ? tradeData.fees_basis : JSON.stringify(tradeData.fees_basis)}</p>}
        {(tradeData?.notes || []).map((n, i) => <p className="ch-note" key={i}>{n}</p>)}
      </section>
    </div>
  );
}
