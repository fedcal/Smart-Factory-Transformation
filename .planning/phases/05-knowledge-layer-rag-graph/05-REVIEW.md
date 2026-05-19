---
phase: 05-knowledge-layer-rag-graph
reviewed: 2026-05-19T13:27:06Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - packages/sft-knowledge/src/sft_knowledge/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/models.py
  - packages/sft-knowledge/src/sft_knowledge/parsers/base.py
  - packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
  - packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
  - packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
  - packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
  - packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
  - packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
  - packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py
  - packages/sft-knowledge/src/sft_knowledge/tools/rag.py
  - packages/sft-knowledge/src/sft_knowledge/tools/graph.py
  - packages/sft-knowledge/src/sft_knowledge/memory/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py
  - packages/sft-agents/src/sft_agents/memory/__init__.py
  - packages/sft-domain/src/sft_domain/failure_modes/models.py
  - packages/sft-domain/src/sft_domain/failure_modes/_loader.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/state.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py
  - services/knowledge-ingest/scripts/generate_rag_testset.py
  - services/knowledge-ingest/scripts/run_ab_eval.py
  - services/knowledge-ingest/scripts/spot_check_testset.py
  - scripts/migrate-sop-acl.py
  - scripts/qdrant-bootstrap.py
  - scripts/neo4j-bootstrap.py
  - scripts/validate-failure-modes.py
  - scripts/validate-corpus-frontmatter.py
  - infra/migrations/timescale/006_create_ingest_state.sql
  - infra/compose/core.yml
  - infra/helm/charts/neo4j/values.yaml
  - infra/helm/charts/neo4j/templates/statefulset.yaml
  - .github/workflows/reindex.yml
findings:
  critical: 4
  warning: 13
  info: 6
  total: 23
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-05-19T13:27:06Z
**Depth:** standard
**Files Reviewed:** 27 source files (scoped from `05-NN-*-SUMMARY.md` `key-files.created` + `key-files.modified`)
**Status:** issues_found

## Riepilogo

Il knowledge layer Phase 5 e' funzionalmente completo e i gate hard (ACL pre-filter,
parametrizzazione SQL/Cypher, deterministic point IDs, dual-write order) sono rispettati
sul percorso principale. Tuttavia la revisione adversariale ha identificato:

- **4 BLOCKER**: una superficie di Cypher injection raggiungibile bypassando il
  validation schema LangChain (`TraverseGraphTool._arun`), una I/O bloccante in un
  percorso `async def`, una divergenza di derivazione `source_uri` tra orchestratore e
  parser che puo' produrre state drift silente, e default password hardcoded inconsistenti
  cross-componente (compose/CI/values.yaml/CLI) che rompono il bootstrap in produzione
  quando non c'e' override e creano superficie di credential reuse.
- **13 WARNING**: side-effect mutation `os.environ` da costruttori di classe (race in
  test paralleli e in servizi multi-tenant), gestione errori CLI fuorviante (comment
  "continue with remaining files" smentito dal codice), validazione assente per
  `category` in `RetrievalPipeline.search` (ACL filter applicato ma collection name
  non vincolata al whitelist KNW-01), `acl_level` senza CHECK constraint in PG,
  shadowing di variabile in `Neo4jGraphBuilder.merge_sop` (latente), assert
  invariant strippabile sotto `-O`, fallback APOC file I/O abilitato di default,
  shell injection potenziale via filename in `reindex.yml`.
- **6 INFO**: dead code (`_require_env` non chiamato), naming inaccurate
  ("immutabile" su dict mutabile), commenti fuorvianti, scrittura file non atomica,
  pattern di matching orphan FailureMode troppo permissivo.

Le regole obbligatorie del prompt (no f-string SQL/Cypher su dati, ACL pre-filter
applicato a engine-level, deterministic point ID, Pydantic frozen) sono rispettate
nel percorso "happy"; le criticita' sopra riguardano percorsi laterali e default
production-grade.

## Critical Issues

### CR-01: Cypher injection bypass su `TraverseGraphTool._arun`

**File:** `packages/sft-knowledge/src/sft_knowledge/tools/graph.py:91-122`

