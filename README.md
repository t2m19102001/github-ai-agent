# 🤖 GitHub AI Agent - Hybrid (Local + Cloud)

Một AI Agent tự động cho GitHub Issues sử dụng **Hybrid Mode** - kết hợp Ollama (Local) + HuggingFace (Cloud).

## ✨ Tính năng

- ✅ **Hybrid Mode**: Chạy Ollama local, fallback sang HuggingFace nếu cần
- ✅ Tự động phân tích GitHub Issues
- ✅ Comment lên issue với AI suggestions chi tiết
- ✅ Code examples & implementation steps
- ✅ Hoàn toàn miễn phí
- ✅ Chạy trên GitHub Actions (24/7)
- ✅ Support Local development
- ✅ Intelligent fallback mechanism

## 🚀 Quick Start

### 1. Tạo HuggingFace Account (2 phút)

```bash
# Vào https://huggingface.co/join
# Signup & xác nhận email
# Vào https://huggingface.co/settings/tokens
# Tạo new token và copy
```

### 2. Setup Repository

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/github-ai-agent.git
cd github-ai-agent

# Install dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env

# Edit .env
# GITHUB_TOKEN=your_token
# REPO_FULL_NAME=your_username/your_repo
# HUGGINGFACE_TOKEN=your_token
```

### 3. Add GitHub Secrets

Repository Settings → Secrets and variables → Actions

```
GITHUB_TOKEN = your_github_personal_access_token
HUGGINGFACE_TOKEN = your_huggingface_api_token
```

### 4. Test Local

```bash
# Make sure Ollama is running (optional for hybrid mode)
ollama serve

# Trong terminal khác
python github_agent_hybrid.py
```

## 📋 Cấu hình

### Environment Variables

```env
# Required
GITHUB_TOKEN=ghp_xxxxx...
REPO_FULL_NAME=username/repo

# Local Mode (Ollama) - Optional
OLLAMA_API=http://localhost:11434
OLLAMA_MODEL=mistral

# Cloud Mode (HuggingFace)
HUGGINGFACE_TOKEN=hf_xxxxx...
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.1

# Settings
MODE=hybrid  # hybrid, local, cloud
DEBUG=false
```

### Modes

- **`hybrid`** (Recommended): Thử Ollama trước, fallback HuggingFace
- **`local`**: Chỉ dùng Ollama (cần máy chạy local)
- **`cloud`**: Chỉ dùng HuggingFace

## 🛠️ Setup Ollama (Optional)

Ollama cho phép agent chạy 100% local, không cần cloud.

### Install Ollama

1. Download: https://ollama.ai
2. Install & run:
   ```bash
   ollama serve
   ```
3. Download model:
   ```bash
   ollama pull mistral
   ```

### Alternative Models

```bash
ollama pull neural-chat      # Chat optimized
ollama pull llama2           # Powerful but slow
ollama pull orca-mini        # Lightweight
```

## 📊 Cách sử dụng

### Automatic Trigger

Agent tự động chạy khi:
- ✅ Issue mới được tạo
- ✅ Issue được thêm label
- ✅ Hàng ngày lúc 9 AM UTC
- ✅ Manual trigger (workflow_dispatch)

### Manual Trigger

```bash
# Local
python github_agent_hybrid.py

# GitHub Actions
# Vào Actions → GitHub AI Agent → Run workflow
```

### Create Test Issue

```markdown
Title: Optimize this function

Body:
def slow_function(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result

How can I make this faster?
```

Agent sẽ tự động comment với analysis!

## 📈 Output Example

```
============================================================
🔍 Processing Issue #1...
============================================================
📌 Title: Optimize this function
👤 Author: @your_username
📝 Status: open

🤖 AI Analysis generated successfully
✅ Comment posted on issue
```

## 🔧 Troubleshooting

### GitHub Connection Error

```
❌ GitHub: [Errno 401] Invalid credentials
```

**Fix**: Kiểm tra GITHUB_TOKEN có đúng không

### Ollama Connection Error

```
⚠️ Ollama: Not available
```

**Fix**: Chạy `ollama serve` hoặc switch mode sang cloud

### HuggingFace Error

```
❌ HuggingFace: 401 Unauthorized
```

**Fix**: Kiểm tra HUGGINGFACE_TOKEN

### Rate Limiting

**Error**: 403 API rate limit exceeded

**Fix**: Agent tự động pause 2s giữa các issues, hoặc reduce limit

## 📊 Performance

### Local Mode (Ollama)
- Response time: ~30-60s (phụ thuộc máy)
- Cost: Free (100%)
- Privacy: 100% (chạy local)

### Cloud Mode (HuggingFace)
- Response time: ~10-30s
- Cost: Free tier 25k requests/month
- Privacy: Data sent to HuggingFace

### Hybrid Mode
- Tries local first (faster)
- Falls back to cloud (reliable)
- Best of both worlds!

## 🔐 Security

- ✅ Tokens trong GitHub Secrets (không commit)
- ✅ `.env` file trong `.gitignore`
- ✅ Local mode không gửi data ra ngoài
- ✅ Cloud mode qua HTTPS

## 📝 Logs

```bash
# Enable debug mode
DEBUG=true python github_agent_hybrid.py
```

Logs sẽ show:
- ✅ Which mode is active
- ✅ API calls details
- ✅ Response times
- ✅ Errors & fallbacks

## 🚀 Next Steps

1. ✅ Setup account (GitHub + HuggingFace)
2. ✅ Add repository secrets
3. ✅ Create test issue
4. ✅ Watch AI comment
5. ✅ Customize prompts (tuỳ chọn)

## 💡 Customize Prompts

Edit `github_agent_hybrid.py` → `generate_analysis()` để change prompt.

Example:

```python
prompt = f"""...
Bạn là security expert. Hãy phân tích security issues...
"""
```

## 📚 Resources

- [GitHub API](https://docs.github.com/en/rest)
- [Ollama](https://ollama.ai)
- [HuggingFace Inference](https://huggingface.co/inference-api)
- [PyGithub](https://pygithub.readthedocs.io/)

## 📄 License

MIT

---

**Made with ❤️ by GitHub AI Agent**

Questions? Create an issue! 🎯