"""Unit tests for `sft_knowledge.embedding.bge_m3.BgeM3Embedder` (Plan 05-07 Task 1).

Strategy:
    - Mock both backends (FlagEmbedding + fastembed) using monkeypatch on `sys.modules`
      so we exercise the import-fallback ladder WITHOUT loading the real ~2GB model.
    - One opt-in `@pytest.mark.gpu` test loads the real FlagEmbedding model; skipped by
      default on CPU CI.

Covers must-haves from PLAN.md:
    * singleton identity (`_get_model()` returns same object on 2nd call)
    * 1024-D dense output shape via mocked FlagEmbedding
    * fastembed fallback when FlagEmbedding import fails → sparse_weights empty
    * RuntimeError when BOTH backends are unavailable
    * `to_qdrant_sparse` filters UNK tokens + len(indices)==len(values)
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_singleton() -> None:
    """Clear the @lru_cache on `_get_model` so each test starts from a cold cache."""
    from sft_knowledge.embedding import bge_m3 as mod

    mod._get_model.cache_clear()


@pytest.fixture(autouse=True)
def _clear_singleton() -> None:
    """Reset the lazy singleton before AND after each test (avoid cross-test pollution)."""
    _reset_singleton()
    yield
    _reset_singleton()


def _make_flagembedding_stub(
    dense_shape: tuple[int, int] = (1, 1024),
    lexical: list[dict[str, float]] | None = None,
    tokenizer: Any | None = None,
) -> types.ModuleType:
    """Build a fake `FlagEmbedding` module exposing `BGEM3FlagModel` for monkeypatching."""
    fake_module = types.ModuleType("FlagEmbedding")

    class _StubBGEM3FlagModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.init_args = args
            self.init_kwargs = kwargs
            self.tokenizer = tokenizer

        def encode(
            self,
            texts: list[str],
            **kwargs: Any,
        ) -> dict[str, Any]:
            n = len(texts)
            dense = [np.zeros(dense_shape[1], dtype=np.float32) for _ in range(n)]
            sparse = lexical if lexical is not None else [{"hello": 0.5} for _ in range(n)]
            return {"dense_vecs": dense, "lexical_weights": sparse}

    fake_module.BGEM3FlagModel = _StubBGEM3FlagModel  # type: ignore[attr-defined]
    return fake_module


def _make_fastembed_stub() -> types.ModuleType:
    """Build a fake `fastembed` module exposing `TextEmbedding`."""
    fake_module = types.ModuleType("fastembed")

    class _StubTextEmbedding:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def embed(self, texts: list[str]):
            for _ in texts:
                yield np.zeros(1024, dtype=np.float32)

    fake_module.TextEmbedding = _StubTextEmbedding  # type: ignore[attr-defined]
    return fake_module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_singleton_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Due chiamate a `_get_model()` ritornano lo stesso oggetto (lru_cache singleton)."""
    monkeypatch.setitem(sys.modules, "FlagEmbedding", _make_flagembedding_stub())

    from sft_knowledge.embedding import bge_m3 as mod

    a = mod._get_model()
    b = mod._get_model()
    assert a is b, "Singleton MUST return identical object on second call"


def test_encode_returns_1024d_dense(monkeypatch: pytest.MonkeyPatch) -> None:
    """`encode()` ritorna `dense_vecs` di shape (1024,) e `sparse_weights` coerente."""
    monkeypatch.setitem(
        sys.modules,
        "FlagEmbedding",
        _make_flagembedding_stub(
            dense_shape=(1, 1024),
            lexical=[{"hello": 0.5, "world": 0.3}],
        ),
    )

    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder

    embedder = BgeM3Embedder()
    out = embedder.encode(["hello world"])

    assert len(out.dense_vecs) == 1
    assert out.dense_vecs[0].shape == (1024,)
    assert len(out.sparse_weights) == 1
    assert out.sparse_weights[0] == {"hello": 0.5, "world": 0.3}


def test_fastembed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando FlagEmbedding non è importabile, ricade su fastembed (sparse vuoto)."""
    # Forza ImportError per FlagEmbedding.
    monkeypatch.setitem(sys.modules, "FlagEmbedding", None)
    # Inietta stub fastembed.
    monkeypatch.setitem(sys.modules, "fastembed", _make_fastembed_stub())

    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder

    embedder = BgeM3Embedder()
    out = embedder.encode(["ciao mondo", "hello world"])

    assert len(out.dense_vecs) == 2
    assert out.dense_vecs[0].shape == (1024,)
    # Modalità degradata: fastembed non espone sparse weights.
    assert out.sparse_weights == [{}, {}]


def test_runtime_error_when_no_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Se né FlagEmbedding né fastembed sono disponibili → `RuntimeError` esplicito."""
    monkeypatch.setitem(sys.modules, "FlagEmbedding", None)
    monkeypatch.setitem(sys.modules, "fastembed", None)

    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder

    embedder = BgeM3Embedder()
    with pytest.raises(RuntimeError, match="FlagEmbedding or fastembed"):
        embedder.encode(["x"])


def test_to_qdrant_sparse_filters_unk(monkeypatch: pytest.MonkeyPatch) -> None:
    """`to_qdrant_sparse` filtra i token che mappano su `unk_token_id`."""
    fake_tokenizer = MagicMock()
    fake_tokenizer.unk_token_id = 0
    # Mapping: "hello"→101, "world"→102, "xyz"→0 (UNK).
    mapping = {"hello": 101, "world": 102, "xyz": 0}
    fake_tokenizer.convert_tokens_to_ids.side_effect = lambda tok: mapping[tok]

    monkeypatch.setitem(
        sys.modules,
        "FlagEmbedding",
        _make_flagembedding_stub(tokenizer=fake_tokenizer),
    )

    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder

    embedder = BgeM3Embedder()
    lexical = {"hello": 0.5, "world": 0.3, "xyz": 0.9}
    sv = embedder.to_qdrant_sparse(lexical)

    # "xyz" filtered → solo hello + world rimangono.
    assert sorted(sv.indices) == [101, 102]
    assert len(sv.indices) == len(sv.values)
    # Pesi corrispondenti agli indici (ordine indipendente — ricostruzione via dict).
    pairs = dict(zip(sv.indices, sv.values))
    assert pairs[101] == pytest.approx(0.5)
    assert pairs[102] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Real-model integration test — only on GPU runners (or willing to wait on CPU)
# ---------------------------------------------------------------------------


@pytest.mark.gpu
@pytest.mark.integration
def test_real_bge_m3_loads() -> None:
    """Carica il vero modello BGE-M3 ed embedda una stringa.

    Skippato di default su CI CPU per via dei ~2GB di download + 30s+ di inferenza CPU.
    Esegue: `nx run sft-knowledge:test --args="-m 'gpu' -v"` per attivarlo.
    """
    try:
        importlib.import_module("FlagEmbedding")
    except ImportError:
        pytest.skip("FlagEmbedding non installato (fallback fastembed non testa il modello reale)")

    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder

    embedder = BgeM3Embedder()
    out = embedder.encode(["hello world"])
    assert len(out.dense_vecs) == 1
    assert out.dense_vecs[0].shape == (1024,)
    assert isinstance(out.sparse_weights[0], dict)
    assert len(out.sparse_weights[0]) > 0
