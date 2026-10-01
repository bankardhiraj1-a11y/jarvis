import { useState, useEffect } from "react";
import KiteDashboard from "./components/KiteDashboard";

export default function App() {
  const [portfolio, setPortfolio] = useState({
    total_pnl: 2450,
    net_worth: 102450,
    positions: { RELIANCE: 5, TCS: 3, NIFTY: 1 },
  });
  const [selectedAgent, setSelectedAgent] = useState("STOCKS");
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const fetchPortfolio = async () => {
      try {
        const apiUrl = "/jarvis2-api";
        const res = await fetch(`${apiUrl}/portfolio`, {
          headers: { "Accept": "application/json" }
        });
        if (res.ok) {
          const data = await res.json();
          setPortfolio(data);
        }
      } catch (err) {
        console.log("Using mock data - Backend not available yet");
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/jarvis2-api/ws/live`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setIsConnected(true);
      ws.onerror = () => setIsConnected(false);
      ws.onclose = () => setIsConnected(false);
      return () => ws.close();
    } catch (err) {
      console.log("WebSocket not available");
    }
  }, []);

  return <KiteDashboard />;
}
