import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import AgentName, Trade, TradeType
from scheduler.autonomous_optimizer import AutonomousOptimizer


class AutonomousOptimizerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "optimizer-test.sqlite"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self.optimizer = self.make_optimizer(["STOCKS", "OPTIONS", "SENSEX"])

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def make_optimizer(self, names):
        return AutonomousOptimizer(
            boss_agent=None,
            agents_map={name: object() for name in names},
            learning_engine=None,
            backtest_engine=None,
            strategy_optimizer=None,
            market_researcher=None,
            performance_monitor=None,
            db_session=self.session_factory,
        )

    def add_trade(
        self,
        *,
        agent=AgentName.STOCKS,
        pnl=1.0,
        source="DHAN",
        timestamp=None,
        exit_timestamp=None,
        status="CLOSED",
        exit_price=101.0,
    ):
        now = datetime.now(timezone.utc)
        entry_timestamp = timestamp or (now - timedelta(seconds=10)).isoformat()
        trade = Trade(
            agent=agent,
            symbol="RELIANCE",
            trade_type=TradeType.BUY,
            quantity=1,
            entry_price=100,
            exit_price=exit_price,
            pnl=pnl,
            status=status,
            created_at=now - timedelta(seconds=9),
            closed_at=now,
            data_source=source,
            entry_data_timestamp=entry_timestamp,
        exit_data_timestamp=(
            exit_timestamp or (now - timedelta(seconds=1)).isoformat()
        ),
        )
        session = self.session_factory()
        try:
            session.add(trade)
            session.commit()
        finally:
            session.close()

    def add_outcomes(self, agent, wins, losses, ties=0):
        for _ in range(wins):
            self.add_trade(agent=agent, pnl=2.0)
        for _ in range(losses):
            self.add_trade(agent=agent, pnl=-2.0)
        for _ in range(ties):
            self.add_trade(agent=agent, pnl=0.0)

    def test_only_verified_live_source_closed_trades_are_counted(self):
        self.add_outcomes(AgentName.STOCKS, wins=90, losses=9, ties=1)

        # These profitable rows must not improve the verified win rate.
        self.add_trade(agent=AgentName.STOCKS, pnl=500.0, source=None)
        self.add_trade(agent=AgentName.STOCKS, pnl=500.0, source="SIMULATED")
        self.add_trade(agent=AgentName.STOCKS, pnl=500.0, timestamp="not-a-time")
        self.add_trade(
            agent=AgentName.STOCKS,
            pnl=500.0,
            exit_timestamp="not-a-time",
        )
        self.add_trade(
            agent=AgentName.STOCKS,
            pnl=500.0,
            timestamp=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        self.add_trade(agent=AgentName.STOCKS, pnl=500.0, status="OPEN")

        # Legacy SENSEX spread trades are not scored, even with a live-source tag.
        self.add_outcomes(AgentName.SENSEX, wins=100, losses=0)

        metrics = self.optimizer._read_verified_metrics()
        stocks = metrics["agents"]["STOCKS"]

        self.assertEqual(stocks["verified_closed_trades"], 100)
        self.assertEqual(stocks["winning_trades"], 90)
        self.assertEqual(stocks["losing_trades"], 9)
        self.assertEqual(stocks["tie_trades"], 1)
        self.assertEqual(stocks["non_winning_trades"], 10)
        self.assertEqual(stocks["win_rate"], 90.0)
        self.assertEqual(stocks["total_pnl"], 162.0)
        self.assertEqual(metrics["agents"]["OPTIONS"]["win_rate"], None)
        self.assertNotIn("SENSEX", metrics["agents"])
        self.assertIn("SENSEX", metrics["excluded_agents"])

    def test_each_supported_agent_needs_100_verified_trades_and_later_losses_apply(self):
        self.add_outcomes(AgentName.STOCKS, wins=90, losses=10)
        self.add_outcomes(AgentName.OPTIONS, wins=90, losses=10)

        first_metrics = asyncio.run(self.optimizer._evaluate_cycle())
        self.assertTrue(self.optimizer.target_hit)
        self.assertEqual(first_metrics["agents"]["STOCKS"]["verified_closed_trades"], 100)
        self.assertEqual(first_metrics["agents"]["OPTIONS"]["win_rate"], 90.0)

        # A new closed loss changes the denominator and can remove qualification.
        self.add_trade(agent=AgentName.STOCKS, pnl=-2.0)
        second_metrics = asyncio.run(self.optimizer._evaluate_cycle())
        self.assertFalse(self.optimizer.target_hit)
        self.assertEqual(second_metrics["agents"]["STOCKS"]["verified_closed_trades"], 101)
        self.assertEqual(second_metrics["agents"]["STOCKS"]["win_rate"], 89.11)

    def test_insufficient_sample_never_qualifies(self):
        self.add_outcomes(AgentName.STOCKS, wins=99, losses=0)
        metrics = self.optimizer._read_verified_metrics()

        self.assertEqual(metrics["agents"]["STOCKS"]["win_rate"], 100.0)
        self.assertFalse(metrics["agents"]["STOCKS"]["sample_ready"])

    def test_monitor_keeps_running_after_target_and_stops_on_request(self):
        self.add_outcomes(AgentName.STOCKS, wins=100, losses=0)
        optimizer = self.make_optimizer(["STOCKS"])

        async def exercise_loop():
            with patch(
                "scheduler.autonomous_optimizer.RECHECK_INTERVAL_SECONDS",
                0.01,
            ):
                task = asyncio.create_task(
                    optimizer.start_autonomous_improvement_loop()
                )
                for _ in range(200):
                    if optimizer.cycle_count >= 2:
                        break
                    await asyncio.sleep(0.01)

                self.assertTrue(optimizer.target_hit)
                self.assertTrue(optimizer.is_running)
                self.assertGreaterEqual(optimizer.cycle_count, 2)

                optimizer.stop()
                await asyncio.wait_for(task, timeout=1)
                self.assertFalse(optimizer.is_running)

        asyncio.run(exercise_loop())


if __name__ == "__main__":
    unittest.main()