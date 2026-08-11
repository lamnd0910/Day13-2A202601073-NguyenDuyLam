# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: **Nhóm K3-DAY13-A2-2**
- Repository: https://github.com/lamnd0910/Day13-2A202601073-NguyenDuyLam
- Commit SHA tích hợp code trước khi tổng hợp báo cáo: `75a6a37`

| Vai trò | Thành viên | Mã sinh viên |
|---|---|---|
| A — API & Middleware | Nguyễn Khắc Huy | 2A202602036 |
| B — Security & PII | Lê Kim Nam | 2A202601803 |
| C — Metrics & Dashboard | Nguyễn Minh Hoàng | 2A202601609 |
| D — SRE, SLO, Alerts & Incident | Nguyễn Quốc Hiệu | 2A202601627 |
| E — Tracing, Prompt Version, QA & Report | Nguyễn Duy Lâm | 2A202601073 |

## 2. Kết quả kỹ thuật

- `python scripts/validate_logs.py`: **100/100** trên 125 log records tại thời điểm kiểm tra challenge.
- Missing required fields: **0**; missing enrichment: **0**; potential PII leaks: **0**.
- Langfuse: **45 root traces** trong evidence, vượt yêu cầu tối thiểu 10 traces.
- Trace waterfall có root `agent-run`, child span `rag-retrieval` và generation `llm-generation`.
- `python scripts/validate_dashboard.py`: **HỢP LỆ — 6/6 panel**.
- Dashboard runtime: chạy bằng `streamlit run dashboard/app.py`, đọc trực tiếp `data/logs.jsonl`, time range 60 phút và refresh 30 giây.
- Toàn bộ incident flags đã được tắt sau điều tra; `/health` trả `rag_slow=false`, `tool_fail=false`, `cost_spike=false`.

Evidence tổng quan:

- Kết quả log validator: `submission/evidence/cp1-validate-logs.txt`.
- Danh sách 45 root traces: `submission/evidence/cp2-trace-list.png.jpg`.
- Dashboard baseline: `submission/evidence/cp2-dashboard-baseline.png`.
- Dashboard khi RAG chậm: `submission/evidence/cp2-dashboard-rag-slow.png`.
- Dashboard challenge: `submission/evidence/cp3-challenge-dashboard.png.jpg`.

## 3. Logging và tracing

Mỗi request có correlation ID dạng `req-xxxxxxxx`, được trả về response, bind vào request context và xuất hiện trong các log `request_received`, `response_sent` hoặc `request_failed`. Log được enrich bằng `session_id`, `feature`, `model`, `env` và `user_id_hash`.

- Evidence correlation ID và schema: `submission/evidence/cp1-validate-logs.txt`.
- Evidence PII redaction: `submission/evidence/cp1-pii-redaction.txt`.
- Không lưu user ID nguyên bản; user ID được hash trước khi ghi log/trace.
- Email, số điện thoại, số thẻ và dữ liệu nhạy cảm lồng trong payload/exception được scrub trước khi ghi.
- Trace không tự động capture raw input/output; query và answer chỉ xuất hiện dưới dạng preview đã sanitize.

Cấu trúc trace:

```text
agent-run
├── rag-retrieval
└── llm-generation
```

`rag-retrieval` ghi component, doc count và query preview đã sanitize. `llm-generation` ghi model, token usage, cost và metadata managed prompt. Root trace ghi prompt name/label/version/source cùng correlation ID để liên kết Trace → Log.

- Baseline waterfall: `submission/evidence/cp2-trace-waterfall-baseline.png.jpg`.
- Candidate waterfall: `submission/evidence/cp2-trace-waterfall-candidate.png.jpg`.
- Challenge waterfall: `submission/evidence/cp3-challenge-trace.png.jpg`.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Prompt contract: `feature`, `docs`, `message`.
- Version 1: labels `baseline` và `production` sau rollback.
- Version 2: label `candidate`.
- Baseline Trace ID: `f5886983b4f1efc531ca1079c57a7381` — `baseline`, version 1, source `langfuse`.
- Candidate Trace ID: `19adf03072d42cd01a9ad52827c2ed64` — `candidate`, version 2, source `langfuse`.

Quy trình rollback đã thực hiện:

1. Gắn `production` sang version 2; version 2 có `production + candidate`, version 1 chỉ còn `baseline`.
2. Xác minh ứng dụng có thể resolve label `production` tới version 2.
3. Rollback `production` về version 1; trạng thái cuối là version 1 có `production + baseline`, version 2 chỉ còn `candidate`.

Evidence:

- Hai prompt versions: `submission/evidence/cp2-prompt-versions.png.jpg`.
- Promote production sang v2: `submission/evidence/cp2-production-promoted-v2.jpg`.
- Rollback production về v1: `submission/evidence/cp2-prompt-rollback.jpg`.

## 5. Dashboard, SLO và alerts

Dashboard đọc nguồn chuẩn `data/logs.jsonl` và có đủ sáu nhóm chỉ số:

| Panel | Chỉ số | Đơn vị/threshold |
|---|---|---|
| Latency | P50, P95, P99 | ms; P95 ≤ 3000 ms |
| Traffic | Request theo phút | requests/minute; ≥ 1 |
| Errors | Error rate và breakdown | percent; ≤ 2% |
| Cost | Cost theo phút và tổng | USD; ≤ 2.5 |
| Tokens | Input/output tokens | tokens; tổng ≤ 50,000 |
| Quality | Quality proxy trung bình | 0–1; ≥ 0.75 |

