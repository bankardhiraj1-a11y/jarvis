"""Isolated runtime wiring checks; synthetic fixtures never touch the trading DB."""

import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from agents.xauusd_multiframe import XAUUSDMultiframeResearchAgent


SOURCE = ast.parse(Path(__file__).with_name("main.py").read_text())
NOW = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def helpers(*names, **namespace):
    nodes = [
        node for node in SOURCE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "isolated-runtime", "exec"), namespace)
    return namespace


def test_refresh_is_throttled_and_failure_invalidates_history():
    clock = {"now": NOW}

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock["now"]

    agent = SimpleNamespace(update_candles=Mock())
    feed = SimpleNamespace(refresh=Mock(return_value={"synthetic": "snapshot"}))
    ns = helpers(
        "_refresh_xau_candles",
        datetime=Clock, timezone=timezone, asyncio=asyncio,
        _XAU_CANDLE_REFRESH_AT=None, xau_multiframe_feed=feed,
        agents_map={"XAUUSD": agent}, logger=Mock(),
    )
    asyncio.run(ns["_refresh_xau_candles"]())
    feed.refresh.assert_called_once_with(now=NOW)
    agent.update_candles.assert_called_once_with({"synthetic": "snapshot"})
    clock["now"] += timedelta(seconds=59)
    asyncio.run(ns["_refresh_xau_candles"]())
    assert feed.refresh.call_count == 1
    clock["now"] += timedelta(seconds=1)
    feed.refresh.side_effect = RuntimeError("synthetic unavailable transport")
    asyncio.run(ns["_refresh_xau_candles"]())
    agent.update_candles.assert_called_with({})
    assert feed.refresh.call_count == 2
    ns["logger"].warning.assert_called_once()


def test_status_reads_do_not_advance_strategy_and_history_contract_matches():
    agent = XAUUSDMultiframeResearchAgent()
    ns = helpers(
        "_xau_signal_status", "_agent_history_status",
        agents_map={"XAUUSD": agent},
    )
    initial_calls = agent.get_diagnostics()["calls"]
    for _ in range(3):
        view = ns["_xau_signal_status"]()
        assert view["timeframes"] == ["H4", "M15", "M3"]
        assert view["planned_price_risk_usd"] == 150
        assert view["validated"] is False
        assert view["live_orders_enabled"] is False
        assert view["history"]["status"] == "WAIT"
        assert ns["_agent_history_status"]("XAUUSD", "XAUUSD")["reason"]
    assert agent.get_diagnostics()["calls"] == initial_calls


def test_runtime_uses_multiframe_agent_and_manual_processors_precede_entries():
    assignments = [
        node for node in SOURCE.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "agents_map"
                for target in node.targets)
    ]
    agent_mapping = assignments[0].value
    gold = next(value for key, value in zip(agent_mapping.keys, agent_mapping.values)
                if isinstance(key, ast.Constant) and key.value == "XAUUSD")
    assert isinstance(gold, ast.Call)
    assert gold.func.id == "XAUUSDMultiframeResearchAgent"
    feeder = next(node for node in ast.walk(SOURCE)
                  if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == "live_market_feeder")
    calls = [
        (node.lineno, ast.unparse(node.func))
        for node in ast.walk(feeder) if isinstance(node, ast.Call)
    ]
    calls.extend(
        (node.lineno, ast.unparse(node))
        for node in ast.walk(feeder)
        if isinstance(node, ast.Attribute) and ast.unparse(node) == "onda_client.get_live_data"
    )
    position = lambda name: min(line for line, called in calls if called == name)
    assert position("_refresh_xau_candles") < position("onda_client.get_live_data")
    assert position("process_pending_orders") < position("_monitor_open_trade")
    assert position("process_manual_orders") < position("_monitor_open_trade")
    assert position("_monitor_open_trade") < position("agent.register_research_entry")
    assert position("_has_manual_pending") < position("agent.register_research_entry")


def test_status_routes_expose_network_free_signal_view():
    for name in ("get_agents_performance", "get_gold_market", "get_performance_summary"):
        node = next((node for node in SOURCE.body
                     if isinstance(node, ast.AsyncFunctionDef) and node.name == name), None)
        assert node is not None
        assert "_xau_signal_status()" in ast.unparse(node)