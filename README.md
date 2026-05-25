# Smart Factory Transformation

Open-source **agentic platform** for the digital transformation of a textile
manufacturing industry. The platform orchestrates specialized LLM agents
(operations, maintenance, knowledge, supply) over a self-hosted, on-premise
stack, with a human-in-the-loop (HITL) approval chain, a multilingual knowledge
layer and a docs-as-code documentation site.

![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)
![Docs](https://img.shields.io/badge/docs-MkDocs%20Material-526CFE.svg)

## Highlights

- **Agentic runtime** — LangGraph supervisor pattern with native HITL interrupts
  (see [ADR-001](docs/docs/adr/ADR-001-langgraph-supervisor.md)).
- **Knowledge layer** — Qdrant + BGE-M3 hybrid retrieval, multilingual IT/EN
  (see [ADR-002](docs/docs/adr/ADR-002-qdrant-bge-m3.md)).
- **Self-hosted LLM** — on-premise inference via Ollama, no cloud API dependency
  (see [ADR-003](docs/docs/adr/ADR-003-self-hosted-llm.md)).
- **4-tier HITL approval** — role-based (RBAC) approval chain with immutable
  audit trail (see [ADR-004](docs/docs/adr/ADR-004-hitl-tiers.md)).
- **Bilingual docs** — MkDocs Material + i18n, IT/EN
  (see [ADR-005](docs/docs/adr/ADR-005-mkdocs-i18n.md)).

## Quick Start

Prerequisites: Node.js (see `.nvmrc`), Python 3.12, [uv](https://docs.astral.sh/uv/),
Docker + Docker Compose, and the Nx CLI.

```bash
# 1. Clone the repository
git clone https://github.com/smart-factory-transformation/smart-factory-transformation.git
cd smart-factory-transformation

# 2. Install Python dependencies (managed by uv, NOT npm)
uv sync

# 3. Install Node workspace dependencies
npm install

# 4. Bring up the development stack (Docker Compose)
make up          # CPU mode
# make up-gpu    # with Ollama on NVIDIA GPU

# 5. Preview the documentation locally
cd docs && python3 -m mkdocs serve   # or: make docs-serve
```

The docs site is served at `http://127.0.0.1:8000` with hot reload.

## Repository Structure

```text
.
├── apps/         # end-user applications (e.g. factory-ui Angular frontend)
├── packages/     # shared Python/TS libraries (sft-agents, sft-knowledge, sft-domain, ...)
├── services/     # backend services and APIs
├── infra/        # infrastructure: Docker Compose, Helm charts, IT/OT stack
├── simulators/   # data/process simulators for development and testing
├── docs/         # docs-as-code site (MkDocs Material, IT/EN) + economic model
└── tests/        # cross-cutting integration / load / e2e tests
```

## Documentation

The full documentation is published as a bilingual (IT/EN) MkDocs Material site
and lives under [`docs/`](docs/). It covers architecture (C4 + ADRs), domain
model, the knowledge layer, the agent catalogue, the functional and economic
analyses, and security & governance.

Build the docs in strict mode:

```bash
cd docs && python3 -m mkdocs build --strict
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the
development workflow (Conventional Commits, pre-commit hooks, tests, docs build)
and the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the **Apache License 2.0** — see the
[LICENSE](LICENSE) file for details. Selected exceptions are documented in
[LICENSE-EXCEPTIONS.md](LICENSE-EXCEPTIONS.md).
