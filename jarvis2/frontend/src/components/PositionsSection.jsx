import React, { useState } from 'react';
import './TradingSections.css';

export default function PositionsSection() {
  const [positions] = useState([
    { symbol: 'NIFTY22JAN22C45000', type: 'LONG', qty: 5, entryPrice: 125, ltp: 145, unrealizedPnL: 100, pnlPercent: 16, margin: 5000 },
    { symbol: 'BANKNIFTY22JAN22P40000', type: 'SHORT', qty: 2, entryPrice: 500, ltp: 480, unrealizedPnL: 40, pnlPercent: 4, margin: 10000 },
    { symbol: 'SBIN22JAN22C800', type: 'LONG', qty: 10, entryPrice: 45, ltp: 55, unrealizedPnL: 100, pnlPercent: 22.22, margin: 2500 },
  ]);

  const totalMargin = positions.reduce((sum, p) => sum + p.margin, 0);
  const totalPnL = positions.reduce((sum, p) => sum + p.unrealizedPnL, 0);

  return (
    <div className="trading-section">
      <div className="section-header">
        <h2>⚡ Positions (Intraday)</h2>
        <div className="summary-stats">
          <span>Margin Used: ₹{totalMargin.toLocaleString()}</span>
          <span className={totalPnL >= 0 ? 'positive' : 'negative'}>Unrealized P&L: ₹{totalPnL}</span>
        </div>
      </div>

      <table className="trading-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Type</th>
            <th>Qty</th>
            <th>Entry Price</th>
            <th>LTP</th>
            <th>Unrealized P&L</th>
            <th>P&L %</th>
            <th>Margin</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos, idx) => (
            <tr key={idx} className={`position-${pos.type.toLowerCase()}`}>
              <td className="symbol">{pos.symbol}</td>
              <td className={`type ${pos.type.toLowerCase()}`}>{pos.type}</td>
              <td className="qty">{pos.qty}</td>
              <td className="price">₹{pos.entryPrice}</td>
              <td className="price">₹{pos.ltp}</td>
              <td className={`pnl ${pos.unrealizedPnL >= 0 ? 'positive' : 'negative'}`}>
                ₹{pos.unrealizedPnL}
              </td>
              <td className={`pnl-percent ${pos.pnlPercent >= 0 ? 'positive' : 'negative'}`}>
                {pos.pnlPercent > 0 ? '+' : ''}{pos.pnlPercent.toFixed(2)}%
              </td>
              <td className="margin">₹{pos.margin.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