SLO trong `config/slo.yaml`:

- Latency P95 objective `3000 ms`, target `99.5%`: bảo vệ tail latency mà average có thể che mất.
- Error rate objective `2%`, target `99%`: vượt 2% thể hiện mất chức năng đáng kể.
- Cost objective `2.5 USD` trong cửa sổ dashboard: phát hiện retry loop hoặc prompt phình.
- Quality average objective `0.75`, target `95%`: phát hiện câu trả lời suy giảm dù latency/error bình thường.

Alert rules trong `config/alert_rules.yaml`:

- `HighLatencyP95`: `latency_p95_ms > 3000` trong 5 phút, severity `warning`, owner `SRE`.
- `HighErrorRate`: `error_rate_pct > 2` trong 5 phút, severity `critical`, owner `API/SRE`.
- `LowQualityScore`: `quality_score_avg < 0.75` trong 10 phút, severity `warning`, owner `AI/LLM`.

Runbook `docs/alerts.md` đi theo luồng Metrics → Traces → Logs và có mitigation/owner cho từng alert.

Evidence:

- Validator: `submission/evidence/cp2-dashboard-validator.txt`.
- Dashboard baseline: `submission/evidence/cp2-dashboard-baseline.png`.
- Dashboard RAG chậm: `submission/evidence/cp2-dashboard-rag-slow.png`.

## 6. Điều tra challenge

- Cohort: `K3`.
- Challenge ID: `day13-k3-observability-v1`.
- Incident: `rag_slow`.
- Feature bị ảnh hưởng: `refund`.
- Ngưỡng latency challenge: `2000 ms`.

Kết quả hai phase dùng cùng năm query chính thức:

| Phase | P50 | P95 | Error rate | Quality avg |
|---|---:|---:|---:|---:|
| Baseline | 151 ms | 1097 ms | 0.00% | 0.86 |
| Incident | 2651 ms | 2653 ms | 0.00% | 0.86 |

P95 incident vượt ngưỡng challenge 2000 ms nhưng vẫn dưới SLO dashboard 3000 ms. Do đó lần chạy này chứng minh suy giảm latency, nhưng chưa kích hoạt `HighLatencyP95`; alert chỉ kích hoạt nếu P95 vượt 3000 ms liên tục 5 phút.

- Trace ID: `3c1c83fbafc6a27991c4dbb59c5cd917`.
- Correlation ID: `req-a30f27c1`.
- Session ID: `k3-challenge-s05`.
- Root `agent-run`: `2.65 s`.
- `rag-retrieval`: `2.50 s`.
- `llm-generation`: `0.15 s`.
- Log cùng correlation ID: `latency_ms=2653`, `cost_usd=0.002154`, `quality_score=0.8`.

Root cause: `rag_slow` chèn `time.sleep(2.5)` trong `retrieve()`; trace xác nhận span `rag-retrieval` chiếm gần toàn bộ root duration. Error rate và quality không đổi, còn LLM generation chỉ mất 0.15 giây, nên loại trừ API error, prompt degradation và LLM slowdown.

Fix action: chạy `python scripts/inject_incident.py --disable`; `/health` sau điều tra xác nhận toàn bộ incident flags bằng false. Với hệ thống thật, cần loại bỏ blocking retrieval, đặt timeout và dùng fallback khi vector store chậm.

Preventive measures: alert tail latency, timeout/fallback/circuit breaker cho retrieval, theo dõi duration theo từng span và duy trì correlation ID xuyên Metrics → Traces → Logs.

Evidence chi tiết: `submission/evidence/cp3-challenge-investigation.md`.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Khắc Huy — 2A202602036 | Correlation ID middleware, request context và structured logging | `d4938fa`, PR #1 | Liên kết request, response và log bằng correlation ID |
| Lê Kim Nam — 2A202601803 | Recursive PII redaction và exception sanitization | `1bf631b`, `2935360`, PR #2 | Scrub dữ liệu nhạy cảm cả trước và sau bước format exception |
| Nguyễn Duy Lâm — 2A202601073 | RAG/LLM waterfall, prompt version/rollback, QA, cloud evidence và report | `1455712`, PR #3 | Liên kết managed prompt với trace và điều tra qua Metrics → Traces → Logs |
| Nguyễn Minh Hoàng — 2A202601609 | Metrics, error rate và Streamlit dashboard sáu panel | `5eb70cd`, PR #4 | Tính percentile từ log chuẩn và kiểm chứng dashboard bằng incident |
| Nguyễn Quốc Hiệu — 2A202601627 | SLO, ba alert rules, runbook và khung điều tra challenge | `d72db40`, PR #5 | Thiết kế alert theo triệu chứng, duration, severity và owner |

## 8. Trạng thái bàn giao

- Code của A, B, C, D và E đã merge vào `main`.
- Prompt v1/v2, promote và rollback đã có evidence.
- Có 45 root traces và trace waterfall RAG/LLM.
- Dashboard runtime đủ sáu panel; validator đạt 6/6.
- Challenge có metric, trace ID, correlation ID, log, root cause, fix và preventive measures.
- `.env`, API keys, `.venv`, runtime logs và file backup log không được đưa vào commit nộp bài.
