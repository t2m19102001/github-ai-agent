# 🤖 GitHub AI Agent - Cloud LLM

Một AI Agent tự động cho GitHub Issues sử dụng **Cloud LLM** (GROQ + HuggingFace).

## ✨ Tính năng

- ✅ **Cloud Mode**: GROQ (5-10s) + HuggingFace (10-30s) fallback
- ✅ Tự động phân tích GitHub Issues
- ✅ Comment lên issue với AI suggestions chi tiết
- ✅ Code examples & implementation steps
- ✅ Hoàn toàn miễn phí
- ✅ Chạy trên GitHub Actions (24/7)
- ✅ Intelligent fallback mechanism (GROQ → HuggingFace)

## 🚀 Quick Start

### 1. Get API Keys (2 phút)

**GROQ (Recommended)** ⭐
```bash
# https://console.groq.com/keys
# Click "Create API Key"
# Copy: gsk_xxxxx...
```

**HuggingFace (Fallback)**
```bash
# https://huggingface.co/settings/tokens
# Create token
# Copy: hf_xxxxx...
```

### 2. Setup Repository (3 phút)

```bash
git clone https://github.com/t2m19102001/github-ai-agent.git
cd github-ai-agent

pip install -r requirements.txt

cp .env.example .env
```

### 3. Configure .env

```env
GITHUB_TOKEN=ghp_your_token
REPO_FULL_NAME=username/repo
GROQ_API_KEY=gsk_your_key
HUGGINGFACE_TOKEN=hf_your_token  # Optional fallback
MODE=cloud
DEBUG=false
```

### 4. Add GitHub Secrets

Repository → Settings → Secrets and variables → Actions

```
GITHUB_TOKEN = your_github_token
GROQ_API_KEY = your_groq_key
```

### 5. Test Local

```bash
python test_agent.py
python github_agent_hybrid.py
```

## 📋 Environment Variables

```env
# Required
GITHUB_TOKEN=ghp_xxxxx...
REPO_FULL_NAME=username/repo

# Cloud Mode (GROQ)
GROQ_API_KEY=gsk_xxxxx...

# Cloud Mode (HuggingFace - Optional)
HUGGINGFACE_TOKEN=hf_xxxxx...
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.1

# Settings
MODE=cloud              # Only 'cloud' mode (no local/hybrid)
DEBUG=false             # Set to true for verbose logs
```

## 🛠️ Modes

- **`cloud`** (Only available): GROQ → HuggingFace fallback

## 📊 Performance

### GROQ Mode ⭐
- Response time: **5-10s**
- Cost: Free (14.4k req/day)
- Privacy: Encrypted
- Best for: GitHub Actions

### HuggingFace Fallback
- Response time: 10-30s
- Cost: Free (25k req/month)
- Privacy: Standard
- Best for: Backup

## 🔐 Security

- ✅ Tokens trong GitHub Secrets (không commit)
- ✅ `.env` file trong `.gitignore`
- ✅ Input sanitization & validation
- ✅ Injection attack prevention
- ✅ HTTPS for all API calls

## 📚 Usage

### Automatic Trigger

Agent tự động chạy khi:
- ✅ Issue mới được tạo
- ✅ Issue được thêm label
- ✅ Hàng ngày lúc 9 AM UTC
- ✅ Manual trigger

### Manual Trigger

```bash
# Local
python github_agent_hybrid.py

# GitHub Actions
# Repository → Actions → GitHub AI Agent → Run workflow
```

### Create Test Issue

```markdown
Title: Test Issue - Optimize this function

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
📌 Title: Test Issue - Optimize this function
👤 Author: @your_username
📝 Status: open

🤖 AI Analysis generated successfully
✅ Comment posted on issue
```

## 🔧 Troubleshooting

### GROQ API Error

```
❌ GROQ error
```

Fix: Kiểm tra GROQ_API_KEY có đúng không

### HuggingFace Error

```
❌ HuggingFace error
```

Fix: Kiểm tra HUGGINGFACE_TOKEN (nếu dùng)

### Connection Error

```
❌ Connection timeout
```

Fix: 
- Check internet connection
- Verify API endpoint
- Enable DEBUG mode

### Rate Limiting

Fix:
- GROQ: 14,400 requests/day
- HuggingFace: 25,000 requests/month
- Reduce `process_open_issues()` limit
- Increase sleep time

## 📊 Costs

| Service | Limit | Cost |
|---------|-------|------|
| GROQ | 14.4k req/day | Free |
| HuggingFace | 25k req/month | Free |
| GitHub Actions | 2k min/month | Free |
| **Total** | - | **$0** ✅ |

## 🎯 Next Steps

1. ✅ Get API keys
2. ✅ Setup `.env`
3. ✅ Add GitHub Secrets
4. ✅ Test locally
5. ✅ Deploy to GitHub Actions
6. ✅ Monitor workflow runs

## 📚 Resources

- [GROQ Console](https://console.groq.com)
- [HuggingFace Tokens](https://huggingface.co/settings/tokens)
- [GitHub Actions](https://docs.github.com/en/actions)
- [PyGithub Docs](https://pygithub.readthedocs.io/)

## 📄 License

MIT

---

**Questions?** Check `docs/` folder for detailed guides! 📖
