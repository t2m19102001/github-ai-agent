#!/usr/bin/env python3
"""
Unit tests for Patch Generator.
"""

import pytest

from src.patch.patch_generator import PatchGenerator, Patch, PatchFormat


class TestPatchGenerator:
    """Test PatchGenerator."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = PatchGenerator(max_patch_size=1024 * 1024)
        
        assert generator.max_patch_size == 1024 * 1024
    
    def test_generate_patch(self):
        """Test patch generation."""
        generator = PatchGenerator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old code",
            new_content="new code",
        )
        
        assert patch.file_path == "src/main.py"
        assert patch.old_content == "old code"
        assert patch.new_content == "new code"
        assert patch.format == PatchFormat.UNIFIED
    
    def test_patch_size_limit(self):
        """Test patch size limit."""
        generator = PatchGenerator(max_patch_size=100)
        
        large_content = "x" * 200
        
        with pytest.raises(ValueError):
            generator.generate(
                file_path="src/main.py",
                old_content="old",
                new_content=large_content,
            )
    
    def test_get_patch_size(self):
        """Test getting patch size."""
        generator = PatchGenerator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="old code",
            new_content="new code",
        )
        
        size = patch.get_size()
        
        assert size > 0
    
    def test_get_line_count(self):
        """Test getting line count."""
        generator = PatchGenerator()
        
        patch = generator.generate(
            file_path="src/main.py",
            old_content="line1\nline2",
            new_content="line1\nline2\nline3",
        )
        
        line_count = patch.get_line_count()
        
        assert line_count == 3
    
    def test_generate_unified_diff(self):
        """Test unified diff generation."""
        generator = PatchGenerator()
        
        diff = generator.generate_unified_diff(
            file_path="src/main.py",
            old_content="line1\nline2",
            new_content="line1\nline2\nline3",
        )
        
        assert "a/src/main.py" in diff
        assert "b/src/main.py" in diff
