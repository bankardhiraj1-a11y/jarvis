"""Read genuine saved evaluations and render an honest strategy comparison."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path


STRATEGY_REVIEW = {
    "STOCKS": {
        "strategy": "Long daily breakout on five NSE equities: EMA200 > EMA50, prior 20-day high breakout, volume >2× average; ATR/candle stop capped at 3%, target 2R; 50 shares.",
        "issues": [
            "EMA200 > EMA50 is opposite the usual bullish trend filter; the existing condition was preserved, not corrected.",
            "Daily signal-close / next-session-open replay approximates the live intraday trigger and its entry-anchored risk levels.",
            "Costs are modeled; five independent lanes are not a capital-constrained portfolio.",
        ],
    },
    "OPTIONS": {
        "strategy": "NIFTY/BANKNIFTY 15-minute momentum, ATR/extreme reversal and an IV/ATR multi-leg tier. The bridge uses long ATM calls/puts; declared quantity 500 units.",
        "issues": [
            "SELL is routed to a long put, which does not match the strategy's SELL PUT description.",
            "Some index-derived targets are used as option-premium distances; these are not interchangeable.",
            "The multi-leg tier has no supported execution path. Exact premium/contract history is required before scoring outcomes.",
            "Dhan rolling option history was accessible, but changes strikes and lacks exact per-row expiry identity and historical bid/ask; it cannot establish a fixed-contract win rate.",
            "The declared daily-loss percentage is not implemented as a reliable capital-based guard.",
        ],
    },
    "SENSEX_OPTIONS_SCALPING": {
        "strategy": "Two same-color completed one-minute candles with a high/low breakout; long ATM CE/PE, 10/15-point target; declared quantity 1,000 units.",
        "issues": [
            "The bridge substitutes a fixed 25-point premium stop for the strategy's candle-extremum stop.",
            "Underlying candle points and option premium points are different quantities.",
            "Underlying signals cannot establish option wins, losses, fills, costs or P&L.",
        ],
    },
    "SENSEX": {
        "strategy": "Legacy weekly credit spreads and Thursday 0-DTE iron condors with multiple exact option legs; currently disabled.",
        "issues": [
            "Exact leg selection, expiry, prices and synchronized exits are not available in the saved evidence.",
            "Wall-clock scheduling needs a historical event-clock adapter. No success ratio is established.",
        ],
    },
    "XAUUSD": {
        "strategy": "EMA12/26 direction, at least $1 EMA separation and $0.50 price confirmation; 30-second throttle; 100-unit model with $1.50 stop and $5 target; entries 16:00–23:00 UTC.",
        "issues": [
            "The three-trades-per-day counter is never reset or decremented: the current code allows only three signals per process, not three each day.",
            "The declared two-consecutive-signal confirmation setting is not used by analyze().",
            "Historical one-minute closes approximate EMA updates from live sampled quotes; a bar study is not tick-level execution validation.",
            "OANDA practice evidence does not establish live-account authorization. Funding, commission, extra slippage and margin are not fully modeled.",
        ],
    },
    "GIFT_NIFTY": {
        "strategy": "No deployed GIFT NIFTY agent or verified instrument mapping/account entitlement.",
        "issues": ["No genuine executable history or strategy result was inferred."],
    },
}


def _read_report(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Evidence report must be an object")
    return value


def load_agent_evaluation(directory, agent):
    """Normalize the two saved report contracts without changing either source."""
    directory = Path(directory)
    if agent == "XAUUSD":
        report = _read_report(directory / "xauusd_backtest.json")
        metric = report.get("overall", {})
        if not isinstance(metric, dict):
            raise ValueError("XAUUSD overall metrics must be an object")
        result = {
            **report,
            "agent": agent,
            "total_trades": metric.get("closed_trades"),
            "winning_trades": metric.get("wins"),
            "losing_trades": metric.get("losses"),
            "win_rate": metric.get("win_rate_pct"),
            "total_pnl": metric.get("net_pnl_usd"),
            "currency": "USD",
            "counted_toward_live_target": False,
        }
        optimization_path = directory / "xauusd_optimization.json"
        if optimization_path.exists():
            result["strategy_optimization"] = _read_report(optimization_path)
        result["quantity_lots"] = 1.0
        result["quantity_troy_ounces"] = 100.0
        return result
    report = _read_report(directory / "latest_backtests.json")
    evaluation = report.get("agents", {}).get(agent)
    if not isinstance(evaluation, dict):
        raise ValueError("Agent is absent from the genuine-history report")
    result = {
        **evaluation,
        "agent": agent,
        "generated_at": report.get("generated_at"),
        "data_source": report.get("data_source"),
        "currency": "INR",
        "counted_toward_live_target": False,
    }
    if result.get("total_trades") is None:
        # Unknown outcomes are not zero-outcome measurements.
        result["winning_trades"] = None
        result["losing_trades"] = None
    return result


def build_comparison(directory):
    directory = Path(directory)
    agents = {}
    for agent, review in STRATEGY_REVIEW.items():
        evaluation = load_agent_evaluation(directory, agent)
        agents[agent] = {**evaluation, "strategy_review": review}
    dhan = _read_report(directory / "latest_backtests.json")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": ["DHAN_HISTORICAL", "OANDA_PRACTICE_HISTORICAL"],
        "win_rate_definition": "100 × profitable closed modeled trades / all closed modeled trades; unclosed positions and signal-only candidates are excluded.",
        "agents": agents,
        "dhan_history_period": dhan.get("retrieval", {}),
        "option_history_access": {
            "verified_on": "2026-10-01",
            "provider": "DHAN",
            "http_status": 200,
            "instruments": ["NIFTY", "BANKNIFTY", "SENSEX"],
            "rows_per_probe": 8470,
            "data_kind": "rolling ATM-relative CE one-minute OHLC, actual strike, IV, OI, volume and spot",
            "fixed_contract_execution_evidence": False,
            "blockers": ["changing strikes", "missing exact expiry date per row", "missing historical bid/ask"],
            "source": "https://docs.dhanhq.co/api/v2/expired-options-data/get-expired-options-data",
        },
        "strategy_changed": False,
        "execution_validated": False,
        "paper_entries_enabled": False,
        "live_orders_enabled": False,
        "limitations": [
            "Agent samples use different periods, instruments and currencies; percentages do not establish a comparable ranking.",
            "Small samples and OHLC studies do not prove a future success rate or achieve the aspirational 90% target.",
            "Missing option execution evidence is not a 0% win rate. No option P&L is derived from underlying index points.",
            "Research P&L is not a trade ledger; no backtest is counted toward live-provider paper targets.",
        ],
    }


def render_html(report):
    """Self-contained table report; no charts, external resources or credentials."""
    esc = lambda value: html.escape(str(value))

    def show(value, suffix=""):
        return "Not established" if value is None else esc(value) + suffix

    table_rows = []
    sections = []
    for name, evaluation in report["agents"].items():
        review = evaluation["strategy_review"]
        measured = evaluation.get("total_pnl")
        pnl = "Not established" if measured is None else f'{measured:,.2f} {evaluation["currency"]}'
        table_rows.append(
            f'<tr><th><a href="#{esc(name)}">{esc(name)}</a></th>'
            f'<td>{show(evaluation.get("total_trades"))}</td>'
            f'<td>{show(evaluation.get("winning_trades"))}</td>'
            f'<td>{show(evaluation.get("losing_trades"))}</td>'
            f'<td>{show(evaluation.get("win_rate"), "%")}</td>'
            f'<td>{esc(pnl)}</td><td>{esc(evaluation.get("status"))}</td></tr>'
        )
        splits = ""
        for label, key in (("Training", "train"), ("Holdout", "out_of_sample")):
            metric = evaluation.get(key)
            if isinstance(metric, dict):
                if name == "XAUUSD":
                    count, rate, net = metric.get("closed_trades"), metric.get("win_rate_pct"), metric.get("net_pnl_usd")
                else:
                    count, rate, net = metric.get("total_trades"), metric.get("win_rate"), metric.get("total_pnl")
                splits += f'<p><strong>{label}:</strong> {show(count)} closed; win rate {show(rate, "%")}; P&amp;L {show(net)} {evaluation["currency"]}.</p>'
        extra = ""
        if name == "XAUUSD":
            extra = (
                f'<p>Period: {esc(evaluation.get("sample_start_inclusive"))} to '
                f'{esc(evaluation.get("sample_end_exclusive"))}, UTC; OANDA practice, complete bid/ask M1 OHLC.</p>'
                f'<p>{esc(evaluation.get("chronology", ""))}</p>'
                f'<p>{esc(evaluation.get("performance_claim_status", ""))}</p>'
                f'<p>{show(evaluation.get("total_complete_bars"))} complete sample candles; '
                f'{show(evaluation.get("complete_pre_sample_warmup_candles"))} earlier warm-up candles. '
                'Results use the application’s 100-unit research quantity. Spread is included; financing, '
                'commission, extra slippage and margin are not fully modeled.</p>'
            )
            optimization = evaluation.get("strategy_optimization")
            if isinstance(optimization, dict):
                extra += (
                    '<h3>Requested strategy search</h3>'
                    f'<p>{esc(optimization.get("status"))}: {esc(optimization.get("reason", ""))}</p>'
                    f'<p>{show(optimization.get("candidate_count"))} configurations tested; '
                    f'{show(optimization.get("training_eligible_candidate_count"))} passed development requirements. '
                    'The baseline figures above are not the optimized strategy’s performance.</p>'
                )
                diagnostic = optimization.get("training_diagnostics", {}).get(
                    "highest_validation_win_rate_candidate", {}
                ).get("inner_validation", {})
                if diagnostic:
                    extra += (
                        '<p><strong>Highest observed development-validation win rate:</strong> '
                        f'{show(diagnostic.get("win_rate_pct"), "%")}; '
                        f'{show(diagnostic.get("wins"))} wins / {show(diagnostic.get("losses"))} losses; '
                        f'{show(diagnostic.get("closed_trades"))} closed modeled trades; '
                        f'P&amp;L {show(diagnostic.get("net_pnl_usd"))} USD. '
                        'This candidate lost money and was rejected; the final holdout remains untested.</p>'
                    )
        if evaluation.get("signal_count") is not None:
            extra += f'<p>{esc(evaluation["signal_count"])} underlying signal candidates — <strong>not trades or a win-rate denominator.</strong></p>'
        sections.append(
            f'<section id="{esc(name)}"><h2>{esc(name)}</h2><p>{esc(review["strategy"])}</p>'
            f'<p>{esc(evaluation.get("reason", ""))}</p>{extra}{splits}'
            '<h3>Strategy and evidence limitations</h3><ul>'
            + "".join(f'<li>{esc(issue)}</li>' for issue in review["issues"])
            + "</ul></section>"
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Jarvis 2 — Strategy backtest review</title><style>'
        'body{margin:0;background:#0c1119;color:#e8edf5;font:16px/1.6 system-ui,sans-serif}'
        'main{max-width:1120px;margin:auto;padding:36px 24px}h1{line-height:1.2}'
        'h2{color:#7cddd3}a{color:#7cddd3}section{border-top:1px solid #334155;margin-top:30px;padding-top:20px}'
        '.notice{padding:18px;border:1px solid #79632c;background:#211d14;border-radius:8px}'
        '.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}'
        'td,th{padding:12px;text-align:left;border-bottom:1px solid #334155;vertical-align:top}'
        'small{color:#a8b6cb}@media print{body{background:white;color:#111}h2,a{color:#164e63}.notice{background:#fff}}'
        '</style><main><small>GENUINE PROVIDER HISTORY • RESEARCH ONLY</small>'
        '<h1>Agent strategies and measured backtest win rates</h1>'
        f'<p>Generated {esc(report["generated_at"])}. Success ratio means win rate on <strong>closed modeled trades</strong>, not live returns.</p>'
        '<div class="notice"><strong>No agent is execution-validated.</strong> Strategies were not changed. '
        'Paper entries and real orders remain disabled. Missing data is not replaced with invented results.</div>'
        '<div class="table"><table><thead><tr><th>Agent</th><th>Closed</th><th>Wins</th>'
        '<th>Losses</th><th>Win rate</th><th>Modeled P&amp;L</th><th>Evidence</th></tr></thead><tbody>'
        + "".join(table_rows) + "</tbody></table></div>"
        + '<p>' + esc(report["win_rate_definition"]) + "</p>"
        + "".join(sections)
        + '<section><h2>How to interpret this comparison</h2><ul>'
        + "".join(f'<li>{esc(item)}</li>' for item in report["limitations"])
        + '</ul><h3>Dhan history coverage</h3><p>Stocks: '
        + esc(report["dhan_history_period"].get("daily_from")) + " to "
        + esc(report["dhan_history_period"].get("to_date_exclusive"))
        + " (end exclusive); underlying intraday history from "
        + esc(report["dhan_history_period"].get("intraday_from"))
        + '. Dhan data was fetched earlier and replayed for this review.</p></section></main></html>'
    )


def write_comparison(directory, html_path):
    report = build_comparison(directory)
    Path(directory, "all_agents_backtest_review.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    destination = Path(html_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_html(report), encoding="utf-8")
    return report