# 🚀 Deployment Guide

## Prerequisites

- Python 3.8+
- GitHub account with Personal Access Token
- GROQ or HuggingFace account for LLM

---

## Step 1: Local Setup

### 1.1 Clone Repository

```bash
git clone https://github.com/t2m19102001/github-ai-agent.git
cd github-ai-agent
```

### 1.2 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 1.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 1.4 Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```env
GITHUB_TOKEN=ghp_xxxxx...
REPO_FULL_NAME=username/repo
GROQ_API_KEY=gsk_xxxxx...
MODE=cloud
DEBUG=false
```

### 1.5 Test Locally

```bash
python test_agent.py
python github_agent_hybrid.py
```

---

## Step 2: Get API Keys

### GROQ (Recommended) ⭐

1. Visit https://console.groq.com/keys
2. Click "Create API Key"
3. Copy key to `.env`

**Advantages:**
- 5-10s response time
- Free tier: 14,400 requests/day
- No verification needed

### HuggingFace (Fallback)

1. Visit https://huggingface.co/settings/tokens
2. Create new token
3. Copy to `.env`

---

## Step 3: GitHub Configuration

### 3.1 Create GitHub Personal Access Token

1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (full control)
   - `workflow` (update workflows)
4. Generate & copy token
5. Add to `.env`

### 3.2 Identify Repository

```env
REPO_FULL_NAME=username/repo
```

---

## Step 4: GitHub Actions Setup

### 4.1 Add Repository Secrets

Repository → Settings → Secrets and variables → Actions

Add:
| Name | Value |
|------|-------|
| `GITHUB_TOKEN` | Your GitHub token |
| `GROQ_API_KEY` | Your GROQ API key |

### 4.2 Workflow Configuration

File `.github/workflows/ai-agent.yml` triggers on:
- Issue created
- Issue labeled
- Daily at 9 AM UTC
- Manual trigger

**Modify schedule:**
```yaml
schedule:
  - cron: '0 9 * * *'  # Change time here (UTC)
```

---

## Step 5: Testing

### 5.1 Local Test

```bash
python test_agent.py
python github_agent_hybrid.py
```

### 5.2 Create Test Issue

```markdown
Title: Test Issue - Performance Optimization

Body:
How can I optimize this code?

```python
def slow_func(items):
    for item in items:
        print(item)
```
```

### 5.3 Manual Workflow Trigger

Repository → Actions → GitHub AI Agent → Run workflow

---

## 🔒 Security Checklist

- ✅ Never commit `.env` file
- ✅ Use GitHub Secrets for tokens
- ✅ Rotate tokens if exposed
- ✅ Limit token permissions
- ✅ Monitor Actions usage

---

## 🐛 Troubleshooting

### "GITHUB_TOKEN not found"

**Fix**: Add to `.env` or GitHub Secrets

### "GROQ error"

**Fix**:
- Verify API key
- Check internet connection
- Enable DEBUG mode

### "Connection timeout"

**Fix**:
- Check API endpoint
- Verify internet connection
- Try different API (HuggingFace)

### "Rate limit exceeded"

**Fix**:
- GROQ: 14,400 req/day
- HuggingFace: 25,000 req/month
- Reduce issue limit
- Increase sleep time

### "Empty response from LLM"

**Fix**:
- Verify API key
- Check prompt length
- Try different LLM

---

## 📊 Costs

| Service | Free Tier | Cost |
|---------|-----------|------|
| GROQ | 14.4k req/day | Free |
| HuggingFace | 25k req/month | Free |
| GitHub Actions | 2k min/month | Free |
| **Total** | - | **$0** |

---

## 📈 Performance

| Mode | Response | Cost | Best For |
|------|----------|------|----------|
| GROQ | 5-10s | Free | GitHub Actions |
| HuggingFace | 10-30s | Free | Backup |

---

## 🎯 Next Steps

1. ✅ Get API keys
2. ✅ Local setup & test
3. ✅ Add GitHub Secrets
4. ✅ Create test issue
5. ✅ Monitor workflow

---

**Questions?** Check other docs or create an issue! 📖
