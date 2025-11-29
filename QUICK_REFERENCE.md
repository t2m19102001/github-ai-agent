# 🚀 Advanced AI-Agent Framework - Quick Reference

## One-Line Commands

### List Agents
```bash
python cli_advanced_agents.py --list
```

### Chat with Agent
```bash
python cli_advanced_agents.py --agent python_expert --chat "Your question"
```

### Get Planning
```bash
python cli_advanced_agents.py --agent devops --plan "Your task"
```

### Interactive Mode
```bash
python cli_advanced_agents.py --agent security --interactive
```

### Show Agent Capabilities
```bash
python cli_advanced_agents.py --agent data_scientist --status
```

---

## Python API

### Basic Usage
```python
from src.agents.agent_factory import create_agent
from src.llm.groq import GroqProvider

llm = GroqProvider()
agent = create_agent("python_expert", llm)

# Simple chat
response = agent.chat("How to optimize Python code?", "groq")
print(response)

# Multi-step planning
plan = agent.execute_with_planning("Build REST API", "groq")
print(plan)

# Code execution
result = agent.execute_code_task("Calculate", "print(2+2)")
print(result)
```

### Agent Types
```python
agents = [
    "python_expert",      # 🐍 Code optimization & reviews
    "devops",             # 🔧 Infrastructure & cloud
    "product_manager",    # 📊 Strategy & roadmaps
    "data_scientist",     # 🤖 ML & analytics
    "security",           # 🔒 Security & compliance
    "creative"            # ✍️ Writing & content
]

for agent_type in agents:
    agent = create_agent(agent_type, llm)
```

---

## REST API

### Get All Agents
```bash
curl http://localhost:5000/api/advanced-agents
```

### Chat with Agent
```bash
curl -X POST http://localhost:5000/api/advanced-agent/chat \
  -H "Content-Type: application/json" \
  -d '{"agent_type":"python_expert","message":"Your question"}'
```

### Get Planning
```bash
curl -X POST http://localhost:5000/api/advanced-agent/planning \
  -H "Content-Type: application/json" \
  -d '{"agent_type":"devops","task":"Your task"}'
```

### Execute Code
```bash
curl -X POST http://localhost:5000/api/advanced-agent/code-execution \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type":"python_expert",
    "description":"Calculate factorial",
    "code":"def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
  }'
```

### Agent Status
```bash
curl http://localhost:5000/api/advanced-agent/status/python_expert
```

---

## Framework Components

### 1. Brain (AgentProfile)
```python
from src.agents.advanced_agent import AgentProfile

profile = AgentProfile(
    name="MyAgent",
    role="Senior Developer",
    expertise=["Python", "AI"],
    personality="Helpful"
)
instruction = profile.get_system_instruction()
```

### 2. Memory (MemoryStore)
```python
from src.agents.advanced_agent import MemoryStore

memory = MemoryStore(max_context_messages=20)

# Store conversation
memory.add_to_short_term("user", "What is Python?")
memory.add_to_short_term("assistant", "Python is...")

# Store knowledge
memory.add_to_long_term("Python best practices")

# Retrieve
context = memory.retrieve_context()
results = memory.search_knowledge("Python optimization", top_k=3)
stats = memory.get_memory_stats()
```

### 3. Planning (PlanningEngine)
```python
from src.agents.advanced_agent import PlanningEngine

engine = PlanningEngine()

# Break down tasks
steps = engine.decompose_goal("Build microservices", llm)

# Show reasoning
reasoning = engine.chain_of_thought("How to optimize?", llm)

# Improve solutions
reflection = engine.self_reflection(solution, problem, llm)
```

### 4. Tools (ToolKit)
```python
from src.agents.advanced_agent import CodeExecutorTool, ToolKit

toolkit = ToolKit()
toolkit.register_tool(CodeExecutorTool())

# Execute
result = toolkit.execute_tool("code_executor", code="print('Hello')")
tools = toolkit.list_tools()
```

---

## Use Cases

### Code Review
```python
agent = create_agent("python_expert", llm)
review = agent.chat("Review this code for bugs: " + code, "groq")
```

### Infrastructure Design
```python
agent = create_agent("devops", llm)
plan = agent.execute_with_planning("Design for 1M users", "groq")
```

### Product Strategy
```python
agent = create_agent("product_manager", llm)
strategy = agent.chat("What's our go-to-market strategy?", "groq")
```

### ML Development
```python
agent = create_agent("data_scientist", llm)
result = agent.execute_code_task("Train model", train_code)
```

### Security Assessment
```python
agent = create_agent("security", llm)
analysis = agent.chat("Analyze security risks: " + code, "groq")
```

---

## Testing

