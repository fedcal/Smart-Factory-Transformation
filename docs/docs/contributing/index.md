# Contributing

Benvenuto nella guida per contribuire a Smart Factory Transformation. Questa sezione raccoglie le risorse essenziali per lavorare sul progetto nel rispetto delle convenzioni stabilite.

## Strumenti e setup

- [Toolchain](../getting-started.md) — prerequisiti di sistema per lo sviluppo locale

## Workflow e convenzioni

- **Convenzioni dei commit** — Conventional Commits, scope, tipi (feat, fix, docs, ...) (documentazione completa in arrivo)
- **Pre-commit hooks** — ruff, eslint, prettier, gitleaks, commitlint (documentazione completa in arrivo)

## CI/CD

- **Pipeline CI** — workflow GitHub Actions, `nx affected`, required checks (documentazione completa in arrivo)
- **Branch protection** — regole per `main`, required status checks, merge policy (documentazione completa in arrivo)

## Sviluppo locale

Per visualizzare la documentazione in locale durante lo sviluppo:

```bash
make docs-serve
```

Il sito sarà disponibile su `http://127.0.0.1:8000` con hot-reload automatico.

---

!!! info "Fase 1"
    Le pagine di dettaglio (toolchain.md, ci-pipeline.md, ecc.) verranno popolate
    progressivamente nelle fasi successive man mano che i componenti vengono costruiti.
    Le convenzioni di base (commit, pre-commit) sono già operative.
