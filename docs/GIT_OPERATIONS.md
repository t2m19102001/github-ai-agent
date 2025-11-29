# Git Operations Integration - Task 6

## Overview
Implemented **full Git operations** support allowing AI agents to automatically commit, create branches, and manage Git workflow.

## Architecture

### Git Tool System
- **Module**: `src/tools/git_tool.py`
- **Safe Subprocess**: Uses `subprocess.run()` with `check=True`
- **Error Handling**: Returns structured dict with success/error status
- **Tool Classes**: Wrapped for agent integration

### Available Operations
1. **git_commit(message)** - Stage all, commit, and push
2. **git_create_branch(name)** - Create and checkout branch
3. **git_status()** - Check repository status
4. **git_diff()** - View unstaged changes
5. **git_branch_list()** - List all branches
6. **git_log(n)** - View commit history

## Files Created/Modified

### 1. `src/tools/git_tool.py` (NEW)
Complete Git operations module:

**Core Functions:**
```python
def git_commit(message: str) -> Dict[str, Any]:
    # 1. git add .
    # 2. git commit -m "message"
    # 3. git push
    return {"success": True, "message": "...", "output": "..."}

def git_create_branch(name: str) -> Dict[str, Any]:
    # git checkout -b name
    return {"success": True, "branch": name}
```

**Tool Classes (for agents):**
```python
class GitCommitTool:
    name = "git_commit"
    description = "Commit all changes with a message and push to remote"
    def execute(self, message: str) -> str: ...

class GitBranchTool:
    name = "git_create_branch"
    description = "Create and checkout a new Git branch"
    def execute(self, name: str) -> str: ...

class GitStatusTool:
    name = "git_status"
    description = "Check Git repository status"
    def execute(self) -> str: ...
```

### 2. `src/agents/code_agent.py` (MODIFIED)
Integrated Git tools into CodeChatAgent:

**Added imports:**
```python
from src.tools.git_tool import GitCommitTool, GitBranchTool, GitStatusTool
```

**Registered tools:**
```python
self.register_tool(GitCommitTool())
self.register_tool(GitBranchTool())
self.register_tool(GitStatusTool())
```

**Updated system prompt:**
```python
Available tools:
- git_commit: Commit changes với message (ví dụ: /git_commit "fix bug")
- git_create_branch: Tạo branch mới (ví dụ: /git_create_branch "feature-x")
- git_status: Kiểm tra Git status
```

### 3. `src/web/app_fastapi.py` (MODIFIED)
Added REST API endpoints for Git operations:

**Endpoints:**
```python
POST   /api/git/commit      # Commit with message
POST   /api/git/branch      # Create branch
GET    /api/git/status      # Get status
GET    /api/git/diff        # Get diff
GET    /api/git/branches    # List branches
GET    /api/git/log?n=10    # Commit history
```

### 4. `scripts/test_git.py` (NEW)
Test script for Git operations:

```bash
python scripts/test_git.py
```

Tests all operations and displays results.

## Usage Examples

### 1. Via API (REST)

**Commit changes:**
```bash
curl -X POST http://localhost:5000/api/git/commit \
  -H "Content-Type: application/json" \
  -d '{"message": "fix: resolve bug in authentication"}'
```

**Create branch:**
```bash
curl -X POST http://localhost:5000/api/git/branch \
  -H "Content-Type: application/json" \
  -d '{"name": "feature/new-ui"}'
```

**Get status:**
```bash
curl http://localhost:5000/api/git/status
```

### 2. Via Agent (Natural Language)

**In chat:**
```
User: "Please commit these changes with message 'fix bug'"
AI: [Automatically calls git_commit("fix bug")]
    "✅ Committed and pushed successfully: fix bug"

User: "Create a new branch called feature-x"
AI: [Automatically calls git_create_branch("feature-x")]
    "✅ Branch 'feature-x' created successfully"

User: "What's the current Git status?"
AI: [Calls git_status()]
    "📝 Changes:
     M src/web/app.py
     M requirements.txt"
```