### Run All Tests
```bash
cd /Users/minhman/Develop/github-ai-agent
.venv/bin/python -m pytest tests/test_advanced_agent_simple.py -v
```

### Run Specific Test
```bash
.venv/bin/python -m pytest tests/test_advanced_agent_simple.py::TestMemoryStoreCore -v
```

### With Coverage
```bash
.venv/bin/python -m pytest tests/test_advanced_agent_simple.py --cov=src/agents
```

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/agents/advanced_agent.py` | Main framework | 500+ |
| `src/agents/agent_factory.py` | Agent factory | 300+ |
| `cli_advanced_agents.py` | CLI tool | 250+ |
| `src/web/app.py` | API endpoints | +100 |
| `tests/test_advanced_agent_simple.py` | Tests | 250+ |
| `ADVANCED_AGENT_DOCS.md` | Documentation | 300+ |

---

## Common Issues

### Agent Not Found
```bash
# Check available agents
python cli_advanced_agents.py --list
```

### API Connection Refused
```bash
# Start server
python run_web.py

# Wait 3 seconds
sleep 3

# Test endpoint
curl http://localhost:5000/api/advanced-agents
```

### Code Execution Timeout
- Default timeout: 10 seconds
- Modify in `CodeExecutorTool.__init__()`
- Note: Long-running code will fail

---

## Performance Tips

1. **Reuse Agents**: Create agent once, use many times
   ```python
   agent = create_agent("python_expert", llm)  # Once
   agent.chat("Q1", "groq")  # Use many times
   agent.chat("Q2", "groq")
   ```

2. **Check Memory**: Prevent context overflow
   ```python
   stats = agent.memory.get_memory_stats()
   if stats["short_term_messages"] > 10:
       # Consider starting new session
   ```

3. **Use Planning**: For complex tasks
   ```python
   # Better for complex tasks
   plan = agent.execute_with_planning(task, "groq")
   
   # Simpler for Q&A
   response = agent.chat(question, "groq")
   ```

---

## Interactive Mode Guide

```
$ python cli_advanced_agents.py --agent python_expert --interactive

============================================================
💬 INTERACTIVE MODE - PyMaster
============================================================
Commands: 'quit' to exit, 'plan <task>' for planning

You: What are best practices for Python async?
🤖 PyMaster: [detailed response about async patterns]

You: plan Build async web server
📋 PyMaster Planning: 
1. Design async architecture
2. Choose framework
3. Implement handlers
...

You: quit
👋 Goodbye!
```

---

## Troubleshooting

### Import Errors
```bash
# Ensure correct Python environment
which python  # Should show .venv path

# Reinstall if needed
pip install -r requirements.txt
```

### Agent Creation Failed
```bash
# Check agent name
python cli_advanced_agents.py --list  # See valid names

# Try with correct name
python cli_advanced_agents.py --agent python_expert --chat "test"
```

### Memory Errors
```bash
# Max context is 20 messages
# If memory grows too large, start new session
# Or reduce max_context_messages:
memory = MemoryStore(max_context_messages=10)
```

---

## Developer Workflow

### 1. Create New Agent
```python
profile = AgentProfile(
    name="MyAgent",
    role="My Role",
    expertise=["skill1", "skill2"],
    personality="Trait1, Trait2"
)
agent = AdvancedAIAgent(profile, llm)
```

### 2. Add to Factory (Optional)
```python
# In src/agents/agent_factory.py
def create_my_agent(llm_provider):
    profile = AgentProfile(...)
    return AdvancedAIAgent(profile, llm_provider)

AGENT_REGISTRY["my_agent"] = create_my_agent
```

### 3. Test It
```python
agent = create_agent("my_agent", llm)
response = agent.chat("test message", "groq")
assert len(response) > 0
```

### 4. Add to CLI
```bash
# Already supported! Try:
python cli_advanced_agents.py --agent my_agent --chat "test"
```

---

## Quick Debug

### Check Framework
```python
from src.agents.advanced_agent import AdvancedAIAgent, MemoryStore, ToolKit
print("✅ Framework imports working")
```

### Check Agents
```python
from src.agents.agent_factory import list_available_agents
agents = list_available_agents()
print(f"✅ {len(agents)} agents available")
```

### Check API
```bash
curl http://localhost:5000/api/advanced-agents
```

### Check CLI
```bash
python cli_advanced_agents.py --list
```

---

## Project Status
- ✅ Framework: Complete and tested
- ✅ Agents: 6 pre-configured specialists
- ✅ API: 5 new endpoints
- ✅ CLI: Full-featured tool
- ✅ Tests: 20/20 passing
- ✅ Docs: Comprehensive

**Ready for production!** 🚀

---

**Last Updated**: November 29, 2025  
**Version**: 1.0.0  
**Status**: ✅ Complete
