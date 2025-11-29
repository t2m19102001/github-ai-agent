# 🔧 FIX GUIDE - How to Run the Project Correctly

**Problem**: `python ./run_web.py` không chạy được
**Solution**: Sử dụng Python từ virtual environment

---

## ✅ Solution 1: Use the Startup Script (EASIEST)

```bash
cd /Users/minhman/Develop/github-ai-agent
./start.sh
```

This script automatically:
- ✅ Checks virtual environment
- ✅ Kills any existing process on port 5000
- ✅ Starts the web server
- ✅ Shows you the dashboard URL

---

## ✅ Solution 2: Use Full Python Path (MANUAL)

```bash
cd /Users/minhman/Develop/github-ai-agent
.venv/bin/python run_web.py
```

Or create an alias:
```bash
# Add to ~/.zshrc
alias github-ai='cd /Users/minhman/Develop/github-ai-agent && .venv/bin/python run_web.py'

# Then just use:
github-ai
```

---

## ✅ Solution 3: Activate Virtual Environment (TRADITIONAL)

```bash
cd /Users/minhman/Develop/github-ai-agent
source .venv/bin/activate
python run_web.py
```

After activating, you can use `python` directly for any Python commands in that terminal.

---

## 🔍 Why This Happens

| Command | Result |
|---------|--------|
| `python run_web.py` | ❌ Uses system Python (not installed or wrong version) |
| `.venv/bin/python run_web.py` | ✅ Uses project's Python with all packages installed |

The virtual environment contains:
- Correct Python version (3.10.0)
- All required packages (Flask, GROQ, PyGithub, etc.)
- Isolated from system Python

---

## 🐛 Troubleshooting

### Error: "Address already in use"
**Fix**: Kill the old process
```bash
lsof -i :5000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9
```

Or use a different port:
```bash
.venv/bin/python run_web.py --port 5001
```

### Error: "Module not found"
**Fix**: Ensure venv is activated
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Error: "Permission denied"
**Fix**: Make script executable
```bash
chmod +x start.sh
./start.sh
```

---

## ✨ Once Server Starts

You'll see:
```
✅ GitHub PRAgent initialized
✅ CodeCompletionAgent initialized
✅ TestGenerationAgent initialized
✅ Flask app initialized with all agents

🌐 Web Server running on http://0.0.0.0:5000
```

Then open in browser:
```
http://localhost:5000/dashboard
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start server (easy) | `./start.sh` |
| Start server (manual) | `.venv/bin/python run_web.py` |
| Activate venv | `source .venv/bin/activate` |
| Stop server | Press `Ctrl+C` |
| Kill port 5000 | `lsof -i :5000 \| grep -v COMMAND \| awk '{print $2}' \| xargs kill -9` |
| View dashboard | `http://localhost:5000/dashboard` |

---

## 📋 Complete Workflow

```bash
# 1. Navigate to project
cd /Users/minhman/Develop/github-ai-agent

# 2. Start server (choose ONE method)
# Method A (Recommended):
./start.sh

# Method B:
.venv/bin/python run_web.py

# Method C:
source .venv/bin/activate && python run_web.py

# 3. Open dashboard in browser
# http://localhost:5000/dashboard

# 4. Test features
# - Code Completion
# - Test Generation
# - PR Analysis

# 5. Stop server
# Press Ctrl+C
```

---

## 💡 Tips

1. **Use `.start.sh`** for easiest setup
2. **Activate venv** if you'll run multiple Python commands
3. **Check port 5000** if you get "Address already in use"
4. **GROQ API key** must be set in environment:
   ```bash
   export GROQ_API_KEY="your-key-here"
   ```

---

## ✅ Verification

After starting, you should see:
```
🌐 Web Server running on http://0.0.0.0:5000
```

Test by opening:
```
http://localhost:5000/dashboard
```

You should see the beautiful dashboard with:
- ✨ Code Completion card
- 🧪 Test Generation card
- 🔍 PR Analysis card

---

**That's it!** 🎉 Your GitHub Copilot Alternative is now running!