**Issue:** `TraverseGraphInput` (Pydantic Literal whitelist) garantisce sicurezza
SOLO quando il tool e' invocato via LangChain `ainvoke(...)`. La firma di
`_arun(self, seed_label: str, seed_id: str, relation_path: list[str], max_depth: int, ...)`
accetta `str` arbitrarie: un caller che chiami direttamente `await tool._arun(...)`
(consentito dal docstring `_run`: *"Use `await tool.ainvoke(...)` or `await tool._arun(...)`"*)
puo' iniettare Cypher al rigo 119:

```python
cypher = (
    f"MATCH (n:{seed_label} {{id: $seed_id}})"
    f"-[:{rel_pipe}*1..{max_depth}]->(m) "
    ...
)
```

Esempio di payload malevolo: `seed_label="Machine) DETACH DELETE n MATCH (x"`,
`relation_path=["HAS_PART"]` → si compone un MATCH che cancella tutti i nodi
del grafo. Il check al rigo 144 (`if label not in whitelist`) e' difensiva ma e'
post-esecuzione Cypher: l'iniezione e' gia' avvenuta.

Threat model `T-05-09-02` dichiara "seed_id ALWAYS as $param" — corretto — ma
non tutela `seed_label` e `rel_pipe` rispetto a call diretti a `_arun`.

**Fix:** Validare gli input dentro `_arun` (oltre che via `args_schema`),
indipendentemente dalla call path:

```python
async def _arun(self, seed_label: str, seed_id: str, relation_path: list[str],
                max_depth: int = 3, **kwargs):
    # Defense-in-depth: re-validate even when bypassing LangChain ainvoke.
    TraverseGraphInput(
        seed_label=seed_label,
        seed_id=seed_id,
        relation_path=relation_path,
        max_depth=max_depth,
    )
    ...
```

In alternativa, sostituire `_arun(...)` con `_arun(self, *, validated: TraverseGraphInput)`
e ricostruire il modello internamente. Aggiungere un test che chiami
`_arun(seed_label="Machine) MATCH (x", ...)` e assert ValidationError.

---

### CR-02: `source_uri` divergence tra orchestratore e parser → state drift silente

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:55-76` e
`packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py:37-40, 123-128`

**Issue:** L'early-exit della pipeline orchestra `state_store.get(source_uri)` al
rigo 174 di `pipeline.py` USANDO `_derive_source_uri(path)` (`parents[4]` dal modulo).
La pipeline al rigo 233 fa POI `state_store.upsert(source_uri=parsed.source_uri, ...)`
dove `parsed.source_uri` viene dal parser, che usa `parents[5]` da
`packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`.

Se i due algoritmi divergono per qualsiasi motivo (worktree, symlink, virtualenv,
re-organizzazione directory packages/services), il flow diventa:

1. `existing = state_store.get(URI_A)` → None (nessuna riga)
2. parse → produce `parsed.source_uri = URI_B`
3. tutto pipeline ok
4. `state_store.upsert(URI_B, ...)` → riga su `URI_B`
5. Next run: `state_store.get(URI_A)` → ancora None → re-ingest infinito,
   never-skipped, e KNW-07 SC#3 invariant rotto silentemente.

Anche se oggi le `parents[*]` puntano alla stessa workspace_root, il
fragility della duplicazione e' una bomba a orologeria. **Inoltre il
fallback nel pipeline (`f"corpus://{path.resolve().as_posix().lstrip(os.sep)}"`)
NON e' equivalente al fallback del parser (`.lstrip('/')`)**: su Windows
`os.sep == '\\'` mentre `as_posix()` ritorna `/`, quindi `lstrip('\\')` su una
posix-path e' un no-op. Cross-platform il fallback differisce.

**Fix:** Estrarre una sola funzione canonica `derive_source_uri(path)` nel modulo
`sft_knowledge.parsers.markdown` (o in un nuovo `sft_knowledge.uri`) e importarla
sia nel parser sia nell'orchestratore. Aggiungere un test parametrizzato che
asserisca `derive_source_uri(p) == MarkdownParser().parse(p).source_uri` per
N path d'esempio (workspace, tmp_path, symlink).

---

### CR-03: Blocking I/O dentro `async def ingest_file`

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:169`

