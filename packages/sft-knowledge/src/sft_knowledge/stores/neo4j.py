"""Neo4jGraphBuilder — UNWIND MERGE per Machine/Part/FailureMode/SOP + DOCUMENTED_BY.

Layer di persistenza grafo (D-65 + D-69) per il knowledge layer Phase 5.

Garanzie:
    - Tutte le Cypher statement sono COSTANTI modulo (zero f-string sui dati);
      i valori delle property passano SOLO via `$param` (T-05-08-01 mitigation).
    - Tutti gli statement usano `MERGE ... ON CREATE SET ... ON MATCH SET ...` →
      re-run idempotenti, nessun duplicato (D-65).
    - `merge_sop` adotta SOP.id = `{frontmatter.id}@{version}` per supportare
      versioni multiple coesistenti dello stesso SOP_ID logico (D-69, RESEARCH §5).
    - Batch size default 500 nodi per UNWIND (D-69 / claudes_discretion).

Threat model:
    - T-05-08-01 Cypher injection: i valori utente fluiscono SOLO via `$param`;
      le label restano stringhe fisse nelle Cypher constants → nessuna superficie
      di label injection.
    - T-05-08-04 Dual-write inconsistency: l'ordine Neo4j-first è enforced dal
      pipeline orchestrator (Plan 05-10); qui esponiamo solo i primitives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver
    from sft_assets import Asset
    from sft_domain.failure_modes.models import FailureMode

    from sft_knowledge.parsers.base import ParsedDoc

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Cypher constants (Shared Pattern 4 — module-level, $-param only).
# ---------------------------------------------------------------------------

# Machine MERGE: id = asset_id, family = asset_family.value.
_MERGE_MACHINE_CYPHER = """
UNWIND $machine_rows AS row
MERGE (m:Machine {id: row.id})
  ON CREATE SET m.family = row.family,
                m.line_id = row.line_id,
                m.opcua_namespace = row.opcua_namespace,
                m.created_at = datetime()
  ON MATCH  SET m.family = row.family,
                m.line_id = row.line_id,
                m.opcua_namespace = row.opcua_namespace,
                m.updated_at = datetime()
"""

# Part MERGE + HAS_PART edge. Le Part sono shared per asset_family (es. la
# Part "warp" è condivisa da tutte le Machine "loom"); l'id Part è
# "{family}:{part_name}" per evitare collisioni tra famiglie.
_MERGE_PART_AND_LINK_CYPHER = """
UNWIND $part_rows AS row
MERGE (p:Part {id: row.id})
  ON CREATE SET p.name = row.name,
                p.family = row.family,
                p.created_at = datetime()
WITH p, row
MATCH (m:Machine {family: row.family})
MERGE (m)-[:HAS_PART]->(p)
"""

# FailureMode MERGE.
_MERGE_FAILURE_MODE_CYPHER = """
UNWIND $fm_rows AS row
MERGE (f:FailureMode {id: row.id})
  ON CREATE SET f.name_it = row.name_it,
                f.name_en = row.name_en,
                f.severity = row.severity,
                f.asset_families = row.asset_families,
                f.created_at = datetime()
  ON MATCH  SET f.name_it = row.name_it,
                f.name_en = row.name_en,
                f.severity = row.severity,
                f.asset_families = row.asset_families,
                f.updated_at = datetime()
"""

# Part → FailureMode link via (part_id, failure_mode_id).
_LINK_PART_TO_FAILURE_MODE_CYPHER = """
UNWIND $link_rows AS row
MATCH (p:Part {id: row.part_id})
MATCH (f:FailureMode {id: row.failure_mode_id})
MERGE (p)-[r:HAS_FAILURE_MODE]->(f)
  ON CREATE SET r.created_at = datetime()
"""

# SOP MERGE — id = "{frontmatter.id}@{version}" (D-69 multi-version).
_MERGE_SOP_CYPHER = """
UNWIND $sop_rows AS row
MERGE (s:SOP {id: row.sop_id})
  ON CREATE SET s.version = row.version,
                s.lang = row.lang,
                s.title = row.title,
                s.source_uri = row.source_uri,
                s.created_at = datetime()
  ON MATCH  SET s.version = row.version,
                s.lang = row.lang,
                s.title = row.title,
                s.source_uri = row.source_uri,
                s.updated_at = datetime()
