# Contributing

Thank you for your interest in contributing to **Smart Factory Transformation**,
the open-source agentic platform for the textile manufacturing industry. This
guide describes the conventions and the local workflow. For the documentation
section dedicated to contributors, see
[`docs/docs/contributing/index.md`](docs/docs/contributing/index.md).

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Getting set up

Prerequisites: Node.js (see `.nvmrc`), Python 3.12, [uv](https://docs.astral.sh/uv/),
Docker + Docker Compose, and the Nx CLI.

```bash
uv sync          # Python dependencies (managed by uv — never via npm)
npm install      # Node workspace dependencies
pre-commit install   # enable the git pre-commit hooks
```

> Python dependencies are declared in the relevant `pyproject.toml` and resolved
> with `uv`. Do **not** add Python libraries via `npm`.

## Commit conventions

This repository follows **Conventional Commits**, enforced by `commitlint`:

```text
<type>(<scope>): <description>
```

Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`,
`style`, `build`. Keep the subject concise and in the imperative mood.

## Pre-commit hooks

Pre-commit runs automatically on staged files and includes, among others:

- `ruff` — Python lint + format
- `eslint` / `prettier` — TS/JS lint + format
- `gitleaks` — secret scanning
- `commitlint` — commit message validation

Run all hooks manually with:

```bash
pre-commit run --all-files
```

## Running tests

The monorepo uses **Nx** with `nx affected` to run only the jobs relevant to your
change, and **pytest** for the Python packages:

```bash
npx nx affected -t test       # affected JS/TS + project tests
make test                     # repo test target
pytest                        # Python test suites
```

Please keep meaningful test coverage for the code you add or change.

## Building the documentation

Documentation is docs-as-code (MkDocs Material, bilingual IT/EN). Every Italian
page under `docs/docs/` must have an English mirror under `docs/docs/en/`.
Build in strict mode before opening a pull request:

```bash
cd docs && python3 -m mkdocs build --strict   # or: make docs-serve to preview
```

A failing strict build (broken links, warnings) must be fixed before merge.

## Pull requests

1. Create a topic branch and keep commits Conventional-Commit compliant.
2. Ensure `pre-commit run --all-files`, the affected tests, and the strict docs
   build all pass.
3. Open a pull request describing the change and its motivation.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
