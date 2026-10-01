import React, { useState } from 'react';
import './TradingSections.css';

export default function HoldingsSection() {
  const [holdings] = useState([
    { symbol: 'NIFTY', qty: 10, avgPrice: 45300, ltp: 45450, value: 454500, investment: 453000, pnl: 1500, pnlPercent: 0.33 },
    { symbol: 'SBIN', qty: 50, avgPrice: 645, ltp: 655, value: 32750, investment: 32250, pnl: 500, pnlPercent: 1.55 },
    { symbol: 'TCS', qty: 20, avgPrice: 3850, ltp: 3920, value: 78400, investment: 77000, pnl: 1400, pnlPercent: 1.82 },
    { symbol: 'INFY', qty: 15, avgPrice: 1650, ltp: 1680, value: 25200, investment: 24750, pnl: 450, pnlPercent: 1.82 },
  ]);

  const totalValue = holdings.reduce((sum, h) => sum + h.value, 0);
  const totalInvestment = holdings.reduce((sum, h) => sum + h.investment, 0);
  const totalPnL = holdings.reduce((sum, h) => sum + h.pnl, 0);

  return (
    <div className="trading-section">
      <div className="section-header">
        <h2>📊 Holdings</h2>
        <div className="summary-stats">
          <span>Value: ₹{totalValue.toLocaleString()}</span>
          <span className={totalPnL >= 0 ? 'positive' : 'negative'}>P&L: ₹{totalPnL.toLocaleString()}</span>
        </div>
      </div>

      <table className="trading-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Qty</th>
            <th>Avg Price</th>
            <th>LTP</th>
            <th>Value</th>
            <th>Investment</th>
            <th>P&L</th>
            <th>P&L %</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map(h => (
            <tr key={h.symbol} className="holding-row">
              <td className="symbol">{h.symbol}</td>
              <td className="qty">{h.qty}</td>
              <td className="price">₹{h.avgPrice}</td>
              <td className="price">₹{h.ltp}</td>
              <td className="value">₹{h.value.toLocaleString()}</td>
              <td className="investment">₹{h.investment.toLocaleString()}</td>
              <td className={`pnl ${h.pnl >= 0 ? 'positive' : 'negative'}`}>₹{h.pnl.toLocaleString()}</td>
              <td className={`pnl-percent ${h.pnlPercent >= 0 ? 'positive' : 'negative'}`}>
                {h.pnlPercent > 0 ? '+' : ''}{h.pnlPercent.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
