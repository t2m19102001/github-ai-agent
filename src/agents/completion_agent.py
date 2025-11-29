#!/usr/bin/env python3
"""
Code Completion Agent
Provides intelligent code suggestions like GitHub Copilot
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import re
from src.agents.base import Agent
from src.llm.groq import GroqProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeCompletionAgent(Agent):
    """
    AI Agent for code completion and suggestions
    
    Features:
    - Context-aware code suggestions
    - Multi-line completions
    - Function/method suggestions
    - Variable name suggestions
    - Import suggestions
    """
    
    def __init__(self, llm_provider: Optional[GroqProvider] = None):
        """
        Initialize Code Completion Agent
        
        Args:
            llm_provider: LLM provider (default: GroqProvider)
        """
        super().__init__(
            name="CodeCompletionAgent",
            description="Provides intelligent code completion and suggestions"
        )
        
        self.llm = llm_provider or GroqProvider()
        logger.info("✅ CodeCompletionAgent initialized")
    
    def think(self, prompt: str) -> str:
        """Analyze and generate completion"""
        messages = [{"role": "user", "content": prompt}]
        result = self.llm.call(messages)
        return result if result else ""
    
    def act(self, action: str) -> bool:
        """Execute an action"""
        logger.info(f"Executing action: {action}")
        return True
    
    def complete(
        self,
        code_before: str,
        code_after: str = "",
        file_path: str = "",
        language: str = "python",
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate code completions
        
        Args:
            code_before: Code before cursor
            code_after: Code after cursor (optional)
            file_path: File path for context (optional)
            language: Programming language
            max_suggestions: Max number of suggestions
            
        Returns:
            List of completion suggestions with confidence scores
        """
        logger.info(f"🔮 Generating completions for {language}")
        
        try:
            # Build context
            context = self._build_context(code_before, code_after, file_path, language)
            
            # Get current line and detect completion type
            current_line = self._get_current_line(code_before)
            completion_type = self._detect_completion_type(current_line, code_before)
            
            logger.info(f"Completion type: {completion_type}")
            
            # Generate suggestions
            suggestions = self._generate_suggestions(
                context,
                current_line,
                completion_type,
                language,
                max_suggestions
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Error generating completions: {e}")
            return []
    
    def _build_context(
        self,
        code_before: str,
        code_after: str,
        file_path: str,
        language: str
    ) -> Dict[str, Any]:
        """Build context for completion"""
        
        # Extract imports
        imports = self._extract_imports(code_before, language)
        
        # Extract function/class definitions
        definitions = self._extract_definitions(code_before, language)
        
        # Get nearby context (last 20 lines)
        lines_before = code_before.split('\n')
        context_lines = lines_before[-20:] if len(lines_before) > 20 else lines_before
        
        # Detect indentation level
        current_line = lines_before[-1] if lines_before else ""
        indent_level = len(current_line) - len(current_line.lstrip())
        
        return {
            'imports': imports,
            'definitions': definitions,
            'recent_code': '\n'.join(context_lines),
            'code_after': code_after[:500] if code_after else "",  # Limit context
            'indent_level': indent_level,
            'file_path': file_path,
            'language': language
        }
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        if language == "python":
            # Match: import X, from X import Y
            import_pattern = r'^(?:from\s+[\w.]+\s+)?import\s+.+$'
            for line in code.split('\n'):
                if re.match(import_pattern, line.strip()):
                    imports.append(line.strip())
        
        elif language in ["javascript", "typescript"]:
            # Match: import X from 'Y', const X = require('Y')
            patterns = [
                r'^import\s+.+\s+from\s+["\'].+["\']',
                r'^const\s+.+\s*=\s*require\(["\'].+["\']\)'
            ]
            for line in code.split('\n'):
                for pattern in patterns:
                    if re.match(pattern, line.strip()):
                        imports.append(line.strip())
                        break
        
        return imports[:10]  # Limit to 10 most recent
    
    def _extract_definitions(self, code: str, language: str) -> List[str]:
        """Extract function/class definitions"""
        definitions = []
        
        if language == "python":
            # Match: def function_name, class ClassName
            patterns = [
                r'^def\s+(\w+)\s*\(',
                r'^class\s+(\w+)[\s:(]'
            ]
        elif language in ["javascript", "typescript"]:
            patterns = [
                r'^function\s+(\w+)\s*\(',
                r'^class\s+(\w+)[\s{]',
                r'^const\s+(\w+)\s*=\s*\(',
                r'^const\s+(\w+)\s*=\s*async\s*\('
            ]
        else:
            return []
        
        for line in code.split('\n'):
            stripped = line.strip()
            for pattern in patterns:
                match = re.match(pattern, stripped)
                if match:
                    definitions.append(match.group(1))
                    break
        
        return definitions[-20:]  # Last 20 definitions
    
    def _get_current_line(self, code_before: str) -> str:
        """Get the current line being edited"""
        lines = code_before.split('\n')
        return lines[-1] if lines else ""
    
    def _detect_completion_type(self, current_line: str, code_before: str) -> str:
        """
        Detect what type of completion is needed
        
        Types:
        - function: Completing a function definition
        - method: Completing a method call
        - variable: Completing a variable name
        - import: Completing an import statement
        - class: Completing a class definition
        - comment: Completing a comment/docstring
        - line: Completing current line
        """
        stripped = current_line.strip()
        
        # Import
        if stripped.startswith('import ') or stripped.startswith('from '):
            return 'import'
        
        # Function definition
        if stripped.startswith('def ') or 'function ' in stripped:
            return 'function'
        
        # Class definition
        if stripped.startswith('class '):
            return 'class'
        
        # Comment/docstring
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            return 'comment'
        
        # Method call (has dot notation)
        if '.' in stripped and not stripped.endswith('.'):
            return 'method'
        
        # Variable assignment
        if '=' in stripped and not stripped.endswith('='):
            return 'variable'
        
        # Default: line completion
        return 'line'
    
    def _generate_suggestions(
        self,
        context: Dict[str, Any],
        current_line: str,
        completion_type: str,
        language: str,
        max_suggestions: int
    ) -> List[Dict[str, Any]]:
        """Generate completion suggestions using AI"""
        
        # Build prompt based on completion type
        prompt = self._build_completion_prompt(
            context,
            current_line,
            completion_type,
            language
        )
        
        # Get AI suggestions
        logger.info("🤖 Requesting AI completions...")
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.call(messages)
        
        if not response:
            return []
        
        # Parse suggestions from response
        suggestions = self._parse_suggestions(response, current_line, max_suggestions)
        
        logger.info(f"✅ Generated {len(suggestions)} suggestions")
        return suggestions
    
    def _build_completion_prompt(
        self,
        context: Dict[str, Any],
        current_line: str,
        completion_type: str,
        language: str
    ) -> str:
        """Build prompt for AI completion"""
        
        prompt_parts = [
            f"You are an expert {language} code completion assistant like GitHub Copilot.",
            f"\nLanguage: {language}",
            f"Completion type: {completion_type}",
        ]
        
        # Add imports if available
        if context['imports']:
            prompt_parts.append(f"\nImports:\n" + "\n".join(context['imports']))
        
        # Add recent code context
        if context['recent_code']:
            prompt_parts.append(f"\nRecent code:\n```{language}\n{context['recent_code']}\n```")
        
        # Add current line
        prompt_parts.append(f"\nCurrent line (incomplete):\n```{language}\n{current_line}")
        
        # Add instructions based on type
        if completion_type == 'function':
            instructions = "Complete the function definition. Include the full function body with proper logic."
        elif completion_type == 'method':
            instructions = "Complete the method call with appropriate arguments and continuation."
        elif completion_type == 'variable':
            instructions = "Complete the variable assignment with appropriate value."
        elif completion_type == 'import':
            instructions = "Complete the import statement with common modules/packages."
        elif completion_type == 'class':
            instructions = "Complete the class definition with __init__ and basic methods."
        elif completion_type == 'comment':
            instructions = "Complete the comment or docstring with helpful description."
        else:
            instructions = "Complete the current line with the most likely continuation."
        
        prompt_parts.append(f"\n{instructions}")
        prompt_parts.append(f"\nProvide 3-5 different completion options, each on a new line.")
        prompt_parts.append("Format: OPTION <number>: <completion>")
        prompt_parts.append("Only provide the completion code, no explanations.")
        
        return "\n".join(prompt_parts)
    
    def _parse_suggestions(
        self,
        response: str,
        current_line: str,
        max_suggestions: int
    ) -> List[Dict[str, Any]]:
        """Parse AI response into structured suggestions"""
        
        suggestions = []
        lines = response.split('\n')
        
        # Try to extract formatted options
        for line in lines:
            line = line.strip()
            
            # Match: OPTION 1: code
            match = re.match(r'OPTION\s+\d+:\s*(.+)', line, re.IGNORECASE)
            if match:
                completion = match.group(1).strip()
                # Remove code fences if present
                completion = re.sub(r'^```\w*\n?', '', completion)
                completion = re.sub(r'\n?```$', '', completion)
                
                suggestions.append({
                    'text': completion,
                    'display_text': completion[:100] + '...' if len(completion) > 100 else completion,
                    'confidence': 0.9 - (len(suggestions) * 0.1),  # Decreasing confidence
                    'type': 'ai_generated'
                })
                
                if len(suggestions) >= max_suggestions:
                    break
        
        # If no structured options found, try to extract code blocks
        if not suggestions:
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', response, re.DOTALL)
            for block in code_blocks[:max_suggestions]:
                block = block.strip()
                if block:
                    suggestions.append({
                        'text': block,
                        'display_text': block[:100] + '...' if len(block) > 100 else block,
                        'confidence': 0.8,
                        'type': 'code_block'
                    })
        
        # If still no suggestions, use the whole response
        if not suggestions and response:
            cleaned = response.strip()
            if cleaned:
                suggestions.append({
                    'text': cleaned,
                    'display_text': cleaned[:100] + '...' if len(cleaned) > 100 else cleaned,
                    'confidence': 0.7,
                    'type': 'raw_response'
                })
        
        return suggestions
    
    def complete_inline(
        self,
        file_content: str,
        cursor_line: int,
        cursor_column: int,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Complete code at specific cursor position
        
        Args:
            file_content: Full file content
            cursor_line: Line number (0-indexed)
            cursor_column: Column number (0-indexed)
            language: Programming language
            
        Returns:
            List of completion suggestions
        """
        lines = file_content.split('\n')
        
        if cursor_line >= len(lines):
            return []
        
        # Get code before and after cursor
        code_before_lines = lines[:cursor_line]
        current_line = lines[cursor_line]
        code_after_lines = lines[cursor_line + 1:]
        
        code_before = '\n'.join(code_before_lines) + '\n' + current_line[:cursor_column]
        code_after = current_line[cursor_column:] + '\n' + '\n'.join(code_after_lines)
        
        return self.complete(
            code_before=code_before,
            code_after=code_after,
            language=language
        )


if __name__ == "__main__":
    # Test the agent
    print("\n" + "="*70)
    print("🧪 Testing Code Completion Agent")
    print("="*70 + "\n")
    
    agent = CodeCompletionAgent()
    
    # Test 1: Function completion
    print("Test 1: Function Completion")
    print("-" * 70)
    code_before = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total

def calculate_
"""
    
    suggestions = agent.complete(code_before, language="python")
    print(f"Generated {len(suggestions)} suggestions:")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['display_text']} (confidence: {sug['confidence']:.2f})")
    
    # Test 2: Method call completion
    print("\n\nTest 2: Method Call Completion")
    print("-" * 70)
    code_before = """
import requests

response = requests.get('https://api.example.com/data')
data = response.
"""
    
    suggestions = agent.complete(code_before, language="python")
    print(f"Generated {len(suggestions)} suggestions:")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['display_text']} (confidence: {sug['confidence']:.2f})")
