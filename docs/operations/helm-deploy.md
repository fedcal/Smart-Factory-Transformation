# Helm Deploy Guide

Guida operativa per deploy dello stack Smart Factory Transformation su Kubernetes tramite i chart Helm produzione-ready (D-17).

## Architettura Chart

Lo stack SFT usa un pattern **umbrella + per-service chart** (D-16):

```
infra/helm/
├── charts/             ← chart per-servizio (deployabili indipendentemente)
│   ├── api-gateway/    ← REST gateway FastAPI (port 8080)
│   ├── ot-bridge/      ← OPC-UA → NATS bridge (port 4840; NetworkPolicy data-diode)
│   ├── orchestrator/   ← Supervisor LangGraph (port 8080)
│   ├── agents-ops/     ← Cluster Operations agents (port 8080)
│   ├── agents-mnt/     ← Cluster Maintenance agents (port 8080)
│   ├── agents-trn/     ← Cluster Knowledge/Training agents (port 8080)
│   ├── agents-scm/     ← Cluster Supply Chain agents (port 8080)
│   └── factory-ui/     ← Angular SSR frontend (port 4000)
└── sft-stack/          ← umbrella chart (aggrega tutto)
    ├── Chart.yaml      ← dependencies: chart locali + upstream (PG, Qdrant, NATS, Langfuse)
    ├── values.yaml     ← valori produzione con documentazione
    ├── values-ci.yaml  ← valori smoke test CI (nginx:1.27-alpine, DB disabilitati)
    └── templates/
        └── sealed-secrets-example.yaml  ← pattern SealedSecret (opt-in)
```

### Dipendenze Upstream Incluse

| Chart | Repository | Condition |
|-------|-----------|-----------|
| `postgresql` | `bitnami` | `postgresql.enabled` |
| `qdrant` | `qdrant/qdrant-helm` | `qdrant.enabled` |
| `nats` | `nats-io/k8s` | `nats.enabled` |
| `langfuse` | `langfuse/langfuse-k8s` | `langfuse.enabled` |
| `ingress-nginx` | `kubernetes/ingress-nginx` | `ingress-nginx.enabled` (default: false) |

## Feature Production-Ready (D-17)

Ogni chart per-servizio include:

| Risorsa | Descrizione | Configurazione |
|---------|-------------|----------------|
| `HorizontalPodAutoscaler` | Autoscaling CPU-based | `autoscaling.enabled: true/false` |
| `PodDisruptionBudget` | Disponibilità durante manutenzione | `podDisruptionBudget.enabled: true/false` |
| `NetworkPolicy` | Isolamento rete | `networkPolicy.enabled: true/false` |
| `PodSecurityContext` | `runAsNonRoot: true`, UID 1000, seccompProfile | Sempre attivo |
| `ServiceAccount` + RBAC | Principio minimo privilegio | `serviceAccount.create: true/false` |
| Resource limits/requests | Protezione scheduler | Configurabili in `resources.*` |

### PodSecurityContext (tutti i chart)

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: true
```

## NetworkPolicy Data-Diode (ot-bridge — D-18)

Il chart `ot-bridge` implementa il principio data-diode OT→IT che anticipa SEC-06 (Fase 11):

- **Ingress consentito:** solo da pod con `component=simulator` (simulatori OPC-UA) sulla porta TCP 4840
- **Egress consentito:** solo verso pod `app.kubernetes.io/name=nats` su TCP 4222 (pubblica eventi OT) + DNS (UDP/TCP 53)
- **Agenti NEGATI implicitamente:** nessuna regola consente ingress da `component=agent`; il deny è by-absence

> **Nota CI:** k3d usa flannel CNI che non enforcea NetworkPolicy. Il smoke test verifica solo che il manifest sia valido. Test funzionale con Calico CNI arriva in Fase 11 (SEC-06).

## Comandi Locali

### Prerequisiti

```bash
# Helm 3.14+
helm version

# kubectl configurato
kubectl cluster-info

