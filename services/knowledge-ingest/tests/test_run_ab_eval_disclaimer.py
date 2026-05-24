"""Regression tests for run_ab_eval.py CLI flag semantics (Plan 05-13 Task 1).

Tests:
    test_main_no_flags_raises_not_implemented     — no flags → NotImplementedError with Phase 8 pointer
    test_main_with_stub_flag_produces_disclaimer  — --stub → exit 0, output contains disclaimer phrase
    test_main_with_full_flag_raises_not_implemented — --full → NotImplementedError
    test_skip_eval_flag_removed                   — --skip-eval is an unknown flag (argparse rejects it)

The script is exercised via ``runpy.run_path`` (not as a subprocess) so the test
runs in-process; ``sys.argv`` is patched to simulate CLI invocation. The --output
flag is pointed at a ``tmp_path`` temp file so no CI artefact is produced.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "services"
    / "knowledge-ingest"
    / "scripts"
    / "run_ab_eval.py"
)


def _run_script(argv: list[str], tmp_path: Path | None = None) -> int:
    """Execute run_ab_eval.py via runpy with patched sys.argv.

    Returns the integer exit code from main(). If the script raises
    NotImplementedError it is propagated (callers assert it). If it raises
    SystemExit the exit code is extracted and returned.
    """
    saved_argv = sys.argv[:]
    try:
        sys.argv = ["run_ab_eval.py"] + argv
        result = runpy.run_path(str(_SCRIPT), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    finally:
        sys.argv = saved_argv
    # If __main__ block calls raise SystemExit(main()), control goes through
    # the except above.  If it does not, return 0.
    return 0


def test_main_no_flags_raises_not_implemented(tmp_path: Path) -> None:
    """Invoking run_ab_eval.py with no flags must raise NotImplementedError.

    The error message must reference Phase 8 / KnowledgeCurator so the deferral
    pointer is discoverable from the CLI.
    """
    saved_argv = sys.argv[:]
    try:
        sys.argv = ["run_ab_eval.py"]
        with pytest.raises(NotImplementedError) as exc_info:
            runpy.run_path(str(_SCRIPT), run_name="__main__")
    finally:
        sys.argv = saved_argv

    msg = str(exc_info.value)
    assert "Phase 8" in msg or "KnowledgeCurator" in msg, (
        f"NotImplementedError message must mention Phase 8 or KnowledgeCurator; got: {msg!r}"
    )


def test_main_with_stub_flag_produces_disclaimer(tmp_path: Path) -> None:
    """--stub must exit 0 and the output file must contain the disclaimer phrase."""
    output_path = tmp_path / "eval_out.md"
    # We also need a testset file (the script checks it exists).
    testset_path = tmp_path / "testset.jsonl"
    testset_path.write_text('{"query": "test", "gold": ["SOP-001"]}\n', encoding="utf-8")

    saved_argv = sys.argv[:]
    try:
        sys.argv = [
            "run_ab_eval.py",
            "--stub",
            f"--output={output_path}",
            f"--testset={testset_path}",
        ]
        try:
            runpy.run_path(str(_SCRIPT), run_name="__main__")
        except SystemExit as exc:
            assert int(exc.code) == 0, f"Expected exit 0 with --stub, got {exc.code}"
    finally:
        sys.argv = saved_argv

    assert output_path.exists(), "Output file must be written when --stub is set"
    content = output_path.read_text(encoding="utf-8")
    assert "⚠ Preliminary stub metrics — pending real eval run" in content, (
        "Output file must contain the disclaimer phrase "
        "'⚠ Preliminary stub metrics — pending real eval run'"
    )


def test_main_with_full_flag_raises_not_implemented(tmp_path: Path) -> None:
    """--full must raise NotImplementedError (live eval deferred to Phase 8)."""
    testset_path = tmp_path / "testset.jsonl"
    testset_path.write_text('{"query": "test", "gold": ["SOP-001"]}\n', encoding="utf-8")

    saved_argv = sys.argv[:]
    try:
        sys.argv = [
            "run_ab_eval.py",
            "--full",
            f"--testset={testset_path}",
        ]
        with pytest.raises(NotImplementedError):
            runpy.run_path(str(_SCRIPT), run_name="__main__")
    finally:
        sys.argv = saved_argv


def test_skip_eval_flag_removed(tmp_path: Path) -> None:
    """--skip-eval must be rejected by argparse (legacy flag removed)."""
    saved_argv = sys.argv[:]
    try:
        sys.argv = ["run_ab_eval.py", "--skip-eval"]
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(_SCRIPT), run_name="__main__")
    finally:
        sys.argv = saved_argv

    assert exc_info.value.code != 0, (
        "--skip-eval is a removed flag; argparse must reject it with a non-zero exit"
    )
