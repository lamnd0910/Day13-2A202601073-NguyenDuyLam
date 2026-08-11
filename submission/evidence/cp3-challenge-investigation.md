# Điều tra challenge chính thức — bàn giao cho mục 6 của REPORT.md

Người thực hiện: thành viên D (SRE, SLO, Alerts & Incident).
Thời điểm chạy: 2026-08-11, khoảng 05:53–05:54 UTC.
File liên quan: [`cp3-challenge-baseline.txt`](cp3-challenge-baseline.txt), [`cp3-challenge-incident.txt`](cp3-challenge-incident.txt), [`cp3-challenge-logs.jsonl`](cp3-challenge-logs.jsonl).

## Nội dung điền vào REPORT mục 6

```text
Challenge ID: day13-k3-observability-v1 (cohort K3, incident rag_slow, seed 1303,
              affected_feature refund, latency_threshold_ms 2000)

Triệu chứng từ metrics: Panel `latency` của dashboard cho thấy P95 nhảy từ 1111 ms
              (baseline) lên 3612 ms sau khi chạy input chính thức, tức +2501 ms.
              Ngưỡng bị vượt gồm cả latency_threshold_ms 2000 của challenge và SLO
              latency_p95_ms 3000 trong config/slo.yaml, đủ điều kiện kích hoạt alert
              HighLatencyP95 (`latency_p95_ms > 3000` trong 5 phút).
              Các panel còn lại KHÔNG đổi: error_rate_pct giữ 0.00%, quality_avg giữ
              0.86, cost cho 5 request là 0.009651 USD (baseline) so với 0.009936 USD
              (incident). Chỉ latency suy giảm, nên loại trừ lỗi tầng API và suy giảm
              chất lượng prompt ngay từ lớp metrics.

Trace ID liên quan: KHÔNG THU ĐƯỢC. `/health` trả `tracing_enabled: true` nhưng
              Langfuse từ chối cả export lẫn fetch prompt với
              `401 Unauthorized – Invalid credentials. Confirm that you've configured
              the correct host.` Do đó không có trace nào được ghi lên Langfuse và
              không có trace ID thật để dẫn. Theo RULES.md không được bịa trace ID.
              Cần cấp lại LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY/LANGFUSE_HOST rồi
              chạy lại bước này để lấy ảnh trace waterfall.
              Cấu trúc span dự kiến khi có key hợp lệ (theo app/agent.py):
              agent-run -> rag-retrieval, llm-generation.

Log line/correlation ID liên quan: correlation_id `req-63c5ec24`
              (session k3-challenge-s03, feature refund) — request chậm nhất của phase
              incident, latency_ms 3612.
              {"service": "api", "latency_ms": 3612, "tokens_in": 34, "tokens_out": 171,
               "cost_usd": 0.002667, "quality_score": 0.8, "event": "response_sent",
               "env": "dev", "session_id": "k3-challenge-s03", "feature": "refund",
               "correlation_id": "req-63c5ec24", "model": "claude-sonnet-4-5",
               "user_id_hash": "b7fde6ae11b0", "level": "info",
               "ts": "2026-08-11T05:53:59.355458Z"}
              Đối chứng baseline: correlation_id `req-2823db27`, cùng feature refund,
              latency_ms 1111, quality_score 0.9.

Root cause: Tầng RAG retrieval bị chèn độ trễ cố định. Khi incident `rag_slow` bật,
              `app/mock_rag.py:18` chạy `time.sleep(2.5)` bên trong `retrieve()` trước
              khi tra CORPUS. `retrieve()` được gọi từ span `rag-retrieval`
              (`app/agent.py:82`) nằm trong root span `agent-run`, nên toàn bộ 2.5 s
              cộng thẳng vào `latency_ms` của mỗi request. Số liệu khớp: delta P95 đo
              được là 2501 ms, đúng bằng 2.5 s. Không phải lỗi LLM generation
              (tokens_out và cost gần như không đổi), không phải lỗi API
              (error_rate_pct = 0), không phải suy giảm chất lượng (quality_avg = 0.86
              ở cả hai phase).

Fix action: Tắt cờ incident — `python scripts/inject_incident.py --disable`, đã xác
              nhận `/health` trả `rag_slow: false` và incident chấm dứt.
              Với hệ thống thật, fix tương ứng là bỏ độ trễ đồng bộ trong đường đi
              retrieval và đặt timeout cứng cho `retrieve()` kèm fallback answer, thay
              vì để request chờ vô hạn theo tốc độ của vector store.

Preventive measure:
              1. Alert `HighLatencyP95` (`latency_p95_ms > 3000`, duration 5m,
                 severity warning, owner SRE) trong config/alert_rules.yaml, runbook
                 docs/alerts.md#alert-1 — phát hiện tái diễn trong vòng 5 phút.
              2. Timeout + fallback ở tầng retrieval, để một dependency chậm biến
                 thành câu trả lời suy giảm chứ không thành vi phạm SLO toàn hệ thống.
              3. Panel `latency` giữ SLO line 3000 ms để triệu chứng nhìn thấy được
                 ngay trên dashboard 60 phút.
              4. Ghi thời lượng từng span (`rag-retrieval` so với `llm-generation`)
                 để lần sau khoanh vùng tầng chậm mà không cần đọc source.
```

## Cách tái lập

```powershell
uvicorn app.main:app --env-file .env          # không dùng --reload, tránh reset STATE
python scripts/load_test.py --challenge --concurrency 5   # baseline
python scripts/inject_incident.py                          # đọc config/challenge.json
python scripts/load_test.py --challenge --concurrency 5   # incident
python scripts/inject_incident.py --disable
```

P50/P95/P99 lấy từ `data/logs.jsonl` (nguồn chuẩn theo README), lọc `event == "response_sent"` và cắt theo phase. `/metrics` là bộ đếm tích luỹ trong tiến trình, không reset giữa hai phase, nên chỉ dùng để đối chiếu.

Lưu ý số liệu: latency in ra bởi `load_test.py` là latency phía client (4.7–17.8 s) vì gồm cả overhead export Langfuse đang lỗi 401 và hàng đợi của 5 request chạy song song. Số dùng cho SLO là `latency_ms` phía server trong log.

## Việc còn thiếu

- Ảnh dashboard tại thời điểm P95 vượt ngưỡng — cần chạy `streamlit run dashboard/app.py` và chụp, chưa có trong `submission/evidence/`.
- Ảnh trace waterfall chỉ ra span `rag-retrieval` chậm — bị chặn bởi lỗi 401 của Langfuse, phải có key hợp lệ mới lấy được.
- `python scripts/validate_logs.py` trên toàn bộ `data/logs.jsonl` hiện chỉ 50/100 vì file còn 57 dòng cũ sinh trước khi middleware correlation ID hoàn thiện. Chạy validator trên riêng phần log mới (từ dòng 58) cho 100/100, không có PII leak. `data/logs.jsonl` nằm trong `.gitignore` nên không ảnh hưởng bài nộp; trước khi chụp evidence cuối nên xoá file log cũ và chạy lại load test.