**Issue:** `content_hash = hashlib.sha256(path.read_bytes()).hexdigest()` esegue
`Path.read_bytes()` (sync, syscall bloccante) dentro un `async def`. Per un singolo
file CLI e' tollerabile, ma `__main__._async_run` itera sequenzialmente N file
mentre tiene aperti `qdrant_client + neo4j_driver + asyncpg.Pool`: ogni I/O
bloccante stalla l'event loop e impedisce health checks / heartbeats /
cancellation propagation. In CI con `reindex.yml` (path filter su corpus), 40+
file vengono iterati: 40+ stalls del loop. Violazione esplicita del focus area
"async correctness: blocking calls inside async functions".

Inoltre il pattern si propaga: ogni futuro chiamante che converta `ingest_file`
in `asyncio.gather([ingest_file(p) for p in paths])` per parallelizzare otterrebbe
serializzazione di fatto sull'I/O bloccante.

**Fix:**

```python
content_hash = hashlib.sha256(
    await asyncio.to_thread(path.read_bytes)
).hexdigest()
```

Ditto per `frontmatter.load(str(path))` nel parser (`markdown.py:83`): wrappare in
`asyncio.to_thread`. La classe e' gia' `async def parse(...)`, quindi non rompe
il contratto.

---

### CR-04: Default credentials inconsistenti + hardcoded in 4 layer diversi

**File:**
- `scripts/neo4j-bootstrap.py:100` → default `neo4j/devpassword`
- `infra/compose/core.yml:64` → default `neo4j/devpassword`
- `infra/helm/charts/neo4j/values.yaml:19` → `password: "devpassword"`
- `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py:166, 251, 319` → default `neo4j/cipassword`
- `.github/workflows/reindex.yml:28, 41` → `NEO4J_AUTH: neo4j/cipassword`

**Issue:** Quattro componenti che devono parlarsi cross-process dichiarano
DEFAULTS DIVERSI senza override esplicito:

| Layer | Default `NEO4J_AUTH` |
|-------|----------------------|
| neo4j-bootstrap (CLI) | `neo4j/devpassword` |
| docker compose core.yml | `neo4j/devpassword` |
| Helm chart values.yaml | `neo4j/devpassword` |
| knowledge-ingest CLI (run/bootstrap/validate) | `neo4j/cipassword` |
| CI workflow reindex.yml | `neo4j/cipassword` |

Conseguenze:

1. **Production accidentale**: chi fa `helm install` senza `existingSecret` ottiene
   Neo4j con `neo4j/devpassword` esposto.
2. **Dev broken**: `docker compose up && knowledge-ingest validate` (entrambi senza
   override) → compose crea DB con `devpassword`, validate prova `cipassword`,
   handshake fallisce. Quattro paia di occhi devono manualmente sincronizzare le
   env var.
3. **Credential reuse / scanning**: la stringa `cipassword` e' embedded nei sorgenti
   commitati; chiunque ottenga lettura del repo conosce la password della pipeline
   CI. Anche se sono container effimeri, gli health endpoint sono temporaneamente
   esposti (porte 7474/6333/5432 mappate al runner host) durante il job.
4. La policy globale `security.md` dice esplicitamente "NEVER hardcode secrets in
   source code".

**Fix:**

1. Rimuovere il default `cipassword` da `__main__.py` (righe 166, 251, 319) e dal
   workflow `reindex.yml` → leggere `NEO4J_AUTH` come `_require_env("NEO4J_AUTH")`
   (la funzione esiste gia' al rigo 70-75 ma non e' usata — vedere IN-01).
2. Unificare il default dev su `neo4j/devpassword` SOLO in `compose/core.yml` e
   `values.yaml`, e marcare quei due come **dev-only** con un assert all'avvio
   del servizio che il default non venga lasciato in `production` (es. `if
   NEO4J_AUTH == "neo4j/devpassword" and APP_ENV == "production": exit(1)`).
3. CI: generare la password runtime (`openssl rand -base64 32`) e injettare via
   `secrets.GITHUB_TOKEN` style — non hardcodarla.

