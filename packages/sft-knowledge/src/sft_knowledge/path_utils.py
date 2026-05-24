"""path_utils — single canonical source_uri derivation helper (Plan 05-12).

Extracts the duplicated source_uri logic from:
  - packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py (inline block)
  - services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py (_derive_source_uri)

into a single importable helper so both consumers always produce the same URI string,
eliminating the CR-02 silent-drift surface across worktrees, symlinks, and Windows paths.

Threat mitigations (05-12 threat_model):
  - T-05-12-01: single helper eliminates source_uri divergence between parser and orchestrator.
  - T-05-12-02: orchestrator content_hash gate now uses the exact URI the parser will emit.
  - T-05-12-03: Path.resolve() already follows symlinks — workspace paths are not sensitive.
"""

from __future__ import annotations

from pathlib import Path

# Walk up from packages/sft-knowledge/src/sft_knowledge/path_utils.py to workspace root:
#   parents[0] = sft_knowledge   (package directory)
#   parents[1] = src
#   parents[2] = sft-knowledge
#   parents[3] = packages
#   parents[4] = <workspace root>
WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[4]

__all__ = ["WORKSPACE_ROOT", "derive_source_uri"]


def derive_source_uri(path: Path, workspace_root: Path | None = None) -> str:
    """Return ``corpus://<rel-posix-path>`` if path is under workspace_root.

    Falls back to ``corpus://<absolute-posix-path-with-leading-slashes-stripped>``
    when path is outside the workspace (e.g. pytest tmp_path, absolute upload paths).

    Args:
        path: The filesystem path to the document (resolved via ``Path.resolve()``).
        workspace_root: Override for the workspace root. Defaults to the module constant
            ``WORKSPACE_ROOT`` (computed at import time from ``__file__``). Tests may
            inject a custom root to exercise the fallback branch without a real workspace.

    Returns:
        A ``corpus://`` URI string using forward slashes only (no ``os.sep`` divergence).
    """
    root = workspace_root if workspace_root is not None else WORKSPACE_ROOT
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root)
        return f"corpus://{rel.as_posix()}"
    except ValueError:
        # Path not under workspace root (e.g. tmp_path fixture, absolute out-of-workspace input).
        # Strip any leading slashes to avoid double-slash after the scheme:
        #   "corpus://" + "/absolute/path" → "corpus:////absolute/path"  (WRONG)
        #   "corpus://" + "absolute/path"  → "corpus://absolute/path"   (CORRECT)
        # We use lstrip('/') instead of lstrip(os.sep) for cross-platform consistency:
        # on Windows, os.sep is '\\', but as_posix() always produces forward slashes.
        return f"corpus://{resolved.as_posix().lstrip('/')}"
