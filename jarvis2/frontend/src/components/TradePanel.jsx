import { useState, useEffect } from "react";

export default function TradePanel({ agent }) {
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const res = await fetch(
          `/jarvis2-api/trades?agent=${agent}`,
          { mode: 'no-cors' }
        );
        if (res.ok) {
          const data = await res.json();
          setTrades(data.slice(0, 10));
        }
      } catch (err) {
        console.error("Failed to fetch trades", err);
      }
    };

    fetchTrades();
    const interval = setInterval(fetchTrades, 3000);
    return () => clearInterval(interval);
  }, [agent]);

  const mockTrades = [
    { id: 1, symbol: "RELIANCE", type: "BUY", qty: 1, price: 2850, time: "10:32", pnl: "+145" },
    { id: 2, symbol: "TCS", type: "SELL", qty: 2, price: 3620, time: "10:15", pnl: "-85" },
    { id: 3, symbol: "INFY", type: "BUY", qty: 3, price: 2920, time: "09:58", pnl: "+320" },
    { id: 4, symbol: "WIPRO", type: "HOLD", qty: 1, price: 380, time: "09:42", pnl: "0" },
    { id: 5, symbol: "ICICIBANK", type: "BUY", qty: 5, price: 920, time: "09:28", pnl: "+485" },
  ];

  return (
    <div>
      <div className="text-xs text-gray-500 mb-4 flex items-center justify-between">
        <span>RECENT TRADES</span>
        <span className="text-neon-cyan">{trades.length || mockTrades.length}</span>
      </div>

      <div className="space-y-2">
        {(trades.length > 0 ? trades : mockTrades).map((trade) => (
          <div
            key={trade.id}
            className="p-3 bg-space-900/50 border border-neon-cyan/20 rounded hover:border-neon-cyan/60 transition-all cursor-pointer"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="font-bold text-sm text-white">{trade.symbol}</div>
              <div className={`text-xs font-bold ${
                trade.pnl?.startsWith("+") ? "text-green-400" : "text-neon-red"
              }`}>
                {trade.pnl}
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>{trade.type}</span>
              <span>₹{trade.price}</span>
            </div>
            <div className="text-xs text-gray-600 mt-1">{trade.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