### 3. Via Python Code

```python
from src.tools.git_tool import git_commit, git_create_branch, git_status

# Commit changes
result = git_commit("feat: add new feature")
if result["success"]:
    print(f"✅ {result['message']}")

# Create branch
result = git_create_branch("hotfix/critical-bug")
if result["success"]:
    print(f"✅ Branch created: {result['branch']}")

# Check status
result = git_status()
if result["success"] and result["has_changes"]:
    print(f"Changes:\n{result['status']}")
```

## Key Features

### ✅ Safe Operations
- No `shell=True` - direct subprocess calls
- Input validation
- Error handling with try/except
- Structured error messages

### ✅ Agent Integration
- Tools registered in CodeChatAgent
- LLM can call automatically
- Natural language triggers
- Tool descriptions for LLM

### ✅ REST API
- HTTP endpoints for all operations
- JSON request/response
- Easy integration with frontend
- Programmatic access

### ✅ Complete Workflow
```python
# Full Git workflow automated:
git_commit("message")
  → git add .
  → git commit -m "message"
  → git push
  → Returns success/error
```

### ✅ Information Queries
- `git_status()` - Current changes
- `git_diff()` - Detailed changes
- `git_branch_list()` - All branches
- `git_log(n)` - Recent commits

## Security

### Input Validation
```python
if not message.strip():
    return {"success": False, "error": "Message required"}
```

### No Shell Injection
```python
# Safe - direct command list
subprocess.run(["git", "commit", "-m", message])

# NOT using (dangerous):
# subprocess.run(f"git commit -m '{message}'", shell=True)
```

### Error Handling
```python
try:
    subprocess.run([...], check=True)
except subprocess.CalledProcessError as e:
    return {"success": False, "error": e.stderr}
```

## Response Format

All Git functions return consistent dict:

**Success:**
```python
{
    "success": True,
    "message": "Operation completed",
    "output": "git output...",
    # ... operation-specific fields
}
```

**Error:**
```python
{
    "success": False,
    "error": "Error message",
    "message": "Operation failed"
}
```

## Agent Tool Integration

### How LLM Calls Tools

1. **User says:** "Commit with message 'fix bug'"
2. **LLM recognizes:** This needs `git_commit` tool
3. **LLM calls:** `git_commit("fix bug")`
4. **Tool executes:** Git operations
5. **Returns:** Success/error message
6. **LLM responds:** "✅ Committed successfully"

### Tool Registration
```python
class CodeChatAgent(Agent):
    def __init__(self, llm_provider):
        # ... other tools
        self.register_tool(GitCommitTool())
        self.register_tool(GitBranchTool())
        self.register_tool(GitStatusTool())
```

### System Prompt
```python
Available tools:
- git_commit: Commit changes với message
- git_create_branch: Tạo branch mới
- git_status: Kiểm tra Git status

Khi user yêu cầu commit hoặc tạo branch, hãy sử dụng Git tools tự động.
```

## Testing

### Run Test Script
```bash
python scripts/test_git.py
```

Output:
```
🧪 Testing Git Operations...

1. 📊 Git Status:
------------------------------------------------------------
Changes detected:
 M src/web/app_fastapi.py
 M src/agents/code_agent.py

2. 🌳 Git Branches:
------------------------------------------------------------
Current branch: main
All branches (3):
  * main
    feature/new-ui
    hotfix/bug-123

3. 📜 Git Log (last 5 commits):
------------------------------------------------------------
  abc123 feat: add Git operations
  def456 fix: resolve authentication bug
  ...

✅ Git operations test complete!
```

### Manual Testing
```python
# Test commit (will actually commit!)
from src.tools.git_tool import git_commit
result = git_commit("test: manual commit test")
print(result)
```

## Error Scenarios

### No Changes to Commit
```python
result = git_commit("test")
# Output: {"success": False, "error": "nothing to commit, working tree clean"}
```

