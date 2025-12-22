"""
Professional Developer Agent - Acts as a full-stack programmer
Can read code, write code, review, test, document like a professional developer
"""

from src.agents.base import Agent, LLMProvider
from src.utils.logger import get_logger
import re
import json
from typing import Dict, List, Optional

logger = get_logger(__name__)


class ProfessionalDeveloperAgent(Agent):
    """
    Advanced AI agent that acts as a professional developer.
    Capabilities:
    - Code Reading & Analysis
    - Code Writing & Implementation
    - Code Review & Refactoring
    - Testing & Quality Assurance
    - Documentation Generation
    - Debugging & Issue Resolution
    - Architecture Design
    - Performance Optimization
    """

    def __init__(self, llm_provider: LLMProvider):
        super().__init__(
            name="Professional Developer",
            description="Full-stack professional developer AI"
        )
        self.llm_provider = llm_provider
        self.register_tools()
        logger.info("✅ ProfessionalDeveloperAgent initialized")

    def register_tools(self):
        """Register developer tools"""
        from src.tools.developer_tools import (
            CodeAnalyzerTool,
            CodeWriterTool,
            CodeReviewTool,
            TestWriterTool,
            DebuggerTool,
            DocumentationTool,
            RefactoringTool,
            ArchitectureTool
        )
        
        self.register_tool(CodeAnalyzerTool())
        self.register_tool(CodeWriterTool())
        self.register_tool(CodeReviewTool())
        self.register_tool(TestWriterTool())
        self.register_tool(DebuggerTool())
        self.register_tool(DocumentationTool())
        self.register_tool(RefactoringTool())
        self.register_tool(ArchitectureTool())
        
        logger.info("✅ All developer tools registered")

    def think(self, task: str) -> str:
        """Think about a task like a professional developer"""
        prompt = f"As a professional developer, how would you approach this: {task}"
        return self.llm_provider.call(prompt)
    
    def act(self, action: str, **kwargs) -> Dict:
        """Execute an action based on the request"""
        actions = {
            "analyze": self.read_and_analyze,
            "write": self.write_complete_solution,
            "review": self.professional_review,
            "refactor": self.refactor_code,
            "debug": self.debug_issue,
            "architecture": self.design_architecture,
            "docs": self.generate_professional_docs,
            "optimize": self.optimize_performance,
            "explain": self.code_explanation,
            "implement": self.implement_feature
        }
        
        if action not in actions:
            return {"error": f"Unknown action: {action}"}
        
        return actions[action](**kwargs)

    def read_and_analyze(self, code: str, context: str = "") -> Dict:
        """
        Read and deeply analyze code
        Returns: Analysis with code structure, patterns, potential issues
        """
        prompt = f"""
As a professional developer, analyze this code comprehensively:

CODE:
```
{code}
```

Context: {context if context else "General analysis"}

Provide detailed analysis including:
1. Code Structure: Functions, classes, imports, dependencies
2. Code Patterns: Design patterns, anti-patterns detected
3. Code Quality: Readability, maintainability, best practices
4. Potential Issues: Bugs, security issues, performance concerns
5. Improvements: Specific suggestions for improvement
6. Dependencies: External packages and their usage
7. Complexity: Time/space complexity analysis

Be thorough and professional.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "analysis": response,
            "status": "success",
            "type": "code_analysis"
        }

    def write_complete_solution(self, requirements: str, language: str = "python", 
                                 context: str = "") -> Dict:
        """
        Write complete, production-ready code based on requirements
        """
        prompt = f"""
You are a senior professional developer. Write production-ready code.

REQUIREMENTS:
{requirements}

LANGUAGE: {language}
CONTEXT: {context if context else "General implementation"}

Requirements:
1. Clean, readable, well-structured code
2. Follow industry best practices and conventions
3. Include comprehensive error handling
4. Add type hints / type annotations
5. Include inline comments for complex logic
6. Structure for scalability and maintainability
7. Include logging statements
8. Consider edge cases
9. Add docstrings
10. Follow SOLID principles

Provide:
- Complete implementation
- Explanation of design choices
- Usage examples
- Potential improvements

