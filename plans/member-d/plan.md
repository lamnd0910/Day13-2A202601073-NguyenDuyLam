# Kế hoạch thành viên D — SRE, SLO, Alerts & Incident

## Mục tiêu

Định nghĩa SLO, alert rules, runbook và dẫn dắt điều tra incident theo luồng Metrics → Traces → Logs → Root cause.

## File phụ trách

- `config/slo.yaml`
- `config/alert_rules.yaml`
- `docs/alerts.md`
- Có thể tạo mới `tests/test_alert_config.py`
- Soạn nội dung mục 6 của `submission/REPORT.md`, sau đó gửi E tổng hợp

Không chỉnh sửa `config/challenge.json`.

## Thứ tự thực hiện

### 1. Hoàn thiện SLO

Đồng bộ với dashboard contract, dự kiến:

- Latency P95 không vượt `3000 ms`.
- Error rate không vượt `2%`.
- Total cost không vượt `2.5 USD` trong cửa sổ dashboard.
- Quality average không thấp hơn `0.75`.

Xóa placeholder như `Replace with your group's target`. Chuẩn bị lý do ngắn gọn cho từng ngưỡng để đưa vào report và phần vấn đáp.

### 2. Hoàn thiện ba alert rules

Alert gợi ý:

#### Alert 1 — HighLatencyP95

- Condition: `latency_p95_ms > 3000`.
- Duration: 5 phút.
- Severity: warning hoặc critical theo quyết định nhóm.
- Owner: SRE.

#### Alert 2 — HighErrorRate

- Condition: `error_rate_pct > 2`.
- Duration: 5 phút.
- Severity: critical.
- Owner: API/SRE.

#### Alert 3 — LowQualityScore

- Condition: `quality_score_avg < 0.75`.
- Duration: 10 phút.
- Severity: warning.
- Owner: AI/LLM.

Mỗi rule phải có:

- `name`
- `severity`
- `condition`
- `duration`
- `type`
- `owner`
- `runbook`

### 3. Hoàn thiện `docs/alerts.md`

Với từng alert, ghi đầy đủ:

- Tên.
- Severity.
- SLI/SLO liên quan.
- Điều kiện và thời gian duy trì.
- Ảnh hưởng tới người dùng.
- Ba bước kiểm tra đầu tiên.
- Mitigation tạm thời.
- Owner.

Ba bước điều tra đầu tiên cần đi theo trình tự:

1. Xác nhận triệu chứng trên dashboard.
2. Mở trace bất thường và xác định span chậm/lỗi.
3. Dùng correlation ID tìm log liên quan.

### 4. Kiểm tra cấu hình

Nếu có thời gian, tạo `tests/test_alert_config.py` để xác nhận:

- YAML đọc được.
- Không còn chuỗi `TODO`.
- Có đúng ba alert.
- Mỗi alert có đủ field bắt buộc.
- Runbook link tới section tồn tại trong `docs/alerts.md`.

### 5. Điều tra challenge chính thức

Repo đã có challenge được release. Không sửa file challenge.

Chạy:

```powershell
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
```

Thu thập:

- Challenge ID.
- Metric bất thường.
- P95 trước và sau incident.
- Trace ID.
- Span bất thường.
- Correlation ID.
- Log line tương ứng.
- Root cause.
- Fix action.
- Preventive measure.

Với challenge hiện tại, giả thuyết ban đầu là tầng RAG chậm, nhưng chỉ kết luận sau khi có metric, trace và log làm bằng chứng.

Sau khi thu thập đủ evidence, tắt incident:

```powershell
python scripts/inject_incident.py --disable
```

## Nội dung bàn giao cho report

Viết sẵn phần sau và gửi E:

```text
Challenge ID:
Triệu chứng từ metrics:
Trace ID liên quan:
Log line/correlation ID liên quan:
Root cause:
Fix action:
Preventive measure:
```

## Evidence cần giao

- Alert rules đã hoàn thiện.
- Runbook đầy đủ.
- Ảnh dashboard có metric bất thường.
- Ảnh trace chỉ ra span bất thường.
- Log đã sanitize có correlation ID liên quan.

## Commit gợi ý

```text
feat(sre): define SLOs alerts and incident runbooks
```

## Phụ thuộc và bàn giao

- Thống nhất threshold với C.
- Nhận trace ID và trace waterfall từ E.
- D dẫn dắt điều tra nhưng cả nhóm phải tham gia để giải thích được phần của mình.
