# Advanced AI-Agent Framework Documentation

## 📚 Overview

The Advanced AI-Agent Framework implements the **industry-standard 4-component AI-Agent architecture**:

1. **🧠 Brain (Profiling)** - LLM with customizable personality and expertise
2. **💾 Memory (Context Management)** - Short-term + Long-term with RAG
3. **📋 Planning (Task Decomposition)** - Multi-step planning with reasoning
4. **🔧 Tools (Execution)** - Code execution, file operations, API calls

This framework enables building sophisticated, specialized AI agents that can handle complex tasks with reasoning, memory retention, and tool execution.

---

## 🎯 Core Components

### 1. AgentProfile - The Brain 🧠

Defines agent personality, role, and expertise.

```python
from src.agents.advanced_agent import AgentProfile

profile = AgentProfile(
    name="PyMaster",
    role="Senior Python Developer",
    expertise=["Python 3.10+", "FastAPI", "Design Patterns"],
    personality="Educational, detailed, best-practice focused",
    system_prompt="Custom system instruction..."  # Optional
)

# Get system instruction
instruction = profile.get_system_instruction()
```

**Key Features:**
- Customizable personality and expertise
- Dynamic system prompt generation
- Defines agent behavior and tone

---

### 2. MemoryStore - Context Management 💾

Manages conversation context and knowledge base with RAG (Retrieval-Augmented Generation).

```python
from src.agents.advanced_agent import MemoryStore

memory = MemoryStore(max_short_term=20)

# Add to conversation history
memory.add_to_short_term("user", "What is Python?")
memory.add_to_short_term("assistant", "Python is...")

# Store long-term knowledge
memory.add_to_long_term("Python best practices", {"topic": "performance"})

# Retrieve context (last N messages)
context = memory.retrieve_context()

# Search knowledge base (RAG)
results = memory.search_knowledge("Python optimization", top_k=3)

# Get statistics
stats = memory.get_memory_stats()
# {'short_term_count': 5, 'long_term_count': 12, 'created_at': '2025-11-29T...'}
```

**Features:**
- **Short-term**: Auto-trimmed conversation history (max 20 messages)
- **Long-term**: Persistent knowledge base with metadata
- **RAG**: Keyword-based retrieval (future: semantic search with embeddings)
- **Auto-cleanup**: Prevents context overflow

---

### 3. PlanningEngine - Task Decomposition 📋

Breaks complex tasks into steps with reasoning and reflection.

```python
from src.agents.advanced_agent import PlanningEngine

engine = PlanningEngine()

# Decompose goal into steps
steps = engine.decompose_goal(
    goal="Build a scalable web application",
    llm_provider="groq"
)
# Returns: ["1. Design architecture", "2. Setup database", ...]

# Chain-of-thought reasoning
reasoning = engine.chain_of_thought(
    problem="How to optimize SQL queries?",
    llm_provider="groq"
)

# Self-reflection and improvement
reflection = engine.self_reflection(
    solution="Use caching for repeated queries",
    problem="Database performance",
    llm_provider="groq"
)
```

**Features:**
- **Goal Decomposition**: Break tasks into 3-5 actionable steps
- **Chain-of-Thought**: Show multi-step reasoning
- **Self-Reflection**: Analyze and improve solutions

---

### 4. Tool System - Execution 🔧

Execute code, manage files, and call APIs.

```python
from src.agents.advanced_agent import CodeExecutorTool, FileOperationsTool, ToolKit

# Individual tools
code_tool = CodeExecutorTool()
result = code_tool.execute(code="print('Hello')")
# {'stdout': 'Hello\n', 'returncode': 0, 'stderr': ''}

# Manage multiple tools
toolkit = ToolKit()
toolkit.register_tool(CodeExecutorTool())
toolkit.register_tool(FileOperationsTool())

# Execute via toolkit
result = toolkit.execute_tool("code_executor", code="x = 2 + 2")
tools_list = toolkit.list_tools()
```

**Available Tools:**
- **CodeExecutorTool**: Execute Python safely (with timeout)
- **FileOperationsTool**: Read/write files
- **APICallTool**: Make HTTP requests
- **ToolKit**: Manage and execute tools

