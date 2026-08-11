# Kế hoạch thành viên A — API & Middleware

## Mục tiêu

Hoàn thiện correlation ID, request context và structured logging cho API. Sau khi bàn giao, mỗi request phải truy vết được bằng một correlation ID xuyên suốt response và log.

## File phụ trách

- `app/middleware.py`
- `app/main.py`
- `config/logging_schema.json` nếu cần cập nhật schema
- Tạo mới `tests/test_middleware.py`
- Có thể tạo `tests/test_logging_context.py`

Không chỉnh `app/pii.py` và `app/logging_config.py`; hai file đó thuộc thành viên B.

## Thứ tự thực hiện

### 1. Hoàn thiện `app/middleware.py`

- Gọi `clear_contextvars()` ở đầu mỗi request.
- Đọc `x-request-id` từ request header.
- Chỉ chấp nhận ID đúng format `req-<8 ký tự hex>`; nếu thiếu hoặc sai thì sinh ID mới.
- Gọi `bind_contextvars(correlation_id=correlation_id)`.
- Gán ID vào `request.state.correlation_id`.
- Đo tổng thời gian xử lý request.
- Thêm hai response header:
  - `x-request-id`
  - `x-response-time-ms`
- Dùng `try/finally` phù hợp để tránh context của request cũ bị giữ lại khi xảy ra lỗi.

### 2. Hoàn thiện `app/main.py`

Trong endpoint `/chat`, bind các trường sau trước khi ghi log:

```python
bind_contextvars(
    user_id_hash=hash_user_id(body.user_id),
    session_id=body.session_id,
    feature=body.feature,
    model=agent.model,
    env=os.getenv("APP_ENV", "dev"),
)
```

Đảm bảo các event API có đủ context:

- `request_received`
- `response_sent`
- `request_failed`

Không ghi `user_id` nguyên bản vào log. Khi có lỗi, log `request_failed` phải có `error_type` nhưng không làm lộ dữ liệu nhạy cảm.

Exception handler toàn cục là phần mở rộng; chỉ thực hiện sau khi các yêu cầu bắt buộc đã chạy đúng.

### 3. Viết test

Trong `tests/test_middleware.py`, kiểm tra:

- Request không có header vẫn nhận ID dạng `req-xxxxxxxx`.
- Request có ID hợp lệ thì server sử dụng lại ID đó.
- Header sai format không được dùng trực tiếp.
- Hai request độc lập có hai ID khác nhau.
- `x-request-id` trùng với `correlation_id` trong response JSON.
- Response có `x-response-time-ms` hợp lệ.

Trong `tests/test_logging_context.py`, kiểm tra log API có:

- `correlation_id`
- `user_id_hash`
- `session_id`
- `feature`
- `model`
- `env`

## Kiểm tra bàn giao

```powershell
python -m pytest -q
```

Sau khi chạy API và load test:

```powershell
python scripts/validate_logs.py
```

Phần của A đạt khi:

- Không còn `correlation_id: "MISSING"` trong log API.
- Có ít nhất hai correlation ID khác nhau.
- Không thiếu enrichment fields.
- Correlation ID trong response và log khớp nhau.

## Evidence cần giao

- Log JSON có correlation ID và metadata.
- Kết quả test middleware.
- Gửi đường dẫn evidence cho E tổng hợp vào `submission/REPORT.md`.

## Commit gợi ý

```text
feat(logging): add correlation ID middleware and request context
```

## Phụ thuộc và bàn giao

- Có thể làm song song với B.
- Merge A trước E để trace có thể liên kết với log qua correlation ID.
- Báo cho B biết chính xác các field context được thêm để B kiểm tra PII trên toàn bộ event.
