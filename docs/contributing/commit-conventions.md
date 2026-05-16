# Convenzioni dei Commit — Smart Factory Transformation

Questo progetto adotta la specifica **[Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/)** per tutti i commit. Il formato è obbligatorio e applicato automaticamente via commitlint nel hook `commit-msg`.

---

## Formato

```
<type>(<scope>): <subject>

[corpo opzionale]

[footer opzionale]
```

### Type (obbligatorio)

| Type | Quando usarlo |
|------|---------------|
| `feat` | Nuova funzionalità visibile all'utente o all'API |
| `fix` | Correzione di un bug |
| `docs` | Modifiche solo alla documentazione |
| `style` | Formattazione, spazi bianchi (nessuna logica cambiata) |
| `refactor` | Refactoring senza aggiunta di feature né fix di bug |
| `perf` | Ottimizzazione delle performance |
| `test` | Aggiunta o modifica di test |
| `build` | Build system, dipendenze esterne |
| `ci` | Workflow CI/CD, GitHub Actions |
| `chore` | Task di manutenzione, configurazioni (es. `.gitignore`) |
| `revert` | Revert di un commit precedente |

### Scope (obbligatorio se applicabile)

Lo scope è il nome del progetto Nx in **kebab-case**:

- `sft-agents`, `sft-domain`, `sft-contracts` — SDK packages
- `ui-factory` — Angular app
- `svc-orchestrator`, `svc-api-gateway`, `svc-ot-bridge` — servizi
- `ops-operator-assistant`, `mnt-predictive-maintenance`, ecc. — agenti
- `sim-textile` — simulatore
- `infra`, `ci`, `docs`, `phase-1`, ecc. — per modifiche cross-cutting

### Subject

- Breve descrizione in inglese o italiano
- Inizia con verbo all'infinito (es. "add", "fix", "aggiunge", "corregge")
- Nessun punto finale
- Massimo 100 caratteri incluso `type(scope): `

---

## Esempi

### Nuove funzionalità

```
feat(sft-agents): add Tool base class with async execute method
```

```
feat(sft-contracts): export OpenAPI schema for AgentRequest model
```

```
feat(ui-factory): implement real-time dashboard with WebSocket updates
```

### Bug fix

```
fix(svc-ot-bridge): handle reconnect on NATS disconnect with exponential backoff
```

```
fix(ops-anomaly-detector): prevent NaN in Z-score when stdev is zero
```

### Documentazione

```
docs(phase-1): update CONTEXT.md with uv workspace decisions
```

```
docs(sft-agents): add usage examples for Memory interface
```

### CI / infrastruttura

```
ci: add pre-commit-check.yml as required status check on main
```

```
chore(infra): pin gitleaks to v8.24.2 in pre-commit config
```

### Breaking changes

Per modifiche che rompono la compatibilita`, aggiungere `!` dopo il type/scope:

```
feat(sft-contracts)!: rename AgentRequest.task_id to AgentRequest.run_id
```

Il footer deve contenere `BREAKING CHANGE:` con la descrizione:

```
feat(sft-api)!: rename endpoint /v1/approve to /v2/approve

BREAKING CHANGE: il path /v1/approve non e' piu' supportato.
Tutti i client devono aggiornare alla v2 API.
```

---

## Regole applicate da commitlint

| Regola | Configurazione |
|--------|---------------|
| `type-enum` | Solo i type elencati sopra |
| `scope-case` | Obbligatoriamente kebab-case |
| `header-max-length` | Massimo 100 caratteri |
| `body-max-line-length` | Warning oltre 120 caratteri per riga |

---

## Multi-package commits

Se una modifica tocca piu` progetti Nx, usa lo scope del progetto principale o `infra`/`ci`:

```
refactor(sft-agents): extract BaseAgent into dedicated module

- Affects: sft-agents (primary), svc-orchestrator (consumer)
```

---

## Riferimenti

- [Conventional Commits 1.0 Specification](https://www.conventionalcommits.org/en/v1.0.0/)
- [Commitlint config](.commitlintrc.cjs)
- [Pre-commit hook setup](pre-commit.md)
- [Changesets release workflow](../../.changeset/README.md)

---

## EN Summary (for non-Italian speakers)

This project enforces Conventional Commits via commitlint. Format: `<type>(<scope>): <subject>`. Allowed types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Scope must be kebab-case Nx project name. Header max 100 chars. Breaking changes use `!` suffix and `BREAKING CHANGE:` footer token.
