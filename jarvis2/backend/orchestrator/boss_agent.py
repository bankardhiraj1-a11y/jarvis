from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    ANALYZE_MARKET = "ANALYZE_MARKET"
    RESEARCH_STRATEGY = "RESEARCH_STRATEGY"
    BACKTEST = "BACKTEST"
    EXECUTE_TRADE = "EXECUTE_TRADE"
    OPTIMIZE = "OPTIMIZE"
    CONSENSUS = "CONSENSUS"

class BossAgent:
    def __init__(self, agents_map: Dict):
        self.agents_map = agents_map  # All 5 trading agents
        self.agent_names = list(agents_map.keys())
        self.work_queue = []
        self.team_results = {}
        self.consensus_decisions = {}
        self.performance_leaderboard = {}

    def daily_standup(self, market_data: Dict) -> Dict:
        """Boss distributes work to all agents for daily analysis"""
        print(f"\n🤖 BOSS AGENT - DAILY STANDUP {datetime.utcnow().isoformat()}")

        tasks = []

        # Task 1: Market Analysis (all agents analyze current market)
        for agent_name in self.agent_names:
            tasks.append({
                "agent": agent_name,
                "task_type": TaskType.ANALYZE_MARKET,
                "data": market_data,
                "priority": "HIGH",
            })

        # Task 2: Strategy Research (each agent suggests improvements)
        for agent_name in self.agent_names:
            tasks.append({
                "agent": agent_name,
                "task_type": TaskType.RESEARCH_STRATEGY,
                "data": market_data,
                "priority": "MEDIUM",
            })

        # Execute all tasks
        self.work_queue = tasks
        results = self._execute_tasks(tasks)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "standup_type": "DAILY",
            "tasks_assigned": len(tasks),
            "results": results,
        }

    def _execute_tasks(self, tasks: List[Dict]) -> Dict:
        """Execute all tasks and collect results"""
        results = {}

        for task in tasks:
            agent_name = task["agent"]
            task_type = task["task_type"]

            agent = self.agents_map.get(agent_name)
            if not agent:
                continue

            result = self._delegate_task(agent, task_type, task.get("data", {}))

            if agent_name not in results:
                results[agent_name] = []
            results[agent_name].append({
                "task": task_type.value,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            })

        self.team_results = results
        return results

    def _delegate_task(self, agent, task_type: TaskType, data: Dict):
        """Delegate specific task to an agent"""
        if task_type == TaskType.ANALYZE_MARKET:
            return agent.analyze(data)
        elif task_type == TaskType.RESEARCH_STRATEGY:
            return {"strategy": "research_in_progress"}
        else:
            return {"status": "task_acknowledged"}

    def build_team_consensus(self, market_conditions: Dict, all_trades: List[Dict]) -> Dict:
        """All agents vote on best strategy"""
        print(f"\n🤝 TEAM CONSENSUS MEETING")

        agent_votes = {}
        confidence_scores = {}

        # Collect each agent's preference
        for agent_name in self.agent_names:
            agent = self.agents_map[agent_name]
            signal = agent.analyze(market_conditions)

            agent_votes[agent_name] = signal.value

            # Calculate confidence based on recent performance
            recent_trades = [t for t in all_trades if t.get("agent") == agent_name][-10:]
            win_rate = len([t for t in recent_trades if t.get("pnl", 0) > 0]) / len(recent_trades) if recent_trades else 0.5
            confidence_scores[agent_name] = win_rate

        # Weighted consensus (agents with higher win rates get more say)
        buy_votes = sum(1 for v in agent_votes.values() if v == "BUY")
        sell_votes = sum(1 for v in agent_votes.values() if v == "SELL")
        hold_votes = sum(1 for v in agent_votes.values() if v == "HOLD")

        # Weighted voting
        weighted_buy = sum(confidence_scores[a] for a in self.agent_names if agent_votes[a] == "BUY")
        weighted_sell = sum(confidence_scores[a] for a in self.agent_names if agent_votes[a] == "SELL")
        weighted_hold = sum(confidence_scores[a] for a in self.agent_names if agent_votes[a] == "HOLD")

        total_weight = weighted_buy + weighted_sell + weighted_hold

        consensus = "HOLD"
        if weighted_buy > weighted_sell and weighted_buy > weighted_hold:
            consensus = "BUY"
        elif weighted_sell > weighted_buy and weighted_sell > weighted_hold:
            consensus = "SELL"

        self.consensus_decisions = {
            "consensus": consensus,
            "confidence": max(weighted_buy, weighted_sell, weighted_hold) / total_weight if total_weight > 0 else 0.5,
            "agent_votes": agent_votes,
            "confidence_scores": confidence_scores,
            "vote_counts": {
                "BUY": buy_votes,
                "SELL": sell_votes,
                "HOLD": hold_votes,
            },
            "weighted_votes": {
                "BUY": round(weighted_buy, 2),
                "SELL": round(weighted_sell, 2),
                "HOLD": round(weighted_hold, 2),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return self.consensus_decisions

    def update_performance_leaderboard(self, agent_metrics: Dict) -> List[Dict]:
        """Rank agents by performance, identify leaders"""
        leaderboard = []

        for agent_name, metrics in agent_metrics.items():
            leaderboard.append({
                "rank": 0,
                "agent": agent_name,
                "win_rate": metrics.get("win_rate", 0),
                "total_pnl": metrics.get("total_pnl", 0),
                "profit_factor": metrics.get("profit_factor", 0),
                "consistency": metrics.get("consistency", 0),
            })

        # Sort by win rate
        leaderboard.sort(key=lambda x: x["win_rate"], reverse=True)

        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        self.performance_leaderboard = leaderboard
        return leaderboard

    def delegate_improvement_tasks(self) -> Dict:
        """Boss identifies weak agents and assigns improvement work"""
        if not self.performance_leaderboard:
            return {"status": "no_data"}

        tasks = {
            "improve_underperformers": [],
            "replicate_winners": [],
            "research_new_strategies": [],
        }

        # Bottom 2 agents get improvement tasks
        underperformers = self.performance_leaderboard[-2:]
        for agent in underperformers:
            tasks["improve_underperformers"].append({
                "agent": agent["agent"],
                "priority": "CRITICAL",
                "assignment": f"Improve from {agent['win_rate']}% to 90%+",
                "resources": "Use market researcher for trend analysis",
            })

        # Top performers share strategies with others
        winners = self.performance_leaderboard[:2]
        for winner in winners:
            tasks["replicate_winners"].append({
                "teacher": winner["agent"],
                "students": [a["agent"] for a in underperformers],
                "share": "Parameter settings, entry signals, risk management",
            })

        # Research tasks
        for agent in self.agent_names:
            tasks["research_new_strategies"].append({
                "agent": agent,
                "focus": "Market conditions where this agent performs best",
                "deadline": "EOD",
            })

        return tasks

    def generate_daily_report(self) -> Dict:
        """Boss generates comprehensive daily report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "team_performance": self.performance_leaderboard,
            "consensus_decisions": self.consensus_decisions,
            "work_summary": {
                "tasks_assigned": len(self.work_queue),
                "results_collected": sum(len(v) for v in self.team_results.values()),
            },
            "recommendations": [
                f"Top performer: {self.performance_leaderboard[0]['agent'] if self.performance_leaderboard else 'N/A'}",
                f"Consensus strategy: {self.consensus_decisions.get('consensus', 'HOLD')}",
                f"Team confidence: {round(self.consensus_decisions.get('confidence', 0) * 100, 1)}%",
            ]
        }
