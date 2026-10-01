from typing import Dict, List
from datetime import datetime

class AgentTeam:
    """Manages collaboration between all agents"""

    def __init__(self, agents_map: Dict):
        self.agents = agents_map
        self.knowledge_base = {}
        self.shared_insights = {}
        self.team_memory = []

    def knowledge_sharing_session(self) -> Dict:
        """Agents share discoveries and strategies"""

        insights = {}

        for agent_name, agent in self.agents.items():
            # Each agent shares what it learned
            insights[agent_name] = {
                "strengths": self._identify_strengths(agent_name),
                "weaknesses": self._identify_weaknesses(agent_name),
                "best_conditions": self._best_market_conditions(agent_name),
                "strategy_tips": self._get_strategy_tips(agent_name),
            }

        self.shared_insights = insights
        self.team_memory.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_type": "knowledge_sharing",
            "insights": insights,
        })

        return insights

    def _identify_strengths(self, agent_name: str) -> List[str]:
        """Identify what this agent does well"""
        strengths_map = {
            "STOCKS": ["Large cap momentum", "Volume breakouts", "Overnight gaps"],
            "SENSEX": ["Index reversals", "Support/resistance", "Day-of-week patterns"],
            "OPTIONS": ["Volatility expansion", "Earnings plays", "Theta decay"],
            "CANDLE": ["Candle patterns", "Trend confirmation", "Support levels"],
            "XAUUSD": ["Forex trends", "Safe haven flows", "Correlation plays"],
        }
        return strengths_map.get(agent_name, [])

    def _identify_weaknesses(self, agent_name: str) -> List[str]:
        """Identify what this agent struggles with"""
        weaknesses_map = {
            "STOCKS": ["Sudden drops", "Corporate actions", "Liquidity dried up"],
            "SENSEX": ["Choppy markets", "Range-bound periods", "High volatility"],
            "OPTIONS": ["Gap fills", "IV crush", "Early expiry"],
            "CANDLE": ["False signals", "Whipsaws", "Micro-charts"],
            "XAUUSD": ["Geo-political shifts", "Central bank decisions", "Correlation breakdowns"],
        }
        return weaknesses_map.get(agent_name, [])

    def _best_market_conditions(self, agent_name: str) -> Dict:
        """Market conditions where agent performs best"""
        conditions_map = {
            "STOCKS": {
                "volatility": "medium",
                "trend": "strong",
                "volume": "high",
                "time_of_day": "10am-2pm",
            },
            "SENSEX": {
                "volatility": "low_to_medium",
                "trend": "any",
                "volume": "medium",
                "time_of_day": "opening",
            },
            "OPTIONS": {
                "volatility": "high",
                "trend": "sideways",
                "volume": "high",
                "time_of_day": "9:15am-4pm",
            },
            "CANDLE": {
                "volatility": "medium",
                "trend": "strong",
                "volume": "any",
                "time_of_day": "all_day",
            },
            "XAUUSD": {
                "volatility": "any",
                "trend": "strong",
                "volume": "high",
                "time_of_day": "london_session",
            },
        }
        return conditions_map.get(agent_name, {})

    def _get_strategy_tips(self, agent_name: str) -> List[str]:
        """Best practices for this agent"""
        tips_map = {
            "STOCKS": [
                "Wait for volume confirmation on breakouts",
                "Avoid trading 30 min before close",
                "Focus on top 10 liquid stocks",
                "Check open interest before entry",
            ],
            "SENSEX": [
                "Trade only in first 30 minutes",
                "Use 5-min reversal signals",
                "Monitor global cues",
                "Avoid Friday afternoons",
            ],
            "OPTIONS": [
                "Buy long calls/puts only in high IV",
                "Sell spreads in low IV environment",
                "Close positions 2 days before expiry",
                "Monitor Greeks closely",
            ],
            "CANDLE": [
                "Confirm with adjacent candles",
                "Avoid patterns in choppy markets",
                "Use moving averages for trend",
                "Scale into positions gradually",
            ],
            "XAUUSD": [
                "Follow US treasury yields",
                "Monitor dollar strength",
                "Avoid breakouts near key levels",
                "Trade with trend, not against",
            ],
        }
        return tips_map.get(agent_name, [])

    def collaborative_decision(self, market_state: Dict, agent_signals: Dict) -> Dict:
        """Make collaborative decision across all agents"""

        # Count signals
        buy_signals = sum(1 for s in agent_signals.values() if s == "BUY")
        sell_signals = sum(1 for s in agent_signals.values() if s == "SELL")
        hold_signals = sum(1 for s in agent_signals.values() if s == "HOLD")

        # Determine collective action
        if buy_signals >= 3 and buy_signals > sell_signals:
            action = "STRONG_BUY"
        elif buy_signals >= 2:
            action = "BUY"
        elif sell_signals >= 3 and sell_signals > buy_signals:
            action = "STRONG_SELL"
        elif sell_signals >= 2:
            action = "SELL"
        else:
            action = "HOLD"

        return {
            "action": action,
            "confidence": max(buy_signals, sell_signals, hold_signals) / 5,
            "agent_signals": agent_signals,
            "signal_breakdown": {
                "buy": buy_signals,
                "sell": sell_signals,
                "hold": hold_signals,
            }
        }

    def get_team_health(self) -> Dict:
        """Overall team performance and harmony"""

        return {
            "total_agents": len(self.agents),
            "agents_active": len([a for a in self.agents if a]),
            "knowledge_shared": len(self.shared_insights),
            "team_memory_size": len(self.team_memory),
            "status": "HEALTHY" if len(self.agents) == 5 else "DEGRADED",
        }
