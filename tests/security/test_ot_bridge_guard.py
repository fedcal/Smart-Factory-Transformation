"""Test AST OT Bridge write-block guard (SEC-06, SC-5).

Test SC-5: l'AST check su services/ot-bridge/src/svc_ot_bridge/*.py NON trova
chiamate a write_value/call_method/set_attribute/write_attributes — nessun path
write OPC-UA. Sostituisce il grep commentato in opcua_client.py con un assert
pytest strutturato (RESEARCH Pattern 7).

Plan 11-03, Task 3 (SEC-06).
"""

from __future__ import annotations

import ast
import pathlib

# OT Bridge source directory — path assoluto basato su __file__ per evitare
# dipendenza dal CWD (WR-05: test falliva se pytest invocato fuori dalla root).
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_OT_BRIDGE_SRC = _REPO_ROOT / "services" / "ot-bridge" / "src" / "svc_ot_bridge"

# Pattern write API OPC-UA (asyncua e librerie compatibili)
# D-51: SUBSCRIBER ONLY — nessuna di queste API deve essere chiamata.
_WRITE_PATTERNS: frozenset[str] = frozenset({
    "write_value",        # asyncua Node.write_value()
    "write_attributes",   # asyncua Node.write_attributes() (batch write — API reale asyncua)
    "set_attribute",      # asyncua Node.set_attribute()
    "call_method",        # asyncua Node.call_method() — esegue metodi OPC-UA (write semantics)
    "set_value",          # asyncua Node.set_value() — write semantics (CR-04, aggiunto per allineamento CI grep)
})


def test_ot_bridge_has_no_write_api_calls():
    """SC-5: nessun modulo in ot-bridge chiama API write OPC-UA.

    Analizza l'AST Python di tutti i *.py in svc_ot_bridge e verifica che
    nessun AttributeNode abbia .attr in WRITE_PATTERNS.

    Più robusto di grep: il pattern AST non produce falsi positivi su
    commenti o stringhe che menzionano i nomi delle API.
    """
    assert _OT_BRIDGE_SRC.exists(), (
        f"OT Bridge source directory non trovata: {_OT_BRIDGE_SRC.resolve()} — "
        "eseguire i test dalla root del progetto"
    )

    violations: list[str] = []

    for py_file in sorted(_OT_BRIDGE_SRC.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            violations.append(f"{py_file}: SyntaxError — {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in _WRITE_PATTERNS:
                # Raccoglie violazione con file + linea + attributo
                line = getattr(node, "lineno", "?")
                violations.append(
                    f"{py_file.relative_to(_OT_BRIDGE_SRC.parent.parent.parent)}:{line} → .{node.attr}()"
                )

    assert not violations, (
        "SEC-06 / SC-5 VIOLATION: OT Bridge contiene chiamate a write API OPC-UA "
        "(D-51 data-diode violato):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_ot_bridge_src_contains_py_files():
    """Sanity check: la directory OT Bridge contiene file Python da analizzare."""
    assert _OT_BRIDGE_SRC.exists(), (
        f"Directory {_OT_BRIDGE_SRC} non trovata — eseguire dalla root del progetto"
    )
    py_files = list(_OT_BRIDGE_SRC.rglob("*.py"))
    assert py_files, (
        f"Nessun file .py trovato in {_OT_BRIDGE_SRC} — "
        "la guardia AST non ha analizzato nulla (false-green risk)"
    )


def test_ot_bridge_write_pattern_set_non_empty():
    """Sanity check: il set WRITE_PATTERNS contiene esattamente i 5 pattern attesi (CR-04).

    Set unificato con il grep CI (ci.yml Gate 3):
    set_value aggiunto per coprire asyncua Node.set_value() con write semantics.
    """
    expected = frozenset({
        "write_value", "write_attributes", "set_attribute", "call_method", "set_value"
    })
    assert _WRITE_PATTERNS == expected, (
        f"WRITE_PATTERNS cambiato inaspettatamente: {_WRITE_PATTERNS!r}"
    )
