# CI Pipeline

Questa pagina documenta i workflow GitHub Actions attivi nel repository **Smart Factory Transformation** e le relative politiche di esecuzione.

---

## Workflow attivi (Fase 1)

| Workflow | File | Trigger | Required check? | Scopo |
|---|---|---|---|---|
| **CI** | `ci.yml` | PR + push su `main` | Si | nx affected lint/test/build, validazione dep graph Python↔TS |
| **Pre-commit Check** | `pre-commit-check.yml` | PR + push su `main` | Si | Quality gates: ruff, mypy, eslint, prettier, commitlint, gitleaks |
| **License Scan** | `license-scan.yml` | PR + push su `main` | Si | SBOM-based supply-chain scan (Syft + Grype); blocca licenze non approvate |
| **Helm Smoke Test** | `helm-smoke-test.yml` | PR + push su `main` | Si | k3d cluster, helm install, kubectl wait, helm test hooks |
| **Docs Deploy** | `docs-deploy.yml` | push su `main` only | No | Pubblica MkDocs Material su GitHub Pages (branch `gh-pages`) |
| **Nx Affected Graph** | `nx-affected-graph.yml` | PR | No | Genera grafo affected HTML come artifact; utile in code review |
| **Test License Fixture** | `test-license-fixture.yml` | Schedule (weekly) | No | Anti-regression: verifica che dipendenza GPL blocchi CI |

> **Branch protection `main`:** I quattro "Required check" (`ci`, `pre-commit-check`, `license-scan`, `helm-smoke-test`) devono essere verdi prima del merge. Il check `docs-deploy` e `nx-affected-graph` sono informativi e non bloccano il merge.

---

## CI workflow in dettaglio (`ci.yml`)

Il workflow principale usa **`nx affected`** per eseguire lint, test e build solo sui progetti modificati dalla PR, risolvendo correttamente le dipendenze polyglot Python↔TypeScript dichiarate tramite `implicitDependencies` in ogni `project.json`.

### Step del job `main`

```
checkout (fetch-depth=0)
  → setup-node@v4 (Node 20, cache npm)
  → setup-python@v5 (Python 3.12)
  → astral-sh/setup-uv@v5 (uv 0.6, enable-cache)
  → actions/cache@v4 (uv: ~/.cache/uv)
  → actions/cache@v4 (Nx: .nx/cache)
  → npm ci
  → uv sync --all-packages
  → nrwl/nx-set-shas@v4  ← imposta NX_BASE e NX_HEAD
  → Validate Nx dep graph (scripts/validate-nx-graph.py)
  → nx affected --target=lint  --base=$NX_BASE --head=$NX_HEAD --parallel=3
  → nx affected --target=test  --base=$NX_BASE --head=$NX_HEAD --parallel=3 --configuration=ci
  → nx affected --target=build --base=$NX_BASE --head=$NX_HEAD --parallel=3
```

### Gestione SHA di base (`nrwl/nx-set-shas@v4`)

Il tool `nrwl/nx-set-shas` individua automaticamente l'ultimo run CI riuscito su `main` e imposta le variabili d'ambiente `NX_BASE` e `NX_HEAD`. Questo garantisce che `nx affected` compari solo i commit della PR rispetto a `main`, non l'intera storia.

Configurazione critica per evitare il **Pitfall 2** (primo commit / squash merge):

```yaml
uses: nrwl/nx-set-shas@v4
with:
  main-branch-name: main
  workflow-id: ci.yml
  fallback-sha: "HEAD~1"                  # fallback se nessun run precedente
  error-on-no-successful-workflow: false  # non fallire su repo nuovo
```

- **`fetch-depth: 0`** — obbligatorio: `nx-set-shas` richiede la storia Git completa per trovare il commit di base
- **`fallback-sha: "HEAD~1"`** — usato al primo commit del repository o dopo squash merge senza SHA precedente
- **`error-on-no-successful-workflow: false`** — previene il fallimento su repository appena creati

### Validazione dep graph Python↔TypeScript

Prima degli step `nx affected`, il workflow esegue:

```bash
npx nx graph --file=tmp/graph.json
python3 scripts/validate-nx-graph.py
```

Lo script `scripts/validate-nx-graph.py` verifica che le edge cross-language dichiarate in `implicitDependencies` siano effettivamente presenti nel grafo Nx. Se un'edge manca (es. `svc-api-gateway` non dichiara dipendenza da `sft-contracts`), il workflow fallisce con un messaggio esplicito prima ancora di eseguire `nx affected`.

Questo cattura il **Pitfall 4** (dipendenze Python→TS non riconosciute automaticamente da Nx).

### Cache

| Layer | Path | Chiave |
|---|---|---|
| uv (Python deps) | `~/.cache/uv` | `uv-{os}-{hash(uv.lock)}` |
| Nx (build cache) | `.nx/cache` | `nx-{os}-{hash(nx.json, package-lock.json)}` |

La chiave Nx include `nx.json` e `package-lock.json` per prevenire il cache poisoning (threat T-1-04): una modifica alla configurazione Nx o alle dipendenze npm invalida la cache automaticamente.

### Cancellazione concorrente

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

I run precedenti della stessa PR vengono cancellati automaticamente. I push su `main` non vengono cancellati (`cancel-in-progress: false`).

