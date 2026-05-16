---
phase: 1
plan: 6
slug: helm
subsystem: infra/helm
tags: [foundation, infra, kubernetes, helm, security, ot-data-diode, sealed-secrets]

dependency_graph:
  requires:
    - 01-01-nx-workspace  # monorepo struttura già presente
    - 01-02-compose       # service inventory (8 servizi nominati nei chart)
  provides:
    - helm charts per-servizio production-ready (8 chart)
    - umbrella chart sft-stack con dependency resolution
    - NetworkPolicy data-diode ot-bridge (D-18, anticipa SEC-06)
    - SealedSecrets workflow documentato (D-19)
    - Smoke test CI helm-smoke-test.yml (D-20)
  affects:
    - Tutte le fasi successive che aggiungono container images ai chart
    - Fase 11 (SEC-06): NetworkPolicy data-diode già presente — solo verifica funzionale
    - CI branch protection (helm-smoke-test.yml come required check)

tech_stack:
  added:
    - Helm 3.16.0 (chart management)
    - k3d (cluster locale CI via AbsaOSS/k3d-action@v2)
    - SealedSecrets bitnami-labs (secret management pattern D-19)
    - postgresql 16.7.27 (Bitnami upstream)
    - qdrant 1.18.0 (upstream)
    - nats 1.3.16 (upstream)
    - langfuse 1.5.30 (upstream)
    - ingress-nginx 4.15.1 (upstream, opt-in)
  patterns:
    - Umbrella chart + chart per-servizio (D-16)
    - PodSecurityContext runAsNonRoot UID 1000 su tutti i deployment (D-17, T-1-04)
    - NetworkPolicy data-diode egress-only per ot-bridge (D-18, T-1-05)
    - SealedSecrets RSA asymmetric per secrets cifrati committati in git (D-19, T-1-03)
    - nginx:1.27-alpine come placeholder per smoke test CI (senza immagini applicative)

key_files:
  created:
    - infra/helm/charts/api-gateway/ (Deployment, Service, HPA, PDB, NetworkPolicy, Ingress, SA, RBAC)
    - infra/helm/charts/orchestrator/ (stessa struttura, porta 8080)
    - infra/helm/charts/factory-ui/ (porta 4000 Angular SSR)
    - infra/helm/charts/ot-bridge/ (NetworkPolicy data-diode anti-OT-write)
    - infra/helm/charts/agents-ops/ (label component=agent, OT_BRIDGE_WRITE_DISABLED=true)
    - infra/helm/charts/agents-mnt/ (stessa struttura)
    - infra/helm/charts/agents-trn/ (stessa struttura)
    - infra/helm/charts/agents-scm/ (stessa struttura)
    - infra/helm/sft-stack/Chart.yaml (8 chart locali + 5 upstream con conditions)
    - infra/helm/sft-stack/Chart.lock (postgresql 16.7.27, qdrant 1.18.0, nats 1.3.16, langfuse 1.5.30, ingress-nginx 4.15.1)
    - infra/helm/sft-stack/values.yaml (produzione con documentazione puntuale)
    - infra/helm/sft-stack/values-ci.yaml (k3d smoke test, nginx placeholder, DB disabilitati)
    - infra/helm/sft-stack/templates/sealed-secrets-example.yaml (pattern opt-in)
    - infra/helm/sft-stack/README.md (documentazione umbrella chart)
    - infra/helm/sealed-secrets-pub-key.pem.placeholder (segnaposto con istruzioni kubeseal)
    - infra/k3d/ci-config.yaml (1 server, traefik+metrics-server disabled)
    - .github/workflows/helm-smoke-test.yml (required check PR: lint+dry-run+install+test)
    - docs/operations/helm-deploy.md (architettura, comandi locali, troubleshooting)
    - docs/operations/sealed-secrets.md (workflow kubeseal completo, backup DR, rotation)
  modified:
    - Makefile (helm-test target: da placeholder a comandi reali)

