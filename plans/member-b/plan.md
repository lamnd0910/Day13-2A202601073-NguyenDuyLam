# Kế hoạch thành viên B — Security & PII

## Mục tiêu

Đảm bảo email, số điện thoại, CCCD, số thẻ và dữ liệu nhạy cảm không được ghi nguyên văn vào log. PII phải được scrub trước khi JSON được ghi xuống `data/logs.jsonl`.

## File phụ trách

- `app/pii.py`
- `app/logging_config.py`
- `tests/test_pii.py`
- Tạo mới `tests/test_logging_pii.py`

Không sửa `scripts/validate_logs.py` để làm validator dễ qua hơn. Dùng script này như bộ kiểm tra độc lập.

## Thứ tự thực hiện

### 1. Rà soát regex trong `app/pii.py`

Đảm bảo phát hiện và che được:

- Email: `student@vinuni.edu.vn`
- Điện thoại: `0901234567`
- Điện thoại có khoảng trắng: `090 123 4567`
- Điện thoại có mã quốc gia: `+84 90 123 4567`
- CCCD 12 chữ số: `012345678901`
- Credit card: `4111 1111 1111 1111`
- Credit card có dấu gạch: `4111-1111-1111-1111`

Passport hoặc địa chỉ là phần mở rộng. Chỉ thêm nếu regex đủ an toàn và không che nhầm dữ liệu thông thường.

### 2. Làm `scrub_event` hoạt động đệ quy

Hiện processor mới xử lý một phần payload. Cần bổ sung hàm scrub đệ quy cho:

- Chuỗi trực tiếp.
- Dictionary lồng nhau.
- List hoặc tuple chứa chuỗi.
- `payload.detail` và exception detail.
- Các field text được thêm về sau.

Không chỉ scrub `message_preview`, vì PII có thể xuất hiện trong nhiều field khác.

### 3. Đăng ký processor trong `app/logging_config.py`

Bật `scrub_event` và đặt nó trước bước ghi file:

```text
merge_contextvars
→ add_log_level
→ timestamp
→ scrub_event
→ exception processors
→ JsonlFileProcessor
→ JSONRenderer
```

Nếu scrub sau `JsonlFileProcessor`, dữ liệu nhạy cảm đã bị ghi xuống file và vẫn bị tính là leak.

### 4. Viết test

Bổ sung vào `tests/test_pii.py`:

- Email.
- Các format số điện thoại.
- CCCD.
- Credit card.
- Nested dictionary.
- List chứa PII.
- Chuỗi không có PII phải được giữ nguyên.

Trong `tests/test_logging_pii.py`:

- Gọi `/chat` bằng message có PII.
- Đọc file log test.
- Xác nhận dữ liệu gốc không xuất hiện.
- Xác nhận placeholder `[REDACTED_...]` xuất hiện.

## Kiểm tra bàn giao

Sau khi tích hợp code của A:

```powershell
uvicorn app.main:app --reload --env-file .env
```

Ở terminal khác:

```powershell
python scripts/load_test.py
python scripts/validate_logs.py
python -m pytest -q
```

Mục tiêu:

```text
Potential PII leaks detected: 0
[PASSED] PII scrubbing
Estimated Score: 100/100
```

## Evidence cần giao

- `submission/evidence/cp1-validate-logs.txt`
- `submission/evidence/cp1-pii-redaction.txt`
- Gửi đường dẫn evidence cho E tổng hợp vào report.

Evidence chỉ được chứa dữ liệu đã redact.

## Commit gợi ý

```text
feat(security): recursively redact PII before writing logs
```

## Phụ thuộc và bàn giao

- Có thể code song song với A.
- Chạy kiểm tra cuối sau khi A đã thêm toàn bộ logging context.
- Bàn giao log sạch cho C dùng làm nguồn dashboard.