## Warnings

### WR-01: `os.environ` mutation in class `__init__` (`BgeM3Embedder`, `BgeReranker`)

**File:** `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py:168-171` e
`packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py:95-96`

**Issue:** Entrambi i costruttori fanno `os.environ["BGE_M3_DEVICE"] = device`
quando `device is not None`. Effetto collaterale invisibile: due istanze
istanziate in ordine `BgeM3Embedder(device="cuda")` poi `BgeM3Embedder(device="cpu")`
clobberano l'env globale, e tutti i futuri `_get_model()` (lru_cache miss in altri
processi forked, test paralleli con `pytest-xdist`) leggono `cpu`. Race anche tra
agent threads concorrenti.

In aggiunta, la docstring riconosce il problema (*"sara' no-op se il modello e'
gia' stato caricato"*) ma non risolve il punto: lo stato persiste a livello di
processo anche dopo la distruzione dell'istanza.

**Fix:** Passare `device` come parametro esplicito a `_get_model()` (ed eliminare
`lru_cache(maxsize=1)` rendendolo `lru_cache` parametrizzato su `device`), oppure
salvare `self._device = device` e usarlo SOLO durante l'init del backend
(spostare la lettura env dentro `_get_model()` come fallback).

---

### WR-02: `category` non vincolata al whitelist in `RetrievalPipeline.search`

**File:** `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:140, 258`

**Issue:** `search(..., category: str = "sop", ...)` passa `category` direttamente
a `client.query_points(collection_name=category, ...)` senza validazione. I 4
collection sono `_COLLECTIONS = {"sop", "manuals", "troubleshooting", "training"}`
(definite in `stores/qdrant.py:42` e `scripts/qdrant-bootstrap.py:49`) ma
`pipeline.py` non importa quella costante.

Un caller che passi `category="user_long_term_memory"` (collezione fuori scope
KNW-01 che non ha i payload index `acl_level`) **eludebbe l'ACL pre-filter**:
il filter sara' applicato ma se la collezione non ha l'index keyword su
`acl_level`, Qdrant fa full-scan e il filter funziona comunque... finche'
qualcuno crea una collezione SENZA il payload `acl_level` settato sui punti
(in quel caso `FieldCondition("acl_level", MatchAny([...]))` ritorna 0 hit —
fail-closed implicito, OK).

Pero' l'RagSearchTool args_schema vincola `category: Literal["sop","manuals",
"troubleshooting","training"]` (rag.py:42). La discrepanza fra Tool e Pipeline
significa che chi usa la Pipeline direttamente (es. `QdrantLongTermMemory._get_pipeline`
→ `pipeline.search(category=str(category))`) eredita il loop hole.

**Fix:** Vincolare `category` in `RetrievalPipeline.search`:

```python
from sft_knowledge.stores.qdrant import _COLLECTIONS

def search(..., category: str = "sop", ...):
    if category not in _COLLECTIONS:
        raise ValueError(f"category {category!r} not in {sorted(_COLLECTIONS)}")
```

---

### WR-03: Variable shadowing in `Neo4jGraphBuilder.merge_sop`

**File:** `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py:296, 313`

**Issue:**

```python
fm_id = str(parsed_doc.frontmatter.get("id", "")).strip()  # outer fm_id (SOP id)
...
link_rows = [
    {"failure_mode_id": fm_id, "sop_id": sop_id}
    for fm_id in failure_mode_ids                          # SHADOWS outer fm_id
]
```

Il comprehension variable `fm_id` shadowa quello esterno. **Il codice attuale
funziona** perche' niente referenzia `fm_id` dopo la list comprehension, ma e'
una bomba: qualsiasi futura modifica che logga `fm_id` dopo questo blocco usa
l'ULTIMO elemento di `failure_mode_ids` invece dell'SOP id. Inoltre rende
il diff difficile da reviewer.

**Fix:** Rinominare la comprehension variable: `for failure_mode in failure_mode_ids`
e `{"failure_mode_id": failure_mode, ...}`.

---

### WR-04: `assert len(indices) == len(values)` strippabile sotto `python -O`

**File:** `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py:256`

**Issue:** L'invariante e' marcato come "Invariante per Qdrant API" (commento)
ma sotto `python -O` (production optimizer) l'assert viene rimosso e qualunque
mismatch produrrebbe un SparseVector inconsistente che Qdrant rifiuta lato server
con messaggio opaco.

**Fix:**

```python
if len(indices) != len(values):
    raise RuntimeError(
        f"sparse vector invariant violated: indices={len(indices)} values={len(values)}"
    )
```

Stesso pattern anche al `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py:186`
(`assert pg_pool is not None`).

---

### WR-05: CLI `run` afferma "Continue with remaining files" ma rilancia subito

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py:215-223`

**Issue:**

```python
try:
    result = await ingest_file(f, ...)
    ...
except Exception as exc:
    log.error("ingest_file_failed", file=str(f), error=str(exc))
    # Continue with remaining files; the CI will surface non-zero rc
    # only via uncaught errors at the top of asyncio.run() if needed.
    raise
```

Il commento promette continuazione, il `raise` la nega. Effetto: un file
malformato a meta' batch interrompe l'intera reindex. In una pipeline CI con
40 file, se il 5° fallisce gli altri 35 non vengono nemmeno tentati.

**Fix:** decidere il contratto. Opzione A (fail-fast): rimuovere il commento
ingannevole. Opzione B (best-effort): rimuovere `raise`, collezionare error
counts e fare `raise typer.Exit(1)` alla fine se `total_errors > 0`.

---

### WR-06: Default `acl_level` `"internal"` invece di fail-closed in pipeline

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:200, 238`

**Issue:**

```python
acl_level=str(parsed.frontmatter.get("acl_level", "internal"))
```

Il parser (`markdown.py:96-104`) gia' inietta `"internal"` di default per i
docs senza `acl_level`, quindi `parsed.frontmatter["acl_level"]` non puo' essere
mancante in pratica. Ma il fallback duplicato in pipeline e' un secondo punto
di silently-default: se un futuro `DocumentParser` non rispetta l'invariante
parser, il bug viene mascherato. Il prompt richiede esplicitamente `T-05-09-01
fail-closed`.

**Fix:** Se la lettura ritorna None/missing, sollevare ValueError. Affidarsi
all'invariante del parser e fallire forte se rotto:

```python
acl = parsed.frontmatter.get("acl_level")
if acl not in {"public", "internal", "restricted"}:
    raise ValueError(f"ParsedDoc missing/invalid acl_level: {acl!r}")
```

---

### WR-07: `acl_level` senza CHECK constraint in PG migration 006

**File:** `infra/migrations/timescale/006_create_ingest_state.sql:25`

**Issue:**

```sql
acl_level     TEXT        NOT NULL
```

L'enum `{public, internal, restricted}` (D-72) non e' enforced lato DB. Una
INSERT diretta (es. da uno script di operations) con
`acl_level='top_secret'` viene accettata, rompendo l'invariante e producendo
un MatchAny miss silenzioso sull'ACL filter (il valore semplicemente non si
matcha mai → il documento e' invisibile a TUTTI). Hard-to-debug.

Lo schema `state.py` (`IngestStateRow`) usa `acl_level: str` (non Literal) →
nessuna validazione client-side neppure.

**Fix:**

```sql
acl_level TEXT NOT NULL CHECK (acl_level IN ('public', 'internal', 'restricted'))
```

(idempotent: usare `DO $$ ... IF NOT EXISTS ...` pattern per backward compat),
e in `IngestStateRow` cambiare `acl_level: Literal["public", "internal", "restricted"]`.

---

### WR-08: Shell injection potenziale via filename in `reindex.yml`

**File:** `.github/workflows/reindex.yml:144-146`

**Issue:**

```bash
FILES=$(paste -sd, changed.txt)
echo "ingesting: $FILES"
npx nx run knowledge-ingest:run --args="--files=$FILES --mode=incremental --collection=sop"
```

1. `paste -sd,` separa con `,`, ma un filename contenente `,` (consentito su
   ext4/posix) corrompe il CSV.
2. `$FILES` viene espanso shell-unquoted dentro `--args="..."`; un filename
   ostile (es. da PR malevola) contenente `"` o `$(...)` puo' rompere il quoting
   e/o causare expansion di backtick (anche se `nx run --args` poi passa il tutto
   come singolo argomento, l'expansion shell e' a livello upstream).

**Fix:**

```bash
mapfile -t FILES_ARR < changed.txt
FILES=$(IFS=, ; echo "${FILES_ARR[*]@Q}")  # quoted-elems join
# o piu' robusto: usare un file di argomenti e --files=@list.txt se supportato
npx nx run knowledge-ingest:run --args="--files=${FILES}" \
  --mode=incremental --collection=sop
```

In aggiunta, validare upstream che i filename matchino `^[A-Za-z0-9._/\-]+$` prima
di passarli alla CLI.

---

### WR-09: APOC file I/O abilitato di default in compose e Helm

**File:** `infra/compose/core.yml:66-68`, `infra/helm/charts/neo4j/values.yaml:26-29`

**Issue:**

```yaml
NEO4J_apoc_export_file_enabled: "true"
NEO4J_apoc_import_file_enabled: "true"
NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
```

L'`apoc.*` namespace contiene `apoc.export.csv`, `apoc.export.json`,
`apoc.load.csv`, `apoc.load.json` — procedure che leggono/scrivono path
arbitrari sul filesystem del container Neo4j. Combinato con Cypher injection
(vedere CR-01) o con un user role che possa eseguire `CALL apoc.*`, queste
diventano vettore di:

- **Read** di file Neo4j-leggibili (`/etc/passwd` del container, ma anche
  `/data/neo4j/conf/*` se mountato).
- **Write** di file CSV/JSON in `/import` (il container Neo4j ufficiale mappa
  `import_file_use_neo4j_config=true` ma con i flag sopra il setting e' loose).

T-05-05-03 dichiara mitigato il rischio "limitando a apoc.*", ma `apoc.*` include
proprio le export/load file procedures. La mitigazione e' insufficiente.

**Fix:** Disabilitare di default:

```yaml
NEO4J_apoc_export_file_enabled: "false"
NEO4J_apoc_import_file_enabled: "false"
```

Mantenere abilitabili via override esplicito quando serve davvero (es. una pipeline
di bulk-load offline). Documentare in `docs/docs/knowledge-layer/acl-model.md`.

---

### WR-10: Helm StatefulSet usa fallback password in produzione senza guard

**File:** `infra/helm/charts/neo4j/templates/statefulset.yaml:26-37`

**Issue:**

```yaml
- name: NEO4J_AUTH
  {{- if .Values.auth.existingSecret }}
  valueFrom: ...
  {{- else }}
  # Dev-only skeleton: production deployments must set auth.existingSecret
  # referencing a SealedSecret (Phase 11 hardening, T-05-05-02).
  value: "{{ .Values.auth.username }}/{{ .Values.auth.password }}"
  {{- end }}
```

Il commento "Dev-only skeleton" e' solo un comment — non c'e' guard runtime.
`helm install neo4j charts/neo4j` senza `--set auth.existingSecret=...` deploya
Neo4j con `neo4j/devpassword` in QUALSIASI cluster (prod incluso).

**Fix:** Aggiungere un required check:

```yaml
{{- if not .Values.auth.existingSecret }}
{{-   if eq .Values.global.environment "production" }}
{{-     fail "auth.existingSecret is required for production deployments (T-05-05-02)" }}
{{-   end }}
{{- end }}
```

Oppure rendere `existingSecret` un required value senza default.

---

### WR-11: `sft_agents.memory.__init__` silently downgrades to stub

**File:** `packages/sft-agents/src/sft_agents/memory/__init__.py:26-31`

**Issue:**

```python
try:
    from sft_knowledge.memory import QdrantLongTermMemory
    LongTermMemory: type = QdrantLongTermMemory
except ImportError:
    LongTermMemory = StubLongTermMemory
```

1. Cattura solo `ImportError`. Se `sft_knowledge.memory` ha errori a module-load
   (es. configurazione runtime mancante), l'eccezione propaga e rompe TUTTO
   l'import di sft-agents — peggio del fallback.
2. Anche con `ImportError`, il downgrade e' silenzioso: produzione con
   sft-knowledge non installato ottiene lo Stub senza alarm, e gli agenti
   "rispondono" senza retrieval reale (citazioni vuote → comportamento clinico
   indistinguibile da un Phase 4 in produzione). Viola il principio fail-loud.

**Fix:**

```python
try:
    from sft_knowledge.memory import QdrantLongTermMemory
    LongTermMemory: type = QdrantLongTermMemory
except ImportError as exc:
    import logging
    logging.getLogger(__name__).warning(
        "sft_knowledge_unavailable_using_stub", error=str(exc)
    )
    LongTermMemory = StubLongTermMemory
```

E in produzione (`APP_ENV=production`) sollevare invece di degradare.

---

### WR-12: `QdrantLongTermMemory._get_pipeline` crea client mai chiusi

**File:** `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py:78-91`

**Issue:** `_get_pipeline` istanzia un `AsyncQdrantClient` al primo `query()`
e lo memorizza in `self._pipeline._client`. Non c'e' una `close()` / `aclose()`
sulla classe `QdrantLongTermMemory`. Quando un agent runner scarta l'istanza
(es. al termine di un workflow Langgraph), il client viene garbage-collected
ma la connessione HTTP resta aperta finche' il GC non chiama `__del__` (mai
garantito su event-loop chiusi).

Anche il `BgeReranker` ha lo stesso pattern (model caricato in lru_cache globale,
non rilasciato). In long-running services (sft-orchestrator, api-gateway),
ripetute istanze di `QdrantLongTermMemory` accumulano connessioni.

**Fix:** Aggiungere `async def aclose(self)` su `QdrantLongTermMemory`:

```python
async def aclose(self) -> None:
    if self._pipeline is not None:
        await self._pipeline._client.close()
        self._pipeline = None
```

E nel caller (Memory ABC) aggiungere `aclose()` contract.

---

### WR-13: `BgeReranker.rerank` puo' droppare hit silenziosamente

**File:** `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py:135-141`

**Issue:**

```python
if isinstance(raw_scores, (int, float)):
    scores: list[float] = [float(raw_scores)]
else:
    scores = [float(s) for s in raw_scores]

return sorted(zip(hits, scores), key=lambda pair: -pair[1])
```

`zip(hits, scores)` trunca silentemente se le due liste hanno lunghezza diversa
(es. backend ritorna `len(scores) != len(hits)`). Risultato: l'utente vede meno
hit del previsto, e l'unica indicazione e' un count mismatch tra log
`retrieval_done.returned` e log Qdrant `query_points`. Diagnosi nightmare.

**Fix:**

```python
if len(scores) != len(hits):
    raise RuntimeError(
        f"BgeReranker score count mismatch: scores={len(scores)} hits={len(hits)}"
    )
```

## Info

### IN-01: Dead code — `_require_env` definito ma mai chiamato

**File:** `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py:70-75`

**Issue:** `_require_env(name)` e' importato? No. E' chiamato? No (`grep _require_env`
da' una sola occorrenza, la definizione). Le funzioni `_async_run`, `bootstrap`,
`_async_validate` ripetono inline `os.environ.get(...) if not ...: raise typer.Exit(2)`.

**Fix:** Usare `_require_env("TIMESCALE_DSN")` nelle tre call site (righe 167-172,
253-255, 320-323), o rimuovere `_require_env` se non si vuole adottarlo.

---

### IN-02: "Immutabile" dict mutabile in `load_failure_modes_dict`

**File:** `packages/sft-domain/src/sft_domain/failure_modes/_loader.py:62-68`

**Issue:** Docstring dichiara *"Restituisce un dizionario {failure_mode_id: FailureMode}
[…] Dizionario immutabile {id: FailureMode}"*. In realta' restituisce un `dict`
standard mutabile. Anche se `FailureMode` values sono frozen, il caller puo' fare
`d["new"] = ...` o `d.clear()` e corrompere la cache (e' `@lru_cache(maxsize=1)`,
quindi la stessa istanza dict e' ritornata a tutti i caller — una mutation in un
test contamina tutto il process).

**Fix:** Usare `types.MappingProxyType(...)` come wrapper read-only:

```python
from types import MappingProxyType

@lru_cache(maxsize=1)
def load_failure_modes_dict() -> MappingProxyType[str, FailureMode]:
    return MappingProxyType({fm.id: fm for fm in load_failure_modes()})
```

---

### IN-03: Migrate-sop-acl write non atomico

**File:** `scripts/migrate-sop-acl.py:117-121`

**Issue:** `open(path, "w")` + `f.write(...)` + `f.write("\n")`. Se il processo
viene killed tra `open` (truncate) e il primo `write`, il file SOP risulta vuoto
e perso. Idempotente solo se il run e' andato a buon fine completamente.

**Fix:** Write atomico via `tempfile + os.replace`:

```python
with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as tmp:
    tmp.write(frontmatter.dumps(updated_post))
    tmp.write("\n")
os.replace(tmp.name, path)
```

Stesso pattern in `generate_rag_testset.py:185` (`args.output.write_text(...)`).

---

### IN-04: Substring-match bidirezionale troppo permissivo

**File:** `scripts/validate-failure-modes.py:117`

**Issue:** `if len(t) >= _MIN_NEEDLE_LEN and (needle in t or t in needle):` — il
ramo `t in needle` permette ad esempio che un tag SOP `"warp"` matchi un needle
`"warp_breakage"` di un FailureMode COMPLETAMENTE diverso, marcandolo come
"referenced". False-positive: un FailureMode realmente orfana puo' essere
nascosta dal validator.

**Fix:** Rimuovere il ramo `t in needle` (mantenere solo `needle in t`); o
aggiungere un test che usi token boundary matching (`re.search(rf"\b{re.escape(needle)}\b", t)`).

---

### IN-05: `run_ab_eval --skip-eval` default produce numeri inventati

**File:** `services/knowledge-ingest/scripts/run_ab_eval.py:256-261, 230-243`

**Issue:** Il default di `--skip-eval=True` significa che `make eval-rag` /
`uv run python services/knowledge-ingest/scripts/run_ab_eval.py` produce un
deliverable markdown che mostra "NDCG@10 = 0.840 ... acceptance gates met" da
numeri hardcoded in `_stub_summary()`. Anche con banner "preliminary",
chiunque legga il PR potrebbe interpretare i numeri come reali. Il docstring
dichiara il design intenzionale, ma la default-truthiness inverte la sicurezza:
chi dimentica di passare `--full` ottiene una falsa convalida dei gate D-71.

**Fix:** Cambiare il default a `--skip-eval=False` e richiedere esplicito
opt-in (`--stub`) per la modalita' CI. Oppure mantenere il default ma
appendere `**FAKE METRICS — DO NOT TRUST**` in tutte e tre le sezioni del
deliverable (titolo, table caption, decision block).

---

### IN-06: Magic number in `qdrant.py` (batch_size, prefetch_limit, snippet_max)

**File:**
- `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py:45` (`_DEFAULT_BATCH_SIZE = 100`)
- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:39, 42` (`_SNIPPET_MAX = 200`, `_PREFETCH_LIMIT = 20`)
- `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py:121` (`_DEFAULT_BATCH_SIZE = 500`)

**Issue:** I valori sono giustificati nei docstring/CONTEXT.md come "claudes_discretion"
ma sono sparsi in 4 file diversi senza un unico modulo di config. Cambiare il
prefetch limit a 30 richiede grep su 3 file (pipeline + reranker + tools/rag.py
indirettamente via `k=Field(le=20)`).

**Fix:** Estrarre in `packages/sft-knowledge/src/sft_knowledge/config.py`:

```python
QDRANT_UPSERT_BATCH = 100
NEO4J_MERGE_BATCH = 500
PREFETCH_LIMIT = 20
RAG_SNIPPET_MAX = 200
DENSE_DIM = 1024
COLLECTIONS = frozenset({"sop", "manuals", "troubleshooting", "training"})
```

Importare da li' in qdrant.py / neo4j.py / pipeline.py / scripts/qdrant-bootstrap.py.

---

_Reviewed: 2026-05-19T13:27:06Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