### Branch Already Exists
```python
result = git_create_branch("main")
# Output: {"success": False, "error": "fatal: A branch named 'main' already exists"}
```

### Not a Git Repository
```python
result = git_status()
# Output: {"success": False, "error": "fatal: not a git repository"}
```

## Best Practices

### 1. Descriptive Commit Messages
```python
# Good
git_commit("feat: add user authentication")
git_commit("fix: resolve memory leak in chat")
git_commit("docs: update README with setup instructions")

# Bad
git_commit("update")
git_commit("changes")
git_commit("wip")
```

### 2. Meaningful Branch Names
```python
# Good
git_create_branch("feature/websocket-chat")
git_create_branch("hotfix/security-vulnerability")
git_create_branch("refactor/code-structure")

# Bad
git_create_branch("test")
git_create_branch("branch1")
git_create_branch("temp")
```

### 3. Check Status First
```python
# Check before committing
status = git_status()
if status["has_changes"]:
    git_commit("feat: implement new feature")
else:
    print("No changes to commit")
```

## Workflow Examples

### Feature Development Flow
```python
# 1. Create feature branch
git_create_branch("feature/new-dashboard")

# 2. Make changes (edit files)

# 3. Check what changed
diff = git_diff()
print(diff["diff"])

# 4. Commit changes
git_commit("feat: add new dashboard UI")

# 5. View history
log = git_log(5)
for commit in log["commits"]:
    print(commit)
```

### Hotfix Flow
```python
# 1. Check current status
status = git_status()

# 2. Create hotfix branch
git_create_branch("hotfix/critical-bug")

# 3. Make fixes

# 4. Commit
git_commit("fix: resolve critical security issue")

# 5. Verify
log = git_log(1)
print(log["commits"][0])  # Latest commit
```

## Future Enhancements

Potential additions:
1. **git_pull()** - Pull latest changes
2. **git_merge(branch)** - Merge branches
3. **git_revert(commit)** - Revert commits
4. **git_stash()** - Stash changes
5. **git_tag(version)** - Create tags
6. **git_cherry_pick(commit)** - Cherry-pick commits
7. **GitHub PR creation** - Create pull requests via API

## Integration with Existing Systems

### Works With:
- ✅ **CodeChatAgent** - Natural language Git commands
- ✅ **FastAPI** - REST API endpoints
- ✅ **WebSocket** - Real-time Git operations
- ✅ **Memory System** - Remembers previous Git actions
- ✅ **RAG** - Context-aware Git suggestions

### Example Integration:
```python
# User asks in chat:
"Show me the changes and commit them with message 'update docs'"

# Agent workflow:
1. Calls git_status() → Shows changes
2. Calls git_diff() → Shows detailed diff
3. Asks for confirmation
4. Calls git_commit("update docs") → Commits
5. Responds: "✅ Changes committed and pushed!"
```

## Monitoring & Logging

All Git operations are logged:

```python
logger.info("📝 Git commit: fix authentication bug")
logger.info("🌿 Git branch: feature/new-ui")
logger.info("📊 Git status")
```

View logs:
```bash
tail -f logs/app.log | grep "Git"
```

## Troubleshooting

### Permission Denied
```bash
# Ensure Git credentials configured
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Push Failed
```bash
# Check remote configuration
git remote -v

# Ensure authentication (SSH/HTTPS)
git config --global credential.helper store
```

### Detached HEAD
```python
# Use git_branch_list() to check current branch
# Switch back: git checkout main
```

## Summary

Task 6 provides complete Git integration:

✅ **Safe Git operations** via subprocess  
✅ **Agent tool integration** for natural language  
✅ **REST API endpoints** for programmatic access  
✅ **Complete workflow** (add → commit → push)  
✅ **Error handling** with structured responses  
✅ **Logging & monitoring** for all operations  

**The AI can now autonomously manage Git workflow!** 🎉
