# Phase 3: VS Code Extension - Setup & Installation Guide

## 📦 Overview

The VS Code extension integrates all three AI agents (PR Analysis, Code Completion, Test Generation) into a single, user-friendly IDE plugin.

## 🏗️ Architecture

```
VS Code Extension (TypeScript)
├── Main Extension (extension.ts)
├── Services
│   └── API Client (communicate with Python backend)
├── Commands
│   ├── Code Completion
│   ├── Test Generation
│   └── PR Analysis
├── Providers
│   └── Completion Provider (inline suggestions)
├── Panels
│   ├── AI Agent Panel (sidebar)
│   └── Settings Panel
└── UI
    └── Status Bar
```

## 📋 Prerequisites

- **Node.js** 16+ and npm 8+
- **TypeScript** 5.0+
- **VS Code** 1.85+
- **Python Backend** running on http://localhost:5000

Check versions:
```bash
node --version
npm --version
```

## 🚀 Installation Steps

### Step 1: Install Dependencies

```bash
cd /Users/minhman/Develop/github-ai-agent/vscode-extension
npm install
```

This installs:
- `@types/vscode` - VS Code API types
- `@types/node` - Node.js types
- `axios` - HTTP client for API calls
- `typescript` - TypeScript compiler
- `esbuild` - Fast bundler

### Step 2: Build the Extension

```bash
npm run esbuild
```

This compiles TypeScript to JavaScript in the `out/` directory.

### Step 3: Test in Development Mode

```bash
npm run esbuild-watch
```

Then in VS Code:
1. Press `F5` to open "Run and Debug"
2. Select "Extension" to launch in debug mode
3. A new VS Code window opens with the extension loaded

### Step 4: Package the Extension (Optional)

```bash
npm install -g vsce
vsce package
```

This creates a `.vsix` file that can be installed directly.

## 🔧 Configuration

### Backend Connection

The extension communicates with the Python backend. Ensure:

1. **Backend running**:
```bash
cd /Users/minhman/Develop/github-ai-agent
python run_web.py
```

2. **API endpoint configured** in VS Code Settings:
   - Open Settings: `Ctrl+,` (Windows/Linux) or `Cmd+,` (Mac)
   - Search: "GitHub AI Agent"
   - Set API Endpoint to `http://localhost:5000`

### Default Settings

All settings are in `package.json` contributions section and can be modified in VS Code:

```json
{
  "github-ai-agent.apiEndpoint": "http://localhost:5000",
  "github-ai-agent.enableAutoComplete": true,
  "github-ai-agent.completionDelay": 1000,
  "github-ai-agent.testFramework": "pytest",
  "github-ai-agent.coverageTarget": 80,
  "github-ai-agent.maxSuggestions": 5
}
```

## 📁 Project Structure

```
vscode-extension/
├── src/
│   ├── extension.ts              # Main entry point
│   ├── services/
│   │   └── apiClient.ts          # API communication
│   ├── commands/
│   │   ├── codeCompletion.ts     # Completion command
│   │   ├── testGeneration.ts     # Test generation command
│   │   └── prAnalysis.ts         # PR analysis command
│   ├── providers/
│   │   └── completionProvider.ts # Inline completions
│   ├── panels/
│   │   ├── aiAgentPanel.ts       # Sidebar panel
│   │   └── settingsPanel.ts      # Settings UI
│   └── ui/
│       └── statusBar.ts          # Status bar manager
├── out/                          # Compiled JavaScript (auto-generated)
├── package.json                  # Extension manifest
├── tsconfig.json                 # TypeScript config
├── README.md                     # User documentation
├── .vscodeignore                 # Package ignore rules
└── INSTALLATION.md               # This file
```

## 🎯 Features Implemented

### ✅ Extension Activation
- Auto-activates on VS Code startup
- Initializes API client and status bar
- Checks backend connection

### ✅ Commands
- `github-ai-agent.completeCode` - Manual completion trigger
- `github-ai-agent.generateTests` - Generate tests for file
- `github-ai-agent.analyzePR` - Analyze PR changes
- `github-ai-agent.showPanel` - Show sidebar panel
- `github-ai-agent.openSettings` - Open settings panel
- `github-ai-agent.toggleAutoComplete` - Toggle auto-complete
- `github-ai-agent.toggleAutoAnalyze` - Toggle PR auto-analysis

