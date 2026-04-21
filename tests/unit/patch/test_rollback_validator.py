#!/usr/bin/env python3
"""
Unit tests for Rollback Validator.
"""

import pytest

from src.patch.rollback_validator import RollbackValidator, RollbackValidationResult
from src.patch.patch_generator import PatchGenerator
from src.patch.patch_validator import ValidationStatus


class TestRollbackValidator:
    """Test RollbackValidator."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = RollbackValidator()
        
        assert validator is not None
    
    def test_validate_with_old_content(self):
        """Test validation with old content preserved."""
        generator = PatchGenerator()
        validator = RollbackValidator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old code",
            new_content="new code",
        )
        
        result = validator.validate(patch)
        
        assert result.can_rollback is True
        assert result.status == ValidationStatus.PASSED
    
    def test_validate_without_old_content(self):
        """Test validation without old content."""
        generator = PatchGenerator()
        validator = RollbackValidator()
        
        patch = Patch(
            id="test-id",
            file_path="src/main.py",
            old_content="",
            new_content="new code",
        )
        
        result = validator.validate(patch)
        
        assert result.can_rollback is False
        assert result.status == ValidationStatus.FAILED
    
    def test_determine_rollback_strategy(self):
        """Test rollback strategy determination."""
        generator = PatchGenerator()
        validator = RollbackValidator()
        
        # SQL file
        patch = generator.generate(
            file_path="migrations/001.sql",
            old_content="old",
            new_content="new",
        )
        result = validator.validate(patch)
        assert result.rollback_strategy == "migration_rollback"
        
        # Python file
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="new",
        )
        result = validator.validate(patch)
        assert result.rollback_strategy == "git_revert"
