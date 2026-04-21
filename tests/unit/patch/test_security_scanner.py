#!/usr/bin/env python3
"""
Unit tests for Security Scanner.
"""

import pytest

from src.patch.security_scanner import SecurityScanner, SecurityFinding, SecurityIssueType
from src.patch.patch_generator import PatchGenerator
from src.patch.patch_validator import ValidationStatus


class TestSecurityScanner:
    """Test SecurityScanner."""
    
    def test_scanner_initialization(self):
        """Test scanner initialization."""
        scanner = SecurityScanner()
        
        assert scanner is not None
    
    def test_scan_secret_leak(self):
        """Test secret leak detection."""
        generator = PatchGenerator()
        scanner = SecurityScanner()
        
        patch = generator.generate(
            file_path="src/config.py",
            old_content="old",
            new_content="password = 'secret123'",
        )
        
        findings = scanner.scan(patch)
        
        assert len(findings) > 0
        assert any(f.type == SecurityIssueType.SECRET_LEAK for f in findings)
    
    def test_scan_dangerous_code(self):
        """Test dangerous code detection."""
        generator = PatchGenerator()
        scanner = SecurityScanner()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="exec(user_input)",
        )
        
        findings = scanner.scan(patch)
        
        assert len(findings) > 0
        assert any(f.type == SecurityIssueType.DANGEROUS_CODE for f in findings)
    
    def test_scan_forbidden_pattern(self):
        """Test forbidden pattern detection."""
        generator = PatchGenerator()
        scanner = SecurityScanner()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="debugger.set_trace()",
        )
        
        findings = scanner.scan(patch)
        
        assert len(findings) > 0
        assert any(f.type == SecurityIssueType.FORBIDDEN_PATTERN for f in findings)
    
    def test_scan_clean_code(self):
        """Test scanning clean code."""
        generator = PatchGenerator()
        scanner = SecurityScanner()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="def hello():\n    return 'world'",
        )
        
        findings = scanner.scan(patch)
        
        # Should have no findings
        assert len(findings) == 0
