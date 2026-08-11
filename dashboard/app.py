"""Run with: streamlit run dashboard/app.py."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
TIME_RANGE_MINUTES = 60
REFRESH_SECONDS = 30


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    index = max(0, min(len(items) - 1, math.ceil(len(items) * p / 100) - 1))
    return float(items[index])


def load_recent_events(path: Path, now: datetime | None = None) -> list[dict[str, Any]]:
    """Read valid JSONL records that fall in the dashboard's 60-minute window."""
    if not path.exists():
        return []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=TIME_RANGE_MINUTES)
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
            timestamp = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if timestamp >= cutoff:
            event["_timestamp"] = timestamp
            events.append(event)
    return events


def calculate_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    responses = [event for event in events if event.get("event") == "response_sent"]
    requests = [event for event in events if event.get("event") == "request_received"]
    failures = [event for event in events if event.get("event") == "request_failed"]
    latencies = [float(event["latency_ms"]) for event in responses if isinstance(event.get("latency_ms"), (int, float))]
    costs = [float(event["cost_usd"]) for event in responses if isinstance(event.get("cost_usd"), (int, float))]
    tokens_in = sum(int(event.get("tokens_in", 0) or 0) for event in responses)
    tokens_out = sum(int(event.get("tokens_out", 0) or 0) for event in responses)
    scores = [float(event["quality_score"]) for event in responses if isinstance(event.get("quality_score"), (int, float))]
    costs_by_minute: dict[str, float] = defaultdict(float)
    for event in responses:
        if isinstance(event.get("cost_usd"), (int, float)) and event.get("_timestamp"):
            costs_by_minute[event["_timestamp"].strftime("%H:%M")] += float(event["cost_usd"])

    return {
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "traffic_per_minute": len(requests) / TIME_RANGE_MINUTES,
        "error_rate_pct": len(failures) / len(requests) * 100 if requests else 0.0,
        "error_breakdown": Counter(str(event.get("error_type", "unknown")) for event in failures),
        "cost_by_minute": dict(costs_by_minute),
        "total_cost_usd": round(sum(costs), 6),
        "tokens_in_total": tokens_in,
        "tokens_out_total": tokens_out,
        "quality_avg": sum(scores) / len(scores) if scores else 0.0,
    }


def render_dashboard(metrics: dict[str, Any]) -> None:
    st.set_page_config(page_title="Day 13 Observability", layout="wide")
    st.title("Day 13 AI Observability")
    st.caption("Time range: 60 minutes · Refresh: 30 seconds · Source: data/logs.jsonl")
    st.autorefresh(interval=REFRESH_SECONDS * 1000, key="dashboard-refresh")

    latency, traffic, errors = st.columns(3)
    with latency:
        st.subheader("Latency")
        st.caption("Unit: ms · SLO: P95 ≤ 3000 ms")
        st.metric("P50", f"{metrics['p50']:.0f} ms")
        st.metric("P95", f"{metrics['p95']:.0f} ms", delta=f"SLO 3000 ms")
        st.metric("P99", f"{metrics['p99']:.0f} ms")
    with traffic:
        st.subheader("Traffic")
        st.caption("Unit: requests/minute · Threshold: ≥ 1 request/minute")
        st.metric("Requests/minute", f"{metrics['traffic_per_minute']:.2f}")
    with errors:
        st.subheader("Errors")
        st.caption("Unit: percent · SLO: error rate ≤ 2%")
        st.metric("Error rate", f"{metrics['error_rate_pct']:.2f}%")
        st.json(dict(metrics["error_breakdown"]) or {"none": 0})

    cost, tokens, quality = st.columns(3)
    with cost:
        st.subheader("Cost")
        st.caption("Unit: USD · SLO: total cost ≤ $2.50")
        st.metric("Total cost", f"${metrics['total_cost_usd']:.6f}")
        st.bar_chart(metrics["cost_by_minute"])
    with tokens:
        st.subheader("Tokens")
        st.caption("Unit: tokens · Threshold: total ≤ 50,000")
        st.metric("Input tokens", f"{metrics['tokens_in_total']:,}")
        st.metric("Output tokens", f"{metrics['tokens_out_total']:,}")
    with quality:
        st.subheader("Quality")
        st.caption("Unit: score 0–1 · SLO: average ≥ 0.75")
        st.metric("Average quality", f"{metrics['quality_avg']:.2f}")


def main() -> None:
    render_dashboard(calculate_metrics(load_recent_events(LOG_PATH)))


if __name__ == "__main__":
    main()
