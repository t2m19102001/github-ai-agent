#!/usr/bin/env python3
"""Lightweight testing utility tools used by legacy test generation agent tests."""

from __future__ import annotations

import re
from typing import Dict, List


class MockGeneratorTool:
    name = "MockGeneratorTool"

    def execute(self, code: str, language: str = "python") -> Dict:
        imports = re.findall(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", code, flags=re.MULTILINE)
        flattened = [item for pair in imports for item in pair if item]
        return {"imports_mocked": flattened, "language": language}


class FixtureGeneratorTool:
    name = "FixtureGeneratorTool"

    def execute(self, code: str, language: str = "python", framework: str = "pytest") -> Dict:
        fixture_block = "@pytest.fixture\ndef sample_fixture():\n    return {}\n"
        return {"fixtures": {"conftest": fixture_block}, "framework": framework, "language": language}


class EdgeCaseAnalyzerTool:
    name = "EdgeCaseAnalyzerTool"

    def execute(self, code: str) -> Dict[str, List[str]]:
        return {
            "null_empty": ["empty input", "None input"],
            "boundary": ["min value", "max value"],
            "type": ["unexpected type"],
        }


class CoverageAnalyzerTool:
    name = "CoverageAnalyzerTool"

    def execute(self, code: str, test_code: str) -> Dict:
        functions = re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
        tested = [fn for fn in functions if f"test_{fn}" in test_code]
        untested = [fn for fn in functions if fn not in tested]
        percentage = (len(tested) / len(functions) * 100) if functions else 0
        return {
            "total_functions": len(functions),
            "tested_functions": len(tested),
            "untested_functions": untested,
            "coverage_percentage": percentage,
        }


class TestFrameworkDetectorTool:
    name = "TestFrameworkDetectorTool"

    def execute(self, language: str) -> Dict:
        lang = language.lower()
        if lang == "python":
            frameworks = ["pytest", "unittest"]
            recommended = "pytest"
        elif lang in {"javascript", "js", "typescript", "ts"}:
            frameworks = ["jest", "vitest", "mocha"]
            recommended = "jest"
        else:
            frameworks = ["generic"]
            recommended = "generic"
        return {"language": lang, "frameworks": frameworks, "recommended": recommended}
