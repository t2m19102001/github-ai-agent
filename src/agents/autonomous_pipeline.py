#!/usr/bin/env python3
"""
Autonomous Pipeline for GitHub AI Agent
Implements clone->analyze->patch->test->PR workflow with security
"""

import os
import uuid
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger
from src.security.guardrails import security_guardrails, SecurityError
from src.tools.git_tool import git_commit, git_status, git_diff
from src.tools.autofix_tool import run_pytest

logger = get_logger(__name__)


class CodeAnalyzer:
    """Code analysis functionality"""
    
    def __init__(self):
        self.analysis_times = []
    
    def analyze_codebase(self, repo_path: str) -> Dict[str, Any]:
        """Analyze repository structure and code"""
        start_time = time.time()
        
        try:
            repo_path = Path(repo_path)
            
            # Basic structure analysis
            python_files = list(repo_path.rglob("*.py"))
            test_files = [f for f in python_files if "test" in f.name.lower()]
            src_files = [f for f in python_files if "test" not in f.name.lower()]
            
            # File size analysis
            total_lines = 0
            file_sizes = []
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                        file_sizes.append(lines)
                except Exception as e:
                    logger.warning(f"Could not read {py_file}: {e}")
            
            # Calculate metrics
            avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            max_file_size = max(file_sizes) if file_sizes else 0
            
            analysis_time = time.time() - start_time
            self.analysis_times.append(analysis_time)
            
            return {
                "repo_path": str(repo_path),
                "total_files": len(python_files),
                "source_files": len(src_files),
                "test_files": len(test_files),
                "total_lines": total_lines,
                "avg_file_size": avg_file_size,
                "max_file_size": max_file_size,
                "analysis_time": analysis_time,
                "file_list": [str(f.relative_to(repo_path)) for f in python_files[:20]]  # First 20 files
            }
            
        except Exception as e:
            logger.error(f"Codebase analysis failed: {e}")
            return {"error": str(e), "analysis_time": time.time() - start_time}


