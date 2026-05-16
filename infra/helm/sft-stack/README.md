# sft-stack — Umbrella Helm Chart

Smart Factory Transformation: umbrella chart che aggrega tutti i servizi SFT e le dipendenze upstream (PostgreSQL, Qdrant, NATS, Langfuse) in un unico deploy gestito.

## Architettura

```
sft-stack/          ← umbrella chart (questo)
├── api-gateway     ← chart locale: REST gateway (FastAPI)
├── ot-bridge       ← chart locale: OPC-UA → NATS bridge (NetworkPolicy data-diode D-18)
├── orchestrator    ← chart locale: supervisor LangGraph
├── agents-ops      ← chart locale: cluster agenti Operations (4 repliche)
├── agents-mnt      ← chart locale: cluster agenti Maintenance
├── agents-trn      ← chart locale: cluster agenti Knowledge/Training
├── agents-scm      ← chart locale: cluster agenti Supply Chain
├── factory-ui      ← chart locale: Angular SSR frontend
├── postgresql      ← upstream Bitnami (condition: postgresql.enabled)
├── qdrant          ← upstream qdrant/qdrant (condition: qdrant.enabled)
├── nats            ← upstream nats-io/nats (condition: nats.enabled)
├── langfuse        ← upstream langfuse/langfuse (condition: langfuse.enabled)
└── ingress-nginx   ← upstream kubernetes/ingress-nginx (condition: ingress-nginx.enabled)
```

## Requisiti

- Helm 3.14+
- kubectl configurato sul cluster target
- SealedSecrets controller installato nel cluster (per secrets cifrati — D-19)
- k3d per test locale (opzionale)

## Deploy Rapido (ambiente di sviluppo)

```bash
# 1. Aggiungere i repo helm upstream
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm repo add nats https://nats-io.github.io/k8s/helm/charts/
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update

# 2. Risolvere le dipendenze
helm dependency update infra/helm/sft-stack/

# 3. Deploy (con valori CI/dev — database disabilitati per rapidità)
helm install sft-test infra/helm/sft-stack/ \
  --values infra/helm/sft-stack/values-ci.yaml

# oppure: target Makefile
make helm-test
```

## Smoke Test CI

Il workflow `.github/workflows/helm-smoke-test.yml` esegue automaticamente su ogni PR che tocca `infra/helm/**`:
- Setup cluster k3d con config `infra/k3d/ci-config.yaml`
- Installa SealedSecrets controller (D-19, Pitfall 5)
- `helm lint` su tutti i chart
- `helm install --dry-run` con `values-ci.yaml`
- `helm install` reale + `kubectl wait` pods ready
- `helm test` (HTTP probe sui service interni)

## Configurazione Production-Ready

Ogni sotto-chart include (D-17):
- `HorizontalPodAutoscaler` (configurabile via `autoscaling.*`)
- `PodDisruptionBudget` (configurabile via `podDisruptionBudget.*`)
- `NetworkPolicy` (configurabile via `networkPolicy.*`)
- `PodSecurityContext` con `runAsNonRoot: true`, UID 1000, seccompProfile RuntimeDefault
- `ServiceAccount` + RBAC minimo
- Resource requests/limits

## NetworkPolicy Data-Diode (ot-bridge)

Il chart `ot-bridge` implementa il principio data-diode OT→IT (D-18, anticipa SEC-06):
- **Ingress consentito:** solo da `component=simulator` (simulatori OPC-UA) sulla porta 4840
- **Egress consentito:** solo verso NATS (`app.kubernetes.io/name=nats`) su TCP 4222 + DNS
- **Agenti NEGATI:** il layer agenti (`component=agent`) non può raggiungere ot-bridge

ATTENZIONE: k3d usa flannel CNI che non enforcea NetworkPolicy per default. Test funzionale completo in Fase 11 con Calico CNI.

## Secrets Management (SealedSecrets)

Le credenziali (database password, API keys) NON vanno nei `values.yaml`. Usare SealedSecrets:

```bash
# Ottenere chiave pubblica cluster
kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem

# Cifrare un secret
kubectl create secret generic postgresql-credentials \
  --from-literal=postgres-password=SUPER_SECRET \
  --dry-run=client -o yaml \
| kubeseal --format yaml --cert infra/helm/sealed-secrets-pub-key.pem \
> infra/helm/sft-stack/templates/sealed-postgresql-credentials.yaml
```

Documentazione completa: [docs/operations/sealed-secrets.md](../../docs/operations/sealed-secrets.md)

## Documentazione

- [Helm Deploy Guide](../../docs/operations/helm-deploy.md) — architettura, comandi, troubleshooting
- [SealedSecrets Workflow](../../docs/operations/sealed-secrets.md) — gestione secrets cifrati
- [CONTEXT.md Helm decisions](../../.planning/phases/01-foundation-monorepo/01-CONTEXT.md) — D-16, D-17, D-18, D-19, D-20
