import React from 'react';
import './TradingSections.css';

export default function FundsSection() {
  const funds = {
    availableBalance: 125000,
    usedMargin: 17500,
    freeBalance: 107500,
    collateral: 50000,
    marginPercentage: (17500 / 125000) * 100,
  };

  return (
    <div className="trading-section">
      <div className="section-header">
        <h2>💰 Funds</h2>
      </div>

      <div className="funds-grid">
        <div className="fund-card">
          <span className="label">Available Balance</span>
          <h3 className="amount">₹{funds.availableBalance.toLocaleString()}</h3>
        </div>

        <div className="fund-card">
          <span className="label">Used Margin</span>
          <h3 className="amount negative">₹{funds.usedMargin.toLocaleString()}</h3>
          <span className="percentage">{funds.marginPercentage.toFixed(2)}% Used</span>
        </div>

        <div className="fund-card">
          <span className="label">Free Balance</span>
          <h3 className="amount positive">₹{funds.freeBalance.toLocaleString()}</h3>
        </div>

        <div className="fund-card">
          <span className="label">Collateral</span>
          <h3 className="amount">₹{funds.collateral.toLocaleString()}</h3>
        </div>
      </div>

      <div className="margin-visualization">
        <h4>Margin Utilization</h4>
        <div className="margin-bar">
          <div className="used" style={{width: `${funds.marginPercentage}%`}}></div>
        </div>
        <div className="margin-labels">
          <span>Used: ₹{funds.usedMargin}</span>
          <span>Free: ₹{funds.freeBalance}</span>
        </div>
      </div>

      <div className="fund-details">
        <h4>Fund Allocation by Agent</h4>
        <div className="agent-allocation">
          <div className="allocation-bar">
            <div className="agent-slot stocks" style={{width: '20%'}} title="STOCKS: ₹25K">STOCKS</div>
            <div className="agent-slot sensex" style={{width: '20%'}} title="SENSEX: ₹25K">SENSEX</div>
            <div className="agent-slot options" style={{width: '20%'}} title="OPTIONS: ₹25K">OPTIONS</div>
            <div className="agent-slot candle" style={{width: '20%'}} title="CANDLE: ₹25K">CANDLE</div>
            <div className="agent-slot xauusd" style={{width: '20%'}} title="XAUUSD: ₹25K">XAUUSD</div>
          </div>
        </div>
      </div>
    </div>
  );
}
