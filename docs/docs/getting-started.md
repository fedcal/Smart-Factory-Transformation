# Iniziare

!!! info "Contenuto in espansione"
    Questa pagina fornisce i riferimenti essenziali per il setup. I contenuti sostanziali
    arriveranno nelle fasi 2 e successive, man mano che la piattaforma viene costruita.

## Prerequisiti della toolchain

Prima di clonare il repo e avviare i servizi, assicurati di avere l'ambiente correttamente configurato:

- [Toolchain prerequisites](../contributing/toolchain.md) — Node.js, Python 3.12, uv, Docker, Nx CLI e tutti gli strumenti richiesti

## Avviare lo stack di sviluppo

Lo stack di sviluppo è orchestrato via Docker Compose e si avvia con un singolo comando:

```bash
make up          # avvia tutto lo stack (CPU mode)
make up-gpu      # avvia con Ollama su GPU NVIDIA
```

Per la documentazione completa sullo stack:

- [Docker Compose dev stack](../contributing/compose-dev-stack.md) — servizi, volumi, healthcheck e profili

## Pipeline CI

Il monorepo usa GitHub Actions con `nx affected` per eseguire solo i job rilevanti per ogni PR:

- [CI pipeline](../contributing/ci-pipeline.md) — workflow, required checks, branch protection

## Deploy Helm (produzione)

Per il deploy su Kubernetes con gli Helm chart inclusi:

- [Helm deploy](../operations/helm-deploy.md) — helm install, values, smoke test

## Preview locale della documentazione

Per visualizzare questo sito in locale durante lo sviluppo:

```bash
make docs-serve
```

Il sito sarà disponibile su `http://127.0.0.1:8000`.

---

!!! note "Fase 1"
    La struttura è predisposta; i contenuti operativi completi (workflow, esempi,
    troubleshooting) saranno aggiunti nelle fasi successive.
