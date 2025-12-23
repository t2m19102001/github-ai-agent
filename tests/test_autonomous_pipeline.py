#!/usr/bin/env python3
"""
Tests for Autonomous Pipeline with performance metrics
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.agents.autonomous_pipeline import (
    AutonomousPipeline,
    CodeAnalyzer,
    CodePatcher,
    TestRunner,
    PRCreator
)
from src.security.guardrails import SecurityError


class TestCodeAnalyzer:
    """Test code analysis functionality"""
    
    def setup_method(self):
        self.analyzer = CodeAnalyzer()
    
    def test_analyze_codebase_success(self):
        """Test successful codebase analysis"""
        # Create temporary directory with Python files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / "test_main.py"
            test_file.write_text("def test_example():\n    assert True\n")
            
            src_file = Path(temp_dir) / "main.py"
            src_file.write_text("def main():\n    print('Hello')\n")
            
            result = self.analyzer.analyze_codebase(temp_dir)
            
            assert result["total_files"] == 2
            assert result["source_files"] == 1
            assert result["test_files"] == 1
            assert result["total_lines"] > 0
            assert "analysis_time" in result
            assert result["analysis_time"] > 0
    
    def test_analyze_empty_directory(self):
        """Test analysis of empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.analyzer.analyze_codebase(temp_dir)
            
            assert result["total_files"] == 0
            assert result["source_files"] == 0
            assert result["test_files"] == 0
            assert result["total_lines"] == 0
    
    def test_analyze_nonexistent_directory(self):
        """Test analysis of nonexistent directory"""
        result = self.analyzer.analyze_codebase("/nonexistent/path")
        
        assert "error" in result
        assert "analysis_time" in result


class TestCodePatcher:
    """Test code patch generation"""
    
    def setup_method(self):
        self.patcher = CodePatcher()
    
    def test_generate_patch_success(self):
        """Test successful patch generation"""
        analysis = {
            "repo_path": "/test/repo",
            "total_files": 5,
            "source_files": 3,
            "test_files": 2
        }
        
        issue_data = {
            "title": "Fix bug in main function",
            "body": "The main function has an error that needs to be fixed"
        }
        
        result = self.patcher.generate_patch(analysis, issue_data)
        
        assert "patch_content" in result
        assert "patch_size" in result
        assert "validation" in result
        assert "generation_time" in result
        
        # Check patch content
        patch = result["patch_content"]
        assert "--- a/" in patch
        assert "+++ b/" in patch
        assert result["validation"]["valid"] == True
    
    def test_generate_patch_security_failure(self):
        """Test patch generation with security failure"""
        # Mock security guardrails to fail
        with patch('src.agents.autonomous_pipeline.security_guardrails.validate_patch') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "issues": ["Dangerous code detected"],
                "risk_level": "high"
            }
            
            analysis = {"repo_path": "/test/repo"}
            issue_data = {"title": "Test issue"}
            
            result = self.patcher.generate_patch(analysis, issue_data)
            
            assert "error" in result
            assert "generation_time" in result
    
    def test_generate_patch_feature_request(self):
        """Test patch generation for feature request"""
        analysis = {"repo_path": "/test/repo"}
        issue_data = {
            "title": "Add new feature",
            "body": "Need to add a new greeting function"
        }
        
        result = self.patcher.generate_patch(analysis, issue_data)
        
        assert result["validation"]["valid"] == True
        assert "def greet" in result["patch_content"]


