# 🤖 PR Analysis Agent - Setup Guide

## Quick Start (5 minutes)

The PR Analysis Agent automatically reviews pull requests and posts intelligent feedback.

---

## ✅ Step 1: Verify Configuration

Make sure your `.env` file has:

```bash
# Required
GITHUB_TOKEN=ghp_your_personal_access_token
REPO_FULL_NAME=your-username/your-repo
GROQ_API_KEY=gsk_your_groq_api_key

# Optional (for webhook security)
GITHUB_WEBHOOK_SECRET=your_secret_key
```

### Get GitHub Token:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✅ `repo` (Full repository access)
   - ✅ `write:discussion` (Post comments)
4. Copy token to `.env`

---

## 🚀 Step 2: Test Manually (Without Webhook)

### Option A: Using Python Script

```python
from src.agents.pr_agent import GitHubPRAgent
import os
from dotenv import load_dotenv

load_dotenv()

# Create agent
agent = GitHubPRAgent(os.getenv('GITHUB_TOKEN'))

# Analyze a PR (replace with your PR number)
result = agent.auto_review_pr('your-username/your-repo', pr_number=1, auto_comment=True)

print(result['analysis'])
```

### Option B: Using API

Start the web server:
```bash
python run_web.py
```

Then make API call:
```bash
curl -X POST http://localhost:5000/api/pr/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "your-username/your-repo",
    "pr_number": 1,
    "auto_comment": true
  }'
```

---

## 🔗 Step 3: Setup GitHub Webhook (Auto-Review)

### 3.1 Make Your Server Public

**Option A: Using ngrok (Development)**
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start tunnel
ngrok http 5000

# Copy the URL (e.g., https://abc123.ngrok.io)
```

**Option B: Deploy to Production**
- Heroku: `https://your-app.herokuapp.com`
- Railway: `https://your-app.railway.app`
- AWS/GCP/Azure: Your public IP/domain

### 3.2 Configure GitHub Webhook

1. Go to your repository on GitHub
2. Settings → Webhooks → Add webhook
3. Configure:
   - **Payload URL**: `https://your-server.com/api/webhook/pr`
   - **Content type**: `application/json`
   - **Secret**: (optional) Set in `.env` as `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select "Pull requests"
   - ✅ Active

4. Click "Add webhook"

### 3.3 Test Webhook

Create a test PR and watch the magic! 🎉

The agent will:
1. ✅ Detect the PR event
2. 🔍 Analyze all changes
3. 🛡️ Check for security issues
4. ⚡ Check for performance problems
5. 💡 Provide suggestions
6. 💬 Post review comment automatically

---

## 📋 Manual Testing Commands

### Test via CLI:
```bash
# Direct test
python -c "
from src.agents.pr_agent import GitHubPRAgent
import os
from dotenv import load_dotenv
load_dotenv()
agent = GitHubPRAgent(os.getenv('GITHUB_TOKEN'))
result = agent.analyze_pr('t2m19102001/github-ai-agent', 1)
print(result['analysis'])
"
```

### Test via Web API:

```bash
# Start server
python run_web.py &

# Test PR analysis
curl -X POST http://localhost:5000/api/pr/analyze \
  -H "Content-Type: application/json" \
  -d '{"pr_number": 1, "auto_comment": false}'

# Post custom comment
curl -X POST http://localhost:5000/api/pr/comment \
  -H "Content-Type: application/json" \
  -d '{
    "pr_number": 1,
    "comment": "Great work! 🎉"
  }'
```

---

## 🔧 API Endpoints

### 1. Webhook Handler (Auto)
```
POST /api/webhook/pr
```
- Automatically triggered by GitHub
- Analyzes and comments on PR

### 2. Manual PR Analysis
```
POST /api/pr/analyze
Body: {
  "repo": "owner/repo",
  "pr_number": 123,
  "auto_comment": true
}
```

### 3. Post Comment
```
POST /api/pr/comment
Body: {
  "repo": "owner/repo",
  "pr_number": 123,
  "comment": "Your comment"
}
```

---

## 🎯 What Gets Analyzed?

The PR Agent checks for:

### 🛡️ Security Issues
- Hardcoded secrets/passwords
- SQL injection vulnerabilities
- XSS vulnerabilities
- Unsafe deserialization
- Weak cryptography

### ⚡ Performance Issues
- N+1 database queries
- Inefficient loops
- Missing database indexes
- Large file loading

### 💎 Code Quality
- Long functions (>50 lines)
- Unused imports
- Bare except clauses
- Print statements (use logging)
- Magic numbers
- TODOs

---

## 📊 Example Review Comment

```markdown
## 🤖 AI Code Review

## 🔍 Summary
This PR adds user authentication with JWT tokens. Overall clean implementation.

## ✅ Strengths
- Good error handling
- Clear variable names
- Proper use of async/await

## ⚠️ Issues Found
1. **Security**: Hardcoded secret key in `auth.py:15`
   - Replace with environment variable
   
2. **Performance**: N+1 query in `user.py:45`
   - Use `.select_related('profile')`

## 💡 Suggestions
- Add unit tests for auth flow
- Consider rate limiting for login endpoint
- Add docstrings to new functions

## 🎯 Overall Assessment
REQUEST CHANGES - Fix security issue before merging

---
*Automated review by AI Agent*  
*Analyzed 8 files with 234 additions and 45 deletions*
```

---

## 🐛 Troubleshooting

### Issue: "401 Unauthorized"
- Check `GITHUB_TOKEN` in `.env`
- Ensure token has `repo` scope
- Token must not be expired

### Issue: "PR not found"
- Verify `REPO_FULL_NAME` format: `owner/repo`
- Check PR number is correct
- Ensure token has access to repository

### Issue: "Webhook not triggering"
- Verify webhook URL is public
- Check webhook secret matches `.env`
- View webhook delivery logs in GitHub

### Issue: "Comment not posting"
- Ensure token has `write:discussion` scope
- Check PR is not from a fork (requires different permissions)

---

## 🚀 Deployment Options

### Heroku
```bash
git init
heroku create your-app-name
heroku config:set GITHUB_TOKEN=your_token
heroku config:set GROQ_API_KEY=your_key
git push heroku main
```

### Railway
1. Connect GitHub repo
2. Add environment variables
3. Deploy automatically

### Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run_web.py"]
```

---

## 📈 Usage Statistics

After deployment, you can track:
- Number of PRs analyzed
- Average analysis time
- Issues detected
- Comments posted

Add analytics endpoint:
```python
@app.route('/api/stats')
def stats():
    return jsonify({
        'prs_analyzed': 42,
        'issues_found': 156,
        'comments_posted': 38
    })
```

---

## 🎉 You're Done!

Your AI PR Reviewer is ready! Every new PR will be automatically analyzed and commented on.

**Next Steps:**
- Test with a real PR
- Customize analysis prompts in `pr_agent.py`
- Add more security patterns in `pr_tools.py`
- Build VS Code extension for inline suggestions

---

## 💡 Tips

1. **Start with manual testing** before enabling webhook
2. **Review AI comments** initially to tune sensitivity
3. **Customize prompts** for your team's code style
4. **Add ignore patterns** for generated files
5. **Set up monitoring** for webhook failures

---

Need help? Check logs in `logs/agent.log` or open an issue! 🚀
