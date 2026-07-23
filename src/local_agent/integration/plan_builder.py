"""Deterministic, read-only Local Agent → SWE handoff builder."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.local_agent.guardrails.validators import FileGuardrails
from src.local_agent.integration.swe16_interface import (
    ChangeType,
    FileChange,
    FileLocation,
    PlanConstraints,
    PlanRequest,
    RetrievedChunk,
    ValidationStep,
    ValidationType,
)
from src.local_agent.planner.analyzer import GoalAnalyzer
from src.local_agent.planner.sequencer import StepSequencer
from src.local_agent.retrieval.retriever import RetrievalResult


class PlanRequestBuilder:
    """Convert grounded retrieval results into an approval-required handoff."""

    def __init__(self, guardrails: FileGuardrails | None = None) -> None:
        self.guardrails = guardrails or FileGuardrails()
        self.analyzer = GoalAnalyzer()
        self.sequencer = StepSequencer()

    def build(
        self,
        goal: str,
        results: Iterable[RetrievalResult],
        max_files: int = 5,
    ) -> PlanRequest:
        hits = list(results)
        analysis = self.analyzer.analyze(goal, hits)
        if analysis["requires_clarification"]:
            raise ValueError("cannot build a grounded plan without retrieved files")

        retrieved = [self._to_chunk(hit) for hit in hits]
        changes = []
        seen = set()
        blocked = []

        for hit in hits:
            path = hit.relative_path or hit.file_path
            if path in seen:
                continue
            allowed, reason = self.guardrails.can_suggest_changes(path)
            if not allowed:
                blocked.append({"file": path, "reason": reason})
                continue
            seen.add(path)
            changes.append(FileChange(
                file_path=path,
                change_type=ChangeType.MODIFY,
                description=f"Implement the goal using grounded context from {path}.",
                rationale=(
                    f"Retrieved at rank {hit.rank}"
                    + (f" for symbol {hit.qualified_name}" if hit.qualified_name else "")
                ),
                location=FileLocation(
                    start_line=max(1, hit.start_line),
                    end_line=max(max(1, hit.start_line), hit.end_line),
                ),
                dependencies=[],
            ))
            if len(changes) >= max_files:
                break

        if not changes:
            raise ValueError("guardrails blocked every retrieved file")

        ordered = self.sequencer.sequence(changes)
        extensions = sorted({Path(item.file_path).suffix for item in ordered if Path(item.file_path).suffix})
        constraints = PlanConstraints(
            auto_execute=False,
            require_approval=True,
            max_files=max_files,
            allowed_extensions=extensions or [".py"],
        )
        validations = [
            ValidationStep(
                type=ValidationType.SYNTAX_CHECK,
                target=item.file_path,
            )
            for item in ordered
        ]
        return PlanRequest(
            goal=analysis["goal"],
            context={
                "mode": "read-only-suggest-only",
                "files": analysis["files"],
                "symbols": analysis["symbols"],
                "blocked_files": blocked,
            },
            retrieved_chunks=retrieved,
            changes=ordered,
            validation_steps=validations,
            constraints=constraints,
        )

    @staticmethod
    def _to_chunk(hit: RetrievalResult) -> RetrievedChunk:
        similarity = 1.0 / (1.0 + max(0.0, hit.score))
        return RetrievedChunk(
            file=hit.relative_path or hit.file_path,
            lines=f"{hit.start_line}-{hit.end_line}",
            content=hit.content,
            relevance_score=min(1.0, similarity),
        )
