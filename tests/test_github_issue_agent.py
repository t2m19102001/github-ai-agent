#!/usr/bin/env python3
"""
Test GitHub Issue Agent
Unit tests for GitHub issue analysis functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.agents.github_issue_agent import (
    GitHubIssueAgent, IssueAnalysis, IssueSuggestion
)
from src.tools.github_tools import GitHubIssue
from src.agents.base_agent import AgentContext


class TestGitHubIssueAgent:
    """Test cases for GitHubIssueAgent"""
    
    @pytest.fixture
    def agent(self):
        """Create GitHubIssueAgent instance for testing"""
        return GitHubIssueAgent(
            repo="testowner/testrepo",
            token="test_token",
            config={"test_mode": True}
        )
    
    @pytest.fixture
    def sample_issue(self):
        """Create sample GitHub issue for testing"""
        return GitHubIssue(
            id=123456,
            number=123,
            title="Bug: Application crashes on startup",
            body="""The application crashes immediately when starting with the following error:
            
            ERROR: Fatal exception occurred
            Stack trace:
            at App.main() line 42
            at System.boot() line 123
            
            This is blocking our development and needs urgent attention.""",
            state="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user="testuser",
            labels=["bug", "urgent"],
            assignees=["developer1"],
            milestone=None,
            comments_count=5,
            url="https://github.com/testowner/testrepo/issues/123"
        )
    
    @pytest.mark.asyncio
    async def test_analyze_bug_issue(self, agent, sample_issue):
        """Test analysis of bug issue"""
        analysis = await agent.analyze_issue(sample_issue)
        
        assert analysis.issue_number == 123
        assert analysis.category == "Bug"
        assert analysis.priority in ["Critical", "High"]
        assert isinstance(analysis.complexity, str)
        assert isinstance(analysis.suggested_labels, list)
        assert isinstance(analysis.confidence, float)
        assert 0 <= analysis.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_analyze_feature_issue(self, agent):
        """Test analysis of feature issue"""
        feature_issue = GitHubIssue(
            id=123457,
            number=124,
            title="Feature: Add dark mode support",
            body="""It would be great to have dark mode support for better user experience.
            This should include:
            - Dark theme toggle
            - System theme detection
            - Persistent user preference""",
            state="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user="featureuser",
            labels=["enhancement"],
            assignees=[],
            milestone=None,
            comments_count=2,
            url="https://github.com/testowner/testrepo/issues/124"
        )
        
        analysis = await agent.analyze_issue(feature_issue)
        
        assert analysis.category == "Feature"
        assert analysis.priority in ["Medium", "Low"]
        assert "enhancement" in analysis.suggested_labels or "feature" in analysis.suggested_labels
    
    @pytest.mark.asyncio
    async def test_analyze_documentation_issue(self, agent):
        """Test analysis of documentation issue"""
        doc_issue = GitHubIssue(
            id=123458,
            number=125,
            title="Documentation: Fix typo in README",
            body="""There's a typo in the README.md file on line 42.
            "recieve" should be "receive".
            
            This makes the documentation look unprofessional.""",
            state="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user="docuser",
            labels=["documentation"],
            assignees=[],
            milestone=None,
            comments_count=1,
            url="https://github.com/testowner/testrepo/issues/125"
        )
        
        analysis = await agent.analyze_issue(doc_issue)
        
        assert analysis.category == "Documentation"
        assert analysis.priority in ["Low", "Medium"]
        assert "documentation" in analysis.suggested_labels
    
    @pytest.mark.asyncio
    async def test_process_analyze_issue_message(self, agent):
        """Test processing analyze issue message"""
        context = AgentContext(
            session_id="test_session",
            user_id="test_user",
            conversation_history=[],
            tools_available=[]
        )
        
        with patch.object(agent.github_tools, 'get_issues') as mock_get_issues:
            # Mock issue data
            mock_issues = [
                GitHubIssue(
                    id=123456,
                    number=123,
                    title="Test Issue",
                    body="Test body",
                    state="open",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="testuser",
                    labels=[],
                    assignees=[],
                    milestone=None,
                    comments_count=0,
                    url="https://github.com/test/test/issues/123"
                )
            ]
            mock_get_issues.return_value = mock_issues
            
            response = await agent.process_message("analyze issue #123", context)
            
            assert "Issue Analysis: #123" in response
            assert "Test Issue" in response
            assert "Categorization" in response
            assert "Suggested Labels" in response
    
    @pytest.mark.asyncio
    async def test_process_list_issues_message(self, agent):
        """Test processing list issues message"""
        context = AgentContext(
            session_id="test_session",
            user_id="test_user",
            conversation_history=[],
            tools_available=[]
        )
        
        with patch.object(agent.github_tools, 'get_issues') as mock_get_issues:
            # Mock issue data
            mock_issues = [
                GitHubIssue(
                    id=123456,
                    number=123,
                    title="Issue 123",
                    body="Body 123",
                    state="open",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="user1",
                    labels=["bug"],
                    assignees=[],
                    milestone=None,
                    comments_count=5,
                    url="https://github.com/test/test/issues/123"
                ),
                GitHubIssue(
                    id=123457,
                    number=124,
                    title="Issue 124",
                    body="Body 124",
                    state="open",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="user2",
                    labels=["feature"],
                    assignees=[],
                    milestone=None,
                    comments_count=2,
                    url="https://github.com/test/test/issues/124"
                )
            ]
            mock_get_issues.return_value = mock_issues
            
            response = await agent.process_message("list issues", context)
            
            assert "Recent Open Issues" in response
            assert "#123 - Issue 123" in response
            assert "#124 - Issue 124" in response
            assert "bug" in response
            assert "feature" in response
    
    @pytest.mark.asyncio
    async def test_process_issue_stats_message(self, agent):
        """Test processing issue statistics message"""
        context = AgentContext(
            session_id="test_session",
            user_id="test_user",
            conversation_history=[],
            tools_available=[]
        )
        
        with patch.object(agent.github_tools, 'get_issues') as mock_get_issues:
            # Mock open issues
            mock_open_issues = [
                GitHubIssue(
                    id=1,
                    number=1,
                    title="Bug Issue",
                    body="Bug description",
                    state="open",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="user1",
                    labels=["bug"],
                    assignees=[],
                    milestone=None,
                    comments_count=0,
                    url="https://github.com/test/test/issues/1"
                ),
                GitHubIssue(
                    id=2,
                    number=2,
                    title="Feature Issue",
                    body="Feature description",
                    state="open",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="user2",
                    labels=["enhancement"],
                    assignees=[],
                    milestone=None,
                    comments_count=0,
                    url="https://github.com/test/test/issues/2"
                )
            ]
            
            # Mock closed issues
            mock_closed_issues = [
                GitHubIssue(
                    id=3,
                    number=3,
                    title="Closed Issue",
                    body="Closed description",
                    state="closed",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    user="user3",
                    labels=[],
                    assignees=[],
                    milestone=None,
                    comments_count=0,
                    url="https://github.com/test/test/issues/3"
                )
            ]
            
            # Configure mock to return different data based on state parameter
            def get_issues_side_effect(owner, repo, state="open", limit=100):
                if state == "open":
                    return mock_open_issues
                elif state == "closed":
                    return mock_closed_issues
                return []
            
            mock_get_issues.side_effect = get_issues_side_effect
            
            response = await agent.process_message("issue stats", context)
            
            assert "Issue Statistics" in response
            assert "Total Open Issues: 2" in response
            assert "Total Closed Issues: 1" in response
            assert "Open Issues by Category" in response
            assert "Bug: 1" in response
            assert "Feature: 1" in response
    
    def test_categorize_issue_bug(self, agent):
        """Test issue categorization for bugs"""
        text = "The application crashes with error message"
        category = agent._categorize_issue(text)
        assert category == "Bug"
    
    def test_categorize_issue_feature(self, agent):
        """Test issue categorization for features"""
        text = "I would like to request a new feature for dark mode"
        category = agent._categorize_issue(text)
        assert category == "Feature"
    
    def test_categorize_issue_documentation(self, agent):
        """Test issue categorization for documentation"""
        text = "There is a typo in the README documentation"
        category = agent._categorize_issue(text)
        assert category == "Documentation"
    
    def test_categorize_issue_question(self, agent):
        """Test issue categorization for questions"""
        text = "How do I configure the application settings?"
        category = agent._categorize_issue(text)
        assert category == "Question"
    
    def test_assess_priority_critical(self, agent):
        """Test priority assessment for critical issues"""
        text = "This is urgent and blocking production deployment"
        priority = agent._assess_priority(text, None)
        assert priority == "Critical"
    
    def test_assess_priority_high(self, agent):
        """Test priority assessment for high priority issues"""
        text = "This is an important bug that needs immediate attention"
        priority = agent._assess_priority(text, None)
        assert priority == "High"
    
    def test_assess_priority_low(self, agent):
        """Test priority assessment for low priority issues"""
        text = "This is a minor suggestion for improvement"
        priority = agent._assess_priority(text, None)
        assert priority == "Low"
    
    def test_assess_complexity_low(self, agent):
        """Test complexity assessment for simple issues"""
        text = "Simple typo fix needed"
        complexity = agent._assess_complexity(text)
        assert complexity == "Low"
    
    def test_assess_complexity_high(self, agent):
        """Test complexity assessment for complex issues"""
        text = """This is a very complex issue that requires:
        1. Database migration
        2. API integration
        3. Performance optimization
        4. UI/UX redesign
        5. Testing and deployment
        
        The architecture needs to be refactored and multiple dependencies updated."""
        complexity = agent._assess_complexity(text)
        assert complexity == "High"
    
    def test_suggest_labels_bug(self, agent):
        """Test label suggestions for bug issues"""
        labels = agent._suggest_labels("Bug", "High", "Medium")
        assert "Bug" in labels
        assert "priority/high" in labels
        assert "complexity/medium" in labels
    
    def test_suggest_labels_feature(self, agent):
        """Test label suggestions for feature issues"""
        labels = agent._suggest_labels("Feature", "Medium", "Low")
        assert "Feature" in labels
        assert "priority/medium" in labels
        assert "complexity/low" in labels
    
    def test_extract_issue_number(self, agent):
        """Test extraction of issue number from message"""
        message1 = "Please analyze issue #123"
        number1 = agent._extract_issue_number(message1)
        assert number1 == 123
        
        message2 = "Check issue #456 for details"
        number2 = agent._extract_issue_number(message2)
        assert number2 == 456
        
        message3 = "No issue number here"
        number3 = agent._extract_issue_number(message3)
        assert number3 is None
    
    def test_calculate_confidence(self, agent):
        """Test confidence calculation"""
        text = "This is a clear bug description with detailed information"
        confidence1 = agent._calculate_confidence(text, "Bug", "High")
        assert confidence1 > 0.7
        
        text2 = "vague issue"
        confidence2 = agent._calculate_confidence(text2, "Other", "Medium")
        assert confidence2 < confidence1
    
    @pytest.mark.asyncio
    async def test_generate_analysis_summary(self, agent):
        """Test generation of analysis summary"""
        from datetime import datetime
        issue = GitHubIssue(
            id=123,
            number=123,
            title="Test Issue",
            body="This is a test issue for analysis",
            state="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user="testuser",
            labels=[],
            assignees=[],
            milestone=None,
            comments_count=0,
            url="https://github.com/test/test/issues/123"
        )
        
        with patch.object(agent, 'generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "This issue appears to be about testing functionality"
            
            summary = await agent._generate_analysis_summary(issue, "Bug", "High", "Medium")
            
            mock_generate.assert_called_once()
            assert summary == "This issue appears to be about testing functionality"
    
    def test_get_status(self, agent):
        """Test agent status retrieval"""
        status = agent.get_status()
        
        assert "name" in status
        assert status["name"] == "GitHubIssueAgent"
        assert "is_active" in status
        assert "tools_count" in status
        assert "config" in status
    
    def test_memory_operations(self, agent):
        """Test agent memory operations"""
        # Test setting and getting memory
        agent.set_memory("test_key", "test_value")
        assert agent.get_memory("test_key") == "test_value"
        
        # Test getting non-existent key
        assert agent.get_memory("non_existent") is None


# Integration tests
class TestGitHubIssueAgentIntegration:
    """Integration tests for GitHubIssueAgent"""
    
    @pytest.mark.asyncio
    async def test_full_issue_analysis_workflow(self):
        """Test complete issue analysis workflow"""
        # Note: This test requires actual GitHub token
        # Skip in CI/CD environment
        if not pytest.getoption("--run-integration", default=False):
            pytest.skip("Integration test requires --run-integration flag")
        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        
        # Use a real public repository for testing
        agent = GitHubIssueAgent("microsoft/vscode", token)
        
        # Get real issues
        owner, repo = "microsoft", "vscode"
        issues = agent.github_tools.get_issues(owner, repo, state="open", limit=5)
        
        if issues:
            # Analyze first issue
            analysis = await agent.analyze_issue(issues[0])
            
            # Verify analysis structure
            assert isinstance(analysis, IssueAnalysis)
            assert analysis.issue_number == issues[0].number
            assert analysis.title == issues[0].title
            assert analysis.category in ["Bug", "Feature", "Documentation", "Question", "Other"]
            assert analysis.priority in ["Critical", "High", "Medium", "Low"]
            assert analysis.complexity in ["Low", "Medium", "High"]
            assert isinstance(analysis.suggested_labels, list)
            assert isinstance(analysis.confidence, float)
            assert 0 <= analysis.confidence <= 1


# Test runner
def run_tests():
    """Run all tests"""
    import sys
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    sys.exit(exit_code)


if __name__ == "__main__":
    run_tests()
