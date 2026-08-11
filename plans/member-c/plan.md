# Kế hoạch thành viên C — Metrics & Dashboard

## Mục tiêu

Hoàn thiện metrics và dựng dashboard runtime đủ sáu nhóm chỉ số từ nguồn chuẩn `data/logs.jsonl`.

## File phụ trách

- `app/metrics.py`
- `config/dashboard.yaml`
- Tạo mới `dashboard/__init__.py`
- Tạo mới `dashboard/app.py`
- Tạo mới `tests/test_dashboard_runtime.py`
- `requirements.txt` nếu dashboard cần thêm Streamlit/Pandas

Không dùng `/metrics` làm nguồn duy nhất cho ảnh dashboard. Nguồn chuẩn theo yêu cầu bài là `data/logs.jsonl`.

## Thứ tự thực hiện

### 1. Hoàn thiện metrics trong `app/metrics.py`

Kiểm tra `/metrics` trả được:

- `traffic`
- `latency_p50`
- `latency_p95`
- `latency_p99`
- `error_rate_pct`
- `error_breakdown`
- `total_cost_usd`
- `tokens_in_total`
- `tokens_out_total`
- `quality_avg`

Error rate được tính theo:

```text
error_rate_pct = số request lỗi / tổng số request × 100
```

Phải xử lý trường hợp chưa có request để không chia cho 0.

### 2. Viết test cho metrics

Kiểm tra:

- Percentile với danh sách rỗng.
- P50, P95, P99 với dữ liệu mẫu.
- Error rate.
- Error breakdown.
- Tổng token input/output.
- Tổng cost.
- Quality trung bình.

### 3. Dựng dashboard runtime

Khuyến nghị tạo `dashboard/app.py` bằng Streamlit. Dashboard phải đọc trực tiếp từng JSON record trong:

```text
data/logs.jsonl
```

Dashboard gồm đúng sáu panel:

1. Latency: P50, P95, P99.
2. Traffic: số request/phút.
3. Errors: `error_rate_pct` và breakdown theo `error_type`.
4. Cost: cost theo phút và tổng cost.
5. Tokens: tổng input token và output token.
6. Quality: `quality_score` trung bình.

Giữ đúng contract:

- Time range: 60 phút.
- Refresh: 30 giây.
- Hiển thị tên panel.
- Hiển thị đơn vị.
- Hiển thị threshold hoặc SLO line.

Nếu dùng Streamlit/Pandas, bổ sung dependency cần thiết vào `requirements.txt` và ghi cách chạy trong comment hoặc tài liệu ngắn.

### 4. Kiểm tra contract

```powershell
python scripts/validate_dashboard.py
```

Kết quả cần có:

```text
HỢP LỆ: 6/6 panel
```

### 5. Kiểm tra dashboard bằng incident practice

Tạo baseline:

```powershell
python scripts/load_test.py --concurrency 5
```

Bật incident chậm RAG:

```powershell
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5
python scripts/inject_incident.py --scenario rag_slow --disable
```

Xác nhận P95 trên dashboard tăng rõ rệt sau khi bật `rag_slow`.

## Kiểm tra bàn giao

```powershell
python scripts/validate_dashboard.py
python -m pytest -q
```

Nếu dùng Streamlit:

```powershell
streamlit run dashboard/app.py
```

## Evidence cần giao

- `submission/evidence/cp2-dashboard-baseline.png`
- `submission/evidence/cp2-dashboard-rag-slow.png`
- `submission/evidence/cp2-dashboard-validator.txt`
- Ảnh phải thấy tên panel, time range, đơn vị và threshold.

## Commit gợi ý

```text
feat(dashboard): add six-panel runtime observability dashboard
```

## Phụ thuộc và bàn giao

- Chỉ dựng dashboard chính thức sau khi A+B tạo được log đúng schema và sạch PII.
- Thống nhất threshold với D; không tự thay đổi ngưỡng chỉ để dashboard đẹp hơn.
- Bàn giao metric bất thường và ảnh dashboard cho D dùng trong điều tra challenge.
