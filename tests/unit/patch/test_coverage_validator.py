#!/usr/bin/env python3
"""
Unit tests for Coverage Validator.
"""

import pytest

from src.patch.coverage_validator import CoverageValidator, CoverageValidationResult
from src.patch.patch_generator import PatchGenerator
from src.patch.patch_validator import ValidationStatus


class TestCoverageValidator:
    """Test CoverageValidator."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = CoverageValidator(coverage_threshold=80.0)
        
        assert validator.coverage_threshold == 80.0
    
    def test_validate_no_coverage_data(self):
        """Test validation with no coverage data."""
        generator = PatchGenerator()
        validator = CoverageValidator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="new",
        )
        
        result = validator.validate(patch)
        
        assert result.status == ValidationStatus.WARNING
    
    def test_validate_low_coverage(self):
        """Test validation with low coverage."""
        generator = PatchGenerator()
        validator = CoverageValidator(coverage_threshold=80.0)
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="new",
        )
        
        coverage_data = {"coverage": 50.0, "uncovered_files": []}
        result = validator.validate(patch, coverage_data)
        
        assert result.status == ValidationStatus.FAILED
    
    def test_validate_high_coverage(self):
        """Test validation with high coverage."""
        generator = PatchGenerator()
        validator = CoverageValidator(coverage_threshold=80.0)
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old",
            new_content="new",
        )
        
        coverage_data = {"coverage": 90.0, "uncovered_files": []}
        result = validator.validate(patch, coverage_data)
        
        assert result.status == ValidationStatus.PASSED
