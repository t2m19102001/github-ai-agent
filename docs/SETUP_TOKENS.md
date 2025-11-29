# 🔐 Getting Your API Tokens

## Step 1: GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: `GitHub AI Agent`
4. Select scopes:
   - ✅ `public_repo` (access public repos)
   - ✅ `repo` (access your repos)
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)

## Step 2: Get Your Repository Name

Format: `username/repository-name`

Example: `t2m19102001/my-awesome-repo`

Go to your GitHub repo → URL is: `https://github.com/username/repo-name`

## Step 3: GROQ API Key (Primary LLM)

1. Go to https://console.groq.com/keys
2. Click "Create API Key"
3. Copy the key

## Step 4: Update `.env` File

Edit `.env` in your project:

```dotenv
GITHUB_TOKEN=ghp_your_actual_token_here
REPO_FULL_NAME=your_username/your_repository
GROQ_API_KEY=gsk_your_actual_groq_key_here
HUGGINGFACE_TOKEN=hf_your_actual_token_here
MODE=cloud
DEBUG=false
```

⚠️ **IMPORTANT:**
- Never commit `.env` to GitHub
- Keep tokens private!
- If exposed, regenerate immediately

## Step 5: Test Configuration

```bash
python test_agent.py
```

If all tests pass ✅, run:

```bash
python github_agent_hybrid.py
```
