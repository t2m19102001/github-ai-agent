# ⚡ Quick Start - 5 Minutes

## 🔴 CRITICAL: Rotate Tokens!

Tokens của bạn bị lộ. **Bạn PHẢI:**
1. Delete old token
2. Create new token
3. Update GitHub Secrets

---

## Step 1: Get GROQ Key (2 min)

```bash
# Visit https://console.groq.com/keys
# Click "Create API Key"
# Copy: gsk_xxxxx...
```

---

## Step 2: Setup (2 min)

```bash
cd /Users/minhman/Develop/github-ai-agent

pip install -r requirements.txt

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

---

## Step 3: Test (1 min)

```bash
python test_agent.py
```

Should show: ✅ All tests passed!

---

## Step 4: Run

```bash
python github_agent_hybrid.py
```

---

## Step 5: Deploy (GitHub Actions)

```
Repository → Settings → Secrets and variables → Actions
Add:
  - GITHUB_TOKEN
  - GROQ_API_KEY
```

---

## ✅ Done!

Your AI Agent is running! Create an issue and watch it auto-analyze. 🎉

---

**Questions?** Check `docs/DEPLOYMENT.md` 📖
