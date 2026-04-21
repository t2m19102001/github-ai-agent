#!/usr/bin/env python3
"""
Issue Analyzer with LLM Integration.

Production-grade implementation with:
- Issue summary generation
- Root cause analysis support
- LLM integration
- Safe prompt construction
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .prompt_safety import PromptSafetyValidator, PromptInjectionError
from .issue_classifier import IssueClassifier, ClassificationResult
from .duplicate_detector import DuplicateDetector, DuplicateMatch
from .audit_trail import AuditTrail

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    """Analysis result."""
    classification: ClassificationResult
    duplicates: list[DuplicateMatch]
    summary: Optional[str]
    root_cause: Optional[str]
    audit_trail: Dict[str, Any]


class IssueAnalyzer:
    """
    Issue analyzer.
    
    Analyzes GitHub issues using classification, duplicate detection,
    and LLM-powered summary generation.
    """
    
    def __init__(
        self,
        llm_provider,
        use_llm: bool = True,
        strict_prompt_safety: bool = True
    ):
        """
        Initialize issue analyzer.
        
        Args:
            llm_provider: LLM provider instance
            use_llm: Whether to use LLM for analysis
            strict_prompt_safety: Strict prompt validation
        """
        self.llm_provider = llm_provider
        self.use_llm = use_llm
        self.strict_prompt_safety = strict_prompt_safety
        
        self.classifier = IssueClassifier()
        self.duplicate_detector = DuplicateDetector()
        self.prompt_validator = PromptSafetyValidator(strict_mode=strict_prompt_safety)
        self.audit_trail = AuditTrail()
        
        logger.info(f"IssueAnalyzer initialized (use_llm: {use_llm})")
    
    async def analyze(
        self,
        title: str,
        body: str,
        labels: Optional[list] = None,
        existing_issues: Optional[list] = None
    ) -> AnalysisResult:
        """
        Analyze issue.
        
        Args:
            title: Issue title
            body: Issue body
            labels: Existing GitHub labels
            existing_issues: List of existing issues for duplicate detection
            
        Returns:
            Analysis result
        """
        # Record analysis start
        analysis_id = self.audit_trail.start_analysis(
            title=title,
            body=body,
            labels=labels
        )
        
        try:
            # Classify issue
            classification = self.classifier.classify(title, body, labels)
            self.audit_trail.record_decision(analysis_id, "classification", classification)
            
            # Detect duplicates
            duplicates = []
            if existing_issues:
                duplicates = self.duplicate_detector.detect_duplicates(title, body, existing_issues)
                self.audit_trail.record_decision(analysis_id, "duplicate_detection", duplicates)
            
            # Generate summary using LLM
            summary = None
            if self.use_llm and self.llm_provider:
                summary = await self._generate_summary(title, body, classification)
                self.audit_trail.record_decision(analysis_id, "summary_generation", summary)
            
            # Root cause analysis
            root_cause = None
            if self.use_llm and self.llm_provider and classification.category.value == "bug":
                root_cause = await self._analyze_root_cause(title, body, classification)
                self.audit_trail.record_decision(analysis_id, "root_cause_analysis", root_cause)
            
            # Complete analysis
            self.audit_trail.complete_analysis(analysis_id)
            
            return AnalysisResult(
                classification=classification,
                duplicates=duplicates,
                summary=summary,
                root_cause=root_cause,
                audit_trail=self.audit_trail.get_trail(analysis_id),
            )
            
        except Exception as e:
            self.audit_trail.record_error(analysis_id, str(e))
            raise
    
    async def _generate_summary(
        self,
        title: str,
        body: str,
        classification: ClassificationResult
    ) -> Optional[str]:
        """
        Generate issue summary using LLM.
        
        Args:
            title: Issue title
            body: Issue body
            classification: Classification result
            
        Returns:
            Generated summary
        """
        if not self.llm_provider:
            return None
        
        # Build safe prompt
        prompt = self._build_summary_prompt(title, body, classification)
        
        # Validate prompt
        sanitized_prompt, is_safe, threat_level = self.prompt_validator.validate_and_sanitize(prompt)
        
        if not is_safe:
            logger.warning(f"Prompt validation failed (threat: {threat_level.value}), skipping summary generation")
            return None
        
        # Generate summary
        from src.llm.provider_interface import LLMRequest, Message, ModelRole
        
        request = LLMRequest(
            model="llama2-70b",  # Default model
            messages=[
                Message(role=ModelRole.SYSTEM, content="You are a helpful assistant that summarizes GitHub issues concisely."),
                Message(role=ModelRole.USER, content=sanitized_prompt),
            ],
            max_tokens=200,
            temperature=0.3,
        )
        
        try:
            response = await self.llm_provider.generate(request)
            return response.content
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None
    
    async def _analyze_root_cause(
        self,
        title: str,
        body: str,
        classification: ClassificationResult
    ) -> Optional[str]:
        """
        Analyze root cause using LLM.
        
        Args:
            title: Issue title
            body: Issue body
            classification: Classification result
            
        Returns:
            Root cause analysis
        """
        if not self.llm_provider:
            return None
        
        # Build safe prompt
        prompt = self._build_root_cause_prompt(title, body, classification)
        
        # Validate prompt
        sanitized_prompt, is_safe, threat_level = self.prompt_validator.validate_and_sanitize(prompt)
        
        if not is_safe:
            logger.warning(f"Prompt validation failed (threat: {threat_level.value}), skipping root cause analysis")
            return None
        
        # Generate root cause analysis
        from src.llm.provider_interface import LLMRequest, Message, ModelRole
        
        request = LLMRequest(
            model="llama2-70b",
            messages=[
                Message(role=ModelRole.SYSTEM, content="You are a helpful assistant that analyzes bug reports to identify root causes."),
                Message(role=ModelRole.USER, content=sanitized_prompt),
            ],
            max_tokens=300,
            temperature=0.5,
        )
        
        try:
            response = await self.llm_provider.generate(request)
            return response.content
        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            return None
    
    def _build_summary_prompt(
        self,
        title: str,
        body: str,
        classification: ClassificationResult
    ) -> str:
        """Build safe prompt for summary generation."""
        return f"""Summarize the following GitHub issue in 1-2 sentences:

Title: {title}
Body: {body[:1000]}  # Truncate to prevent excessive length
Category: {classification.category.value}
Priority: {classification.priority.value}

Focus on the core issue and what needs to be done."""
    
    def _build_root_cause_prompt(
        self,
        title: str,
        body: str,
        classification: ClassificationResult
    ) -> str:
        """Build safe prompt for root cause analysis."""
        return f"""Analyze the potential root cause of this bug report:

Title: {title}
Body: {body[:1000]}  # Truncate to prevent excessive length
Severity: {classification.severity.value}

Identify the most likely root cause and suggest a fix approach."""
