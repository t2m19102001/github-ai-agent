"""Tests for the deterministic read-only planning handoff."""

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from src.local_agent.integration.plan_builder import PlanRequestBuilder
from src.local_agent.planner.analyzer import GoalAnalyzer
from src.local_agent.planner.output_schema import PlanOutput
from src.local_agent.planner.risk_assessor import RiskAssessor
from src.local_agent.planner.sequencer import StepSequencer
from src.local_agent.retrieval.retriever import RetrievalResult, RetrievalSource


def _hit(path: str = "src/service.py", rank: int = 1) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=f"chunk-{rank}",
        file_path=f"/repo/{path}",
        relative_path=path,
        name="run",
        qualified_name="Service.run",
        level="method",
        start_line=10,
        end_line=20,
        content="def run(self): ...",
        docstring=None,
        symbols=["Service.run"],
        parent_name="Service",
        score=0.25,
        rank=rank,
        source=RetrievalSource.DENSE,
    )


def test_goal_analyzer_is_grounded() -> None:
    analysis = GoalAnalyzer().analyze("Add robust retry handling", [_hit()])
    assert analysis["files"] == ["src/service.py"]
    assert analysis["symbols"] == ["Service.run"]
    assert analysis["requires_clarification"] is False


def test_goal_analyzer_rejects_vague_goal() -> None:
    with pytest.raises(ValueError):
        GoalAnalyzer().analyze("fix", [_hit()])


def test_step_sequencer_orders_dependencies() -> None:
    first = SimpleNamespace(dependencies=[])
    second = SimpleNamespace(dependencies=[1])
    assert StepSequencer().sequence([second, first]) == [first, second]


def test_step_sequencer_rejects_cycle() -> None:
    with pytest.raises(ValueError):
        StepSequencer().sequence([SimpleNamespace(dependencies=[2])])


def test_risk_assessor_flags_missing_tests() -> None:
    risks = RiskAssessor().assess([1], [SimpleNamespace(validation="syntax")])
    assert risks


def test_plan_request_requires_approval_and_is_grounded() -> None:
    request = PlanRequestBuilder().build("Add robust retry handling", [_hit()])
    assert request.constraints.auto_execute is False
    assert request.constraints.require_approval is True
    assert request.changes[0].file_path == "src/service.py"
    assert request.changes[0].suggested_code is None
    assert request.retrieved_chunks[0].relevance_score == pytest.approx(0.8)


def test_plan_request_guardrails_block_sensitive_files() -> None:
    with pytest.raises(ValueError, match="guardrails blocked"):
        PlanRequestBuilder().build(
            "Update sensitive configuration safely",
            [_hit("config/settings.py")],
        )


def test_plan_output_serializes() -> None:
    plan = PlanOutput(
        goal="Add robust retry handling",
        assumptions=[],
        files_to_change=[],
        steps=[],
        risks=[],
        validation_overall="Run targeted tests",
        estimated_effort="small",
        overall_confidence=0.8,
        confidence_rationale="Grounded retrieval",
    )
    assert asdict(plan)["goal"] == "Add robust retry handling"