"""

# FailureMode → SOP link (DOCUMENTED_BY).
_LINK_FAILURE_MODE_TO_SOP_CYPHER = """
UNWIND $link_rows AS row
MATCH (f:FailureMode {id: row.failure_mode_id})
MATCH (s:SOP {id: row.sop_id})
MERGE (f)-[r:DOCUMENTED_BY]->(s)
  ON CREATE SET r.created_at = datetime()
"""


_DEFAULT_BATCH_SIZE: int = 500


def _chunked(rows: list[Any], size: int) -> list[list[Any]]:
    """Splitta `rows` in batch di lunghezza ≤ `size`."""
    return [rows[i : i + size] for i in range(0, len(rows), size)]


class Neo4jGraphBuilder:
    """Builder grafo con UNWIND MERGE parametrizzato (D-65).

    Usage:
        builder = Neo4jGraphBuilder(driver=async_neo4j_driver)
        await builder.merge_machines_from_assets(load_assets())
        await builder.merge_failure_modes(load_failure_modes())
        await builder.merge_sop(parsed_doc, failure_mode_ids=["broken_end"])
    """

    def __init__(
        self,
        driver: AsyncDriver,
        batch_size: int = _DEFAULT_BATCH_SIZE,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(f"batch_size deve essere > 0, got {batch_size}")
        self._driver = driver
        self.batch_size = batch_size
        self._log = logger.bind(component="neo4j_graph_builder")

    # ------------------------------------------------------------------
    # Machine + Part seeding from sft-assets registry.
    # ------------------------------------------------------------------

    async def merge_machines_from_assets(self, assets) -> int:
        """MERGE Machine nodes da `sft_assets.Asset` (D-65 + D-45).

        Asset model in sft-assets non espone `parts` direttamente: le Part
        vengono create da `merge_failure_modes` (deriva da failure_modes.yaml)
        e linkate alle Machine via `Machine.family == Part.family`.

        Args:
            assets: iterable di sft_assets.Asset.

        Returns:
            Numero di Machine merged.
        """
        machine_rows = [
            {
                "id": a.asset_id,
                # AssetFamily è un Enum string; Neo4j salva il valore .value.
                "family": getattr(a.asset_family, "value", str(a.asset_family)),
                "line_id": a.line_id,
                "opcua_namespace": a.opcua_namespace,
            }
            for a in assets
        ]
        if not machine_rows:
            self._log.warning("merge_machines_noop", reason="empty_assets")
            return 0

        total = 0
        try:
            async with self._driver.session(database="neo4j") as session:
                for batch in _chunked(machine_rows, self.batch_size):
                    await session.run(
                        _MERGE_MACHINE_CYPHER,
                        machine_rows=batch,
                    )
                    total += len(batch)
        except Exception as exc:
            self._log.error("merge_machines_failed", error=str(exc))
            raise

        self._log.info("merge_machines_done", count=total)
        return total

    # ------------------------------------------------------------------
    # FailureMode + Part seeding from failure_modes.yaml.
    # ------------------------------------------------------------------

    async def merge_failure_modes(self, fms) -> int:
        """MERGE FailureMode + Part + HAS_PART/HAS_FAILURE_MODE.

        Per ciascun FailureMode crea:
            - 1 nodo FailureMode (id = fm.id).
            - 1 nodo Part per ogni (family, part_name) ∈ asset_families × parts
              con id Part = "{family}:{part_name}".
            - edge HAS_PART (Machine{family} → Part) tramite _MERGE_PART_AND_LINK.
            - edge HAS_FAILURE_MODE (Part → FailureMode).

        Args:
            fms: iterable di sft_domain.failure_modes.models.FailureMode.

        Returns:
            Numero di FailureMode merged.
        """
        fm_list = list(fms)
        if not fm_list:
            self._log.warning("merge_failure_modes_noop", reason="empty_fms")
            return 0

        fm_rows = [
            {
                "id": fm.id,
                "name_it": fm.name_it,
                "name_en": fm.name_en,
                "severity": fm.severity,
                "asset_families": list(fm.asset_families),
            }
            for fm in fm_list
        ]

        # Costruisci Part rows: una Part per (family, part_name) ∈ fm × parts.
        part_rows_set: dict[tuple[str, str], dict[str, str]] = {}
        link_rows: list[dict[str, str]] = []
        for fm in fm_list:
            for family in fm.asset_families:
                for part_name in fm.parts:
                    pid = f"{family}:{part_name}"
                    part_rows_set[(family, part_name)] = {
                        "id": pid,
                        "name": part_name,
                        "family": family,
                    }
                    link_rows.append(
                        {"part_id": pid, "failure_mode_id": fm.id}
                    )
        part_rows = list(part_rows_set.values())

        try:
            async with self._driver.session(database="neo4j") as session:
                # 1. MERGE FailureMode.
                for batch in _chunked(fm_rows, self.batch_size):
                    await session.run(_MERGE_FAILURE_MODE_CYPHER, fm_rows=batch)
                # 2. MERGE Part + HAS_PART edge.
                for batch in _chunked(part_rows, self.batch_size):
                    await session.run(_MERGE_PART_AND_LINK_CYPHER, part_rows=batch)
                # 3. MERGE Part → FailureMode.
                for batch in _chunked(link_rows, self.batch_size):
                    await session.run(
                        _LINK_PART_TO_FAILURE_MODE_CYPHER, link_rows=batch
                    )
        except Exception as exc:
            self._log.error("merge_failure_modes_failed", error=str(exc))
            raise

        self._log.info(
            "merge_failure_modes_done",
            count_fm=len(fm_rows),
            count_part=len(part_rows),
            count_link=len(link_rows),
        )
        return len(fm_rows)

    # ------------------------------------------------------------------
    # SOP MERGE + DOCUMENTED_BY edges.
    # ------------------------------------------------------------------

    async def merge_sop(
        self,
        parsed_doc: ParsedDoc,
        failure_mode_ids: list[str],
    ) -> int:
        """MERGE SOP node + DOCUMENTED_BY edges da `failure_mode_ids`.

        SOP.id = `{frontmatter.id}@{version}` (D-69 multi-version coexistence).

        Args:
            parsed_doc: ParsedDoc dal MarkdownParser.
            failure_mode_ids: lista di FailureMode.id (Plan 05-10 orchestrator
                              fornisce la heuristica di matching tag→fm.id).

        Returns:
            Numero di edge DOCUMENTED_BY creati + 1 (per il SOP node).
        """
        fm_id = str(parsed_doc.frontmatter.get("id", "")).strip()
        if not fm_id:
            raise ValueError(
                "parsed_doc.frontmatter['id'] obbligatorio per merge_sop"
            )
        sop_id = f"{fm_id}@{parsed_doc.version}"

        sop_rows = [
            {
                "sop_id": sop_id,
                "version": parsed_doc.version,
                "lang": parsed_doc.lang,
                "title": str(parsed_doc.frontmatter.get("title", "")),
                "source_uri": parsed_doc.source_uri,
            }
        ]
        link_rows = [
            {"failure_mode_id": fm_id, "sop_id": sop_id}
            for fm_id in failure_mode_ids
        ]

        try:
            async with self._driver.session(database="neo4j") as session:
                await session.run(_MERGE_SOP_CYPHER, sop_rows=sop_rows)
                if link_rows:
                    await session.run(
                        _LINK_FAILURE_MODE_TO_SOP_CYPHER, link_rows=link_rows
                    )
        except Exception as exc:
            self._log.error(
                "merge_sop_failed",
                sop_id=sop_id,
                error=str(exc),
            )
            raise

        self._log.info(
            "merge_sop_done",
            sop_id=sop_id,
            edges=len(link_rows),
        )
        return len(link_rows) + 1


__all__ = ["Neo4jGraphBuilder"]
