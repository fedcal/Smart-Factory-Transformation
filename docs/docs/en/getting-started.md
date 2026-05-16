# Getting Started

!!! info "Content Expanding"
    This page provides essential setup references. Substantive content will arrive
    in phases 2 and beyond as the platform is built.

## Toolchain Prerequisites

Before cloning the repo and starting the services, ensure your environment is correctly configured:

- [Toolchain prerequisites](../contributing/toolchain.md) — Node.js, Python 3.12, uv, Docker, Nx CLI and all required tools

## Starting the Development Stack

The development stack is orchestrated via Docker Compose and starts with a single command:

```bash
make up          # start the full stack (CPU mode)
make up-gpu      # start with Ollama on NVIDIA GPU
```

For complete documentation on the stack:

- [Docker Compose dev stack](../contributing/compose-dev-stack.md) — services, volumes, healthchecks, and profiles

## CI Pipeline

The monorepo uses GitHub Actions with `nx affected` to run only the jobs relevant to each PR:

- [CI pipeline](../contributing/ci-pipeline.md) — workflows, required checks, branch protection

## Helm Deploy (Production)

For Kubernetes deployment using the included Helm charts:

- [Helm deploy](../operations/helm-deploy.md) — helm install, values, smoke test

## Local Documentation Preview

To view this site locally during development:

```bash
make docs-serve
```

The site will be available at `http://127.0.0.1:8000`.

---

!!! note "Phase 1"
    The structure is in place; complete operational content (workflows, examples,
    troubleshooting) will be added in subsequent phases.
