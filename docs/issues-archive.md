# Issues Archive

> Bản lưu trữ các issue gốc (#1–#5) trước khi xóa vĩnh viễn khỏi GitHub.
> Xuất ngày 2026-06-20. Các issue này thuộc kiến trúc AI Agent giai đoạn đầu,
> đã được thay thế bằng bộ roadmap 2-surface mới.

---

## #1 — Test Issue: AI Agent Analysis

- **Author:** @t2m19102001
- **Created:** 2025-11-28
- **Labels:** (none)

# Test Issue

This is a test issue to demonstrate the GitHub AI Agent capabilities.

## Problem
The agent should be able to:
1. Detect and parse issue content
2. Analyze the issue using an AI model
3. Generate helpful comments with insights

## Expected Behavior
The agent should provide a detailed analysis of this issue.

## Additional Context
This is a test to verify the AI agent is working correctly.

---

## #2 — Thiết kế abstract base cho AI Provider (Groq, HuggingFace, Ollama, ...): Chuẩn hoá tích hợp đa AI backend

- **Author:** @t2m19102001
- **Created:** 2025-12-23
- **Labels:** (none)

## Mục tiêu
- Xây dựng abstract base class `ProviderBase` để gom toàn bộ logic gọi AI (Groq, HuggingFace, Local Ollama, v.v.) qua 1 interface duy nhất.
- Dễ mở rộng thêm provider về sau (plug-n-play, dễ test), tránh lặp code.

## Công việc
- [ ] Tạo file `src/agent/ai_provider.py`
- [ ] Thiết kế abstract base class `ProviderBase` với các method bắt buộc: `get_response(prompt)`, `is_available()`, `name`
- [ ] Implement GroqProvider, HuggingFaceProvider, OllamaProvider theo interface chung
- [ ] Các provider đọc config từ `.env` (hoặc truyền runtime param)
- [ ] Viết unit test tối giản cho các class provider
- [ ] Cập nhật `main.py`/core workflow để sử dụng ProviderBase interface
- [ ] Update README/docs giải thích kiến trúc mới, hướng dẫn thêm provider

## Ghi chú
- Base này là nền tảng để agent có thể hybrid hoặc fallback nhiều AI backend linh hoạt
- Tất cả provider đều return response dạng string, throw exception nếu error
- Có thể dùng ABC và typing của Python cho type-safe

---

## #3 — Refactor agent workflow: sử dụng ProviderBase cho luồng xử lý chính (CLI/API/Web)

- **Author:** @t2m19102001
- **Created:** 2025-12-23
- **Labels:** (none)

## Mục tiêu
- Chuẩn hoá workspace: mọi nơi gọi AI đều đi qua interface ProviderBase (tạo bởi task-provider-base-interface)
- Giảm duplicate code, dễ bảo trì, cho phép mix nhiều provider, dễ test từng backend

## Công việc
- [ ] Refactor `main.py`, `run_web.py`, `run_fastapi.py` (nếu có) để dùng ProviderBase
- [ ] Tích hợp chọn provider (Groq, HuggingFace, Ollama,...) động qua config/biến môi trường/CLI option
- [ ] Đảm bảo mọi exception/timeout đều được log + xử lý rõ ràng
- [ ] Cho phép agent fallback giữa các provider nếu provider chính fail
- [ ] Test thử với ít nhất 2 provider (vd: Groq + HuggingFace)
- [ ] Update tài liệu, mô tả use-case mới, cách config provider

## Ghi chú:
- Kết nối mạnh hơn giữa core agent logic và AI backend (ProviderBase)
- Hướng tới plug-n-play và test tự động từng backend AI khác nhau

---

## #4 — Thiết kế cấu trúc plugin cho AI Agent: hỗ trợ workflow mở rộng dễ dàng

- **Author:** @t2m19102001
- **Created:** 2025-12-23
- **Labels:** enhancement

## Mục tiêu
- Cho phép AI Agent mở rộng các workflow mới (plugin pattern): auto test code, auto tạo PR, custom comment, rule trigger theo label, ...
- Tách biệt code logic từng feature/thành phần → gắn-tráo đổi dễ test/dễ bảo trì

## Công việc
- [ ] Thiết kế base `AgentPluginBase` trong `src/agent/plugins/`
- [ ] Ví dụ 2-3 plugin nhỏ: auto_comment_on_issue, auto_create_pr, auto_check_code_quality
- [ ] Tích hợp registry: cho phép enable/disable plugin qua config/env
- [ ] Update workflow để gọi plugin tương ứng khi gặp đúng trigger (vd: khi issue có label bug thì bật code quality plugin)
- [ ] Viết tài liệu hướng dẫn viết plugin mới

## Ghi chú
- Hệ thống plugin giúp sản phẩm phát triển mở rộng lâu dài, code luôn clean
- Với mỗi plugin có thể viết test riêng dễ dàng
- Lấy cảm hứng từ VSCode extension hoặc pytest plugin pattern

---

## #5 — Xây dựng REST API chuẩn (với FastAPI) cho AI Agent

- **Author:** @t2m19102001
- **Created:** 2025-12-23
- **Labels:** (none)

## Mục tiêu
- Phục vụ nhu cầu tích hợp với hệ thống ngoài, có thể trigger từ script/custom app/webhook/postman
- Dễ dàng test & mở rộng tính năng bên ngoài CLI truyền thống

## Công việc
- [ ] Tạo service FastAPI trong `run_fastapi.py`/`src/agent/api.py`
- [ ] Expose: /analyze-issue, /providers, /plugins endpoint (ví dụ)
- [ ] Swagger UI auto-gen để test API
- [ ] Allow config qua env/CLI (port, debug)
- [ ] Bảo mật cơ bản (token/base auth/allowlist IP)
- [ ] Viết ví dụ request (curl, Postman, ...)

## Ghi chú
- Đây là bước quan trọng để AI agent scale hơn, dễ UI/web app hóa sau này
- FastAPI dễ maint/support async, OpenAPI hỗ trợ tốt auto-docs

---