---

## 🤖 AdvancedAIAgent - Main Integration

Orchestrates all 4 components.

```python
from src.agents.advanced_agent import AdvancedAIAgent, AgentProfile
from src.llm.groq import GroqProvider

# Create profile
profile = AgentProfile(
    name="PyMaster",
    role="Senior Python Developer",
    expertise=["Python", "Testing"],
    personality="Educational"
)

# Create agent
llm = GroqProvider()
agent = AdvancedAIAgent(profile, llm)

# 1. Simple chat (with memory + RAG)
response = agent.chat(
    user_input="How to write unit tests?",
    llm_provider="groq"
)

# 2. Complex planning
plan = agent.execute_with_planning(
    task="Build a REST API with authentication",
    llm_provider="groq"
)

# 3. Code execution
result = agent.execute_code_task(
    description="Calculate factorial",
    code="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
)

# 4. Agent status
status = agent.get_agent_status()
# {'name': 'PyMaster', 'role': '...', 'expertise': [...], 'tools': [...]}
```

---

## 🏭 Agent Factory - Pre-configured Specialists

Create specialized agents with one function call.

```python
from src.agents.agent_factory import create_agent

# Create Python Expert
python_agent = create_agent("python_expert", llm)

# Create DevOps Engineer
devops_agent = create_agent("devops", llm)

# Create Product Manager
pm_agent = create_agent("product_manager", llm)

# Available agents
agents = [
    "python_expert",      # Senior Python Developer
    "devops",             # DevOps Engineer
    "product_manager",    # Product Manager
    "data_scientist",     # ML Engineer
    "security",           # Security Engineer
    "creative"            # Content Writer
]
```

---

## 🌐 Web API Endpoints

### List Available Agents
```bash
GET /api/advanced-agents

Response:
{
  "status": "success",
  "agents": [
    {
      "type": "python_expert",
      "name": "Python Expert",
      "description": "Senior Python Developer & Code Architect"
    },
    ...
  ],
  "count": 6
}
```

### Chat with Agent
```bash
POST /api/advanced-agent/chat

Request:
{
  "agent_type": "python_expert",
  "message": "How to optimize this code?"
}

Response:
{
  "status": "success",
  "agent": "python_expert",
  "agent_name": "PyMaster",
  "response": "Here's how to optimize..."
}
```

### Get Planning
```bash
POST /api/advanced-agent/planning

Request:
{
  "agent_type": "devops",
  "task": "Design scalable microservices"
}

Response:
{
  "status": "success",
  "agent": "devops",
  "plan": "1. Define service boundaries\n2. Design API contracts\n..."
}
```

### Execute Code
```bash
POST /api/advanced-agent/code-execution

Request:
{
  "agent_type": "python_expert",
  "description": "Calculate fibonacci",
  "code": "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)"
}

Response:
{
  "status": "success",
  "agent": "python_expert",
  "result": "Execution result..."
}
```

### Get Agent Status
```bash
GET /api/advanced-agent/status/<agent_type>

Response:
{
  "status": "success",
  "agent_type": "python_expert",
  "agent_info": {
    "name": "PyMaster",
    "role": "Senior Python Developer",
    "expertise": ["Python 3.10+", "FastAPI", ...],
    "tools": ["code_executor", "file_operations"]
  },
  "capabilities": {
    "chat": true,
    "planning": true,
    "code_execution": true,
    "memory": true,
    "reflection": true
  }
}
```

---

## 💻 CLI Usage

### List All Agents
```bash
python cli_advanced_agents.py --list
```

### Chat Mode
```bash
python cli_advanced_agents.py --agent python_expert --chat "Optimize this code"
```

### Planning Mode
```bash
python cli_advanced_agents.py --agent devops --plan "Design microservices"
```

### Interactive Mode
```bash
python cli_advanced_agents.py --agent security --interactive

# In interactive mode:
# > What are common security vulnerabilities?
# > plan Design authentication system
# > quit
```

