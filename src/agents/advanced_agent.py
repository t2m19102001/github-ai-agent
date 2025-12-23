from typing import List, Dict, Optional, Any
import io
import contextlib


def call_llm(prompt: str, provider: Any) -> str:
    return str(prompt)


class AgentProfile:
    def __init__(self, name: str, role: str, expertise: List[str], personality: str, system_prompt: str):
        self.name = name
        self.role = role
        self.expertise = expertise
        self.personality = personality
        self.system_prompt = system_prompt

    def get_system_instruction(self) -> str:
        if self.system_prompt:
            return self.system_prompt
        expertise_text = ", ".join(self.expertise) if self.expertise else ""
        return f"Agent {self.name} ({self.role}) {expertise_text} {self.personality}".strip()


class MemoryStore:
    def __init__(self, max_context_messages: int = 20):
        self.max_context_messages = max_context_messages
        self.short_term_memory: List[Dict[str, str]] = []
        self.long_term_memory: List[Dict[str, Any]] = []

    def add_to_short_term(self, role: str, content: str) -> None:
        self.short_term_memory.append({"role": role, "content": content})
        if len(self.short_term_memory) > self.max_context_messages:
            self.short_term_memory = self.short_term_memory[-self.max_context_messages :]

    def add_to_long_term(self, knowledge: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.long_term_memory.append({"knowledge": knowledge, "metadata": metadata or {}})

    def retrieve_context(self) -> str:
        parts = []
        for msg in self.short_term_memory[-self.max_context_messages :]:
            parts.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(parts)

    def search_knowledge(self, query: str, top_k: int = 3) -> List[str]:
        results: List[str] = []
        q = (query or "").lower()
        for item in self.long_term_memory:
            text = item.get("knowledge", "")
            if q in text.lower():
                results.append(text)
            if len(results) >= top_k:
                break
        return results

    def get_memory_stats(self) -> Dict[str, int]:
        return {
            "short_term_messages": len(self.short_term_memory),
            "long_term_knowledge": len(self.long_term_memory),
            "short_term_count": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
        }


class Tool:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    def execute(self, *args, **kwargs) -> Any:
        return None


class CodeExecutorTool(Tool):
    def __init__(self):
        super().__init__(name="code_executor", description="Execute Python code and capture output")

    def execute(self, code: str) -> Dict[str, Any]:
        buf = io.StringIO()
        ns: Dict[str, Any] = {}
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, ns, ns)
            output = buf.getvalue()
            return {"status": "success", "output": output, "return_code": 0}
        except Exception as e:
            return {"status": "error", "error": str(e), "output": buf.getvalue(), "return_code": 1}


class FileOperationsTool(Tool):
    def __init__(self):
        super().__init__(name="file_operations", description="Read/write files")

    def execute(self, operation: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        try:
            if operation == "read":
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                return {"status": "success", "result": data}
            elif operation == "write":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content or "")
                return {"status": "success", "result": "written"}
            else:
                return {"status": "error", "error": "unsupported operation"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class APICallTool(Tool):
    def __init__(self):
        super().__init__(name="api_call", description="Call external APIs")

    def execute(self, url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "success", "result": {"url": url, "method": method, "data": data}}


class ToolsList:
    def __init__(self, items: List[Dict[str, str]]):
        self._items = items
    def __iter__(self):
        return iter(self._items)
    def __len__(self):
        return len(self._items)
    def __contains__(self, x: Any) -> bool:
        if isinstance(x, str):
            return any(i.get("name") == x for i in self._items)
        return x in self._items


class ToolKit:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self):
        items = [{"name": t.name, "description": t.description} for t in self.tools.values()]
        return ToolsList(items)


class PlanningEngine:
    def decompose_goal(self, goal: str, provider: Any) -> List[str]:
        text = call_llm(goal, provider)
        lines = [l.strip() for l in str(text).splitlines() if l.strip()]
        return lines if lines else [goal]

    def chain_of_thought(self, question: str, provider: Any) -> str:
        return call_llm(question, provider)

    def self_reflection(self, answer: str, problem: str, provider: Any) -> str:
        return call_llm(f"{answer}\n{problem}", provider)


class AdvancedAIAgent:
    def __init__(self, profile: AgentProfile, llm_provider: Any):
        self.profile = profile
        self.llm_provider = llm_provider
        self.memory = MemoryStore()
        self.toolkit = ToolKit()
        self.toolkit.register_tool(CodeExecutorTool())
        self.toolkit.register_tool(FileOperationsTool())
        self.toolkit.register_tool(APICallTool())

    def chat(self, message: str, provider: Any) -> str:
        self.memory.add_to_short_term("user", message)
        resp = call_llm(message, provider)
        self.memory.add_to_short_term("assistant", resp)
        return resp

    def get_agent_status(self) -> Dict[str, Any]:
        return {
            "agent_name": self.profile.name,
            "agent_role": self.profile.role,
            "name": self.profile.name,
            "role": self.profile.role,
            "expertise": self.profile.expertise,
            "tools": self.toolkit.list_tools(),
            "memory": self.memory.get_memory_stats(),
        }

    def execute_with_planning(self, goal: str, provider: Any) -> List[str]:
        engine = PlanningEngine()
        return engine.decompose_goal(goal, provider)
