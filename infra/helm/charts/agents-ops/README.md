# agents-ops Helm Chart

Skeleton chart per il cluster Operations (Fase 1).

## Agenti inclusi

- operator-assistant
- shift-report
- kpi-monitor
- anomaly-alert

## Stato Fase 1

Deployment singolo "cluster-stack" come placeholder. La decomposizione fine per-agente
arriverà in Fase 6-9 (D-03) quando i singoli agenti saranno deployati come app separate.

## Sicurezza

- Label `app.kubernetes.io/component: agent` — blocca l'accesso a ot-bridge via NetworkPolicy (D-18)
- `OT_BRIDGE_WRITE_DISABLED=true` come difesa applicativa aggiuntiva
- `runAsNonRoot: true` con UID 1000 (D-17, T-1-04)

## Valori principali

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `replicaCount` | `1` | Numero di repliche |
| `image.repository` | `ghcr.io/smart-factory-transformation/sft-agents-ops` | Repository immagine |
| `networkPolicy.enabled` | `true` | Abilita NetworkPolicy |
