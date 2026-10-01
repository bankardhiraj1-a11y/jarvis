"""Continuous monitor for verified live-price paper-trade performance.

This module deliberately does not backtest, optimize, create trades, or modify
agent strategies. The 90% figure is a measured target, never an assurance.
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import sessionmaker

from models import Trade


MIN_VERIFIED_TRADES = 100
TARGET_WIN_RATE = 90.0
LIVE_DATA_SOURCES = frozenset({"DHAN", "OANDA"})
DISABLED_AGENTS = {
    "XAUUSD": "Pricing collection only; XAUUSD historical execution validation is pending.",
    "SENSEX": (
        "Legacy SENSEX spread/condor agent is disabled; it is not scored as a "
        "single-leg paper strategy."
    ),
}
RECHECK_INTERVAL_SECONDS = 300


def _as_agent_name(value: Any) -> str:
    """Normalize SQLAlchemy enums and strings to an agent-map key."""
    return str(
        getattr(value, "name", None)
        or getattr(value, "value", None)
        or value
    ).strip().upper()


def _parse_utc(value: Any) -> Optional[datetime]:
    """Parse provider timestamps without accepting missing or malformed values."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


class AutonomousOptimizer:
    """Recheck win-rate performance from closed, live-provider paper trades.

    The historical constructor arguments remain accepted for compatibility;
    agent/optimizer collaborators are intentionally not called or mutated.
    ``db_session`` should be a SQLAlchemy session factory (such as
    ``SessionLocal``). A Session instance is supported by deriving a fresh
    factory from its bind, so a long-running session is never reused.
    """

    def __init__(
        self,
        boss_agent,
        agents_map,
        learning_engine,
        backtest_engine,
        strategy_optimizer,
        market_researcher,
        performance_monitor,
        db_session,
    ):
        # Retain the old constructor contract, but do not run the former
        # fabricated standups, backtests, optimizer mutations, or consensus.
        self.boss_agent = boss_agent
        self.agents_map = agents_map or {}
        self.learning_engine = learning_engine
        self.backtest_engine = backtest_engine
        self.strategy_optimizer = strategy_optimizer
        self.market_researcher = market_researcher
        self.performance_monitor = performance_monitor

        if callable(db_session) and not hasattr(db_session, "query"):
            self._session_factory = db_session
        elif callable(getattr(db_session, "get_bind", None)):
            self._session_factory = sessionmaker(bind=db_session.get_bind())
        else:
            raise TypeError(
                "db_session must be a SQLAlchemy session factory or Session"
            )

        self.supported_agents = sorted(
            name
            for name in (_as_agent_name(key) for key in self.agents_map)
            if name and name not in DISABLED_AGENTS
        )
        self.is_running = False
        self.cycle_count = 0
        self.target_hit = False
        self.improvement_log: List[Dict[str, Any]] = []
        self.latest_metrics: Dict[str, Any] = {}
        self.evaluation_status = "not_started"
        self.last_update: Optional[str] = None
        self.last_error: Optional[str] = None
        self._stop_event = asyncio.Event()

    async def start_autonomous_improvement_loop(self):
        """Keep measuring performance; meeting the target never stops the loop."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event = asyncio.Event()
        try:
            while self.is_running:
                self.cycle_count += 1
                try:
                    await self._evaluate_cycle()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Do not publish a stale target as current when DB review
                    # fails; avoid logging provider/credential-bearing details.
                    self.target_hit = False
                    self.evaluation_status = "unavailable"
                    self.latest_metrics = {}
                    self.last_update = datetime.now(timezone.utc).isoformat()
                    self.last_error = type(exc).__name__
                    self._append_log({
                        "cycle": self.cycle_count,
                        "timestamp": self.last_update,
                        "status": "unavailable",
                        "reason": (
                            "Could not verify the trade records this cycle; "
                            "no performance qualification was made."
                        ),
                        "error_type": self.last_error,
                    })
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                    except asyncio.TimeoutError:
                        pass
                    continue

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=RECHECK_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self.is_running = False

    def stop(self):
        """Request a graceful stop without waiting for the next polling interval."""
        self.is_running = False
        self._stop_event.set()

    async def _evaluate_cycle(self) -> Dict[str, Any]:
        report = await asyncio.to_thread(self._read_verified_metrics)
        self.latest_metrics = report
        self.last_update = datetime.now(timezone.utc).isoformat()
        self.last_error = None

        agents = report["agents"]
        qualified = bool(agents) and all(
            metrics["sample_ready"] and metrics["win_rate"] >= TARGET_WIN_RATE
            for metrics in agents.values()
        )
        self.target_hit = qualified

        enough_samples = bool(agents) and all(
            metrics["sample_ready"] for metrics in agents.values()
        )
        if not agents:
            self.evaluation_status = "no_supported_agents"
            reason = "There are no supported agents to measure."
        elif enough_samples:
            self.evaluation_status = "measured"
            reason = (
                "All supported agents have at least 100 verified closed paper "
                "trades; the measured target is checked again every cycle."
                if qualified
                else "The 90% target is not currently met by every supported agent."
            )
        else:
            self.evaluation_status = "insufficient_data"
            reason = (
                "Insufficient verified closed live-price paper trades; "
                "the 90% target has not been established."
            )

        self._append_log({
            "cycle": self.cycle_count,
            "timestamp": self.last_update,
            "status": self.evaluation_status,
            "target_hit": self.target_hit,
            "metrics_source": "closed DHAN/OANDA paper trades only",
            "agents": agents,
            "reason": reason,
        })
        return report

    def _read_verified_metrics(self) -> Dict[str, Any]:
        """Load closed trades using a fresh session and fail closed on bad rows."""
        session = self._session_factory()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.status == "CLOSED")
                .all()
            )
            grouped: Dict[str, List[Any]] = {
                name: [] for name in self.supported_agents
            }
            for trade in trades:
                agent_name = _as_agent_name(getattr(trade, "agent", None))
                if agent_name not in grouped or not self._has_verified_provenance(trade):
                    continue
                grouped[agent_name].append(trade)

            agent_metrics = {
                name: self._summarize_agent(trades)
                for name, trades in grouped.items()
            }
            return {
                "metrics_source": "closed DHAN/OANDA paper trades only",
                "minimum_verified_trades_per_agent": MIN_VERIFIED_TRADES,
                "target_win_rate": TARGET_WIN_RATE,
                "pnl_basis": (
                    "Stored realized Trade.pnl from the paper runner; India fees "
                    "are modeled estimates, while XAUUSD entries/exits use OANDA "
                    "ask/bid fills and do not add an unverified commission."
                ),
                "excluded_agents": dict(DISABLED_AGENTS),
                "agents": agent_metrics,
            }
        finally:
            session.close()

    @staticmethod
    def _has_verified_provenance(trade: Any) -> bool:
        """Require a closed, finite, time-stamped live-source result."""
        source = str(getattr(trade, "data_source", "") or "").strip().upper()
        if source not in LIVE_DATA_SOURCES:
            return False
        if str(getattr(trade, "status", "") or "").strip().upper() != "CLOSED":
            return False

        entry_timestamp = _parse_utc(
            getattr(trade, "entry_data_timestamp", None)
        )
        exit_timestamp = _parse_utc(
            getattr(trade, "exit_data_timestamp", None)
        )
        closed_at = _parse_utc(getattr(trade, "closed_at", None))
        if (
            entry_timestamp is None
            or exit_timestamp is None
            or closed_at is None
            or exit_timestamp < entry_timestamp
            or closed_at < exit_timestamp
        ):
            return False

        entry = _finite_number(getattr(trade, "entry_price", None))
        exit_price = _finite_number(getattr(trade, "exit_price", None))
        quantity = _finite_number(getattr(trade, "quantity", None))
        pnl = _finite_number(getattr(trade, "pnl", None))
        return (
            entry is not None and entry > 0
            and exit_price is not None and exit_price > 0
            and quantity is not None and quantity > 0
            and pnl is not None
        )

    @staticmethod
    def _summarize_agent(trades: List[Any]) -> Dict[str, Any]:
        pnls = [
            _finite_number(getattr(trade, "pnl", None))
            for trade in trades
        ]
        # Provenance and finite P&L are checked before rows are grouped.
        verified_pnls = [pnl for pnl in pnls if pnl is not None]
        count = len(verified_pnls)
        wins = sum(1 for pnl in verified_pnls if pnl > 0)
        losses = sum(1 for pnl in verified_pnls if pnl < 0)
        ties = count - wins - losses
        rate = round((wins / count) * 100, 2) if count else None
        total_pnl = round(sum(verified_pnls), 2) if count else 0.0
        sample_ready = count >= MIN_VERIFIED_TRADES

        if not sample_ready:
            status = "insufficient_data"
        elif rate is not None and rate >= TARGET_WIN_RATE:
            status = "target_met"
        else:
            status = "below_target"

        return {
            "verified_closed_trades": count,
            "minimum_sample_size": MIN_VERIFIED_TRADES,
            "sample_ready": sample_ready,
            "winning_trades": wins,
            "losing_trades": losses,
            "tie_trades": ties,
            "non_winning_trades": losses + ties,
            "win_rate": rate,
            "total_pnl": total_pnl,
            "pnl_basis": "stored realized Trade.pnl",
            "status": status,
        }

    async def _check_target_achievement(self) -> bool:
        """Refresh and return the currently measured target qualification."""
        await self._evaluate_cycle()
        return self.target_hit

    def _append_log(self, item: Dict[str, Any]):
        self.improvement_log.append(item)
        # Bound memory use during long-running monitoring.
        if len(self.improvement_log) > 500:
            del self.improvement_log[:-500]

    def get_improvement_log(self) -> List[Dict[str, Any]]:
        """Return recent measurement cycles (never synthetic optimization logs)."""
        return list(self.improvement_log)

    def get_status(self) -> Dict[str, Any]:
        """Return explicit metric provenance, sample state, and exclusions."""
        return {
            "is_running": self.is_running,
            "cycle_count": self.cycle_count,
            "target_hit": self.target_hit,
            "target_win_rate": TARGET_WIN_RATE,
            "minimum_verified_trades_per_agent": MIN_VERIFIED_TRADES,
            "evaluation_status": self.evaluation_status,
            "metrics_source": "closed DHAN/OANDA paper trades only",
            "pnl_basis": (
                "Stored realized Trade.pnl from the paper runner; India fees are "
                "modeled estimates, while XAUUSD spread is reflected in executable "
                "OANDA side fills."
            ),
            "agents": self.latest_metrics.get("agents", {}),
            "excluded_agents": dict(DISABLED_AGENTS),
            "cycles_logged": len(self.improvement_log),
            "last_update": self.last_update,
            "reason": (
                "The target is a measured result, not a guarantee. Monitoring "
                "continues after qualification and later trades can change it."
            ),
            "last_error": self.last_error,
        }