"""CLI tests for the `index` subcommand."""

from __future__ import annotations

import hashlib
import io
import textwrap
from pathlib import Path

import pytest

from src.local_agent import cli as cli_module
from src.local_agent.ingestion.embedder import Embedder


_FAKE_DIM = 8


class _FakeModel:
    """Deterministic fake SentenceTransformer for hermetic indexing tests."""

    def get_sentence_embedding_dimension(self) -> int:
        return _FAKE_DIM

    def eval(self) -> None:
        return None

    def encode(self, texts, batch_size: int, **_):
        import numpy as np

        rows = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            rows.append([digest[i] / 255.0 for i in range(_FAKE_DIM)])
        return np.asarray(rows, dtype="float32")


@pytest.fixture(autouse=True)
def _patch_embedder(monkeypatch):
    pytest.importorskip("numpy")
    fake = _FakeModel()
    monkeypatch.setattr(
        Embedder,
        "_load_model",
        lambda self: setattr(self, "_model", fake) or fake,
    )
    return fake


def _seed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pkg").mkdir()
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "foo.py").write_text(
        textwrap.dedent(
            '''
            """Foo module."""

            def hello():
                """Say hi."""
                return "hello"


            class Greeter:
                """Greets people."""

                def greet(self, name: str) -> str:
                    """Greet by name."""
                    return f"hi {name}"
            '''
        ).lstrip()
    )
    return repo


def _run_index(argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    code = cli_module.main(argv, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


# 1. Index help works.
def test_index_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["index", "--help"])
    assert exc.value.code == 0


# 2. Happy path: real pipeline runs end-to-end on a tiny fixture repo.
def test_index_succeeds_on_real_repo(tmp_path: Path) -> None:
    pytest.importorskip("faiss")
    repo = _seed_repo(tmp_path)
    index_dir = tmp_path / "index"
    code, stdout, _ = _run_index(
        ["index", str(repo), "--index-dir", str(index_dir), "--model", "fake-model"]
    )
    assert code == 0
    assert "Indexed" in stdout
    assert "chunks" in stdout
    assert (index_dir / "code.index").is_file()
    assert (index_dir / "metadata.json").is_file()


# 3. Verbose mode prints progress messages.
def test_index_verbose_prints_progress(tmp_path: Path) -> None:
    pytest.importorskip("faiss")
    repo = _seed_repo(tmp_path)
    index_dir = tmp_path / "index"
    code, stdout, _ = _run_index(
        [
            "index",
            str(repo),
            "--index-dir",
            str(index_dir),
            "--model",
            "fake-model",
            "--verbose",
        ]
    )
    assert code == 0
    assert "Crawling" in stdout
    assert "Embedding" in stdout
    assert "Writing FAISS index" in stdout


# 4. Invalid repo_path → exit code 2.
def test_index_invalid_repo_path_exits_two(tmp_path: Path) -> None:
    code, _, stderr = _run_index(
        ["index", str(tmp_path / "does-not-exist"), "--index-dir", str(tmp_path / "idx")]
    )
    assert code == 2
    assert "not a directory" in stderr.lower()


# 5. Repo with no Python files → exit 1 + clear message.
def test_index_no_python_files_exits_one(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "readme.md").write_text("hi")
    code, _, stderr = _run_index(
        ["index", str(empty), "--index-dir", str(tmp_path / "idx"), "--model", "fake-model"]
    )
    assert code == 1
    assert "no python files" in stderr.lower()


# 6. Pipeline injection works (factor for unit-style testing).
def test_pipeline_injection_isolates_io(tmp_path: Path) -> None:
    captured = {}

    def fake_pipeline(*, repo_path, index_dir, model_name, batch_size, verbose, log):
        captured.update(
            repo_path=repo_path,
            index_dir=index_dir,
            model_name=model_name,
            batch_size=batch_size,
            verbose=verbose,
        )
        return {
            "total_files": 7,
            "total_chunks": 42,
            "elapsed_ms": 100,
            "index_dir": str(index_dir),
        }

    repo = tmp_path / "repo"
    repo.mkdir()
    code = cli_module.main(
        ["index", str(repo), "--index-dir", str(tmp_path / "idx"), "--batch-size", "16"],
        index_pipeline=fake_pipeline,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert code == 0
    assert captured["batch_size"] == 16
    assert captured["model_name"] == "llama3:8b"  # default
    assert str(captured["repo_path"]).endswith("repo")


# 7. Pipeline exception → exit 1 + error message.
def test_pipeline_exception_exits_one(tmp_path: Path) -> None:
    def boom(**_):
        raise RuntimeError("disk full")

    repo = tmp_path / "repo"
    repo.mkdir()
    out = io.StringIO()
    err = io.StringIO()
    code = cli_module.main(
        ["index", str(repo)],
        index_pipeline=boom,
        stdout=out,
        stderr=err,
    )
    assert code == 1
    assert "indexing failed" in err.getvalue().lower()
    assert "disk full" in err.getvalue()