# (Opzionale locale) k3d per test
k3d version
```

### Setup Iniziale

```bash
# 1. Aggiungere repo upstream
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm repo add nats https://nats-io.github.io/k8s/helm/charts/
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# 2. Risolvere dipendenze umbrella (genera Chart.lock)
helm dependency update infra/helm/sft-stack/
```

### Smoke Test Locale (make helm-test)

```bash
make helm-test
```

Equivalente a:

```bash
helm dependency update infra/helm/sft-stack/
for chart in infra/helm/charts/*; do helm lint "$chart"; done
helm lint infra/helm/sft-stack/
helm install sft-test infra/helm/sft-stack/ \
  --values infra/helm/sft-stack/values-ci.yaml \
  --dry-run
```

### Verifica Manifest (debug)

```bash
# Render tutti i manifest senza deploy
helm template sft-test infra/helm/sft-stack/ \
  -f infra/helm/sft-stack/values-ci.yaml | less

# Verifica che tutti i Deployment abbiano runAsNonRoot
helm template sft-test infra/helm/sft-stack/ \
  -f infra/helm/sft-stack/values-ci.yaml | grep -c "runAsNonRoot: true"
# Atteso: >= 8 (uno per chart locale)

# Verifica NetworkPolicy data-diode presente
helm template sft-test infra/helm/sft-stack/ \
  -f infra/helm/sft-stack/values-ci.yaml | grep -c "kind: NetworkPolicy"
# Atteso: >= 1

# Lint singolo chart
helm lint infra/helm/charts/ot-bridge/
```

### Deploy Produzione

```bash
# Installare SealedSecrets controller PRIMA (Pitfall 5)
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
  --namespace kube-system --wait

# Ottenere chiave pubblica per cifrare i secrets
kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem

# Cifrare i secrets di produzione (vedere docs/operations/sealed-secrets.md)
# ...

# Deploy stack completo
helm install sft-prod infra/helm/sft-stack/ \
  --values infra/helm/sft-stack/values.yaml \
  --namespace sft \
  --create-namespace \
  --wait

# Upgrade rolling
helm upgrade sft-prod infra/helm/sft-stack/ \
  --values infra/helm/sft-stack/values.yaml \
  --namespace sft \
  --wait
```

## CI Workflow (helm-smoke-test.yml)

Il workflow `.github/workflows/helm-smoke-test.yml` è un **required check** su branch protection di `main` (vedere [branch-protection.md](branch-protection.md)).

Si attiva su PR che modificano:
- `infra/helm/**`
- `infra/k3d/**`
- `.github/workflows/helm-smoke-test.yml`

Steps CI:
1. Setup cluster k3d (`infra/k3d/ci-config.yaml`)
2. Installa SealedSecrets controller (Pitfall 5 — deve precedere umbrella install)
3. `helm lint` tutti i chart (per-servizio + umbrella)
4. `helm dependency update` (risolve dipendenze upstream)
5. `helm install --dry-run` (verifica validità manifest senza deploy)
6. `helm install` reale + `kubectl wait` pods ready
7. `helm test` (HTTP probe sui service interni via wget)

## Troubleshooting

### `helm dependency update` fallisce

```bash
# Aggiornare i repo
helm repo update
helm dependency update infra/helm/sft-stack/
```

### `helm lint` fallisce con "no matches for kind"

```bash
# Installare SealedSecrets CRD prima di lintare sft-stack
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
  --namespace kube-system --wait
```

### Pod non si avvia (ImagePullBackOff)

In ambiente dev usare `values-ci.yaml` che usa `nginx:1.27-alpine` come placeholder:
```bash
helm install sft-test infra/helm/sft-stack/ --values infra/helm/sft-stack/values-ci.yaml
```

## Riferimenti

- [SealedSecrets Workflow](sealed-secrets.md) — gestione secrets cifrati per GitOps
- [Branch Protection](branch-protection.md) — required checks configurati
- [01-CONTEXT.md Helm decisions](../../.planning/phases/01-foundation-monorepo/01-CONTEXT.md) — D-16 D-17 D-18 D-19 D-20
- [infra/helm/sft-stack/README.md](../../infra/helm/sft-stack/README.md) — documentazione umbrella chart
