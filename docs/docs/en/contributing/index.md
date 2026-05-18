# Contributing

Welcome to the Smart Factory Transformation contributing guide. This section gathers the essential resources for working on the project in compliance with the established conventions.

## Tools and Setup

- [Toolchain](../getting-started.md) — system prerequisites for local development

## Workflow and Conventions

- **Commit conventions** — Conventional Commits, scopes, types (feat, fix, docs, ...) (full documentation coming)
- **Pre-commit hooks** — ruff, eslint, prettier, gitleaks, commitlint (full documentation coming)

## CI/CD

- **CI pipeline** — GitHub Actions workflows, `nx affected`, required checks (full documentation coming)
- **Branch protection** — rules for `main`, required status checks, merge policy (full documentation coming)

## Local Development

To preview the documentation locally during development:

```bash
make docs-serve
```

The site will be available at `http://127.0.0.1:8000` with automatic hot-reload.

---

!!! info "Phase 1"
    Detail pages (toolchain.md, ci-pipeline.md, etc.) will be progressively populated
    in subsequent phases as components are built. Base conventions (commit, pre-commit)
    are already operational.
