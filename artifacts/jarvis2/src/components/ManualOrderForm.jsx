import { useEffect, useMemo, useState } from 'react';

const OPTION_UNDERLYINGS = ['SENSEX', 'NIFTY', 'BANKNIFTY', 'FINNIFTY'];
const ALLOWED_MARKETS = new Set(['GOLD', 'STOCKS', 'OPTIONS']);

function errorMessage(payload, fallback) {
  const detail = payload?.detail || payload?.message || payload?.error;
  return detail ? String(detail) : fallback;
}

function readMarkets(payload) {
  if (payload?.mode !== 'PAPER' || !Array.isArray(payload.markets)) {
    throw new Error('Order configuration is unavailable or is not in PAPER mode.');
  }
  const markets = payload.markets
    .filter((market) => ALLOWED_MARKETS.has(market?.value) && Array.isArray(market.symbols))
    .map((market) => ({
      ...market,
      symbols: market.symbols.filter((symbol) => typeof symbol === 'string' && symbol.trim()),
    }));
  if (!markets.length) throw new Error('Order configuration did not include any supported markets.');
  return markets;
}

function positiveNumber(value) {
  const number = Number(value);
  return value !== '' && Number.isFinite(number) && number > 0;
}

export default function ManualOrderForm({ apiRoot, onSuccess, onClose }) {
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState('');
  const [market, setMarket] = useState('');
  const [symbol, setSymbol] = useState('');
  const [side, setSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [entryPrice, setEntryPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [takeProfitTwo, setTakeProfitTwo] = useState('');
  const [quantity, setQuantity] = useState('15');
  const [quantityLots, setQuantityLots] = useState('1');
  const [optionType, setOptionType] = useState('CE');
  const [strike, setStrike] = useState('');
  const [expiry, setExpiry] = useState('');
  const [maxHoldMinutes, setMaxHoldMinutes] = useState('25');
  const [clientOrderId, setClientOrderId] = useState(() => globalThis.crypto?.randomUUID?.() || '');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submission, setSubmission] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await fetch(`${apiRoot}/paper/order-config`, { credentials: 'include' });
        if (!response.ok) throw new Error(`Order configuration request failed (HTTP ${response.status}).`);
        const payload = await response.json();
        const markets = readMarkets(payload);
        if (active) {
          setConfig({ ...payload, markets });
          setMarket(markets[0].value);
          setSymbol(markets[0].symbols[0] || '');
          setMaxHoldMinutes(markets[0].value === 'GOLD' ? '25' : '20');
          setQuantity(markets[0].value === 'GOLD' ? '15' : '1');
        }
      } catch (requestError) {
        if (active) {
          setConfigError(requestError instanceof Error
            ? requestError.message
            : 'Could not load paper order configuration.');
        }
      }
    })();
    return () => { active = false; };
  }, [apiRoot]);

  const selectedMarket = config?.markets.find((item) => item.value === market);
  const symbols = selectedMarket?.symbols || [];
  const optionUnderlyings = useMemo(
    () => OPTION_UNDERLYINGS.filter((underlying) => symbols.includes(underlying)),
    [symbols],
  );
  const availableSymbols = market === 'OPTIONS' ? optionUnderlyings : symbols;
  const isOption = market === 'OPTIONS';
  const isGold = market === 'GOLD';
  const holdMaximum = 25;
  const configuredRisk = config?.risk_limits?.[market];
  const canSubmit = Boolean(
    config
    && !configError
    && availableSymbols.length
    && clientOrderId
    && !submitting,
  );

  const handleMarketChange = (nextMarket) => {
    setSubmitError('');
    setMarket(nextMarket);
    const nextConfig = config?.markets.find((item) => item.value === nextMarket);
    const nextSymbols = nextMarket === 'OPTIONS'
      ? OPTION_UNDERLYINGS.filter((underlying) => nextConfig?.symbols.includes(underlying))
      : (nextConfig?.symbols || []);
    setSymbol(nextSymbols[0] || '');
    setMaxHoldMinutes(nextMarket === 'GOLD' ? '25' : '20');
    setQuantity(nextMarket === 'GOLD' ? '15' : '1');
    setTakeProfitTwo('');
  };

  const validate = () => {
    if (!selectedMarket || !availableSymbols.includes(symbol)) return 'Choose an instrument from the loaded paper order configuration.';
    if (!['MARKET', 'LIMIT', 'STOP'].includes(orderType)) return 'Choose a supported order type.';
    if (orderType !== 'MARKET' && !positiveNumber(entryPrice)) return 'Enter a positive limit / entry price for pending orders.';
    if (!positiveNumber(stopLoss)) return 'Enter a positive stop-loss price.';
    if (!positiveNumber(takeProfit)) return 'Enter a positive first take-profit price.';
    if (takeProfitTwo && !positiveNumber(takeProfitTwo)) return 'Enter a positive second take-profit price or leave it blank.';
    const hold = Number(maxHoldMinutes);
    if (!Number.isInteger(hold) || hold < 1 || hold > holdMaximum) return 'Maximum hold must be a whole number from 1 to 25 minutes.';
    if (isOption) {
      if (!Number.isInteger(Number(quantityLots)) || Number(quantityLots) < 1) return 'Option quantity must be at least one whole lot.';
      if (!positiveNumber(strike)) return 'Enter a positive option strike.';
      if (!expiry) return 'Choose the option expiry date.';
      if (takeProfitTwo && Number(quantityLots) < 2) return 'A second target requires at least two option lots.';
    } else if (isGold) {
      if (!positiveNumber(quantity)) return 'Enter a positive quantity in troy ounces.';
    } else if (!Number.isInteger(Number(quantity)) || Number(quantity) < 1) {
      return 'Stock quantity must be at least one whole share.';
    }
    if (!clientOrderId) return 'This browser cannot create an idempotency key. Please use a browser with crypto.randomUUID support.';
    return '';
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    setSubmission(null);
    const validationError = validate();
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    const payload = {
      mode: 'PAPER',
      market,
      symbol,
      side: isOption ? 'BUY' : side,
      order_type: orderType,
      limit_price: orderType === 'MARKET' ? null : Number(entryPrice),
      stop_loss: Number(stopLoss),
      take_profit: Number(takeProfit),
      take_profit_2: takeProfitTwo ? Number(takeProfitTwo) : null,
      quantity: !isGold && !isOption ? Number(quantity) : null,
      quantity_troy_ounces: isGold ? Number(quantity) : null,
      quantity_lots: isOption ? Number(quantityLots) : null,
      option_type: isOption ? optionType : null,
      strike: isOption ? Number(strike) : null,
      expiry: isOption ? expiry : null,
      max_hold_minutes: Number(maxHoldMinutes),
      client_order_id: clientOrderId,
    };

    setSubmitting(true);
    try {
      const response = await fetch(`${apiRoot}/paper/orders`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      let responseBody;
      try {
        responseBody = await response.json();
      } catch {
        responseBody = null;
      }
      if (!response.ok) {
        throw new Error(errorMessage(responseBody, `Paper order submission failed (HTTP ${response.status}).`));
      }
      if (!responseBody || typeof responseBody !== 'object') {
        await onSuccess?.();
        throw new Error('The server accepted the request but did not return an order response. The same idempotency key is retained for a safe retry.');
      }
      const order = responseBody.order && typeof responseBody.order === 'object'
        ? responseBody.order
        : responseBody;
      const status = order.status === null || order.status === undefined ? '' : String(order.status);
      setSubmission({
        status,
        id: order.id === null || order.id === undefined ? '' : String(order.id),
        symbol: order.symbol || symbol,
      });
      if (['PENDING', 'FILLED'].includes(status.toUpperCase())) {
        setClientOrderId(globalThis.crypto?.randomUUID?.() || '');
      }
      await onSuccess?.();
    } catch (requestError) {
      setSubmitError(requestError instanceof Error ? requestError.message : 'Could not submit the paper order.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section id="manual-order-panel" className="manual-order-panel" aria-labelledby="manual-order-title" data-testid="section-manual-order">
      <div className="manual-order-heading">
        <div>
          <h2 id="manual-order-title">Manual Paper Order</h2>
          <p>Paper mode only · server controls simulated fills.</p>
        </div>
        <button className="manual-order-close" type="button" onClick={onClose} aria-label="Close manual order form">Close</button>
      </div>

      {configError ? (
        <div className="manual-order-message is-error" role="alert" data-testid="status-order-config-error">
          Could not load allowed instruments: {configError} Submission is disabled until the server configuration is available.
        </div>
      ) : !config ? (
        <div className="manual-order-message" role="status">Loading allowed instruments from the paper server…</div>
      ) : (
        <form className="manual-order-form" onSubmit={handleSubmit}>
          <div className="manual-order-grid">
            <label>
              <span>Market</span>
              <select value={market} onChange={(event) => handleMarketChange(event.target.value)}>
                {config.markets.map((item) => <option value={item.value} key={item.value}>{item.label || item.value}</option>)}
              </select>
            </label>
            <label>
              <span>{isOption ? 'Underlying' : 'Instrument'}</span>
              <select
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                disabled={!availableSymbols.length}
              >
                {!availableSymbols.length && <option value="" disabled>No instrument listed by server</option>}
                {availableSymbols.map((item) => <option value={item} key={item}>{item}</option>)}
              </select>
            </label>
            {!isOption && (
              <label>
                <span>Side</span>
                <select value={side} onChange={(event) => setSide(event.target.value)}>
                  <option value="BUY">Buy</option>
                  <option value="SELL">Sell</option>
                </select>
              </label>
            )}
            <label>
              <span>Order type</span>
              <select value={orderType} onChange={(event) => setOrderType(event.target.value)}>
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
                <option value="STOP">Stop</option>
              </select>
            </label>
            {orderType !== 'MARKET' && (
              <label>
                <span>{orderType === 'LIMIT' ? 'Limit price' : 'Stop / entry price'} · {isGold ? 'USD' : 'INR'}</span>
                <input type="number" min="0.01" step="any" value={entryPrice} onChange={(event) => setEntryPrice(event.target.value)} required />
              </label>
            )}
            {isOption ? (
              <>
                <label>
                  <span>Option type · opening only</span>
                  <select value={optionType} onChange={(event) => setOptionType(event.target.value)}>
                    <option value="CE">Buy CE</option>
                    <option value="PE">Buy PE</option>
                  </select>
                </label>
                <label>
                  <span>Expiry date</span>
                  <input type="date" value={expiry} onChange={(event) => setExpiry(event.target.value)} required />
                </label>
                <label>
                  <span>Strike</span>
                  <input type="number" min="0.01" step="any" value={strike} onChange={(event) => setStrike(event.target.value)} required />
                </label>
                <label>
                  <span>Quantity · lots</span>
                  <input type="number" min="1" step="1" value={quantityLots} onChange={(event) => setQuantityLots(event.target.value)} required />
                </label>
              </>
            ) : (
              <label>
                <span>{isGold ? 'Quantity · troy ounces' : 'Quantity · shares'}</span>
                <input
                  type="number"
                  min={isGold ? '0.01' : '1'}
                  step={isGold ? 'any' : '1'}
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  required
                />
              </label>
            )}
            <label>
              <span>Stop loss · {isGold ? 'USD' : 'INR'}</span>
              <input type="number" min="0.01" step="any" value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} required />
            </label>
            <label>
              <span>Take profit 1 · {isGold ? 'USD' : 'INR'}</span>
              <input type="number" min="0.01" step="any" value={takeProfit} onChange={(event) => setTakeProfit(event.target.value)} required />
            </label>
            <label>
              <span>Take profit 2 · {isGold ? 'USD' : 'INR'} · optional{isOption ? ' · 2+ lots' : ''}</span>
              <input type="number" min="0.01" step="any" value={takeProfitTwo} onChange={(event) => setTakeProfitTwo(event.target.value)} />
            </label>
            <label>
              <span>Max hold · minutes (1–25)</span>
              <input type="number" min="1" max={holdMaximum} step="1" value={maxHoldMinutes} onChange={(event) => setMaxHoldMinutes(event.target.value)} required />
            </label>
          </div>

          {!availableSymbols.length && (
            <p className="manual-order-note is-error" role="alert">
              The server configuration does not list an available {isOption ? 'supported options underlying' : 'instrument'} for this market.
            </p>
          )}
          {isOption && (
            <p className="manual-order-note">Options open with BUY CE/PE only. Naked SELL orders are unavailable.</p>
          )}
          {!clientOrderId && (
            <p className="manual-order-note is-error" role="alert">
              This browser does not support crypto.randomUUID, so an idempotent order cannot be submitted.
            </p>
          )}
          {configuredRisk !== null && configuredRisk !== undefined && configuredRisk !== ''
            && Number.isFinite(Number(configuredRisk)) && (
            <p className="manual-order-note">
              Configured {market} risk limit: {isGold ? '$' : '₹'}{Number(configuredRisk).toLocaleString(isGold ? 'en-US' : 'en-IN')}
              {' '}(server setting; not a fill or fee guarantee).
            </p>
          )}
          {config.note && <p className="manual-order-note">{config.note}</p>}
          <p className="manual-order-note">Option prices are not quoted here. Fills and fees are determined by the server; assumptions are not guarantees.</p>
          {submitError && <div className="manual-order-message is-error" role="alert" data-testid="status-manual-order-error">{submitError}</div>}
          {submission && (
            <div className="manual-order-message is-success" role="status" data-testid="status-manual-order-success">
              Server response: {submission.status ? `order status ${submission.status}` : 'order status was not included'}{submission.id ? ` · order ${submission.id}` : ''} · {submission.symbol}
            </div>
          )}
          <div className="manual-order-actions">
            <button className="manual-order-submit" type="submit" disabled={!canSubmit}>
              {submitting ? 'Submitting…' : 'Submit paper order'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}