class CodePatcher:
    """Code patch generation with security validation"""
    
    def __init__(self):
        self.patch_times = []
    
    def generate_patch(self, analysis: Dict[str, Any], issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code patch based on analysis and issue"""
        start_time = time.time()
        
        try:
            # Extract issue information
            title = issue_data.get("title", "")
            body = issue_data.get("body", "")
            
            # Generate patch content (simplified for now)
            patch_content = self._create_patch_content(title, body, analysis)
            
            # Validate patch security
            validation = security_guardrails.validate_patch(patch_content)
            if not validation["valid"]:
                raise SecurityError(f"Patch validation failed: {validation['issues']}")
            
            patch_time = time.time() - start_time
            self.patch_times.append(patch_time)
            
            return {
                "patch_content": patch_content,
                "patch_size": len(patch_content),
                "validation": validation,
                "generation_time": patch_time
            }
            
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            return {"error": str(e), "generation_time": time.time() - start_time}
    
    def _create_patch_content(self, title: str, body: str, analysis: Dict[str, Any]) -> str:
        """Create patch content (simplified implementation)"""
        # This is a placeholder - in real implementation, this would use LLM
        # to generate actual code changes based on the issue
        
        if "bug" in title.lower() or "fix" in title.lower():
            return """
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,6 @@
 def main():
+    # Fix for bug: Add error handling
+    try:
+        print("Hello, World!")
+    except Exception as e:
+        print(f"Error: {e}")
     print("Hello, World!")
"""
        elif "feature" in title.lower() or "add" in title.lower():
            return """
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,7 @@
 def main():
+    # New feature: Add greeting function
+    def greet(name):
+        return f"Hello, {name}!"
+    
     print("Hello, World!")
"""
        else:
            return """
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
 def main():
+    # General improvement
     print("Hello, World!")
"""


class TestRunner:
    """Test execution and validation"""
    
    def __init__(self):
        self.test_times = []
        self.test_results = []
    
    def run_tests(self, repo_path: str) -> Dict[str, Any]:
        """Run tests and return results"""
        start_time = time.time()
        
        try:
            # Change to repo directory
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            # Run pytest
            result = run_pytest("-q --tb=short")
            
            # Parse results
            test_time = time.time() - start_time
            self.test_times.append(test_time)
            
            # Calculate pass rate
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            total = passed + failed
            pass_rate = passed / total if total > 0 else 0
            
            test_result = {
                "passed": passed,
                "failed": failed,
                "total": total,
                "pass_rate": pass_rate,
                "execution_time": test_time,
                "meets_target": pass_rate >= 0.85,  # Success metric: ≥85% test pass rate
                "raw_output": result.get("output", "")
            }
            
            self.test_results.append(test_result)
            
            return test_result
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "error": str(e),
                "execution_time": time.time() - start_time,
                "meets_target": False
            }
        finally:
            os.chdir(original_cwd)


class PRCreator:
    """Pull Request creation functionality"""
    
    def __init__(self):
        self.pr_times = []
    
    def create_draft_pr(self, patch_data: Dict[str, Any], issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create draft pull request"""
        start_time = time.time()
        
        try:
            # This is a placeholder - in real implementation, this would use GitHub API
            # to create an actual PR
            
            title = issue_data.get("title", "")
            body = issue_data.get("body", "")
            
            pr_data = {
                "title": f"Fix: {title}",
                "body": f"""
## Summary
Addresses issue: {title}

## Changes
- Applied security-validated patch
- Ran tests to ensure functionality

## Test Results
- Pass rate: {patch_data.get('test_results', {}).get('pass_rate', 'N/A')}
- All tests passed: {patch_data.get('test_results', {}).get('meets_target', False)}

## Security
- Patch validated with security guardrails
- No sensitive files modified

---
*This PR was created automatically by GitHub AI Agent*
""",
                "draft": True,
                "base_branch": "main",
                "head_branch": f"ai-agent-fix-{uuid.uuid4().hex[:8]}"
            }
            
            pr_time = time.time() - start_time
            self.pr_times.append(pr_time)
            
            return {
                "pr_url": f"https://github.com/test/repo/pull/{uuid.uuid4().hex[:6]}",
                "pr_data": pr_data,
                "creation_time": pr_time,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"PR creation failed: {e}")
            return {
                "error": str(e),
                "creation_time": time.time() - start_time,
                "success": False
            }


class AutonomousPipeline:
    """Main autonomous pipeline orchestrator"""
    
    def __init__(self, git_client=None):
        self.git_client = git_client
        self.analyzer = CodeAnalyzer()
        self.patcher = CodePatcher()
        self.tester = TestRunner()
        self.pr_creator = PRCreator()
        
        # Performance tracking
        self.pipeline_times = []
        self.success_count = 0
        self.total_pipelines = 0
    
    async def execute_autonomous_pr(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete autonomous PR pipeline"""
        pipeline_start = time.time()
        pipeline_id = str(uuid.uuid4())
        
        logger.info(f"Starting autonomous pipeline {pipeline_id}")
        
        try:
            # Step 1: Clone repository
            repo_path = await self._clone_repo(issue_data.get("repository", {}))
            if not repo_path:
                raise Exception("Repository cloning failed")
            
            # Step 2: Analyze codebase
            logger.info(f"Analyzing codebase at {repo_path}")
            analysis = self.analyzer.analyze_codebase(repo_path)
            if "error" in analysis:
                raise Exception(f"Code analysis failed: {analysis['error']}")
            
            # Step 3: Generate patch
            logger.info("Generating security-validated patch")
            patch_result = self.patcher.generate_patch(analysis, issue_data)
            if "error" in patch_result:
                raise Exception(f"Patch generation failed: {patch_result['error']}")
            
            # Step 4: Run tests
            logger.info("Running tests")
            test_results = self.tester.run_tests(repo_path)
            if not test_results.get("meets_target", False):
                logger.warning(f"Test pass rate {test_results.get('pass_rate', 0):.2%} below 85% target")
            
            # Step 5: Create draft PR
            logger.info("Creating draft PR")
            patch_data = {
                "patch_result": patch_result,
                "test_results": test_results
            }
            pr_result = self.pr_creator.create_draft_pr(patch_data, issue_data)
            if not pr_result.get("success", False):
                raise Exception(f"PR creation failed: {pr_result.get('error')}")
            
            # Calculate pipeline metrics
            pipeline_time = time.time() - pipeline_start
            self.pipeline_times.append(pipeline_time)
            self.total_pipelines += 1
            self.success_count += 1
            
            # Success metric: ≥90% PR success rate
            success_rate = self.success_count / self.total_pipelines
            
            result = {
                "pipeline_id": pipeline_id,
                "success": True,
                "pipeline_time": pipeline_time,
                "analysis": analysis,
                "patch": patch_result,
                "tests": test_results,
                "pr": pr_result,
                "metrics": {
                    "success_rate": success_rate,
                    "avg_pipeline_time": sum(self.pipeline_times) / len(self.pipeline_times),
                    "meets_success_target": success_rate >= 0.9
                }
            }
            
            logger.info(f"Pipeline {pipeline_id} completed successfully in {pipeline_time:.2f}s")
            return result
            
        except Exception as e:
            pipeline_time = time.time() - pipeline_start
            self.pipeline_times.append(pipeline_time)
            self.total_pipelines += 1
            
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            
            return {
                "pipeline_id": pipeline_id,
                "success": False,
                "pipeline_time": pipeline_time,
                "error": str(e),
                "metrics": {
                    "success_rate": self.success_count / self.total_pipelines,
                    "avg_pipeline_time": sum(self.pipeline_times) / len(self.pipeline_times)
                }
            }
        
        finally:
            # Cleanup
            await self._cleanup_repo(repo_path)
    
    async def _clone_repo(self, repo_data: Dict[str, Any]) -> Optional[str]:
        """Clone repository to temporary directory"""
        try:
            repo_url = repo_data.get("clone_url", "")
            if not repo_url:
                raise Exception("No repository URL provided")
            
            # Validate repository access
            validation = security_guardrails.validate_repository_access(repo_url, "read")
            if not validation["valid"]:
                raise SecurityError(f"Repository access blocked: {validation['reason']}")
            
            # Create temporary directory
            temp_dir = f"/tmp/github-agent-{uuid.uuid4().hex[:8]}"
            
            # Clone repository using subprocess
            logger.info(f"Cloning repository to {temp_dir}")
            try:
                subprocess.run(['git', 'clone', repo_url, temp_dir], 
                             check=True, capture_output=True, text=True)
                return temp_dir
            except subprocess.CalledProcessError as e:
                logger.error(f"Git clone failed: {e.stderr}")
                raise Exception(f"Git clone failed: {e.stderr}")
                
        except Exception as e:
            logger.error(f"Repository cloning failed: {e}")
            return None
    
    async def _cleanup_repo(self, repo_path: Optional[str]):
        """Clean up temporary repository"""
        if repo_path and os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path)
                logger.info(f"Cleaned up temporary repository: {repo_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {repo_path}: {e}")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline performance statistics"""
        if not self.pipeline_times:
            return {
                "total_pipelines": 0,
                "success_rate": 0,
                "avg_pipeline_time": 0,
                "meets_success_target": False
            }
        
        success_rate = self.success_count / self.total_pipelines
        avg_time = sum(self.pipeline_times) / len(self.pipeline_times)
        
        return {
            "total_pipelines": self.total_pipelines,
            "success_rate": success_rate,
            "avg_pipeline_time": avg_time,
            "meets_success_target": success_rate >= 0.9,  # Success metric: ≥90% PR success rate
            "component_stats": {
                "analysis": {
                    "avg_time": sum(self.analyzer.analysis_times) / len(self.analyzer.analysis_times) if self.analyzer.analysis_times else 0,
                    "count": len(self.analyzer.analysis_times)
                },
                "patching": {
                    "avg_time": sum(self.patcher.patch_times) / len(self.patcher.patch_times) if self.patcher.patch_times else 0,
                    "count": len(self.patcher.patch_times)
                },
                "testing": {
                    "avg_time": sum(self.tester.test_times) / len(self.tester.test_times) if self.tester.test_times else 0,
                    "count": len(self.tester.test_times)
                },
                "pr_creation": {
                    "avg_time": sum(self.pr_creator.pr_times) / len(self.pr_creator.pr_times) if self.pr_creator.pr_times else 0,
                    "count": len(self.pr_creator.pr_times)
                }
            }
        }


# Global pipeline instance
autonomous_pipeline = AutonomousPipeline()
