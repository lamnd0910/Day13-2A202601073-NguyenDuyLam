from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dashboard.app import calculate_metrics, load_recent_events
from streamlit.testing.v1 import AppTest


def test_dashboard_calculates_six_panel_values() -> None:
    now = datetime.now(timezone.utc)
    events = [
        {"event": "request_received", "_timestamp": now},
        {"event": "request_received", "_timestamp": now},
        {"event": "request_failed", "error_type": "TimeoutError", "_timestamp": now},
        {"event": "response_sent", "latency_ms": 100, "cost_usd": 0.1, "tokens_in": 10, "tokens_out": 20, "quality_score": 0.8, "_timestamp": now},
        {"event": "response_sent", "latency_ms": 400, "cost_usd": 0.2, "tokens_in": 30, "tokens_out": 40, "quality_score": 1.0, "_timestamp": now},
    ]

    result = calculate_metrics(events)

    assert result["p50"] == 100
    assert result["p95"] == 400
    assert result["p99"] == 400
    assert result["traffic_per_minute"] == 2 / 60
    assert result["error_rate_pct"] == 50.0
    assert result["error_breakdown"] == {"TimeoutError": 1}
    assert result["total_cost_usd"] == 0.3
    assert result["tokens_in_total"] == 40
    assert result["tokens_out_total"] == 60
    assert result["quality_avg"] == 0.9


def test_dashboard_ignores_invalid_and_expired_log_records(tmp_path) -> None:
    path = tmp_path / "logs.jsonl"
    path.write_text(
        "\n".join(
            [
                "not json",
                json.dumps({"event": "response_sent", "ts": "2020-01-01T00:00:00Z"}),
                json.dumps({"event": "response_sent", "ts": datetime.now(timezone.utc).isoformat()}),
            ]
        ),
        encoding="utf-8",
    )

    events = load_recent_events(path)

    assert len(events) == 1
    assert events[0]["event"] == "response_sent"


def test_dashboard_app_renders_without_runtime_exception() -> None:
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    dashboard = AppTest.from_file(str(app_path)).run(timeout=15)

    assert not dashboard.exception
    assert [item.value for item in dashboard.subheader] == [
        "Latency",
        "Traffic",
        "Errors",
        "Cost",
        "Tokens",
        "Quality",
    ]
