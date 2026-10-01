import { useState, useEffect } from "react";
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function Dashboard({ agent }) {
  const [chartData, setChartData] = useState([
    { time: "09:15", price: 45000, volume: 1200 },
    { time: "09:30", price: 45150, volume: 1500 },
    { time: "09:45", price: 45100, volume: 1300 },
    { time: "10:00", price: 45250, volume: 1800 },
    { time: "10:15", price: 45200, volume: 1400 },
    { time: "10:30", price: 45350, volume: 2000 },
  ]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-xs text-gray-500">NIFTY 50 INDEX</div>
          <div className="text-3xl font-bold text-neon-cyan">45,350</div>
          <div className="text-sm text-green-400 mt-1">▲ +1.2% TODAY</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">VOLUME</div>
          <div className="text-2xl font-bold text-neon-blue">2.04M</div>
          <div className="text-xs text-gray-500 mt-1">Contracts</div>
        </div>
      </div>

      {/* Price Chart */}
      <div className="mb-6 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00f0ff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,240,255,0.1)" />
            <XAxis dataKey="time" stroke="#666" />
            <YAxis stroke="#666" />
            <Tooltip
              contentStyle={{ backgroundColor: "#050B14", border: "1px solid #00f0ff" }}
              cursor={{ stroke: "#00f0ff" }}
            />
            <Area
              type="monotone"
              dataKey="price"
              stroke="#00f0ff"
              fillOpacity={1}
              fill="url(#colorPrice)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Technical Indicators */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 bg-space-900/50 border border-neon-cyan/20 rounded">
          <div className="text-xs text-gray-500">RSI(14)</div>
          <div className="text-lg font-bold text-neon-cyan mt-1">62.4</div>
          <div className="text-xs text-gray-600 mt-1">Neutral</div>
        </div>
        <div className="p-3 bg-space-900/50 border border-neon-cyan/20 rounded">
          <div className="text-xs text-gray-500">MACD</div>
          <div className="text-lg font-bold text-green-400 mt-1">BULLISH</div>
          <div className="text-xs text-gray-600 mt-1">Divergence</div>
        </div>
        <div className="p-3 bg-space-900/50 border border-neon-cyan/20 rounded">
          <div className="text-xs text-gray-500">BB WIDTH</div>
          <div className="text-lg font-bold text-neon-blue mt-1">320</div>
          <div className="text-xs text-gray-600 mt-1">Expansion</div>
        </div>
      </div>
    </div>
  );
}
