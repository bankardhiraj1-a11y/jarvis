import { useEffect, useState } from "react";

export default function AgentMetrics({ selectedAgent }) {
  const [metrics, setMetrics] = useState({});

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch("/jarvis2-api/agents/performance", {
          mode: 'no-cors'
        });
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const mockMetrics = {
    STOCKS: { total_trades: 24, winning_trades: 16, losing_trades: 8, win_rate: 66.7, total_pnl: 12450 },
    SENSEX: { total_trades: 18, winning_trades: 12, losing_trades: 6, win_rate: 66.7, total_pnl: 8920 },
    OPTIONS: { total_trades: 32, winning_trades: 20, losing_trades: 12, win_rate: 62.5, total_pnl: 15680 },
    CANDLE: { total_trades: 41, winning_trades: 28, losing_trades: 13, win_rate: 68.3, total_pnl: 18750 },
    XAUUSD: { total_trades: 15, winning_trades: 11, losing_trades: 4, win_rate: 73.3, total_pnl: 6250 },
  };

  const agents = ["STOCKS", "SENSEX", "OPTIONS", "CANDLE", "XAUUSD"];
  const data = Object.keys(metrics).length > 0 ? metrics : mockMetrics;

  return (
    <div>
      <div className="text-xs text-gray-500 mb-4">AGENT PERFORMANCE MATRIX</div>
      <div className="grid grid-cols-5 gap-3">
        {agents.map((agent) => {
          const agentData = data[agent] || mockMetrics[agent];
          const isSelected = selectedAgent === agent;

          return (
            <div
              key={agent}
              className={`p-4 rounded-lg border transition-all ${
                isSelected
                  ? "border-neon-cyan bg-neon-cyan/10 shadow-glow"
                  : "border-neon-cyan/30 bg-space-900/50 hover:border-neon-cyan/60"
              }`}
            >
              <div className="text-xs text-gray-500 font-bold mb-3">{agent}</div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">Win Rate</span>
                  <span className="text-neon-cyan font-bold">{agentData.win_rate}%</span>
                </div>

                <div className="w-full bg-space-900 rounded h-1.5">
                  <div
                    className="bg-gradient-to-r from-neon-cyan to-neon-blue h-1.5 rounded"
                    style={{ width: `${agentData.win_rate}%` }}
                  />
                </div>

                <div className="flex justify-between mt-3">
                  <span className="text-gray-600">Trades</span>
                  <span className="text-white font-bold">{agentData.total_trades}</span>
                </div>

                <div className="flex justify-between text-gray-600 text-xs">
                  <span>✓ {agentData.winning_trades}</span>
                  <span>✗ {agentData.losing_trades}</span>
                </div>

                <div className="mt-3 pt-3 border-t border-neon-cyan/20">
                  <div className={`font-bold ${agentData.total_pnl >= 0 ? "text-green-400" : "text-neon-red"}`}>
                    ₹{agentData.total_pnl?.toLocaleString("en-IN")}
                  </div>
                  <div className="text-xs text-gray-600">Total P&L</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
