# Contributing

Welcome to the Smart Factory Transformation contributing guide. This section gathers the essential resources for working on the project in compliance with the established conventions.

## Tools and Setup

- [Toolchain](../getting-started.md) — system prerequisites for local development

## Workflow and Conventions

- [Commit conventions](../../../contributing/commit-conventions.md) — Conventional Commits, scopes, types (feat, fix, docs, ...)
- [Pre-commit hooks](../../../contributing/pre-commit.md) — ruff, eslint, prettier, gitleaks, commitlint

## CI/CD

- [CI pipeline](../../../contributing/ci-pipeline.md) — GitHub Actions workflows, `nx affected`, required checks
- [Branch protection](../../../operations/branch-protection.md) — rules for `main`, required status checks, merge policy

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
