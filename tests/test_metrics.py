from app import metrics


def test_percentile_basic() -> None:
    assert metrics.percentile([100, 200, 300, 400], 50) == 200


def test_percentile_empty_and_tail_percentiles() -> None:
    assert metrics.percentile([], 50) == 0.0
    assert metrics.percentile([100, 200, 300, 400], 95) == 400
    assert metrics.percentile([100, 200, 300, 400], 99) == 400


def test_snapshot_aggregates_metrics(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "REQUEST_LATENCIES", [100, 200, 300, 400])
    monkeypatch.setattr(metrics, "REQUEST_COSTS", [0.1, 0.2])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_IN", [10, 20])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_OUT", [30, 40])
    monkeypatch.setattr(metrics, "QUALITY_SCORES", [0.8, 1.0])
    monkeypatch.setattr(metrics, "TRAFFIC", 4)
    monkeypatch.setattr(metrics, "ERRORS", metrics.Counter({"TimeoutError": 1}))

    result = metrics.snapshot()

    assert result["latency_p50"] == 200
    assert result["latency_p95"] == 400
    assert result["latency_p99"] == 400
    assert result["error_rate_pct"] == 25.0
    assert result["error_breakdown"] == {"TimeoutError": 1}
    assert result["tokens_in_total"] == 30
    assert result["tokens_out_total"] == 70
    assert result["total_cost_usd"] == 0.3
    assert result["quality_avg"] == 0.9


def test_snapshot_has_no_division_by_zero(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", metrics.Counter({"TimeoutError": 1}))

    assert metrics.snapshot()["error_rate_pct"] == 0.0


def test_failed_request_counts_toward_traffic_and_error_rate(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", metrics.Counter())
    monkeypatch.setattr(metrics, "REQUEST_LATENCIES", [])
    monkeypatch.setattr(metrics, "REQUEST_COSTS", [])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_IN", [])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_OUT", [])
    monkeypatch.setattr(metrics, "QUALITY_SCORES", [])

    metrics.record_request(100, 0.1, 10, 20, 0.8)
    metrics.record_error("TimeoutError")

    result = metrics.snapshot()
    assert result["traffic"] == 2
    assert result["error_rate_pct"] == 50.0
    assert result["error_breakdown"] == {"TimeoutError": 1}
