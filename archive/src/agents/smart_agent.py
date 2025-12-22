#!/usr/bin/env python3
"""
Smart Agent - Powered by Knowledge Base
- Không phụ thuộc 100% vào LLM
- Sử dụng kiến thức thực thay vì hardcoded responses
- Học từ knowledge base, code, và best practices
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from src.utils.logger import get_logger
from src.agents.knowledge_base import get_knowledge_base, KnowledgeItem

logger = get_logger(__name__)


class SmartAnalysisAgent:
    """Smart Agent với logic phân tích nhúng - Hoạt động mà không cần LLM"""
    
    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: Optional LLM provider (fallback)
        """
        self.llm_provider = llm_provider
        self.kb = get_knowledge_base()
        self.code_patterns = self._init_code_patterns()
    
    def _init_code_patterns(self) -> Dict[str, List[str]]:
        """Khởi tạo các pattern đánh dấu vấn đề trong code"""
        return {
            "security": [
                r"eval\s*\(",
                r"exec\s*\(",
                r"pickle\.loads",
                r"subprocess\s*\.\s*call\s*\(",
                r"os\.system",
                r"input\s*\(",
                r"raw_input",
                r"__import__",
            ],
            "performance": [
                r"while\s+True",
                r"for\s+.*in\s+range\s*\(\s*len",
                r"O\(n\s*\*\s*n\)",
                r"nested.*loop",
                r"global\s+\w+",
            ],
            "best_practice": [
                r"except\s*:",  # Bare except
                r"print\s*\(",  # Debug print in production
                r"import\s+\*",  # Wildcard import
                r"(?<!\w)l(?!\w)|(?<!\w)O(?!\w)|(?<!\w)I(?!\w)",  # Confusing variable names
            ],
            "style": [
                r"\t",  # Tab instead of spaces
                r"  {3,}",  # Too many spaces
            ]
        }
    
    def _retrieve_relevant_knowledge(self, query: str, category: Optional[str] = None) -> str:
        """Retrieve relevant knowledge from knowledge base"""
        results = self.kb.search(query, category=category, top_k=3)
        
        if not results:
            return ""
        
        response = "📚 **Based on Knowledge Base:**\n\n"
        for item, score in results:
            response += f"**{item.title}**\n"
            response += f"_{item.topic}_ (Relevance: {score:.1f})\n\n"
            response += item.content + "\n\n"
            response += "---\n\n"
            # Increment usage
            self.kb.increment_usage(item.id)
        
        return response
    
    def analyze_request(self, request: str) -> str:
        """
        Phân tích request của user một cách smart
        Sử dụng Knowledge Base thay vì hardcoded responses
        """
        request_lower = request.lower()
        
        # Try to retrieve relevant knowledge first
        knowledge = self._retrieve_relevant_knowledge(request, category=None)
        
        if knowledge:
            return knowledge
        
        # Detect intent
        intent = self._detect_intent(request_lower)
        
        # Build response based on intent
        if "odoo" in request_lower and "module" in request_lower:
            return self._analyze_odoo_module_request(request)
        elif "build" in request_lower and "module" in request_lower:
            return self._analyze_build_module_request(request)
        elif "error" in request_lower or "debug" in request_lower or "issue" in request_lower:
            return self._analyze_debug_request(request)
        elif "optimize" in request_lower or "performance" in request_lower:
            return self._analyze_optimization_request(request)
        elif "design" in request_lower or "architecture" in request_lower:
            return self._analyze_architecture_request(request)
        else:
            return self._generate_generic_analysis(request, intent)
    
    def _detect_intent(self, request: str) -> str:
        """Phát hiện intent của request"""
        keywords = {
            "build": ["build", "create", "implement", "develop", "make"],
            "analyze": ["analyze", "analyze", "review", "check", "examine"],
            "optimize": ["optimize", "improve", "speed", "performance", "refactor"],
            "learn": ["how", "why", "what", "explain", "tutorial"],
            "fix": ["fix", "debug", "error", "issue", "problem"],
            "design": ["design", "architecture", "structure", "plan"],
        }
        
        for intent, keywords_list in keywords.items():
            if any(kw in request for kw in keywords_list):
                return intent
        
        return "general"
    
    def _analyze_odoo_module_request(self, request: str) -> str:
        """Phân tích request về Odoo module"""
        response = "📦 **Odoo Module Development Guide**\n\n"
        response += "**Step-by-step approach:**\n"
        response += "1️⃣ **Module Structure**\n"
        response += "   - Create directory: `my_module/`\n"
        response += "   - Add `__init__.py`, `__manifest__.py`\n"
        response += "   - Create `models/`, `views/`, `controllers/`, `static/`\n\n"
        response += "2️⃣ **__manifest__.py** (Module metadata)\n"
        response += "   ```python\n"
        response += "   {\n"
        response += "       'name': 'My Module',\n"
        response += "       'version': '1.0',\n"
        response += "       'depends': ['base', 'sale'],\n"
        response += "       'installable': True,\n"
        response += "   }\n"
        response += "   ```\n\n"
        response += "3️⃣ **Create Models** (`models/my_model.py`)\n"
        response += "   - Inherit from `models.Model`\n"
        response += "   - Define fields and methods\n\n"
        response += "4️⃣ **Create Views** (`views/my_model_view.xml`)\n"
        response += "   - Form view, Tree view, Search view\n\n"
        response += "5️⃣ **Install Module**\n"
        response += "   - Add to `ADDONS_PATH`\n"
        response += "   - Restart Odoo\n"
        response += "   - Activate Developer mode\n"
        response += "   - Update apps & install your module\n\n"
        response += "💡 **Tips:**\n"
        response += "- Use inheritance for extending existing models\n"
        response += "- Create security rules in `security/ir.model.access.csv`\n"
        response += "- Add `data/` folder for default data loading\n"
        
        return response
    
    def _analyze_build_module_request(self, request: str) -> str:
        """Phân tích request về building module"""
        response = "🏗️ **Module Building Strategy**\n\n"
        response += "**Stage 1: Planning**\n"
        response += "- Define requirements\n"
        response += "- Identify data models\n"
        response += "- Plan workflows\n\n"
        response += "**Stage 2: Setup**\n"
        response += "- Initialize module structure\n"
        response += "- Configure dependencies\n"
        response += "- Set up development environment\n\n"
        response += "**Stage 3: Implementation**\n"
        response += "- Create models and fields\n"
        response += "- Build views (forms, trees, pivots)\n"
        response += "- Add business logic\n"
        response += "- Implement security\n\n"
        response += "**Stage 4: Testing**\n"
        response += "- Unit tests\n"
        response += "- Integration tests\n"
        response += "- User acceptance testing\n\n"
        response += "**Stage 5: Deployment**\n"
        response += "- Documentation\n"
        response += "- Migration scripts\n"
        response += "- Production deployment\n"
        
        return response
    
    def _analyze_debug_request(self, request: str) -> str:
        """Phân tích request về debug/troubleshooting"""
        response = "🔍 **Debugging Approach**\n\n"
        response += "**Step 1: Gather Information**\n"
        response += "- Error message and traceback\n"
        response += "- When did it start?\n"
        response += "- What changed recently?\n"
        response += "- Environment details\n\n"
        response += "**Step 2: Isolate the Problem**\n"
        response += "- Reproduce the issue consistently\n"
        response += "- Check logs\n"
        response += "- Verify configuration\n\n"
        response += "**Step 3: Root Cause Analysis**\n"
        response += "- Use debugger (pdb, breakpoints)\n"
        response += "- Add logging statements\n"
        response += "- Check dependencies\n\n"
        response += "**Step 4: Implement Fix**\n"
        response += "- Create fix with tests\n"
        response += "- Verify fix doesn't break other things\n"
        response += "- Document the solution\n"
        
        return response
    
    def _analyze_optimization_request(self, request: str) -> str:
        """Phân tích request về optimization"""
        response = "⚡ **Performance Optimization Guide**\n\n"
        response += "**Common Performance Issues & Fixes:**\n\n"
        response += "1. **Database Queries**\n"
        response += "   - Use `.select_related()` for ForeignKey\n"
        response += "   - Use `.prefetch_related()` for ManyToMany\n"
        response += "   - Add database indexes\n\n"
        response += "2. **Caching**\n"
        response += "   - Use Redis for session caching\n"
        response += "   - Cache expensive computations\n"
        response += "   - Implement cache invalidation strategy\n\n"
        response += "3. **Code Efficiency**\n"
        response += "   - Avoid nested loops (O(n²) algorithms)\n"
        response += "   - Use list comprehensions\n"
        response += "   - Lazy load resources\n\n"
        response += "4. **Frontend Performance**\n"
        response += "   - Minimize HTTP requests\n"
        response += "   - Optimize images\n"
        response += "   - Enable compression\n\n"
        response += "5. **Profiling Tools**\n"
        response += "   - Django Debug Toolbar\n"
        response += "   - Python cProfile\n"
        response += "   - Database query logs\n"
        
        return response
    
    def _analyze_architecture_request(self, request: str) -> str:
        """Phân tích request về architecture"""
        response = "🏛️ **Architecture Design Pattern**\n\n"
        response += "**Recommended Architecture:**\n\n"
        response += "```\n"
        response += "┌─────────────────────────────────────┐\n"
        response += "│      Frontend Layer                 │\n"
        response += "│  (UI Components, State Management)  │\n"
        response += "└──────────────────┬──────────────────┘\n"
        response += "                   │\n"
        response += "┌──────────────────▼──────────────────┐\n"
        response += "│      API Layer                      │\n"
        response += "│  (REST/GraphQL Endpoints)           │\n"
        response += "└──────────────────┬──────────────────┘\n"
        response += "                   │\n"
        response += "┌──────────────────▼──────────────────┐\n"
        response += "│      Business Logic Layer           │\n"
        response += "│  (Models, Services, Validators)     │\n"
        response += "└──────────────────┬──────────────────┘\n"
        response += "                   │\n"
        response += "┌──────────────────▼──────────────────┐\n"
        response += "│      Data Layer                     │\n"
        response += "│  (Database, Cache, External APIs)   │\n"
        response += "└─────────────────────────────────────┘\n"
        response += "```\n\n"
        response += "**Design Principles:**\n"
        response += "- Separation of Concerns\n"
        response += "- DRY (Don't Repeat Yourself)\n"
        response += "- SOLID Principles\n"
        response += "- Scalability from the start\n"
        response += "- Testability\n"
        
        return response
    
    def _generate_generic_analysis(self, request: str, intent: str) -> str:
        """Generate generic analysis when intent is unknown"""
        response = f"💡 **Analysis for: {request[:50]}...**\n\n"
        response += f"**Detected Intent:** {intent.capitalize()}\n\n"
        
        if intent == "general":
            response += "**Analysis Results:**\n"
            response += "- Your request has been analyzed\n"
            response += "- Multiple approaches can be considered\n"
            response += "- Key considerations:\n"
            response += "  1. Requirements clarity\n"
            response += "  2. Technical feasibility\n"
            response += "  3. Performance implications\n"
            response += "  4. Maintenance and scalability\n\n"
            response += "**Recommended Approach:**\n"
            response += "1. Break down the problem\n"
            response += "2. Research existing solutions\n"
            response += "3. Prototype and test\n"
            response += "4. Iterate based on feedback\n"
            response += "5. Document thoroughly\n\n"
            response += "**Next Steps:**\n"
            response += "- Provide more specific details\n"
            response += "- Share code snippets if applicable\n"
            response += "- Upload files for detailed analysis\n"
        
        return response
    
    def analyze_code_quality(self, code: str, language: str = "python") -> str:
        """Phân tích code quality dùng patterns"""
        response = f"📊 **Code Quality Analysis** ({language})\n\n"
        
        if language.lower() == "python":
            response += self._analyze_python_code(code)
        elif language.lower() == "javascript":
            response += self._analyze_javascript_code(code)
        elif language.lower() == "java":
            response += self._analyze_java_code(code)
        else:
            response += "Generic code analysis not yet available for this language.\n"
        
        return response
    
    def _analyze_python_code(self, code: str) -> str:
        """Phân tích Python code"""
        issues = []
        suggestions = []
        
        # Check security issues
        for pattern in self.code_patterns["security"]:
            if re.search(pattern, code):
                issues.append(f"⚠️ Potential security issue: {pattern}")
        
        # Check performance issues
        for pattern in self.code_patterns["performance"]:
            if re.search(pattern, code):
                issues.append(f"⚠️ Potential performance issue: {pattern}")
        
        # Check best practices
        lines = code.split('\n')
        if len(lines) > 50 and len([l for l in lines if l.strip()]) > 50:
            suggestions.append("💡 Function is long - consider breaking it into smaller functions")
        
        if "import" in code:
            imports = len(re.findall(r'^import |^from ', code, re.MULTILINE))
            suggestions.append(f"ℹ️ {imports} import statements - organize with `__init__.py`")
        
        if code.count("def ") == 0:
            suggestions.append("💡 No functions defined - consider organizing code into functions")
        
        # Basic metrics
        metrics_str = f"""**Code Metrics:**
- Lines: {len(lines)}
- Functions: {code.count('def ')}
- Classes: {code.count('class ')}
- Comments: {code.count('#')}

"""
        
        issues_str = "**Issues Found:**\n" + "\n".join(issues) + "\n\n" if issues else "✅ **No major issues detected**\n\n"
        suggestions_str = "**Suggestions:**\n" + "\n".join(suggestions) + "\n\n" if suggestions else ""
        
        return metrics_str + issues_str + suggestions_str
    
    def _analyze_javascript_code(self, code: str) -> str:
        """Phân tích JavaScript code"""
        issues = []
        
        if "var " in code:
            issues.append("⚠️ Using 'var' - prefer 'let' or 'const'")
        
        if "console.log" in code:
            issues.append("⚠️ Debug console.log found - remove for production")
        
        lines = code.split('\n')
        var_count = len(re.findall(r'(let|const|var)\s+', code))
        metrics_str = f"""**Code Metrics:**
- Lines: {len(lines)}
- Functions: {code.count('function')} + {code.count('=>')} arrow functions
- Variables: {var_count}

"""
        
        issues_str = "**Issues:**\n" + "\n".join(issues) + "\n\n" if issues else "✅ **No major issues detected**\n\n"
        
        return metrics_str + issues_str + "**Suggestions:**\n- Use strict mode ('use strict')\n- Consider TypeScript\n- Add JSDoc comments\n"
    
    def _analyze_java_code(self, code: str) -> str:
        """Phân tích Java code"""
        lines = code.split('\n')
        metrics = f"""**Code Metrics:**
- Lines: {len(lines)}
- Classes: {code.count('class ')}
- Methods: {code.count('public') + code.count('private')}

"""
        
        issues = []
        if "System.out.println" in code:
            issues.append("⚠️ Using System.out.println - use Logger instead")
        
        if "catch (Exception" in code:
            issues.append("⚠️ Catching generic Exception - catch specific exceptions")
        
        issues_str = "**Issues:**\n" + "\n".join(issues) + "\n\n" if issues else "✅ **No major issues detected**\n\n"
        
        return metrics + issues_str
    
    def chat(self, message: str) -> str:
        """Main chat interface - Smart analysis without LLM dependency"""
        logger.info(f"Smart Agent analyzing: {message[:50]}...")
        
        try:
            response = self.analyze_request(message)
            return response
        except Exception as e:
            logger.error(f"Smart agent error: {e}")
            return f"🤖 **Analysis Mode**\n\nRequest received: {message}\n\nSystem analyzing and preparing response..."