### ✅ Keyboard Shortcuts
- `Ctrl+Shift+Space` / `Cmd+Shift+Space` - Complete code
- `Ctrl+Shift+T` / `Cmd+Shift+T` - Generate tests
- `Ctrl+Shift+G` / `Cmd+Shift+G` - Show panel

### ✅ Completion Provider
- Registers for 12+ languages
- Provides inline suggestions
- Shows confidence scores
- Filters by code context

### ✅ Sidebar Panel
- Quick action buttons
- Status messages
- Agent information
- Easy access to commands

### ✅ Settings Panel
- API endpoint configuration
- Test framework selection
- Coverage target setting
- Auto-complete options
- Toggle enable/disable features

### ✅ Status Bar
- Shows connection status
- Updates on actions
- Color-coded indicators
- Click to open panel

## 🧪 Testing the Extension

### Test Code Completion

1. Create a Python file with:
```python
def calculate_total(items):
    
```

2. Press `Ctrl+Shift+Space` (Windows) or `Cmd+Shift+Space` (Mac)
3. See suggestions for completing the function

### Test Test Generation

1. Open a Python file with functions
2. Run command "Generate Tests" from command palette
3. See generated pytest code in new document

### Test PR Analysis

1. Run command "Analyze PR" from command palette
2. See analysis results in output channel

### Test Settings

1. Run command "Open Settings"
2. Configure:
   - API endpoint
   - Test framework
   - Coverage target
   - Auto-complete settings
3. Click "Save Settings"

## 🔍 Debugging

### Enable Debug Logging

In extension.ts, uncomment debug lines:
```typescript
console.log('🚀 GitHub AI Agent Extension activated');
console.log('✅ GitHub AI Agent Extension initialized successfully');
```

### Check Extension Logs

1. Press `Ctrl+Shift+P` and search "Developer: Open Extension Logs"
2. Or press `F1` > "Output" > "GitHub AI Agent"

### Test Backend Connection

Open browser and visit: `http://localhost:5000`
Should return Flask welcome page.

### Enable VS Code Debug Console

Press `Ctrl+Shift+Y` to see console output during development.

## 🚚 Deployment

### Local Installation

1. Build: `npm run esbuild-base -- --minify`
2. Package: `vsce package`
3. Install: Open `github-ai-agent-1.0.0.vsix` with VS Code

### VS Code Marketplace

To publish to marketplace:
1. Create publisher account on https://marketplace.visualstudio.com
2. Get publisher token
3. Run: `vsce publish`

## 🐛 Troubleshooting

### Extension not loading

Check:
1. Is backend running? Check `http://localhost:5000`
2. Is node_modules installed? Run `npm install`
3. Is TypeScript compiled? Run `npm run esbuild`

### Completions not showing

Check:
1. Is `enableAutoComplete` setting enabled?
2. Is language supported? Check `package.json` languages
3. Is delay too long? Reduce `completionDelay` setting

### API connection errors

Check:
1. Is backend server running?
2. Is correct endpoint configured?
3. Check backend logs for errors

### Test generation fails

Check:
1. Is code valid for the language?
2. Is test framework installed?
3. Check backend console for errors

## 📚 Learning Resources

- **VS Code Extension API**: https://code.visualstudio.com/api
- **Extension Examples**: https://github.com/microsoft/vscode-extension-samples
- **Webview Documentation**: https://code.visualstudio.com/api/extension-guides/webview
- **TypeScript Handbook**: https://www.typescriptlang.org/docs

## ✅ Next Steps

1. ✅ Install Node.js 16+
2. ✅ Run `npm install` to install dependencies
3. ✅ Start Python backend with `python run_web.py`
4. ✅ Run `npm run esbuild` to compile
5. ✅ Press `F5` in VS Code to test
6. ✅ Try commands and features
7. ✅ Configure settings as needed
8. ✅ Build and package when ready

## 📞 Support

For issues:
1. Check debug logs (F12)
2. Verify backend is running
3. Check configuration in settings
4. Look at backend console for errors
5. Create issue on GitHub

---

**Extension Version**: 1.0.0  
**Created**: November 29, 2024  
**Status**: ✅ Ready for testing
