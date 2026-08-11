# Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

Cấu hình máy đọc được nằm ở [`config/alert_rules.yaml`](../config/alert_rules.yaml); ngưỡng lấy từ [`config/slo.yaml`](../config/slo.yaml) và phải khớp threshold trong [`config/dashboard.yaml`](../config/dashboard.yaml). Sửa ngưỡng ở một nơi thì phải sửa cả ba; `tests/test_alert_config.py` sẽ chặn nếu lệch.

## Quy ước severity

- `critical`: người dùng đang mất chức năng, gọi on-call ngay.
- `warning`: trải nghiệm suy giảm nhưng dịch vụ vẫn trả lời được, xử lý trong giờ làm việc.

Vì vậy chỉ `HighErrorRate` là `critical`. Latency và quality để `warning` để tránh alert fatigue — nếu mọi alert đều critical thì không alert nào còn critical.

## Luồng điều tra chung

Ba bước đầu tiên của cả ba alert đều đi theo cùng một trình tự, từ triệu chứng đến bằng chứng:

1. **Metrics** — xác nhận triệu chứng trên dashboard (time range 60 phút), so panel liên quan với đường threshold.
2. **Traces** — mở một trace bất thường trong khoảng đó, so thời lượng các span: `agent-run` (root) so với `rag-retrieval` và `llm-generation`.
3. **Logs** — lấy `correlation_id` từ metadata của trace, tìm dòng tương ứng trong `data/logs.jsonl`.

Chỉ kết luận root cause khi bằng chứng khớp ở cả ba lớp.

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- SLI/SLO liên quan: `latency_p95_ms`, objective 3000 ms, target 99.5%. Nguồn: `response_sent.latency_ms` trong `data/logs.jsonl`, panel dashboard `latency`.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong 5 phút. Chọn 5 phút để một burst ngắn hoặc một cold start không tạo alert giả.
- Ảnh hưởng tới người dùng: 5% request chậm nhất mất hơn 3 giây mới có câu trả lời; người dùng bỏ ngang hội thoại hoặc bấm gửi lại, làm tải tăng thêm.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `latency`, xác nhận đường P95 vượt threshold 3000 ms và ghi lại thời điểm bắt đầu; đối chiếu panel `traffic` xem latency tăng có đi kèm traffic tăng không.
  2. Mở một trace chậm trong khoảng đó, so `rag-retrieval` với `llm-generation` để biết thời gian nằm ở tầng nào. Nếu `rag-retrieval` chiếm phần lớn `agent-run` thì nghi ngờ tầng retrieval.
  3. Lấy `correlation_id` trong metadata của trace, tìm dòng `response_sent` cùng ID trong `data/logs.jsonl` và đọc `latency_ms` để xác nhận số liệu khớp trace.
- Mitigation tạm thời: rollback thay đổi gần nhất ở tầng retrieval; đặt timeout cứng cho `retrieve()` kèm fallback answer; hạ concurrency để giảm hàng đợi. Nếu nguyên nhân là incident flag đang bật thì tắt bằng `python scripts/inject_incident.py --disable`.
- Owner: SRE

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- SLI/SLO liên quan: `error_rate_pct`, objective 2%, target 99.0%. Nguồn: `count(request_failed) / count(request_received) * 100` trên `data/logs.jsonl`, panel dashboard `errors`.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục trong 5 phút. Giữ 5 phút để bỏ qua một lỗi lẻ trong lúc traffic thấp, nhưng vẫn phát hiện sớm khi lỗi thành hệ thống.
- Ảnh hưởng tới người dùng: request trả HTTP 500, người dùng không nhận được câu trả lời nào. Đây là mất chức năng chứ không phải chậm.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `errors`, xác nhận `error_rate_pct` vượt 2% và xem breakdown theo `error_type` để biết một loại lỗi chiếm ưu thế hay nhiều loại cùng tăng.
  2. Mở một trace lỗi trong khoảng đó, xác định span nào kết thúc bất thường — ví dụ `rag-retrieval` dừng sớm khi vector store timeout.
  3. Lọc `data/logs.jsonl` theo `event == "request_failed"`, đọc `error_type` và `payload.detail` (ví dụ `RuntimeError` kèm `Vector store timeout`), rồi dùng `correlation_id` để đối chiếu ngược lại trace.
- Mitigation tạm thời: trả fallback answer khi vector store lỗi thay vì raise; bật circuit breaker cho dependency đang hỏng; rollback deploy gần nhất. Nếu do incident practice thì `python scripts/inject_incident.py --scenario tool_fail --disable`.
- Owner: API/SRE

## Alert 3

- Tên: `LowQualityScore`
- Severity: `warning`
- SLI/SLO liên quan: `quality_score_avg`, objective 0.75, target 95%. Nguồn: `mean(response_sent.quality_score)` trên `data/logs.jsonl`, panel dashboard `quality`.
- Điều kiện và thời gian duy trì: `quality_score_avg < 0.75` liên tục trong 10 phút. Cửa sổ dài hơn hai alert kia vì quality là trung bình động, nhạy với số mẫu nhỏ và dao động tự nhiên giữa các loại câu hỏi.
- Ảnh hưởng tới người dùng: hệ thống vẫn trả lời nhanh và không lỗi, nhưng câu trả lời chung chung, thiếu dẫn chứng từ tài liệu. Đây là loại sự cố mà latency và error rate không phát hiện được.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel `quality`, xác nhận đường trung bình nằm dưới SLO line 0.75; đối chiếu panel `latency` và `errors` để chắc chắn đây là suy giảm chất lượng độc lập, không phải hệ quả của sự cố khác.
  2. Mở vài trace điểm thấp, kiểm tra `doc_count` trên span `rag-retrieval` (retrieval trả rỗng thì mất 0.2 điểm) và `prompt_name` / `prompt_label` / `prompt_version` trên `llm-generation` xem có trùng thời điểm đổi prompt version không.
  3. Dùng `correlation_id` tìm dòng `response_sent` tương ứng, đọc `quality_score` và `payload.answer_preview`; nếu preview chứa `[REDACTED_...]` thì điểm tụt do PII bị che trong câu trả lời chứ không phải do prompt.
- Mitigation tạm thời: rollback label `production` về prompt version trước theo [PROMPT_VERSIONING.md](PROMPT_VERSIONING.md); nếu nguyên nhân là retrieval trả rỗng thì khôi phục corpus hoặc nới điều kiện match trước khi tinh chỉnh prompt.
- Owner: AI/LLM
