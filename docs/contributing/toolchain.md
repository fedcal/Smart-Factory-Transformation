# Toolchain Prerequisites

This document lists all tools required to work on Smart Factory Transformation and their
minimum required versions. Follow these instructions before running any `make` command.

---

## Required Tools

| Tool | Minimum Version | Verify Command | Notes |
|------|----------------|----------------|-------|
| **Node.js** | 20.x | `node -v` | Must be `>= v20` |
| **npm** | 11.x | `npm -v` | Bundled with Node 20 |
| **uv** | 0.6+ | `uv --version` | Python package/workspace manager |
| **Python** | 3.12 | `python3.12 --version` | Exact runtime version |
| **Docker Engine** | 29+ | `docker --version` | With Compose v2 plugin |
| **Docker Compose** | v2 | `docker compose version` | Plugin syntax (not `docker-compose`) |
| **helm** | 3.x | `helm version` | Kubernetes chart manager |
| **k3d** | any | `k3d version` | Optional: only for `make helm-test` |

---

## Installation Links

### Node.js 20 (via nvm — recommended)

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Install and use Node 20
nvm install 20
nvm use 20
```

Or download from: <https://nodejs.org/en/download/> (choose LTS 20.x)

### uv (Python package manager)

```bash
# Official installer (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Docs: <https://docs.astral.sh/uv/>  
Minimum version: `0.6`. This project uses `uv` workspace mode with a single `uv.lock`.

### Python 3.12 (via uv — recommended)

```bash
# Install Python 3.12 managed by uv
uv python install 3.12
```

### Docker Engine 29+

Follow official guide: <https://docs.docker.com/engine/install/>  
After installing, verify Compose v2 plugin: `docker compose version`

### Helm 3.x

```bash
# Linux/macOS quick install
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Docs: <https://helm.sh/docs/intro/install/>

### k3d (optional, for Helm smoke tests)

```bash
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

Docs: <https://k3d.io/>

---

## Quick Start

After installing all required tools, run the following sequence from the repository root:

```bash
# 1. Use correct Node version (reads .nvmrc -> 20)
nvm use

# 2. Install Python 3.12 if not already installed via uv
uv python install 3.12

# 3. Install Python dev tools
pip install uv pre-commit

# 4. Install Node dependencies (Nx, Angular, plugins)
npm ci

# 5. Sync all Python workspace packages (generates / updates uv.lock)
uv sync --all-packages

# 6. Install pre-commit hooks
pre-commit install
```

---

## Verification Checklist

Run these commands to verify your setup is complete:

```bash
# Node.js >= 20
node -v | grep -E "^v(2[0-9]|[3-9][0-9])"

# npm >= 11
npm -v | grep -E "^1[1-9]"

# uv >= 0.6
uv --version

# Python 3.12
python3.12 --version

# Docker Engine >= 29
docker --version

# Docker Compose v2
docker compose version

# Helm 3.x
helm version --short

# Nx (after npm ci)
npx nx --version
```

---

## Notes

- **Nx Cloud** is disabled by default. To enable, set the environment variable
  `NX_CLOUD_ACCESS_TOKEN` to your token from <https://cloud.nx.app/>.
- **k3d** is only required for running `make helm-test` (Helm smoke tests in CI and locally).
- All Python packages in this workspace require Python `>=3.12,<3.13`. Do not use 3.13+.
- Use `nvm use` (reads `.nvmrc`) to switch to the correct Node version automatically.