decisions:
  - "D-16 implementato: 8 chart per-servizio in infra/helm/charts/ + umbrella sft-stack in infra/helm/sft-stack/"
  - "D-17 soddisfatto: ogni chart ha HPA, PDB, NetworkPolicy, runAsNonRoot UID 1000, seccompProfile RuntimeDefault, RBAC minimo"
  - "D-18 NetworkPolicy data-diode ot-bridge: egress ALLOW solo verso NATS 4222 + DNS; ingress ALLOW solo da component=simulator; agenti DENY by absence"
  - "D-19 SealedSecrets: template esempio + placeholder chiave pubblica + documentazione workflow completa kubeseal"
  - "D-20 smoke test CI: k3d 1-server con traefik disabled, AbsaOSS/k3d-action@v2, SealedSecrets controller installato prima (Pitfall 5), helm lint+install+test"
  - "agents-* shared chart pattern: un chart per cluster (ops/mnt/trn/scm) con replicaCount come placeholder; decomposizione per-agente rinviata a Fase 6-9 (D-03)"
  - "Chart.lock committato per riproducibilità deploy (upstream pinned: postgresql 16.7.27)"
  - "nginx:1.27-alpine usato come immagine placeholder in values-ci.yaml per smoke test CI senza immagini applicative"

metrics:
  duration_minutes: 25
  completed_date: "2026-05-16"
  tasks_completed: 3
  files_created: 50+
  charts_created: 8
  helm_lint_pass: "9/9 (8 per-service + 1 umbrella)"
  runAsNonRoot_count: 16
  networkpolicy_count: 8

---

# Phase 1 Plan 6: Helm — Skeleton Production-Ready Summary

**One-liner:** 8 chart Helm production-ready (HPA/PDB/NetworkPolicy/RBAC/runAsNonRoot) + umbrella sft-stack con dependency upstream risolte + NetworkPolicy data-diode ot-bridge (D-18) + SealedSecrets documentati (D-19) + CI smoke test k3d (D-20).

## Obiettivo Raggiunto

Skeleton Helm production-ready completo per lo stack Smart Factory Transformation. Ogni fase successiva estende i chart aggiungendo image references e environment specifici — senza riscrivere infrastruttura.

## Struttura Finale

```
infra/helm/
├── charts/
│   ├── api-gateway/       (Deployment, Service, HPA, PDB, NetworkPolicy, Ingress, SA, RBAC, test)
│   ├── orchestrator/      (stessa struttura, porta 8080)
│   ├── factory-ui/        (stessa struttura, porta 4000 Angular SSR)
│   ├── ot-bridge/         (NetworkPolicy data-diode: egress NATS 4222, ingress solo simulator)
│   ├── agents-ops/        (label component=agent, OT_BRIDGE_WRITE_DISABLED=true)
│   ├── agents-mnt/        (stessa struttura)
│   ├── agents-trn/        (stessa struttura)
│   └── agents-scm/        (stessa struttura)
└── sft-stack/
    ├── Chart.yaml          (8 locali + 5 upstream con conditions)
    ├── Chart.lock          (pinned: pg 16.7.27, qdrant 1.18.0, nats 1.3.16, langfuse 1.5.30)
    ├── values.yaml         (produzione documentata)
    ├── values-ci.yaml      (smoke test: nginx placeholder, DB disabilitati)
    ├── README.md
    └── templates/
        └── sealed-secrets-example.yaml
```

## Verifica Qualità

| Check | Risultato |
|-------|-----------|
| `helm lint infra/helm/charts/*` (8 chart) | 8/8 PASS |
| `helm lint infra/helm/sft-stack/` | PASS |
| `helm dependency update infra/helm/sft-stack/` | PASS (Chart.lock generato) |
| `helm template | grep -c "runAsNonRoot: true"` | 16 (expected >= 8) |
| `helm template | grep -c "kind: NetworkPolicy"` | 8 (expected >= 1) |
| YAML validity (python yaml.safe_load) | 5/5 PASS |
| Immagini pinned (no latest) | nginx:1.27-alpine + busybox:1.37.0 in CI values |

## Sicurezza (Threat Model)