### Code Execution
```bash
python cli_advanced_agents.py --agent python_expert --code "print('Hello')"
```

### Show Agent Status
```bash
python cli_advanced_agents.py --agent data_scientist --status
```

---

## 📝 Use Cases

### 1. Python Code Review
```python
python_agent = create_agent("python_expert", llm)

# Chat mode
python_agent.chat("Review this code for bugs", "groq")

# Planning mode - multi-step review
python_agent.execute_with_planning("Complete code audit for production", "groq")

# Execute test
python_agent.execute_code_task("Test the code", "pytest tests/")
```

### 2. DevOps Architecture Design
```python
devops_agent = create_agent("devops", llm)

# Get architecture plan
plan = devops_agent.execute_with_planning(
    "Design AWS infrastructure for 1M users",
    "groq"
)

# Execute infrastructure code
devops_agent.execute_code_task(
    "Create Terraform configuration",
    "terraform_code_here"
)
```

### 3. Product Strategy
```python
pm_agent = create_agent("product_manager", llm)

# Get strategic insights
response = pm_agent.chat("What's our go-to-market strategy?", "groq")

# Multi-step planning
pm_agent.execute_with_planning(
    "Plan Q1 product roadmap",
    "groq"
)
```

### 4. Data Science Workflow
```python
ds_agent = create_agent("data_scientist", llm)

# Analyze problem
analysis = ds_agent.chat("How to approach this ML problem?", "groq")

# Plan approach
plan = ds_agent.execute_with_planning(
    "Build recommendation system",
    "groq"
)

# Execute experiments
ds_agent.execute_code_task(
    "Run model comparison",
    "train_models_code"
)
```

---

## 🧪 Testing

Run comprehensive tests:

```bash
# Test individual components
pytest tests/test_advanced_agent.py::TestAgentProfile -v
pytest tests/test_advanced_agent.py::TestMemoryStore -v
pytest tests/test_advanced_agent.py::TestPlanningEngine -v
pytest tests/test_advanced_agent.py::TestCodeExecutorTool -v

# Test integration
pytest tests/test_advanced_agent.py::TestIntegration -v

# Run all tests
pytest tests/test_advanced_agent.py -v
```

---

## 🔧 Configuration

### Memory Settings
```python
memory = MemoryStore(
    max_short_term=20,      # Max conversation history
    max_long_term=1000      # Max knowledge base size
)
```

### Agent Profile
```python
profile = AgentProfile(
    name="Agent",
    role="Role",
    expertise=["skill1", "skill2"],
    personality="Trait1, Trait2",
    system_prompt="Custom instruction"  # Optional
)
```

### Tool Configuration
```python
code_tool = CodeExecutorTool(timeout=10)  # 10 second timeout
```

---

## 📊 Agent Capabilities Matrix

| Agent | Chat | Planning | Code | Memory | Files | API |
|-------|------|----------|------|--------|-------|-----|
| Python Expert | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DevOps | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Product Manager | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Data Scientist | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Security | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Creative | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |

---

## 🚀 Best Practices

1. **Profile Definition**: Clearly define agent role and expertise
2. **Memory Management**: Regularly check memory stats to prevent overflow
3. **Error Handling**: Always wrap agent calls in try-except
4. **Planning First**: Use planning for complex tasks, chat for simple queries
5. **Tool Validation**: Verify tool execution results
6. **Reflection**: Use self-reflection for critical decisions

---

## 📚 Related Files

- `src/agents/advanced_agent.py` - Framework implementation (500+ lines)
- `src/agents/agent_factory.py` - Pre-configured agent creators
- `tests/test_advanced_agent.py` - Comprehensive test suite
- `cli_advanced_agents.py` - Command-line interface
- `src/web/app.py` - REST API endpoints

---

## 📞 Support

For issues or questions:
1. Check test cases for usage examples
2. Review agent factory for pre-configured agents
3. Consult web API documentation
4. Check CLI help: `python cli_advanced_agents.py --help`

---

**Version**: 1.0.0  
**Last Updated**: November 29, 2025  
**Framework**: Advanced AI-Agent with 4-Component Architecture