Make it production-quality code that a professional would write.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "code": response,
            "status": "success",
            "type": "code_writing",
            "language": language
        }

    def professional_review(self, code: str, review_type: str = "comprehensive") -> Dict:
        """
        Professional code review like a senior developer
        review_type: comprehensive, security, performance, style, architecture
        """
        review_types = {
            "comprehensive": "Overall code quality, structure, best practices",
            "security": "Security vulnerabilities, data protection, authentication",
            "performance": "Performance bottlenecks, optimization opportunities",
            "style": "Code style, consistency, readability",
            "architecture": "System design, patterns, scalability"
        }
        
        focus = review_types.get(review_type, review_types["comprehensive"])
        
        prompt = f"""
As a senior professional developer with 10+ years experience, conduct a thorough code review.

CODE TO REVIEW:
```
{code}
```

REVIEW FOCUS: {focus}

Provide professional review including:

1. **Overall Assessment**: Grade (A-F) and summary
2. **Strengths**: What's done well
3. **Issues Found**: Problems categorized by severity
4. **Security Concerns**: Any vulnerabilities
5. **Performance Issues**: Optimization opportunities
6. **Best Practices**: Violations and improvements
7. **Maintainability**: Long-term code health
8. **Testing**: Test coverage suggestions
9. **Documentation**: Docs needed
10. **Specific Recommendations**: Actionable fixes with code examples

Be professional, constructive, and specific with examples.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "review": response,
            "status": "success",
            "type": "professional_review",
            "review_type": review_type
        }

    def refactor_code(self, code: str, goals: str = "") -> Dict:
        """
        Professional code refactoring
        goals: What to improve (readability, performance, design, etc.)
        """
        prompt = f"""
As a professional developer, refactor this code professionally.

ORIGINAL CODE:
```
{code}
```

REFACTORING GOALS: {goals if goals else "Improve overall quality, readability, and maintainability"}

Provide:
1. **Refactored Code**: Clean, professional version
2. **Changes Made**: Detailed list of improvements
3. **Before/After Comparison**: Show improvements
4. **Rationale**: Why each change was made
5. **Benefits**: Performance, readability, maintainability gains
6. **Breaking Changes**: Any API changes needed
7. **Migration Path**: How to migrate if needed

Make it production-quality and follow industry best practices.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "refactored_code": response,
            "status": "success",
            "type": "refactoring",
            "goals": goals
        }

    def debug_issue(self, error: str, code: str, context: str = "") -> Dict:
        """
        Professional debugging - identify root cause and fix
        """
        prompt = f"""
As a professional debugger, analyze and fix this issue.

ERROR/ISSUE:
{error}

RELATED CODE:
```
{code}
```

CONTEXT: {context if context else "General debugging"}

Provide:
1. **Root Cause Analysis**: What's really causing the issue
2. **Issue Severity**: Critical/High/Medium/Low
3. **Reproduction Steps**: How to reproduce (if applicable)
4. **Solution**: Fixed code
5. **Alternative Fixes**: Other possible solutions
6. **Prevention**: How to prevent similar issues
7. **Testing**: How to verify the fix works
8. **Related Issues**: Similar issues to watch for

Be thorough and professional in your analysis.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "debug_report": response,
            "status": "success",
            "type": "debugging"
        }

    def design_architecture(self, project: str, requirements: str, 
                            scale: str = "medium") -> Dict:
        """
        Design system architecture like a principal architect
        scale: small, medium, large, enterprise
        """
        prompt = f"""
As a principal architect, design a professional system architecture.

PROJECT: {project}
REQUIREMENTS: {requirements}
SCALE: {scale}

Design and provide:

1. **Architecture Overview**: System design diagram (text)
2. **Components**: Detailed component breakdown
3. **Technology Stack**: Recommended technologies with rationale
4. **Data Flow**: How data flows through system
5. **Database Design**: Schema, relationships, scalability
6. **API Design**: REST/GraphQL endpoints and contracts
7. **Security Architecture**: Authentication, authorization, data protection
8. **Scalability**: How to scale each component
9. **Deployment**: Infrastructure and deployment strategy
10. **Monitoring**: Logging, metrics, alerting
11. **Code Structure**: Recommended folder structure and organization
12. **Performance**: Optimization strategies
13. **Disaster Recovery**: Backup and recovery strategy
14. **Cost Optimization**: Efficiency improvements