| Threat | Mitigazione Implementata |
|--------|--------------------------|
| T-1-04: container con UID 0 | `runAsNonRoot: true, runAsUser: 1000, seccompProfile: RuntimeDefault` su tutti i deployment |
| T-1-05: agente scrive su OT | NetworkPolicy data-diode ot-bridge: egress ALLOW solo NATS+DNS; ingress ALLOW solo simulator; agenti DENY by absence |
| T-1-03: secrets in plaintext | SealedSecrets template pattern + documentazione kubeseal completa; values.yaml riferisce solo nomi secret, mai valori |
| T-1-SC: drift upstream | Chart.lock committato per riproducibilità; range `*.x.x` per aggiornamenti controllati |

## NetworkPolicy Data-Diode (D-18)

```yaml
# ot-bridge: NetworkPolicy esatta implementazione
egress:
  - to: [podSelector: {app.kubernetes.io/name: nats}]
    ports: [{TCP: 4222}]
  - to: []
    ports: [{UDP: 53}, {TCP: 53}]
ingress:
  - from: [podSelector: {component: simulator}]
    ports: [{TCP: 4840}]
  # component=agent: NESSUNA regola -> DENY by absence
```

Nota CI: k3d usa flannel CNI che non enforcea NetworkPolicy — smoke test verifica solo validità manifest. Test funzionale con Calico CNI in Fase 11 (SEC-06).

## CI Smoke Test (D-20)

`.github/workflows/helm-smoke-test.yml` — required check su PR che toccano `infra/helm/**`:

1. k3d cluster 1-server (traefik+metrics-server disabled)
2. SealedSecrets controller installato PRIMA dell'umbrella (Pitfall 5)
3. `helm lint` tutti i chart (per-service + umbrella)
4. `helm dependency update` (risolve Chart.lock)
5. `helm install --dry-run` (validità manifest)
6. `helm install` reale + `kubectl wait` pods ready
7. `helm test sft-test --logs` (HTTP probe)

Nota: deploy reale su cluster k3d richiede la CI — non verificabile localmente senza k3d installato. La verifica client-side (`helm template` + `helm lint`) è completa e passa.

## Deviazioni dal Piano

### Auto-fixed Issues

Nessuna deviazione — piano eseguito esattamente come scritto.

**Nota su files esistenti da task precedenti:** I file `infra/helm/sft-stack/Chart.yaml`, `values.yaml`, `values-ci.yaml` erano stati creati durante il Task 2 ma non committati. Includiti nel commit del Task 3 insieme ai nuovi artefatti.

## Known Stubs

| Stub | File | Note |
|------|------|------|
| `image.tag: ""` → default a appVersion | tutti i Chart.yaml values.yaml | Intenzionale — placeholder per quando le immagini applicative saranno buildate da CI (Fase 2+) |
| `replicaCount: 1` per agents-* | agents-*/values.yaml | Placeholder per cluster agenti — decomposizione per-agente arriva con D-03 in Fase 6-9 |
| `docs/operations/helm-deploy.md → make helm-test` | Makefile | helm-test fa dry-run locale; deploy reale su k3d richiede CI o installazione k3d locale |

## Self-Check: PASSED

- [x] `infra/helm/charts/api-gateway/Chart.yaml` — FOUND
- [x] `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` — FOUND, contiene `policyTypes` e `app.kubernetes.io/name: nats`
- [x] `infra/helm/sft-stack/Chart.yaml` — FOUND, contiene `dependencies:`
- [x] `.github/workflows/helm-smoke-test.yml` — FOUND, contiene `AbsaOSS/k3d-action@v2`
- [x] `infra/k3d/ci-config.yaml` — FOUND, contiene `--disable=traefik`
- [x] `docs/operations/helm-deploy.md` — FOUND, contiene "umbrella"
- [x] `docs/operations/sealed-secrets.md` — FOUND, contiene "kubeseal"
- [x] Makefile helm-test target — reale, non placeholder
- [x] Commit f995c70 (Task 1) — FOUND
- [x] Commit c9018a8 (Task 2) — FOUND
- [x] Commit de02c21 (Task 3) — FOUND
