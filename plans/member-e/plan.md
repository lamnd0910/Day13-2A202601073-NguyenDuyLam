# Kế hoạch thành viên E — Tracing, Prompt Version, QA & Report

## Mục tiêu

Hoàn thiện trace waterfall cho RAG/LLM, tạo bằng chứng prompt versioning và rollback, chạy QA tích hợp, sau đó tổng hợp report cùng evidence của cả nhóm.

## File phụ trách

- `app/tracing.py`
- `app/prompt_management.py`
- `app/agent.py`
- `tests/test_tracing_adapter.py`
- `tests/test_prompt_management.py`
- `tests/test_agent_prompt_trace.py`
- `submission/REPORT.md`
- Quản lý danh sách file trong `submission/evidence/`

Không commit `.env` hoặc Langfuse key.

## Thứ tự thực hiện

### 1. Kiểm tra cấu hình Langfuse

Trong `.env` local, cấu hình:

```dotenv
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

Khởi động lại API sau khi thay đổi biến môi trường. Kiểm tra `/health` trả `tracing_enabled: true`.

### 2. Hoàn thiện trace waterfall

Trace nên có cấu trúc rõ ràng:

```text
agent-run
├── rag-retrieval
└── llm-generation
```

Công việc trong `app/agent.py`:

- Dùng root span cho toàn bộ agent run.
- Tạo child span cho RAG retrieval.
- Tạo generation observation cho LLM call.
- Ghi latency, token và cost vào observation phù hợp.
- Giữ liên kết managed prompt với generation.
- Không capture raw input/output có thể chứa PII.
- Chỉ dùng preview đã qua `summarize_text()`.

Metadata trace/generation cần có:

- `user_id_hash`
- `session_id`
- `feature`
- `model`
- `prompt_name`
- `prompt_label`
- `prompt_version`
- `prompt_source`

### 3. Hoàn thiện và chạy test tracing

Kiểm tra:

- Không có key thì tracing disabled và app vẫn chạy local fallback.
- Có Langfuse thì managed prompt được lấy đúng name/label.
- Fetch prompt lỗi thì hiện rõ `local-fallback`.
- Trace metadata chứa prompt version.
- Generation được link với managed prompt.
- Input/output nhạy cảm không bị capture tự động.

Chạy:

```powershell
python -m pytest -q tests/test_tracing_adapter.py tests/test_prompt_management.py tests/test_agent_prompt_trace.py
```

### 4. Tạo prompt version trên Langfuse

Prompt `day13-chat` phải giữ đúng biến:

```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

Thực hiện:

1. Tạo version 1 với labels `baseline` và `production`.
2. Tạo version 2 với label `candidate`.
3. Chạy cùng một input với `baseline` và `candidate`.
4. Kiểm tra trace có đúng prompt name, label và version.
5. Chuyển `production` sang version 2 và chạy lại request.
6. Rollback `production` về version 1.
7. Chụp bằng chứng trước/sau rollback.

Không cần chứng minh version 2 trả lời hay hơn; yêu cầu chính là truy vết và rollback được.

### 5. Tạo ít nhất 10 traces

Sau khi A đã merge correlation ID:

```powershell
python scripts/load_test.py --concurrency 5
```

Kiểm tra:

- Có tối thiểu 10 traces.
- Có trace waterfall.
- Trace có metadata prompt.
- Có thể lấy correlation ID từ request để tìm log tương ứng.
- Có trace baseline và candidate.

### 6. QA tích hợp

Sau khi A, B, C và D merge:

```powershell
python scripts/load_test.py --concurrency 5
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python -m pytest -q
git status --short
```

Kiểm tra thêm:

- Không có secret trong Git.
- Evidence không chứa PII nguyên bản.
- Không commit `.env`, `.venv`, cache hoặc log runtime.
- Mỗi thành viên có commit riêng.

### 7. Tổng hợp `submission/REPORT.md`

Nhận nội dung từ từng người:

- A: correlation ID và metadata.
- B: PII redaction và kết quả `validate_logs.py`.
- C: dashboard, metrics và validator.
- D: SLO, alerts, runbook và challenge investigation.
- E: traces, prompt versions và rollback.

Điền đầy đủ:

- Thông tin nhóm và repository.
- Kết quả kỹ thuật.
- Logging và tracing.
- Prompt versioning.
- Dashboard, SLO và alerts.
- Challenge investigation.
- Bảng đóng góp cá nhân và commit/PR.

## Evidence E trực tiếp phụ trách

- `submission/evidence/cp2-trace-list.png`
- `submission/evidence/cp2-trace-waterfall.png`
- `submission/evidence/cp2-prompt-versions.png`
- `submission/evidence/cp2-baseline-trace.png`
- `submission/evidence/cp2-candidate-trace.png`
- `submission/evidence/cp2-prompt-rollback.png`

E cũng kiểm tra tất cả đường dẫn evidence trong report là đường dẫn tương đối và mở được.

## Commit gợi ý

Commit tracing:

```text
feat(tracing): add RAG and LLM spans with prompt metadata
```

Commit tổng hợp cuối:

```text
docs(submission): complete observability report and evidence index
```

## Phụ thuộc và bàn giao

- Bắt đầu tích hợp tracing sau khi A hoàn thiện correlation ID.
- Cung cấp trace ID và waterfall cho D điều tra incident.
- E là người duy nhất tổng hợp `submission/REPORT.md` cuối để tránh merge conflict; các thành viên khác gửi nội dung và evidence cho E.
