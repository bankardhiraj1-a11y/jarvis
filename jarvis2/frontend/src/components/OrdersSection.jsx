import React, { useState } from 'react';
import './TradingSections.css';

export default function OrdersSection() {
  const [orders] = useState([
    { id: 1, time: '11:30:45', agent: 'SENSEX', symbol: 'NIFTY', type: 'BUY', qty: 10, price: 45350, filled: 10, status: 'COMPLETE', pnl: 1000 },
    { id: 2, time: '11:28:12', agent: 'STOCKS', symbol: 'SBIN', type: 'BUY', qty: 50, price: 650, filled: 50, status: 'COMPLETE', pnl: 250 },
    { id: 3, time: '11:25:33', agent: 'OPTIONS', symbol: 'NIFTY22JAN22C45000', type: 'SELL', qty: 5, price: 125, filled: 5, status: 'COMPLETE', pnl: 375 },
    { id: 4, time: '11:22:10', agent: 'CANDLE', symbol: 'RELIANCE', type: 'BUY', qty: 25, price: 2850, filled: 25, status: 'COMPLETE', pnl: 500 },
    { id: 5, time: '11:18:45', agent: 'XAUUSD', symbol: 'GOLDM', type: 'SELL', qty: 100, price: 52550, filled: 100, status: 'COMPLETE', pnl: 650 },
  ]);

  return (
    <div className="trading-section">
      <div className="section-header">
        <h2>📋 Orders</h2>
        <span className="order-count">{orders.length} Orders</span>
      </div>

      <table className="trading-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Agent</th>
            <th>Symbol</th>
            <th>Type</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Filled</th>
            <th>Status</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(order => (
            <tr key={order.id} className={`order-${order.type.toLowerCase()}`}>
              <td className="time">{order.time}</td>
              <td className="agent-badge">{order.agent}</td>
              <td className="symbol">{order.symbol}</td>
              <td className={`type ${order.type.toLowerCase()}`}>{order.type}</td>
              <td className="qty">{order.qty}</td>
              <td className="price">₹{order.price}</td>
              <td className="filled">{order.filled}/{order.qty}</td>
              <td><span className="status-badge complete">{order.status}</span></td>
              <td className={`pnl ${order.pnl >= 0 ? 'positive' : 'negative'}`}>
                ₹{order.pnl}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
