# Điều tra challenge chính thức — bàn giao cho mục 6 của REPORT.md

- Người thiết kế SLO, alert và runbook: Thành viên D — SRE, SLO, Alerts & Incident.
- Người chạy lại trên Langfuse Cloud và thu thập evidence: Thành viên E — Tracing, QA & Report.
- Thời điểm chạy lại: 2026-08-11, khoảng 06:35–06:37 UTC.
- Evidence dashboard: [`cp3-challenge-dashboard.png.jpg`](cp3-challenge-dashboard.png.jpg).
- Evidence trace waterfall: [`cp3-challenge-trace.png.jpg`](cp3-challenge-trace.png.jpg).

## Kết luận điều tra

### Challenge

- Cohort: `K3`.
- Challenge ID: `day13-k3-observability-v1`.
- Incident: `rag_slow`.
- Seed: `1303`.
- Feature bị ảnh hưởng: `refund`.
- Ngưỡng latency của challenge: `2000 ms`.

### Triệu chứng từ metrics

Hai phase dùng cùng năm query chính thức trong `config/challenge.json`:

| Phase | Số request | P50 | P95 | Error rate | Quality avg | Total cost |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (`rag_slow=false`) | 5 | 151 ms | 1097 ms | 0.00% | 0.86 | 0.011766 USD |
| Incident (`rag_slow=true`) | 5 | 2651 ms | 2653 ms | 0.00% | 0.86 | 0.011226 USD |

P95 tăng từ `1097 ms` lên `2653 ms` và vượt ngưỡng challenge `2000 ms`. Error rate vẫn bằng 0, quality trung bình giữ nguyên 0.86 và cost không tăng bất thường. Vì vậy triệu chứng nằm ở latency, không phải lỗi API, cost spike hay suy giảm chất lượng prompt.

P95 `2653 ms` vẫn thấp hơn SLO dashboard `3000 ms`, nên lần chạy ngắn này **chưa kích hoạt** `HighLatencyP95`. Alert chỉ kích hoạt nếu `latency_p95_ms > 3000` được duy trì liên tục trong 5 phút.

### Bằng chứng từ trace

- Trace ID: `3c1c83fbafc6a27991c4dbb59c5cd917`.
- Correlation ID: `req-a30f27c1`.
- Session ID: `k3-challenge-s05`.
- Feature: `refund`.
- Root `agent-run`: `2.65 s`.
- Child span `rag-retrieval`: `2.50 s`.
- Generation `llm-generation`: `0.15 s`.
- Prompt: `day13-chat`, label `candidate`, version `2`, source `langfuse`.
- Cost của request: `0.002154 USD`.

Waterfall cho thấy `rag-retrieval` chiếm gần như toàn bộ thời gian của `agent-run`, trong khi `llm-generation` chỉ mất khoảng 0.15 giây. Đây là bằng chứng trực tiếp khoanh vùng sự cố ở tầng retrieval.

### Bằng chứng từ log

Log `response_sent` có cùng correlation ID với trace:

```json
{
  "service": "api",
  "event": "response_sent",
  "latency_ms": 2653,
  "tokens_in": 63,
  "tokens_out": 131,
  "cost_usd": 0.002154,
  "quality_score": 0.8,
  "env": "dev",
  "session_id": "k3-challenge-s05",
  "feature": "refund",
  "correlation_id": "req-a30f27c1",
  "model": "claude-sonnet-4-5",
  "user_id_hash": "5da42a0d3d01",
  "level": "info",
  "ts": "2026-08-11T06:37:19.966727Z"
}
```

`latency_ms=2653` trong log khớp với root trace `2.65 s`. User ID đã được hash và message/answer chỉ được lưu dưới dạng preview đã sanitize.

### Root cause

Khi `rag_slow` được bật, `retrieve()` trong `app/mock_rag.py` thực hiện `time.sleep(2.5)` trước khi tra corpus. Hàm này được gọi bên trong span `rag-retrieval` của `app/agent.py`, nên độ trễ 2.5 giây được cộng trực tiếp vào thời gian root `agent-run`.

Các request incident có latency server `2651–2653 ms`; trace được chọn ghi nhận `rag-retrieval=2.50 s`. Trong khi đó, bốn trong năm request baseline sau khi prompt đã được cache chỉ mất `151 ms`. Số liệu metrics, trace và log cùng chỉ về tầng RAG retrieval.

### Fix action

Incident đã được tắt bằng:

```powershell
python scripts/inject_incident.py --disable
```

`GET /health` sau điều tra trả:

```json
{"ok":true,"tracing_enabled":true,"incidents":{"rag_slow":false,"tool_fail":false,"cost_spike":false}}
```

Trong hệ thống thật, fix tương ứng là loại bỏ thao tác blocking trên đường retrieval, đặt timeout cho vector store và trả fallback answer khi dependency vượt timeout.

### Preventive measures

1. Duy trì alert `HighLatencyP95` với điều kiện `latency_p95_ms > 3000` trong 5 phút, severity `warning`, owner `SRE`.
2. Bổ sung timeout, fallback và circuit breaker cho tầng retrieval.
3. Theo dõi riêng duration của `rag-retrieval` và `llm-generation` để phân biệt RAG chậm với LLM chậm.
4. Giữ panel latency có P50/P95/P99 và SLO line; đối chiếu thêm traffic để phát hiện latency do hàng đợi.
5. Dùng correlation ID xuyên suốt Metrics → Traces → Logs trong mọi lần điều tra.

## Cách tái lập

```powershell
uvicorn app.main:app --env-file .env
python scripts/inject_incident.py --disable
python scripts/load_test.py --challenge --concurrency 5
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
python scripts/inject_incident.py --disable
```

Không dùng `--reload` khi chạy incident vì reload tiến trình sẽ reset trạng thái incident trong bộ nhớ.

## Kết quả kiểm tra cuối của log

`python scripts/validate_logs.py` trên 125 records:

- Missing required fields: `0`.
- Missing enrichment: `0`.
- Potential PII leaks: `0`.
- Estimated score: `100/100`.
