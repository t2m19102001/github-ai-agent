"""End-to-end smoke test for the Local Agent CLI.

Hermetic: no Ollama, no network, no env state. Drives the real `cli.main`
entrypoint twice — first `index <repo>` then `query "?"` — against a tiny
fixture repo, with a deterministic fake embedder + fake LLM injected.

Verifies the workflow contract a new dev would follow:
    clone → index → query → answer with citations
"""

from __future__ import annotations

import hashlib
import io
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss", reason="faiss-cpu required for E2E smoke test")
np = pytest.importorskip("numpy", reason="numpy required for E2E smoke test")

from src.local_agent import cli as cli_module
from src.local_agent.core import LocalAgent, QueryConfig
from src.local_agent.ingestion.embedder import Embedder
from src.local_agent.retrieval.context_builder import ContextBuilder
from src.local_agent.retrieval.retriever import BasicRetriever


_DIM = 8
_MODEL = "fake-model"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeModel:
    """Deterministic 8-dim sha256 embedder; no weights, no network."""

    def get_sentence_embedding_dimension(self) -> int:
        return _DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rows.append([digest[i] / 255.0 for i in range(_DIM)])
        return np.asarray(rows, dtype="float32")


@dataclass
class _FakeLLM:
    """Stand-in for OllamaProvider; returns a canned answer by default."""

    model_name: str = _MODEL
    response: str = (
        "Overview:\n- hello returns a greeting string\n\n"
        "Key points:\n- defined in app.py"
    )

    def generate(self, system_prompt, user_prompt, max_tokens=1200, temperature=0.0):
        return self.response


@pytest.fixture(autouse=True)
def _patch_embedder(monkeypatch):
    """Replace Embedder._load_model with the deterministic fake everywhere."""
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder,
        "_load_model",
        lambda self: setattr(self, "_model", fake) or fake,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_repo(tmp_path: Path) -> Path:
    """Write a minimal 2-file Python repo into tmp_path/repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        textwrap.dedent(
            '''
            """Top-level app module."""

            def hello(name):
                """Greet someone by name and return the greeting string."""
                return f"hello {name}"
            '''
        ).lstrip()
    )
    (repo / "utils.py").write_text(
        textwrap.dedent(
            '''
            """Tiny math utilities."""

            def add(a, b):
                """Sum two numbers."""
                return a + b
            '''
        ).lstrip()
    )
    return repo


def _make_agent_factory(index_dir: Path, llm: _FakeLLM | None = None):
    """Factory returning a LocalAgent that loads the real index from disk."""
    fake_llm = llm or _FakeLLM()

    def factory(*, config, index_dir: str, model_name: str):  # noqa: ARG001
        return LocalAgent(
            retriever=BasicRetriever(index_dir=index_dir, model_name=_MODEL),
            context_builder=ContextBuilder(
                max_tokens=config.max_context_tokens,
                reserve_tokens=config.reserve_tokens,
            ),
            llm_client=fake_llm,
            config=config,
        )

    return factory


def _run_index(repo: Path, idx: Path) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    code = cli_module.main(
        ["index", str(repo), "--index-dir", str(idx), "--embed-model", _MODEL],
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


def _run_query(
    question: str,
    idx: Path,
    *,
    as_json: bool = True,
    llm: _FakeLLM | None = None,
) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    argv = ["query", question, "--index-dir", str(idx), "--model", _MODEL]
    if as_json:
        argv.insert(1, "--json")  # query --json "..."
    code = cli_module.main(
        argv,
        agent_factory=_make_agent_factory(idx, llm=llm),
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# 1. Happy path: index + query both exit 0.
def test_index_then_query_succeeds_end_to_end(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"

    code_idx, out_idx, _ = _run_index(repo, idx)
    assert code_idx == 0
    assert "Indexed" in out_idx

    code_q, _, _ = _run_query("What does hello do?", idx)
    assert code_q == 0


# 2. Index step writes both FAISS + metadata files.
def test_index_creates_faiss_files_on_disk(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"
    code, _, _ = _run_index(repo, idx)
    assert code == 0
    assert (idx / "code.index").is_file()
    assert (idx / "metadata.json").is_file()

    # metadata.json must declare the model used at build time.
    payload = json.loads((idx / "metadata.json").read_text("utf-8"))
    assert payload["model_name"] == _MODEL
    assert payload["embedding_dim"] == _DIM
    assert payload["chunks"], "expected at least one chunk in the sidecar"


# 3. Query response (JSON mode) carries non-empty citations.
def test_query_response_contains_citations(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"
    _run_index(repo, idx)

    code, stdout, _ = _run_query("What does hello do?", idx)
    assert code == 0
    payload = json.loads(stdout)
    assert "citations" in payload
    assert len(payload["citations"]) > 0, "expected at least one citation"
    first = payload["citations"][0]
    for required in (
        "chunk_id",
        "relative_path",
        "file_path",
        "start_line",
        "end_line",
        "rank",
        "score",
    ):
        assert required in first, f"citation missing field {required!r}"


# 4. Citations point at the fixture files.
def test_citations_reference_fixture_files(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"
    _run_index(repo, idx)
    _, stdout, _ = _run_query("What does hello do?", idx)

    payload = json.loads(stdout)
    paths = {(c.get("relative_path") or c["file_path"]) for c in payload["citations"]}
    assert any("app.py" in p or "utils.py" in p for p in paths), (
        f"no fixture file referenced; got {paths!r}"
    )


# 5. Human-readable mode prints the answer + headers.
def test_query_human_mode_renders_answer(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"
    _run_index(repo, idx)

    code, stdout, _ = _run_query("What does hello do?", idx, as_json=False)
    assert code == 0
    assert "Question:" in stdout
    assert "Answer:" in stdout
    assert "hello" in stdout.lower()  # fake LLM answer mentions hello
    assert f"Model: {_MODEL}" in stdout


# 6. Pipeline is deterministic across two runs (same input → same chunks/citations).
def test_pipeline_is_deterministic(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx_a = tmp_path / "idx_a"
    idx_b = tmp_path / "idx_b"
    _run_index(repo, idx_a)
    _run_index(repo, idx_b)

    _, out_a, _ = _run_query("What does hello do?", idx_a)
    _, out_b, _ = _run_query("What does hello do?", idx_b)
    pa, pb = json.loads(out_a), json.loads(out_b)

    # Order-sensitive equality on chunk-level fields. Skip volatile fields
    # like `timestamp` and `latency_ms` which vary by wall clock.
    assert pa["retrieved_chunks"] == pb["retrieved_chunks"]
    assert [c["chunk_id"] for c in pa["citations"]] == [
        c["chunk_id"] for c in pb["citations"]
    ]
    assert [c["rank"] for c in pa["citations"]] == [
        c["rank"] for c in pb["citations"]
    ]


# 7. Question with unrelated content still completes (no crash); fallback path
#    still surfaces *some* answer or reports insufficient info.
def test_query_with_unrelated_question_still_completes(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    idx = tmp_path / "index"
    _run_index(repo, idx)

    # FAISS search always returns top-k regardless of relevance — even for an
    # unrelated query, the retriever yields chunks. The fake LLM still answers.
    # The contract we lock here: exit 0, JSON parses, citations present (or at
    # worst empty without crash).
    code, stdout, _ = _run_query("How do I configure a Kubernetes ingress?", idx)
    assert code == 0
    payload = json.loads(stdout)
    assert "answer" in payload
    assert isinstance(payload["citations"], list)
    assert payload["model_name"] == _MODEL