Provide professional-grade architecture suitable for production systems.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "architecture": response,
            "status": "success",
            "type": "architecture_design",
            "scale": scale
        }

    def generate_professional_docs(self, code: str, project_type: str = "general") -> Dict:
        """
        Generate professional documentation
        """
        prompt = f"""
As a professional technical writer, generate comprehensive documentation.

CODE/PROJECT:
```
{code}
```

PROJECT TYPE: {project_type}

Generate professional documentation including:

1. **Project Overview**: What it does, key features
2. **Installation Guide**: Step-by-step setup
3. **Configuration**: All configuration options
4. **API Documentation**: Complete API reference
5. **Usage Examples**: Real-world usage examples
6. **Architecture**: System design explanation
7. **Database Schema**: If applicable
8. **Security**: Security considerations
9. **Deployment**: Deployment instructions
10. **Troubleshooting**: Common issues and solutions
11. **Contributing**: Contribution guidelines
12. **FAQ**: Frequently asked questions
13. **Changelog**: Version history format
14. **License**: License considerations

Make it professional, clear, and comprehensive.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "documentation": response,
            "status": "success",
            "type": "documentation"
        }

    def optimize_performance(self, code: str, bottleneck: str = "") -> Dict:
        """
        Performance optimization by professional
        """
        prompt = f"""
As a performance optimization expert, optimize this code.

CODE:
```
{code}
```

KNOWN BOTTLENECK: {bottleneck if bottleneck else "Identify and optimize all bottlenecks"}

Provide:
1. **Performance Analysis**: Current state analysis
2. **Bottlenecks Identified**: What's slow and why
3. **Optimization Strategies**: Multiple approaches
4. **Optimized Code**: Best solution implemented
5. **Benchmark**: Expected performance improvement (% faster)
6. **Tradeoffs**: Any tradeoffs made
7. **Memory Profile**: Memory usage analysis
8. **Scalability**: How it scales
9. **Best Practices**: Performance patterns used
10. **Monitoring**: How to monitor performance

Be specific with numbers and benchmarks where possible.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "optimization_report": response,
            "status": "success",
            "type": "performance_optimization"
        }

    def code_explanation(self, code: str, detail_level: str = "comprehensive") -> Dict:
        """
        Explain code in detail like a senior developer teaching
        detail_level: basic, intermediate, comprehensive, expert
        """
        prompt = f"""
As a senior developer explaining code to a colleague, explain this code thoroughly.

CODE:
```
{code}
```

DETAIL LEVEL: {detail_level}

Explain:
1. **What**: What does this code do
2. **How**: Step-by-step how it works
3. **Why**: Why it's written this way
4. **Patterns**: Design patterns used
5. **Dependencies**: What it depends on
6. **Edge Cases**: Edge cases handled
7. **Potential Issues**: Potential problems
8. **Alternatives**: Alternative approaches
9. **Performance**: Performance characteristics
10. **Usage**: How to use it

Be thorough and make it educational.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "explanation": response,
            "status": "success",
            "type": "code_explanation",
            "detail_level": detail_level
        }

    def implement_feature(self, feature_spec: str, existing_code: str = "", 
                         language: str = "python") -> Dict:
        """
        Implement a complete feature professionally
        """
        prompt = f"""
As a professional developer, implement this feature.

FEATURE SPECIFICATION:
{feature_spec}

EXISTING CODE (if any):
{existing_code if existing_code else "No existing code - start fresh"}

LANGUAGE: {language}

Provide:
1. **Implementation**: Complete, production-ready code
2. **Integration Points**: How to integrate with existing code
3. **Tests**: Comprehensive test suite
4. **Documentation**: Usage documentation
5. **Configuration**: Any configuration needed
6. **Dependencies**: New dependencies required
7. **Breaking Changes**: Any breaking changes
8. **Migration Guide**: How to migrate if needed
9. **Performance**: Performance characteristics
10. **Security**: Security considerations

Write professional, scalable, well-tested code.
"""
        response = self.llm_provider.call(prompt)
        
        return {
            "feature_implementation": response,
            "status": "success",
            "type": "feature_implementation",
            "language": language
        }
