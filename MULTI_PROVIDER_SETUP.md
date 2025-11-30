# Multi-Provider Setup Guide

## 🎯 Overview

This project now supports **3 LLM providers**:
- 🏠 **Ollama** (Local) - Free, no API key needed, requires GPU
- ⚡ **Groq** (Cloud) - Super fast, free tier, no GPU needed
- 🤖 **OpenAI** (Cloud) - Most powerful, requires API key

**No more mandatory Ollama installation!** Choose the provider that fits your setup.

---

## 🚀 Quick Start

### Option 1: Ollama (Local - Default)

**Best for:** Users with GPU, want 100% privacy

```bash
# 1. Install Ollama (if not already)
# macOS/Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from: https://ollama.ai

# 2. Pull the model
ollama pull deepseek-coder-v2:16b-instruct-qat

# 3. Run the app (no env vars needed)
uvicorn src.web.app:app --reload --port=5000
```

---

### Option 2: Groq (Cloud - Recommended for laptops)

**Best for:** Fast responses, no GPU, free tier available

```bash
# 1. Get API key from: https://console.groq.com/keys

# 2. Set environment variables
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# 3. Run the app
uvicorn src.web.app:app --reload --port=5000
```

**Alternative:** Create `.env` file:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

---

### Option 3: OpenAI (Cloud - Most powerful)

**Best for:** Maximum quality, GPT-4 models

```bash
# 1. Get API key from: https://platform.openai.com/api-keys

# 2. Set environment variables
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# 3. Run the app
uvicorn src.web.app:app --reload --port=5000
```

**Alternative:** Create `.env` file:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## 🔧 Configuration

All settings are in `src/config/settings.py`:

```python
# Change default provider
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", LLMProvider.OLLAMA)

# Customize models
MODELS = {
    LLMProvider.OLLAMA: "deepseek-coder-v2:16b-instruct-qat",
    LLMProvider.GROQ: "llama3-70b-8192",  # or mixtral-8x7b-32768
    LLMProvider.OPENAI: "gpt-4o-mini"      # or gpt-4-turbo
}
```

---

## 📊 Provider Comparison

| Feature | Ollama | Groq | OpenAI |
|---------|--------|------|--------|
| **Cost** | Free | Free tier | Paid |
| **Speed** | Fast (GPU) | Very Fast | Fast |
| **Privacy** | 100% Local | Cloud | Cloud |
| **Setup** | Install required | API key only | API key only |
| **GPU needed** | Yes (recommended) | No | No |
| **Best for** | Privacy, offline | Speed, free | Quality, features |

---

## 🧪 Testing Different Providers

```bash
# Test with Groq
LLM_PROVIDER=groq GROQ_API_KEY=gsk_xxx uvicorn src.web.app:app --port=5001

# Test with OpenAI
LLM_PROVIDER=openai OPENAI_API_KEY=sk-xxx uvicorn src.web.app:app --port=5002

# Test with Ollama (default)
uvicorn src.web.app:app --port=5000
```

---

## 🔑 Getting API Keys

### Groq (Free Tier)
1. Go to https://console.groq.com
2. Sign up (free)
3. Navigate to API Keys
4. Create new key
5. Copy `gsk_...`

### OpenAI (Paid)
1. Go to https://platform.openai.com
2. Sign up
3. Add payment method
4. Navigate to API Keys
5. Create new key
6. Copy `sk-...`

---

## 🐛 Troubleshooting

### "Connection refused" with Ollama
- Make sure Ollama is running: `ollama serve`
- Check if model is pulled: `ollama list`
- Pull model: `ollama pull deepseek-coder-v2:16b-instruct-qat`

### "Invalid API key" with Groq/OpenAI
- Check if API key is set: `echo $GROQ_API_KEY`
- Verify key is valid on provider dashboard
- Make sure no extra spaces in `.env` file

### "Module not found" errors
- Install dependencies: `pip install -r requirements.txt`
- For OpenAI: `pip install langchain-openai`
- For Ollama: `pip install langchain-ollama`

---

## 💡 Pro Tips

1. **Best for development:** Groq (fast + free)
2. **Best for production:** OpenAI (most reliable)
3. **Best for privacy:** Ollama (100% local)
4. **Mix and match:** Use Groq for chat, Ollama for embeddings

---

## 📝 Example Usage

```python
# In your code, the provider is auto-detected
from src.config.settings import DEFAULT_PROVIDER

print(f"Using provider: {DEFAULT_PROVIDER}")
# Output: Using provider: groq (or ollama/openai)
```

Open browser: http://127.0.0.1:5000

Chat commands work the same regardless of provider! 🎉
