# GitHub AI Agent Extension

A powerful VS Code extension bringing GitHub Copilot-like features to your IDE with PR analysis, intelligent code completion, and automatic test generation.

## 🚀 Features

### 💡 Code Completion
- **Context-aware suggestions** - Understands your code context
- **Multi-language support** - Python, JavaScript, TypeScript, Java, C#, and more
- **Confidence scores** - See how confident the AI is in each suggestion
- **Keyboard shortcut** - `Ctrl+Shift+Space` (Windows/Linux) or `Cmd+Shift+Space` (Mac)

### 🧪 Test Generation
- **Automatic test creation** - Generate unit tests from your code
- **Multiple frameworks** - pytest, unittest, jest, vitest, mocha, and more
- **Edge case detection** - Automatically identifies edge cases
- **Mock generation** - Creates mocks and fixtures automatically
- **Keyboard shortcut** - `Ctrl+Shift+T` (Windows/Linux) or `Cmd+Shift+T` (Mac)

### 📋 PR Analysis
- **Security checking** - Identifies security vulnerabilities
- **Performance analysis** - Detects performance issues
- **Code quality** - Suggests code improvements
- **GitHub integration** - Works with GitHub webhooks
- **Command** - Open command palette and search "Analyze PR"

### ⚙️ Configuration
- **API endpoint** - Connect to your backend server
- **Framework selection** - Choose your preferred test framework
- **Coverage targets** - Set test coverage goals
- **Auto-complete settings** - Fine-tune suggestion behavior

## 📦 Installation

### From VS Code
1. Open VS Code Extensions (Ctrl+Shift+X / Cmd+Shift+X)
2. Search for "GitHub AI Agent"
3. Click Install

### From GitHub
```bash
git clone https://github.com/t2m19102001/github-ai-agent.git
cd github-ai-agent/vscode-extension
npm install
npm run esbuild
```

## ⚡ Quick Start

### 1. Start the Backend Server

Make sure the Python backend is running:

```bash
cd /path/to/github-ai-agent
python run_web.py
```

The server should start on `http://localhost:5000`

### 2. Open VS Code Settings

Open VS Code Settings (Ctrl+, / Cmd+,) and search for "GitHub AI Agent"

### 3. Configure API Endpoint

Ensure the API endpoint is set to your backend:
```
http://localhost:5000
```

### 4. Start Using!

- **Code Completion**: Start typing and AI suggestions appear
- **Generate Tests**: Select code and run "Generate Tests" command
- **Analyze PR**: Run "Analyze PR" from command palette

## 🎮 Keyboard Shortcuts

| Action | Windows/Linux | Mac |
|--------|---------------|-----|
| Complete Code | Ctrl+Shift+Space | Cmd+Shift+Space |
| Generate Tests | Ctrl+Shift+T | Cmd+Shift+T |
| Show Panel | Ctrl+Shift+G | Cmd+Shift+G |

## ⚙️ Configuration Options

### API Endpoint
- **Setting**: `github-ai-agent.apiEndpoint`
- **Default**: `http://localhost:5000`
- **Description**: URL of the GitHub AI Agent backend

### Enable Auto-Complete
- **Setting**: `github-ai-agent.enableAutoComplete`
- **Default**: `true`
- **Description**: Show code completions while typing

### Enable Auto-Analyze PR
- **Setting**: `github-ai-agent.enableAutoAnalyze`
- **Default**: `false`
- **Description**: Automatically analyze PRs on save

### Completion Delay
- **Setting**: `github-ai-agent.completionDelay`
- **Default**: `1000` ms
- **Range**: 100-5000 ms
- **Description**: Delay before showing suggestions

### Test Framework
- **Setting**: `github-ai-agent.testFramework`
- **Default**: `pytest`
- **Options**: pytest, unittest, jest, vitest, mocha

### Coverage Target
- **Setting**: `github-ai-agent.coverageTarget`
- **Default**: `80`
- **Range**: 0-100
- **Description**: Target code coverage percentage

### Max Suggestions
- **Setting**: `github-ai-agent.maxSuggestions`
- **Default**: `5`
- **Range**: 1-10
- **Description**: Maximum completion suggestions

## 🎯 Commands

Open command palette (Ctrl+Shift+P / Cmd+Shift+P) and type:

| Command | Description |
|---------|-------------|
| `GitHub AI: Complete Code` | Get code completion suggestions |
| `GitHub AI: Generate Tests` | Generate unit tests for current file |
| `GitHub AI: Analyze PR` | Analyze pull request |
| `GitHub AI: Show Agent Panel` | Open AI Agent sidebar panel |
| `GitHub AI: Open Settings` | Open settings panel |
| `GitHub AI: Toggle Auto-Complete` | Enable/disable auto-complete |
| `GitHub AI: Toggle Auto-Analyze PR` | Enable/disable PR auto-analysis |

## 🔧 Troubleshooting

### "Backend not available" Error
- Ensure Python backend is running on configured endpoint
- Check `github-ai-agent.apiEndpoint` setting
- Run `python run_web.py` in the backend directory

### Completion suggestions not showing
- Check `github-ai-agent.enableAutoComplete` is enabled
- Increase `github-ai-agent.completionDelay` if needed
- Verify backend connection in status bar

### Tests not generating
- Verify file language is supported (Python, JS, TS, etc.)
- Check test framework is installed (`pip install pytest` for Python)
- Check backend console for errors

### PR analysis not working
- Git extension must be active
- Repository must have a .git directory
- PR branch must exist locally

## 📚 Supported Languages

**Code Completion & Test Generation**:
- Python
- JavaScript
- TypeScript
- Java
- C#
- C++
- Go
- Rust
- Ruby
- PHP
- Swift
- Kotlin

## 🧪 Test Frameworks

**Python**:
- pytest
- unittest
- nose2

**JavaScript/TypeScript**:
- jest
- vitest
- mocha

**Java**:
- junit
- testng

**C#**:
- nunit
- xunit

## 📖 Learn More

- **Backend Setup**: See [github-ai-agent README](../README.md)
- **API Documentation**: See [TEST_GENERATION_API.md](../docs/TEST_GENERATION_API.md)
- **Code Completion**: See [CODE_COMPLETION_API.md](../docs/CODE_COMPLETION_API.md)
- **PR Analysis**: See [PR_AGENT_SETUP.md](../docs/PR_AGENT_SETUP.md)

## 🔐 Privacy & Security

- All code sent to the backend for analysis
- Backend runs locally (http://localhost:5000 by default)
- No data stored or sent to external services
- API endpoint can be configured for private deployments

## 💬 Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs
3. Open an issue on GitHub
4. Check VS Code extension logs (Help → Toggle Developer Tools)

## 📝 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Built with:
- VS Code Extension API
- GROQ LLM (llama-3.3-70b)
- Python Flask backend
- Multiple AI technologies

---

**Version**: 1.0.0  
**Last Updated**: November 29, 2024
