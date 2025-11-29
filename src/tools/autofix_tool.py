#!/usr/bin/env python3
"""
Auto Test & Fix Tool
Automatically runs tests, detects failures, and fixes code using AI agent
"""

import subprocess
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_pytest(test_args: str = "-q") -> Dict[str, Any]:
    """
    Run pytest and capture output
    
    Args:
        test_args: pytest arguments (default: "-q" for quiet mode)
    
    Returns:
        Dict with test results
    """
    try:
        result = subprocess.run(
            ["pytest", test_args],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return {
            "success": success,
            "returncode": result.returncode,
            "output": output,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Test timeout (60s)")
        return {
            "success": False,
            "error": "Test execution timeout",
            "output": "Tests took too long to run (>60s)"
        }
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "output": f"Failed to run tests: {e}"
        }


def auto_fix(code: str, agent=None, max_iterations: int = 5) -> Dict[str, Any]:
    """
    Automatically test and fix code in a loop
    
    Args:
        code: Code to test and fix
        agent: AI agent for fixing (CodeChatAgent instance)
        max_iterations: Maximum fix attempts (default: 5)
    
    Returns:
        Dict with final code and iteration results
    """
    if agent is None:
        return {
            "success": False,
            "error": "Agent required for auto-fix",
            "code": code
        }
    
    current_code = code
    iterations = []
    
    logger.info(f"🔄 Starting auto-fix loop (max {max_iterations} iterations)")
    
    for i in range(max_iterations):
        iteration_num = i + 1
        logger.info(f"🔄 Iteration {iteration_num}/{max_iterations}")
        
        # Run tests
        result = run_pytest("-q")
        
        if result["success"]:
            # Tests passed!
            logger.info(f"✅ Tests passed on iteration {iteration_num}")
            iterations.append({
                "iteration": iteration_num,
                "success": True,
                "message": "Tests passed",
                "output": result["output"]
            })
            return {
                "success": True,
                "code": current_code,
                "iterations": iterations,
                "fixed_on_iteration": iteration_num,
                "message": f"Code fixed successfully in {iteration_num} iteration(s)"
            }
        
        # Tests failed - ask agent to fix
        error = result["stdout"] + result["stderr"]
        logger.warning(f"❌ Tests failed on iteration {iteration_num}")
        
        # Build fix prompt
        fix_prompt = f"""Fix this code based on test error:

Error:
{error}

Code:
{current_code}

Please provide the fixed code."""
        
        try:
            # Get fix from agent
            fixed_code = agent.chat(fix_prompt)
            
            # Extract code from response (simple extraction)
            # Assumes agent returns code in markdown code blocks
            if "```python" in fixed_code:
                parts = fixed_code.split("```python")
                if len(parts) > 1:
                    code_part = parts[1].split("```")[0]
                    current_code = code_part.strip()
            elif "```" in fixed_code:
                parts = fixed_code.split("```")
                if len(parts) > 2:
                    current_code = parts[1].strip()
            else:
                # No code blocks, use full response
                current_code = fixed_code.strip()
            
            iterations.append({
                "iteration": iteration_num,
                "success": False,
                "error": error[:500],  # First 500 chars
                "fix_attempted": True
            })
            
            logger.info(f"🔧 Applied fix from agent, retrying...")
            
        except Exception as e:
            logger.error(f"❌ Failed to get fix from agent: {e}")
            iterations.append({
                "iteration": iteration_num,
                "success": False,
                "error": str(e),
                "fix_attempted": False
            })
            break
    
    # Max iterations reached without success
    logger.error(f"❌ Failed to fix code after {max_iterations} iterations")
    return {
        "success": False,
        "code": current_code,
        "iterations": iterations,
        "message": f"Failed to fix code after {max_iterations} attempts",
        "final_error": iterations[-1].get("error") if iterations else "Unknown error"
    }


# Tool wrapper for agent integration
class AutoFixTool:
    """Tool for auto test & fix loop"""
    
    name = "auto_fix"
    description = "Automatically test code and fix errors in a loop (max 5 iterations)"
    
    def __init__(self, agent=None):
        self.agent = agent
    
    def execute(self, code: str, max_iterations: int = 5) -> str:
        """Execute auto-fix"""
        result = auto_fix(code, agent=self.agent, max_iterations=max_iterations)
        
        if result["success"]:
            return f"✅ {result['message']}\n\nFixed code:\n{result['code']}"
        else:
            return f"❌ {result['message']}\n\nLast error:\n{result.get('final_error', 'Unknown')}"


class PytestTool:
    """Tool for running pytest"""
    
    name = "run_pytest"
    description = "Run pytest with specified arguments"
    
    def execute(self, args: str = "-q") -> str:
        """Execute pytest"""
        result = run_pytest(args)
        
        if result["success"]:
            return f"✅ Tests passed\n\n{result['output']}"
        else:
            return f"❌ Tests failed\n\n{result['output']}"
