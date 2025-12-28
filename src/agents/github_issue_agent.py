#!/usr/bin/env python3
"""
GitHub Issue Agent
Analyzes and manages GitHub issues automatically
"""

import os
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from .base_agent import BaseAgent, AgentContext, AgentMessage
    from ..tools.github_tools import GitHubTools, GitHubIssue
except ImportError:
    from src.agents.base_agent import BaseAgent, AgentContext, AgentMessage
    from src.tools.github_tools import GitHubTools, GitHubIssue

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IssueAnalysis:
    """Issue analysis result"""
    issue_number: int
    title: str
    category: str
    priority: str
    complexity: str
    estimated_time: str
    suggested_labels: List[str]
    suggested_assignee: Optional[str]
    analysis_summary: str
    confidence: float


@dataclass
class IssueSuggestion:
    """Suggested action for issue"""
    action_type: str  # comment, label, assign, close
    content: str
    reasoning: str
    confidence: float


class GitHubIssueAgent(BaseAgent):
    """Agent for analyzing and managing GitHub issues"""
    
    def __init__(self, repo: str, token: str, config: Dict[str, Any] = None):
        super().__init__("GitHubIssueAgent", config=config)
        
        self.repo = repo
        self.github_tools = GitHubTools(token, repo)
        
        # Issue analysis patterns
        self.bug_patterns = [
            r'\b(bug|error|issue|problem|fail|crash|broken|exception)\b',
            r'\b(not working|doesn\'t work|unable to|can\'t|cannot)\b',
            r'\b(stack trace|traceback|error message|exception)\b'
        ]
        
        self.feature_patterns = [
            r'\b(feature|enhancement|improvement|add|implement|create)\b',
            r'\b(would like|request|suggest|propose)\b',
            r'\b(new|additional|extra|more)\s+\b(functionality|feature|option)\b'
        ]
        
        self.urgency_patterns = [
            r'\b(urgent|critical|blocking|immediate|asap)\b',
            r'\b(breaking|production|live|deployed)\b',
            r'\b(can\'t proceed|blocked|stuck|waiting)\b'
        ]
        
        # Set system prompt
        self.system_prompt = f"""You are GitHubIssueAgent, an AI assistant specialized in analyzing GitHub issues for the repository {repo}.

Your responsibilities:
1. Analyze issue titles and descriptions to categorize them
2. Assess priority and complexity
3. Suggest appropriate labels and assignees
4. Provide helpful suggestions and solutions
5. Generate automated responses when appropriate

Categories:
- Bug: Error reports, broken functionality, crashes
- Feature: New features, enhancements, improvements
- Documentation: Docs issues, README updates
- Question: User questions, clarifications
- Maintenance: Dependencies, updates, refactoring

Priority Levels:
- Critical: Blocking issues, production problems
- High: Important bugs, urgent features
- Medium: Normal bugs, standard features
- Low: Minor issues, nice-to-have features

Always be helpful, professional, and provide actionable insights."""
        
        logger.info(f"Initialized GitHubIssueAgent for repo: {repo}")
    
    async def analyze_issue(self, issue: GitHubIssue) -> IssueAnalysis:
        """Analyze a GitHub issue"""
        try:
            # Combine title and body for analysis
            full_text = f"{issue.title}\n\n{issue.body}"
            
            # Categorize issue
            category = self._categorize_issue(full_text)
            
            # Assess priority
            priority = self._assess_priority(full_text, issue)
            
            # Assess complexity
            complexity = self._assess_complexity(full_text)
            
            # Estimate time
            estimated_time = self._estimate_time(complexity)
            
            # Suggest labels
            suggested_labels = self._suggest_labels(category, priority, complexity)
            
            # Suggest assignee
            suggested_assignee = self._suggest_assignee(issue, category)
            
            # Generate analysis summary
            analysis_summary = await self._generate_analysis_summary(
                issue, category, priority, complexity
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(full_text, category, priority)
            
            return IssueAnalysis(
                issue_number=issue.number,
                title=issue.title,
                category=category,
                priority=priority,
                complexity=complexity,
                estimated_time=estimated_time,
                suggested_labels=suggested_labels,
                suggested_assignee=suggested_assignee,
                analysis_summary=analysis_summary,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error analyzing issue #{issue.number}: {e}")
            raise
    
    async def process_message(self, message: str, context: AgentContext) -> str:
        """Process incoming message"""
        try:
            # Check if message contains issue analysis request
            if "analyze issue" in message.lower() or "review issue" in message.lower():
                # Extract issue number from message
                issue_number = self._extract_issue_number(message)
                
                if issue_number:
                    return await self._analyze_and_respond(issue_number)
                else:
                    return "Please specify an issue number to analyze (e.g., 'analyze issue #123')."
            
            # Check for issue listing request
            elif "list issues" in message.lower() or "show issues" in message.lower():
                return await self._list_recent_issues()
            
            # Check for issue statistics request
            elif "issue stats" in message.lower() or "issue summary" in message.lower():
                return await self._get_issue_statistics()
            
            # Default response
            else:
                return """I can help you with GitHub issues! Here's what I can do:

1. **Analyze Issue**: "analyze issue #123" - Analyze a specific issue
2. **List Issues**: "list issues" - Show recent open issues
3. **Issue Stats**: "issue stats" - Show issue statistics

What would you like me to help with?"""
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing your request: {str(e)}"
    
    async def _analyze_and_respond(self, issue_number: int) -> str:
        """Analyze issue and generate response"""
        try:
            # Get issue from GitHub
            owner, repo = self.repo.split('/')
            issues = self.github_tools.get_issues(owner, repo, state="open", limit=50)
            
            # Find the specific issue
            target_issue = None
            for issue in issues:
                if issue.number == issue_number:
                    target_issue = issue
                    break
            
            if not target_issue:
                return f"Issue #{issue_number} not found or is not open."
            
            # Analyze the issue
            analysis = await self.analyze_issue(target_issue)
            
            # Format response
            response = f"""## Issue Analysis: #{issue_number} - {target_issue.title}

### 📊 Analysis Summary
{analysis.analysis_summary}

### 🏷️ Categorization
- **Category**: {analysis.category}
- **Priority**: {analysis.priority}
- **Complexity**: {analysis.complexity}
- **Estimated Time**: {analysis.estimated_time}

### 🏷️ Suggested Labels
{', '.join([f'`{label}`' for label in analysis.suggested_labels])}

### 👥 Suggested Assignee
{analysis.suggested_assignee or 'No specific assignee suggested'}

### 💡 Recommendations
{await self._generate_recommendations(analysis)}

---
*Analysis confidence: {analysis.confidence:.1%}*"""
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing issue #{issue_number}: {e}")
            return f"Error analyzing issue #{issue_number}: {str(e)}"
    
    async def _list_recent_issues(self) -> str:
        """List recent open issues"""
        try:
            owner, repo = self.repo.split('/')
            issues = self.github_tools.get_issues(owner, repo, state="open", limit=10)
            
            if not issues:
                return "No open issues found."
            
            response = "## Recent Open Issues\n\n"
            
            for issue in issues[:5]:  # Show top 5
                response += f"### #{issue.number} - {issue.title}\n"
                response += f"- **Labels**: {', '.join(issue.labels) if issue.labels else 'None'}\n"
                response += f"- **Created**: {issue.created_at.strftime('%Y-%m-%d')}\n"
                response += f"- **Comments**: {issue.comments_count}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error listing issues: {e}")
            return f"Error listing issues: {str(e)}"
    
    async def _get_issue_statistics(self) -> str:
        """Get issue statistics"""
        try:
            owner, repo = self.repo.split('/')
            
            # Get open and closed issues
            open_issues = self.github_tools.get_issues(owner, repo, state="open", limit=100)
            closed_issues = self.github_tools.get_issues(owner, repo, state="closed", limit=100)
            
            # Count by category
            categories = {"Bug": 0, "Feature": 0, "Documentation": 0, "Question": 0, "Other": 0}
            
            for issue in open_issues:
                category = self._categorize_issue(f"{issue.title}\n\n{issue.body}")
                categories[category] += 1
            
            total_open = len(open_issues)
            total_closed = len(closed_issues)
            
            response = f"""## Issue Statistics for {owner}/{repo}

### 📈 Overview
- **Total Open Issues**: {total_open}
- **Total Closed Issues**: {total_closed}
- **Open Rate**: {(total_open / (total_open + total_closed) * 100):.1f}%

### 🏷️ Open Issues by Category
"""
            
            for category, count in categories.items():
                if count > 0:
                    percentage = (count / total_open * 100) if total_open > 0 else 0
                    response += f"- **{category}**: {count} ({percentage:.1f}%)\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return f"Error getting statistics: {str(e)}"
    
    def _categorize_issue(self, text: str) -> str:
        """Categorize issue based on content"""
        text_lower = text.lower()
        
        # Check for bug patterns
        for pattern in self.bug_patterns:
            if re.search(pattern, text_lower):
                return "Bug"
        
        # Check for feature patterns
        for pattern in self.feature_patterns:
            if re.search(pattern, text_lower):
                return "Feature"
        
        # Check for documentation patterns
        doc_patterns = [r'\b(documentation|docs|readme|guide|tutorial)\b', 
                      r'\b(typo|spelling|grammar|format)\b']
        for pattern in doc_patterns:
            if re.search(pattern, text_lower):
                return "Documentation"
        
        # Check for question patterns
        question_patterns = [r'\?', r'\b(how|what|why|when|where|can you)\b']
        for pattern in question_patterns:
            if re.search(pattern, text_lower):
                return "Question"
        
        return "Other"
    
    def _assess_priority(self, text: str, issue: GitHubIssue) -> str:
        """Assess issue priority"""
        text_lower = text.lower()
        
        # Check for urgency patterns
        for pattern in self.urgency_patterns:
            if re.search(pattern, text_lower):
                return "Critical"
        
        # Check for high priority indicators
        high_patterns = [r'\b(urgent|important|high priority|asap)\b']
        for pattern in high_patterns:
            if re.search(pattern, text_lower):
                return "High"
        
        # Check for low priority indicators
        low_patterns = [r'\b(minor|nice to have|low priority|suggestion)\b']
        for pattern in low_patterns:
            if re.search(pattern, text_lower):
                return "Low"
        
        # Default to medium
        return "Medium"
    
    def _assess_complexity(self, text: str) -> str:
        """Assess issue complexity"""
        text_lower = text.lower()
        
        # Count complexity indicators
        complexity_score = 0
        
        # Length indicators
        if len(text) > 1000:
            complexity_score += 2
        elif len(text) > 500:
            complexity_score += 1
        
        # Technical complexity
        tech_patterns = [r'\b(api|database|algorithm|architecture)\b',
                       r'\b(dependency|integration|migration)\b',
                       r'\b(refactor|optimize|performance)\b']
        for pattern in tech_patterns:
            if re.search(pattern, text_lower):
                complexity_score += 1
        
        # Multiple components
        if re.search(r'\b(and|also|plus|additionally)\b', text_lower):
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 4:
            return "High"
        elif complexity_score >= 2:
            return "Medium"
        else:
            return "Low"
    
    def _estimate_time(self, complexity: str) -> str:
        """Estimate time to resolve issue"""
        time_estimates = {
            "Low": "1-2 hours",
            "Medium": "4-8 hours",
            "High": "1-3 days"
        }
        return time_estimates.get(complexity, "Unknown")
    
    def _suggest_labels(self, category: str, priority: str, complexity: str) -> List[str]:
        """Suggest appropriate labels"""
        labels = [category]
        
        # Add priority label
        if priority in ["Critical", "High"]:
            labels.append("priority/high")
        elif priority == "Medium":
            labels.append("priority/medium")
        elif priority == "Low":
            labels.append("priority/low")
        
        # Add complexity label
        if complexity == "High":
            labels.append("complexity/high")
        elif complexity == "Medium":
            labels.append("complexity/medium")
        elif complexity == "Low":
            labels.append("complexity/low")
        
        return labels
    
    def _suggest_assignee(self, issue: GitHubIssue, category: str) -> Optional[str]:
        """Suggest assignee based on issue content and category"""
        # This is a simplified version - in real implementation, 
        # you'd analyze team expertise, workload, etc.
        
        assignee_mapping = {
            "Bug": "backend-team",
            "Feature": "feature-team", 
            "Documentation": "docs-team",
            "Question": "support-team"
        }
        
        return assignee_mapping.get(category)
    
    async def _generate_analysis_summary(self, issue: GitHubIssue, 
                                   category: str, priority: str, 
                                   complexity: str) -> str:
        """Generate analysis summary using LLM"""
        prompt = f"""Analyze this GitHub issue and provide a concise summary:

Issue Title: {issue.title}
Issue Body: {issue.body[:500]}...
Category: {category}
Priority: {priority}
Complexity: {complexity}

Provide a 2-3 sentence summary of what this issue is about and what needs to be done."""
        
        return await self.generate_response(prompt)
    
    async def _generate_recommendations(self, analysis: IssueAnalysis) -> str:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if analysis.category == "Bug":
            recommendations.append("🔍 **Investigation**: Reproduce the bug and identify root cause")
            recommendations.append("🧪 **Testing**: Write test cases to prevent regression")
        
        elif analysis.category == "Feature":
            recommendations.append("📋 **Planning**: Break down into smaller tasks")
            recommendations.append("🎨 **Design**: Consider UI/UX implications")
        
        if analysis.complexity == "High":
            recommendations.append("👥 **Collaboration**: Consider pair programming or code review")
            recommendations.append("📅 **Timeline**: Plan for multiple iterations")
        
        if analysis.priority == "Critical":
            recommendations.append("🚨 **Urgency**: Address immediately to minimize impact")
        
        return "\n".join(recommendations) if recommendations else "No specific recommendations."
    
    def _calculate_confidence(self, text: str, category: str, priority: str) -> float:
        """Calculate confidence score for analysis"""
        confidence = 0.7  # Base confidence
        
        # Increase confidence for clear patterns
        if category != "Other":
            confidence += 0.1
        
        if priority != "Medium":
            confidence += 0.1
        
        # Increase confidence for longer text
        if len(text) > 200:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _extract_issue_number(self, message: str) -> Optional[int]:
        """Extract issue number from message"""
        match = re.search(r'#(\d+)', message)
        return int(match.group(1)) if match else None


# Test function
async def test_github_issue_agent():
    """Test GitHubIssueAgent functionality"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable not set")
        return
    
    try:
        agent = GitHubIssueAgent("torvalds/linux", token)
        
        # Test issue analysis
        from datetime import datetime
        test_issue = GitHubIssue(
            id=123456,
            number=123456,
            title="Bug: Kernel panic on boot",
            body="System crashes with kernel panic when booting Ubuntu 22.04",
            state="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user="testuser",
            labels=["bug", "urgent"],
            assignees=[],
            milestone=None,
            comments_count=5,
            url="https://github.com/torvalds/linux/issues/123456"
        )
        
        analysis = await agent.analyze_issue(test_issue)
        print(f"Issue Analysis:")
        print(f"Category: {analysis.category}")
        print(f"Priority: {analysis.priority}")
        print(f"Complexity: {analysis.complexity}")
        print(f"Confidence: {analysis.confidence:.1%}")
        
        # Test chat interface
        response = await agent.chat("analyze issue #123456")
        print(f"Chat response: {response}")
        
    except Exception as e:
        print(f"Error testing GitHubIssueAgent: {e}")


if __name__ == "__main__":
    asyncio.run(test_github_issue_agent())
