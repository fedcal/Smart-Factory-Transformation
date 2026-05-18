# Iniziare

!!! info "Contenuto in espansione"
    Questa pagina fornisce i riferimenti essenziali per il setup. I contenuti sostanziali
    arriveranno nelle fasi 2 e successive, man mano che la piattaforma viene costruita.

## Prerequisiti della toolchain

Prima di clonare il repo e avviare i servizi, assicurati di avere l'ambiente correttamente configurato:

- **Toolchain prerequisites** — Node.js, Python 3.12, uv, Docker, Nx CLI e tutti gli strumenti richiesti (documentazione completa in arrivo con le fasi successive)

## Avviare lo stack di sviluppo

Lo stack di sviluppo è orchestrato via Docker Compose e si avvia con un singolo comando:

```bash
make up          # avvia tutto lo stack (CPU mode)
make up-gpu      # avvia con Ollama su GPU NVIDIA
```

Per la documentazione completa sullo stack (in arrivo con le fasi successive):

- **Docker Compose dev stack** — servizi, volumi, healthcheck e profili

## Pipeline CI

Il monorepo usa GitHub Actions con `nx affected` per eseguire solo i job rilevanti per ogni PR:

- **CI pipeline** — workflow, required checks, branch protection (documentazione completa in arrivo)

## Deploy Helm (produzione)

Per il deploy su Kubernetes con gli Helm chart inclusi:

- **Helm deploy** — helm install, values, smoke test (documentazione completa in arrivo con le fasi operative)

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
