"""Export the FastAPI OpenAPI 3.1 spec to packages/sft-contracts/openapi.json.

Usage (from repo root):
    cd apps/api-gateway && uv run python ../../packages/sft-contracts/scripts/generate-openapi.py
    # OR from repo root:
    uv --directory apps/api-gateway run python packages/sft-contracts/scripts/generate-openapi.py

The script resolves the output path relative to this file's own location so it
works correctly regardless of the caller's cwd.

Requirements: svc_api_gateway must be installed in the api-gateway venv (it
always is — the gateway pyproject declares it as the project package).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve output path: always <repo-root>/packages/sft-contracts/openapi.json
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_CONTRACTS_DIR = _SCRIPT_DIR.parent
_OUTPUT = _CONTRACTS_DIR / "openapi.json"


def _build_openapi_schema() -> dict:
    """Import build_app() and return the generated OpenAPI schema dict."""
    try:
        from svc_api_gateway.main import build_app  # noqa: PLC0415
    except ImportError as exc:
        print(  # noqa: T201
            f"ERROR: cannot import svc_api_gateway — run this script from the "
            f"apps/api-gateway venv (uv run python ...).\n  {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    app = build_app()
    return app.openapi()


def main() -> None:
    schema = _build_openapi_schema()

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")

    # Validate key models are present (SRV-05 guard).
    schemas = schema.get("components", {}).get("schemas", {})
    required_models = {"KpiSnapshot", "LoginRequest", "LoginResponse", "MeResponse"}
    missing = required_models - schemas.keys()
    if missing:
        print(  # noqa: T201
            f"ERROR: required models missing from OpenAPI schema: {sorted(missing)}",
            file=sys.stderr,
        )
        sys.exit(2)

    print(  # noqa: T201
        f"openapi.json written to {_OUTPUT}\n"
        f"  schemas exported: {len(schemas)}\n"
        f"  required models present: {sorted(required_models)}"
    )


if __name__ == "__main__":
    main()
