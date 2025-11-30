# 🚀 Quick Start - GitHub AI Agent

## ✅ Chạy Ngay (3 bước)

### Bước 1: Cài Dependencies
```bash
pip install -r requirements.txt
```

### Bước 2: Chọn LLM Provider

#### Option A: Groq (Khuyến nghị - Free & Fast)
```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_your_key_here
```
- Đăng ký free tại: https://console.groq.com/keys
- Tốc độ: ~300-400 token/s
- Không cần GPU/Ollama

#### Option B: Ollama (Local)
```bash
export LLM_PROVIDER=ollama
# Cài Ollama tại: https://ollama.com/download
ollama pull deepseek-coder-v2:16b-instruct-qat
```

#### Option C: OpenAI (Mạnh nhất)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk_your_key_here
```

### Bước 3: Khởi Động Server
```bash
uvicorn src.web.app:app --reload --port=5000
```

Mở trình duyệt: **http://127.0.0.1:5000**

---

## 🎯 Tính Năng

### 1. **Chat với Codebase**
```
Bạn: "Tìm code liên quan đến embeddings"
AI: [Tự động RAG search 15 file → trả lời chính xác]
```

### 2. **Memory Dài Hạn**
- Ghi nhớ toàn bộ lịch sử chat
- Tự động load 20 message gần nhất
- Persist qua restart server

### 3. **Git Automation**
```
Bạn: "commit nhé"
AI: [Auto git add + commit + push]

Bạn: "tạo branch feature/new-ui"
AI: [Auto git checkout -b feature/new-ui]

Bạn: "có gì thay đổi không?"
AI: [Auto git status + hiện danh sách file]
```

### 4. **Auto Test & Fix**
```
/autofix           → Chạy all tests, tự sửa code nếu fail
/autofix <file>    → Test file cụ thể + auto fix
/test -v           → Run pytest với custom args
```

### 5. **Slash Commands**
```
/help              → Hiện hướng dẫn
/autofix           → Auto test & fix
/test <args>       → Custom pytest
```

---

## 📦 Dependencies Chính

```
langchain-groq        # Groq LLM provider
langchain-ollama      # Ollama provider (local)
langchain-huggingface # Free embeddings
langchain-chroma      # Vector store (RAG + Memory)
fastapi               # Web server
uvicorn               # ASGI server
```

---

## ⚡ So Sánh Providers

| Provider | Tốc độ | Chi phí | GPU | Setup |
|----------|--------|---------|-----|-------|
| **Groq** | ⚡⚡⚡ Nhanh nhất | 🆓 Free | ❌ Không cần | 5 giây |
| Ollama | ⚡⚡ Trung bình | 🆓 Free | ✅ Cần GPU | 10 phút |
| OpenAI | ⚡⚡ Tốt | 💰 Trả phí | ❌ Không cần | 5 giây |

**Khuyến nghị:** Dùng **Groq** cho dev/test, **OpenAI** cho production.

---

## 🐛 Troubleshooting

### Lỗi: "Failed to connect to Ollama"
→ Đổi sang Groq: `export LLM_PROVIDER=groq`

### Lỗi: "HuggingFaceEmbeddings not found"
→ Cài: `pip install langchain-huggingface sentence-transformers`

### Lỗi: Memory corrupt
→ Server tự recover, hoặc xóa: `rm -rf .memory/`

### Lỗi: Chroma deprecation warning
→ Đã fix! Dùng `langchain-chroma` thay vì `langchain-community`

---

## 📚 Cấu Trúc Project

```
github-ai-agent/
├── src/
│   ├── agents/          # CodeChatAgent + tools
│   ├── config/          # LLM provider settings
│   ├── llm/             # Ollama/Groq providers
│   ├── tools/           # RAG, Git, AutoFix
│   ├── web/             # FastAPI + WebSocket
│   ├── memory.py        # Long-term memory
│   └── utils/           # Logger, helpers
├── .memory/             # Memory vector store
├── .chroma/             # RAG vector store
└── requirements.txt     # Dependencies
```

---

## 🎉 Features Hoàn Thành

- ✅ Multi-provider LLM (Groq/Ollama/OpenAI)
- ✅ RAG Semantic Search (15 file/query)
- ✅ Long-term Memory (20 message history)
- ✅ Git Automation (commit, branch, status)
- ✅ Auto Test & Fix Loop
- ✅ WebSocket Real-time UI
- ✅ No mandatory Ollama dependency

---

**Phát triển bởi:** [@t2m19102001](https://github.com/t2m19102001)  
**Ngày cập nhật:** 30 Nov 2025  
**Version:** 1.0.0 - Production Ready 🚀
