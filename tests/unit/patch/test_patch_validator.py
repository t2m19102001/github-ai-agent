#!/usr/bin/env python3
"""
Unit tests for Patch Validator.
"""

import pytest

from src.patch.patch_validator import PatchValidator, ValidationResult, ValidationStatus
from src.patch.patch_generator import PatchGenerator, Patch


class TestPatchValidator:
    """Test PatchValidator."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = PatchValidator(max_patch_size=1024 * 1024)
        
        assert validator.max_patch_size == 1024 * 1024
    
    def test_validate_valid_patch(self):
        """Test validating valid patch."""
        generator = PatchGenerator()
        validator = PatchValidator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old code",
            new_content="new code",
        )
        
        result = validator.validate(patch)
        
        assert result.is_valid() is True
        assert result.status == ValidationStatus.PASSED
    
    def test_validate_oversized_patch(self):
        """Test validating oversized patch."""
        generator = PatchGenerator(max_patch_size=100)
        validator = PatchValidator(max_patch_size=100)
        
        large_content = "x" * 200
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content=large_content,
        )
        
        result = validator.validate(patch)
        
        assert result.is_valid() is False
        assert result.status == ValidationStatus.FAILED
    
    def test_validate_long_line(self):
        """Test validating long line."""
        generator = PatchGenerator()
        validator = PatchValidator(max_line_length=50)
        
        long_line = "x" * 100
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content=long_line,
        )
        
        result = validator.validate(patch)
        
        assert result.status == ValidationStatus.WARNING
    
    def test_validate_syntax_error(self):
        """Test validating syntax error."""
        generator = PatchGenerator()
        validator = PatchValidator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="def invalid syntax here",
        )
        
        result = validator.validate(patch)
        
        # Should have syntax error
        assert any(i.type == "syntax_error" for i in result.issues)
