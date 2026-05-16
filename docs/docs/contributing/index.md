# Contributing

Benvenuto nella guida per contribuire a Smart Factory Transformation. Questa sezione raccoglie le risorse essenziali per lavorare sul progetto nel rispetto delle convenzioni stabilite.

## Strumenti e setup

- [Toolchain](../getting-started.md) — prerequisiti di sistema per lo sviluppo locale

## Workflow e convenzioni

- [Convenzioni dei commit](../../../contributing/commit-conventions.md) — Conventional Commits, scope, tipi (feat, fix, docs, ...)
- [Pre-commit hooks](../../../contributing/pre-commit.md) — ruff, eslint, prettier, gitleaks, commitlint

## CI/CD

- [Pipeline CI](../../../contributing/ci-pipeline.md) — workflow GitHub Actions, `nx affected`, required checks
- [Branch protection](../../../operations/branch-protection.md) — regole per `main`, required status checks, merge policy

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
