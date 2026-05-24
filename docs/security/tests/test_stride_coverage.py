"""Test di copertura STRIDE (SC-4) — Plan 11-05, Task 1.

Verifica che STRIDE-threat-model.md contenga tutte le 18 celle (6 categorie × 3 superfici)
e che ciascuna celle citi almeno un riferimento a codice (pattern .py o file:funzione).

Eseguire dalla root del progetto:
    uv run pytest docs/security/tests/test_stride_coverage.py -x -q
"""

from __future__ import annotations

import pathlib
import re

# ---------------------------------------------------------------------------
# Percorso del documento STRIDE
# ---------------------------------------------------------------------------

_STRIDE_DOC = pathlib.Path("docs/security/STRIDE-threat-model.md")

# ---------------------------------------------------------------------------
# Costanti di copertura attesa (SC-4)
# ---------------------------------------------------------------------------

# Categorie STRIDE attese (header di sezione nel documento)
_STRIDE_CATEGORIES: tuple[str, ...] = (
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
)

# Superfici attese (cellule per ogni categoria)
_SURFACES: tuple[str, ...] = (
    "IT/OT boundary",
    "RAG ingest",
    "Agent orchestration",
)

# Pattern per rilevare un riferimento a codice reale:
# - path/to/file.py:function_name
# - services/foo/src/bar.py
# - packages/baz/src/something.py
# - `file.py` (inline code fence)
# - .ts file (frontend)
_CODE_REF_PATTERN = re.compile(
    r"(?:"
    r"[\w/\-]+\.py"           # any .py path
    r"|[\w/\-]+\.ts"          # any .ts path
    r")"
    ,
    re.IGNORECASE,
)

# Pattern per identificare le sezioni di categoria STRIDE (es. "### S — Spoofing")
_CATEGORY_HEADER_PATTERN = re.compile(
    r"^###\s+[A-Z]\s+—\s+(" + "|".join(re.escape(c) for c in _STRIDE_CATEGORIES) + r")\b",
    re.MULTILINE,
)