---

## Nx Affected Graph workflow (`nx-affected-graph.yml`)

Workflow **informativo** eseguito su ogni PR. Genera due artifact:

- `tmp/affected.html` — grafo interattivo dei soli progetti affected dalla PR
- `tmp/graph-full.html` — grafo completo del workspace

Gli artifact sono disponibili nella tab **Actions** → run della PR per 14 giorni. Utili durante code review per visualizzare l'impatto di una modifica cross-boundary (es. una modifica a `sft-contracts` che propaga a `ui-factory` e `svc-api-gateway`).

---

## Performance expectations

| Scenario | Cache fredda | Cache calda |
|---|---|---|
| PR che tocca 1 package Python | ~3-4 min | ~30-45 s |
| PR che tocca `sft-contracts` (propaga a TS+Python) | ~5-6 min | ~1-2 min |
| PR che tocca solo `docs/` o `infra/` | ~1-2 min | ~15 s |
| Push su `main` (full affected da ultimo merge) | ~4-6 min | ~1-2 min |

> **Obiettivo Fase 1:** PR tipica ≤ 5 minuti con cache calda. Se i tempi superano 10 minuti con 16+ agenti attivi (Fase 6+), valutare Nx Cloud paid tier (decisione rinviata — vedi `01-CONTEXT.md` sezione Deferred).

---

## Troubleshooting

### `nx affected` ritorna 0 progetti (tutto skippato)

**Cause possibili:**

1. **`fetch-depth` non è 0** — verificare che il checkout abbia `fetch-depth: 0`. Senza storia completa, `nx-set-shas` non riesce a trovare il commit base e imposta `NX_BASE=NX_HEAD`, rendendo l'affected set vuoto.

2. **Primo run su repo nuovo** — al primo commit non esiste un run precedente su `main`. Il parametro `error-on-no-successful-workflow: false` + `fallback-sha: "HEAD~1"` dovrebbe gestire questo caso automaticamente.

3. **Squash merge senza SHA tracciato** — dopo uno squash merge, il SHA del commit di merge non corrisponde a nessun SHA del run CI originale. `nrwl/nx-set-shas` con `workflow-id: ci.yml` usa il SHA del run, non del commit — questo dovrebbe essere già gestito.

4. **`implicitDependencies` mancanti** — se un progetto Python non dichiara dipendenza da un package TypeScript in `project.json`, la modifica al package TS non appare come affecting il progetto Python. Eseguire `python3 scripts/validate-nx-graph.py` localmente dopo `nx graph --file=tmp/graph.json`.

### Cache miss frequente

La chiave di cache include `nx.json` e `package-lock.json`. Ogni modifica a questi file invalida la cache Nx. Normale dopo aggiornamenti di dipendenze; non richiede azione.

La chiave uv include il lockfile `uv.lock`. Cache miss su uv indica che le dipendenze Python sono cambiate — normale dopo `uv add` o `uv update`.

### Build fallisce solo in CI (passa in locale)

Verificare:

- Python version: CI usa 3.12; localmente potrebbe essere diversa. Controllare `.python-version` o `pyproject.toml`.
- `npm ci` vs `npm install`: CI usa `npm ci` (lock-exact). In locale potrebbe essere stato usato `npm install` che aggiorna il lock. Committare il `package-lock.json` aggiornato.
- Variabili d'ambiente: verificare che il codice non dipenda da variabili locali non dichiarate nel workflow.

### `validate-nx-graph.py` fallisce (MISSING edges)

Lo script richiede che certi edge cross-language siano presenti nel grafo. Per aggiungere un'edge mancante, aprire `project.json` del progetto sorgente e aggiungere:

```json
{
  "implicitDependencies": ["nome-progetto-target"]
}
```

Rieseguire `nx graph --file=tmp/graph.json && python3 scripts/validate-nx-graph.py` per verificare.

---

## Osservabilita CI (OBS-01)

**Langfuse v3 self-hosted** e disponibile via `make up` come servizio dev (configurato in `infra/compose/obs.yml`). Consente il tracing LLM degli agenti runtime durante lo sviluppo locale.

**Stato attuale del wiring SDK (Fase 1):** gli agent runtime non emettono ancora traces verso Langfuse. Il cablaggio SDK (`langfuse.trace()`, `langfuse.generation()`) e la configurazione delle variabili `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` sono schedulati a **Phase 11** (Observability & Evaluation).

**CI non esegue runtime call verso Langfuse.** Il workflow `ci.yml` non dipende da Langfuse per nessuno step. La pipeline CI rimane completamente funzionale anche senza lo stack Langfuse attivo.

Riferimento requirement: **OBS-01** — Langfuse v3 self-hosted come dev observability service.

---

## Aggiornamento workflow nelle fasi successive

Le fasi successive estenderanno i workflow esistenti:

- **Phase 6+ (agenti):** aggiungere job `eval` con DeepEval al workflow CI (step opzionale, non required check)
- **Phase 11 (Observability):** aggiungere smoke test Langfuse SDK nel job CI
- **Phase 12 (Brand Scrub):** aggiungere job `brand-check` se necessario

I workflow CI esistenti non devono essere modificati senza aggiornare questa documentazione.