class TestTestRunner:
    """Test execution functionality"""
    
    def setup_method(self):
        self.tester = TestRunner()
    
    @patch('src.agents.autonomous_pipeline.run_pytest')
    def test_run_tests_success(self, mock_pytest):
        """Test successful test execution"""
        mock_pytest.return_value = {
            "passed": 10,
            "failed": 0,
            "total": 10,
            "output": ".........."
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.tester.run_tests(temp_dir)
            
            assert result["passed"] == 10
            assert result["failed"] == 0
            assert result["total"] == 10
            assert result["pass_rate"] == 1.0
            assert result["meets_target"] == True  # ≥85% pass rate
            assert "execution_time" in result
    
    @patch('src.agents.autonomous_pipeline.run_pytest')
    def test_run_tests_failure(self, mock_pytest):
        """Test test execution with failures"""
        mock_pytest.return_value = {
            "passed": 7,
            "failed": 3,
            "total": 10,
            "output": ".......FFF"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.tester.run_tests(temp_dir)
            
            assert result["passed"] == 7
            assert result["failed"] == 3
            assert result["pass_rate"] == 0.7
            assert result["meets_target"] == False  # Below 85% target
    
    @patch('src.agents.autonomous_pipeline.run_pytest')
    def test_run_test_pass_rate_85_percent_target(self, mock_pytest):
        """Test test execution meets 85% pass rate target"""
        # Test exactly 85% pass rate
        mock_pytest.return_value = {
            "passed": 85,
            "failed": 15,
            "total": 100,
            "output": "." * 85 + "F" * 15
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.tester.run_tests(temp_dir)
            
            assert result["pass_rate"] == 0.85
            assert result["meets_target"] == True  # Exactly meets target


class TestPRCreator:
    """Test PR creation functionality"""
    
    def setup_method(self):
        self.pr_creator = PRCreator()
    
    def test_create_draft_pr_success(self):
        """Test successful draft PR creation"""
        patch_data = {
            "test_results": {
                "pass_rate": 0.9,
                "meets_target": True
            }
        }
        
        issue_data = {
            "title": "Fix authentication bug",
            "body": "Users cannot login with valid credentials"
        }
        
        result = self.pr_creator.create_draft_pr(patch_data, issue_data)
        
        assert result["success"] == True
        assert "pr_url" in result
        assert "pr_data" in result
        assert "creation_time" in result
        
        # Check PR data
        pr_data = result["pr_data"]
        assert "Fix: Fix authentication bug" in pr_data["title"]
        assert "draft" in pr_data
        assert "Pass rate: 90%" in pr_data["body"]
    
    def test_create_pr_with_test_failure(self):
        """Test PR creation when tests fail"""
        patch_data = {
            "test_results": {
                "pass_rate": 0.7,
                "meets_target": False
            }
        }
        
        issue_data = {"title": "Test issue"}
        
        result = self.pr_creator.create_draft_pr(patch_data, issue_data)
        
        assert result["success"] == True
        assert "Pass rate: 70%" in result["pr_data"]["body"]


class TestAutonomousPipeline:
    """Test complete autonomous pipeline"""
    
    def setup_method(self):
        self.pipeline = AutonomousPipeline()
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_success(self):
        """Test complete successful pipeline execution"""
        # Mock all components
        with patch.object(self.pipeline, '_clone_repo') as mock_clone, \
             patch.object(self.pipeline.analyzer, 'analyze_codebase') as mock_analyze, \
             patch.object(self.pipeline.patcher, 'generate_patch') as mock_patch, \
             patch.object(self.pipeline.tester, 'run_tests') as mock_test, \
             patch.object(self.pipeline.pr_creator, 'create_draft_pr') as mock_pr:
            
            # Setup mocks
            mock_clone.return_value = "/tmp/test-repo"
            mock_analyze.return_value = {
                "total_files": 5,
                "source_files": 3,
                "test_files": 2
            }
            mock_patch.return_value = {
                "patch_content": "test patch",
                "validation": {"valid": True}
            }
            mock_test.return_value = {
                "pass_rate": 0.9,
                "meets_target": True
            }
            mock_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/test/repo/pull/123"
            }
            
            # Execute pipeline
            issue_data = {
                "title": "Test issue",
                "repository": {"clone_url": "https://github.com/test/repo.git"}
            }
            
            result = await self.pipeline.execute_autonomous_pr(issue_data)
            
            # Verify success
            assert result["success"] == True
            assert "pipeline_id" in result
            assert "pipeline_time" in result
            assert "analysis" in result
            assert "patch" in result
            assert "tests" in result
            assert "pr" in result
            assert "metrics" in result
            
            # Verify metrics
            metrics = result["metrics"]
            assert metrics["success_rate"] == 1.0  # 100% success
            assert metrics["meets_success_target"] == True  # ≥90% target
    
    @pytest.mark.asyncio
    async def test_pipeline_cloning_failure(self):
        """Test pipeline failure during cloning"""
        with patch.object(self.pipeline, '_clone_repo') as mock_clone:
            mock_clone.return_value = None  # Cloning failed
            
            issue_data = {
                "title": "Test issue",
                "repository": {"clone_url": "https://github.com/test/repo.git"}
            }
            
            result = await self.pipeline.execute_autonomous_pr(issue_data)
            
            assert result["success"] == False
            assert "error" in result
            assert "Repository cloning failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_pipeline_test_failure(self):
        """Test pipeline with test failure"""
        with patch.object(self.pipeline, '_clone_repo') as mock_clone, \
             patch.object(self.pipeline.analyzer, 'analyze_codebase') as mock_analyze, \
             patch.object(self.pipeline.patcher, 'generate_patch') as mock_patch, \
             patch.object(self.pipeline.tester, 'run_tests') as mock_test, \
             patch.object(self.pipeline.pr_creator, 'create_draft_pr') as mock_pr:
            
            # Setup mocks with test failure
            mock_clone.return_value = "/tmp/test-repo"
            mock_analyze.return_value = {"total_files": 5}
            mock_patch.return_value = {
                "patch_content": "test patch",
                "validation": {"valid": True}
            }
            mock_test.return_value = {
                "pass_rate": 0.7,  # Below 85% target
                "meets_target": False
            }
            mock_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/test/repo/pull/123"
            }
            
            issue_data = {
                "title": "Test issue",
                "repository": {"clone_url": "https://github.com/test/repo.git"}
            }
            
            result = await self.pipeline.execute_autonomous_pr(issue_data)
            
            # Pipeline should still succeed even with test failure
            assert result["success"] == True
            assert result["tests"]["pass_rate"] == 0.7
            assert result["tests"]["meets_target"] == False
    
    @pytest.mark.asyncio
    async def test_pipeline_security_validation_failure(self):
        """Test pipeline failure due to security validation"""
        with patch.object(self.pipeline, '_clone_repo') as mock_clone, \
             patch.object(self.pipeline.analyzer, 'analyze_codebase') as mock_analyze, \
             patch.object(self.pipeline.patcher, 'generate_patch') as mock_patch:
            
            # Setup mocks with security failure
            mock_clone.return_value = "/tmp/test-repo"
            mock_analyze.return_value = {"total_files": 5}
            mock_patch.return_value = {
                "error": "Security validation failed",
                "generation_time": 0.1
            }
            
            issue_data = {
                "title": "Test issue",
                "repository": {"clone_url": "https://github.com/test/repo.git"}
            }
            
            result = await self.pipeline.execute_autonomous_pr(issue_data)
            
            assert result["success"] == False
            assert "Security validation failed" in result["error"]
    
    def test_pipeline_stats(self):
        """Test pipeline statistics"""
        # Add some mock pipeline times
        self.pipeline.pipeline_times = [10.5, 12.3, 9.8]
        self.pipeline.success_count = 2
        self.pipeline.total_pipelines = 3
        
        stats = self.pipeline.get_pipeline_stats()
        
        assert stats["total_pipelines"] == 3
        assert stats["success_rate"] == pytest.approx(0.667, rel=1e-2)
        assert stats["avg_pipeline_time"] == pytest.approx(10.87, rel=1e-2)
        assert stats["meets_success_target"] == False  # Below 90%
    
    def test_pipeline_stats_empty(self):
        """Test pipeline statistics with no data"""
        stats = self.pipeline.get_pipeline_stats()
        
        assert stats["total_pipelines"] == 0
        assert stats["success_rate"] == 0
        assert stats["avg_pipeline_time"] == 0
        assert stats["meets_success_target"] == False
    
    @pytest.mark.asyncio
    async def test_repo_cloning_with_security_validation(self):
        """Test repository cloning with security validation"""
        repo_data = {
            "clone_url": "https://github.com/test/repo.git"
        }
        
        with patch('src.agents.autonomous_pipeline.git_clone') as mock_git_clone, \
             patch('src.agents.autonomous_pipeline.security_guardrails.validate_repository_access') as mock_validate:
            
            # Setup successful validation and clone
            mock_validate.return_value = {"valid": True}
            mock_git_clone.return_value = True
            
            result = await self.pipeline._clone_repo(repo_data)
            
            assert result is not None
            assert result.startswith("/tmp/github-agent-")
            mock_validate.assert_called_once_with("https://github.com/test/repo.git", "read")
    
    @pytest.mark.asyncio
    async def test_repo_cloning_security_blocked(self):
        """Test repository cloning when security blocks access"""
        repo_data = {
            "clone_url": "https://malicious.com/repo.git"
        }
        
        with patch('src.agents.autonomous_pipeline.security_guardrails.validate_repository_access') as mock_validate:
            # Setup blocked validation
            mock_validate.return_value = {
                "valid": False,
                "reason": "Access to blocked domain"
            }
            
            result = await self.pipeline._clone_repo(repo_data)
            
            assert result is None


class TestPerformanceMetrics:
    """Test performance metrics across components"""
    
    def test_analyzer_performance_tracking(self):
        """Test analyzer performance tracking"""
        analyzer = CodeAnalyzer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            (Path(temp_dir) / "test.py").write_text("print('test')")
            
            # Run analysis
            analyzer.analyze_codebase(temp_dir)
            
            # Check tracking
            assert len(analyzer.analysis_times) == 1
            assert analyzer.analysis_times[0] > 0
    
    def test_patcher_performance_tracking(self):
        """Test patcher performance tracking"""
        patcher = CodePatcher()
        
        analysis = {"repo_path": "/test"}
        issue_data = {"title": "Test"}
        
        result = patcher.generate_patch(analysis, issue_data)
        
        assert len(patcher.patch_times) == 1
        assert patcher.patch_times[0] > 0
        assert result["generation_time"] == patcher.patch_times[0]
    
    def test_tester_performance_tracking(self):
        """Test tester performance tracking"""
        tester = TestRunner()
        
        with patch('src.agents.autonomous_pipeline.run_pytest') as mock_pytest:
            mock_pytest.return_value = {"passed": 1, "failed": 0, "total": 1}
            
            with tempfile.TemporaryDirectory() as temp_dir:
                result = tester.run_tests(temp_dir)
                
                assert len(tester.test_times) == 1
                assert tester.test_times[0] > 0
                assert result["execution_time"] == tester.test_times[0]
    
    def test_pr_creator_performance_tracking(self):
        """Test PR creator performance tracking"""
        pr_creator = PRCreator()
        
        patch_data = {"test_results": {"pass_rate": 0.9}}
        issue_data = {"title": "Test"}
        
        result = pr_creator.create_draft_pr(patch_data, issue_data)
        
        assert len(pr_creator.pr_times) == 1
        assert pr_creator.pr_times[0] > 0
        assert result["creation_time"] == pr_creator.pr_times[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