# Pattern per identificare le celle superficie (es. "#### S1: IT/OT boundary")
_CELL_HEADER_PATTERN = re.compile(
    r"^####\s+[A-Z]\d+:\s+(.+)$",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Helper: parse celle dal documento
# ---------------------------------------------------------------------------


def _parse_cells(doc_text: str) -> dict[str, list[dict[str, str]]]:
    """Parsa le celle STRIDE dal testo del documento.

    Ritorna un dict: {categoria: [{"surface": ..., "body": ...}, ...]}
    """
    result: dict[str, list[dict[str, str]]] = {}

    # Split per categorie STRIDE (sezioni ###)
    category_sections = _CATEGORY_HEADER_PATTERN.split(doc_text)
    # split() ritorna: [testo_prima, nome_cat1, testo1, nome_cat2, testo2, ...]
    # I nomi delle categorie sono agli indici dispari (1, 3, 5, ...)

    if len(category_sections) < 3:
        return result

    for i in range(1, len(category_sections), 2):
        category_name = category_sections[i].strip()
        category_body = category_sections[i + 1] if (i + 1) < len(category_sections) else ""

        # Split per celle superficie (sezioni ####)
        cell_parts = _CELL_HEADER_PATTERN.split(category_body)
        # cell_parts: [pre_text, surface1, body1, surface2, body2, ...]

        cells: list[dict[str, str]] = []
        for j in range(1, len(cell_parts), 2):
            surface_raw = cell_parts[j].strip()
            cell_body = cell_parts[j + 1] if (j + 1) < len(cell_parts) else ""
            cells.append({"surface": surface_raw, "body": cell_body})

        result[category_name] = cells

    return result


# ---------------------------------------------------------------------------
# Test 1: documento esiste e non è vuoto
# ---------------------------------------------------------------------------


def test_stride_doc_exists():
    """STRIDE-threat-model.md deve esistere nella directory docs/security/."""
    assert _STRIDE_DOC.exists(), (
        f"STRIDE threat model non trovato: {_STRIDE_DOC.resolve()} — "
        "eseguire i test dalla root del progetto"
    )
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    assert len(content) > 1000, (
        f"STRIDE doc troppo corto ({len(content)} caratteri) — probabilmente vuoto o incompleto"
    )


# ---------------------------------------------------------------------------
# Test 2: tutte le 6 categorie STRIDE presenti
# ---------------------------------------------------------------------------


def test_stride_all_categories_present():
    """Tutte le 6 categorie STRIDE devono essere presenti come sezioni ###."""
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    missing: list[str] = []
    for category in _STRIDE_CATEGORIES:
        # Cerca pattern "### X — Category" nel documento
        if not re.search(rf"###\s+[A-Z]\s+—\s+{re.escape(category)}", content):
            missing.append(category)

    assert not missing, (
        f"Categorie STRIDE mancanti nel documento: {missing}. "
        f"Tutte le 6 categorie sono obbligatorie (SC-4)."
    )


# ---------------------------------------------------------------------------
# Test 3: 18 celle presenti (6 categorie × 3 superfici)
# ---------------------------------------------------------------------------


def test_stride_18_cells_present():
    """Devono essere presenti esattamente 18 celle STRIDE (6 categorie × 3 superfici).

    Ogni cella è identificata da un header #### XX: Surface Name.
    """
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    cells = _parse_cells(content)

    total_cells = sum(len(cell_list) for cell_list in cells.values())

    assert total_cells >= 18, (
        f"Trovate solo {total_cells} celle STRIDE, attese 18 (6×3). "
        f"Distribuzione: { {k: len(v) for k, v in cells.items()} }"
    )


# ---------------------------------------------------------------------------
# Test 4: ogni categoria ha esattamente 3 celle superficie
# ---------------------------------------------------------------------------


def test_stride_each_category_has_3_surfaces():
    """Ogni categoria STRIDE deve avere celle per tutte e 3 le superfici."""
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    cells = _parse_cells(content)

    missing: list[str] = []
    for category in _STRIDE_CATEGORIES:
        if category not in cells:
            missing.append(f"{category}: CATEGORIA MANCANTE")
            continue
        cell_count = len(cells[category])
        if cell_count < 3:
            missing.append(f"{category}: solo {cell_count} celle (attese 3)")

    assert not missing, (
        f"Copertura superfici incompleta:\n" + "\n".join(f"  - {m}" for m in missing)
    )


# ---------------------------------------------------------------------------
# Test 5: ogni cella cita almeno un riferimento a codice reale (.py o .ts)
# ---------------------------------------------------------------------------


def test_stride_all_cells_have_code_reference():
    """Ogni cella STRIDE deve citare almeno un file .py o .ts come riferimento al codice.

    Realizza il requisito SC-4: "mitigazione mappata a codice reale".
    """
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    cells = _parse_cells(content)

    missing_code_refs: list[str] = []

    for category, cell_list in cells.items():
        for cell in cell_list:
            surface = cell["surface"]
            body = cell["body"]
            # Cerca almeno un riferimento .py o .ts nel body della cella
            if not _CODE_REF_PATTERN.search(body):
                missing_code_refs.append(f"{category} / {surface}")

    assert not missing_code_refs, (
        f"Le seguenti celle non citano un riferimento a codice (.py/.ts):\n"
        + "\n".join(f"  - {r}" for r in missing_code_refs)
        + "\nOgni cella deve mappare la mitigazione a un file sorgente (SC-4)."
    )


# ---------------------------------------------------------------------------
# Test 6: verifica pattern specifici richiesti da SC-4 / PLAN.md
# ---------------------------------------------------------------------------


def test_stride_required_mitigations_referenced():
    """Verifica che le mitigazioni chiave siano citate nel documento STRIDE.

    Controlla i riferimenti specifici indicati nel PLAN.md:
    - sanitize_document (SEC-04, 11-03)
    - RESTRICTED_DOC_ACCESS (SEC-07, 11-03)
    - NatsHeaderCarrier (11-01)
    - recursion_limit (CORE-03)
    - test_ot_bridge_guard (SEC-06, 11-03)
    """
    content = _STRIDE_DOC.read_text(encoding="utf-8")

    required_patterns: list[tuple[str, str]] = [
        ("sanitize_document", "SEC-04: sanitizer anti prompt-injection"),
        ("RESTRICTED_DOC_ACCESS", "SEC-07: restricted document access audit"),
        ("NatsHeaderCarrier", "11-01: NATS OTEL carrier W3C traceparent"),
        ("recursion_limit", "CORE-03: LangGraph recursion limit guard"),
        ("test_ot_bridge_guard", "SEC-06: AST guard OT Bridge no-write"),
        ("build_acl_filter", "SEC-07: Qdrant ACL pre-filter"),
    ]

    missing: list[str] = []
    for pattern, description in required_patterns:
        if pattern not in content:
            missing.append(f"{pattern!r} — {description}")

    assert not missing, (
        f"Mitigazioni obbligatorie non citate nel STRIDE doc:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )


# ---------------------------------------------------------------------------
# Test 7: frontmatter dichiara cells: 18
# ---------------------------------------------------------------------------


def test_stride_frontmatter_cells_count():
    """Il frontmatter YAML deve dichiarare cells: 18."""
    content = _STRIDE_DOC.read_text(encoding="utf-8")
    # Cerca "cells: 18" nel frontmatter (tra i due ---)
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert frontmatter_match, "STRIDE doc non ha frontmatter YAML valido"
    frontmatter = frontmatter_match.group(1)
    assert "cells: 18" in frontmatter, (
        f"Frontmatter non dichiara 'cells: 18'. Frontmatter trovato:\n{frontmatter}"
    )
