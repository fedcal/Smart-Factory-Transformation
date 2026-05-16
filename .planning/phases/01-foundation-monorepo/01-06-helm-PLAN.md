---
phase: 1
plan: 6
slug: helm
type: execute
wave: 4
depends_on: ["01", "02"]
files_modified:
  - infra/helm/charts/api-gateway/Chart.yaml
  - infra/helm/charts/api-gateway/values.yaml
  - infra/helm/charts/api-gateway/templates/_helpers.tpl
  - infra/helm/charts/api-gateway/templates/deployment.yaml
  - infra/helm/charts/api-gateway/templates/service.yaml
  - infra/helm/charts/api-gateway/templates/hpa.yaml
  - infra/helm/charts/api-gateway/templates/pdb.yaml
  - infra/helm/charts/api-gateway/templates/networkpolicy.yaml
  - infra/helm/charts/api-gateway/templates/ingress.yaml
  - infra/helm/charts/api-gateway/templates/serviceaccount.yaml
  - infra/helm/charts/api-gateway/templates/rbac.yaml
  - infra/helm/charts/api-gateway/templates/tests/test-connection.yaml
  - infra/helm/charts/ot-bridge/Chart.yaml
  - infra/helm/charts/ot-bridge/values.yaml
  - infra/helm/charts/ot-bridge/templates/_helpers.tpl
  - infra/helm/charts/ot-bridge/templates/deployment.yaml
  - infra/helm/charts/ot-bridge/templates/service.yaml
  - infra/helm/charts/ot-bridge/templates/hpa.yaml
  - infra/helm/charts/ot-bridge/templates/pdb.yaml
  - infra/helm/charts/ot-bridge/templates/networkpolicy.yaml
  - infra/helm/charts/ot-bridge/templates/serviceaccount.yaml
  - infra/helm/charts/ot-bridge/templates/rbac.yaml
  - infra/helm/charts/orchestrator/Chart.yaml
  - infra/helm/charts/orchestrator/values.yaml
  - infra/helm/charts/orchestrator/templates/_helpers.tpl
  - infra/helm/charts/orchestrator/templates/deployment.yaml
  - infra/helm/charts/orchestrator/templates/service.yaml
  - infra/helm/charts/orchestrator/templates/hpa.yaml
  - infra/helm/charts/orchestrator/templates/pdb.yaml
  - infra/helm/charts/orchestrator/templates/networkpolicy.yaml
  - infra/helm/charts/orchestrator/templates/serviceaccount.yaml
  - infra/helm/charts/orchestrator/templates/rbac.yaml
  - infra/helm/charts/agents-ops/**
  - infra/helm/charts/agents-mnt/**
  - infra/helm/charts/agents-trn/**
  - infra/helm/charts/agents-scm/**
  - infra/helm/charts/factory-ui/**
  - infra/helm/sft-stack/Chart.yaml
  - infra/helm/sft-stack/values.yaml
  - infra/helm/sft-stack/values-ci.yaml
  - infra/helm/sft-stack/templates/sealed-secrets-example.yaml
  - infra/helm/sft-stack/README.md
  - infra/helm/sealed-secrets-pub-key.pem.placeholder
  - infra/k3d/ci-config.yaml
  - .github/workflows/helm-smoke-test.yml
  - docs/operations/helm-deploy.md
  - docs/operations/sealed-secrets.md
  - Makefile
autonomous: true
requirements: [PLAT-08]
tags: [foundation, infra, kubernetes, helm, security, ot-data-diode]

must_haves:
  truths:
    - "Esistono 8 chart per-servizio in `infra/helm/charts/{api-gateway,ot-bridge,orchestrator,agents-ops,agents-mnt,agents-trn,agents-scm,factory-ui}/` ognuno con Deployment, Service, HPA, PDB, NetworkPolicy, ServiceAccount, RBAC"
    - "Ogni chart applica `podSecurityContext.runAsNonRoot: true` con UID 1000 (D-17)"
    - "Il chart `ot-bridge` ha NetworkPolicy che permette egress verso `app.kubernetes.io/name=nats` su TCP 4222 e nega ingress dai pod con label `app.kubernetes.io/component=agent` (D-18 data-diode)"
    - "L'umbrella chart `infra/helm/sft-stack/` ha dependencies su 8 chart locali + 4 upstream (Bitnami postgresql, qdrant/qdrant, langfuse/langfuse, nats-io/nats) + 1 opzionale (ingress-nginx)"
    - "Workflow `helm-smoke-test.yml` su PR: setup k3d, install sealed-secrets controller, `helm dependency update`, `helm install --dry-run`, `helm install`, `kubectl wait --all`, `helm test` — exit 0 (D-20)"
    - "Esiste documentazione SealedSecrets in `docs/operations/sealed-secrets.md` con workflow kubeseal completo (D-19)"
  artifacts:
    - path: "infra/helm/sft-stack/Chart.yaml"
      provides: "Umbrella chart con dependencies upstream e locali"
      contains: "dependencies:"
    - path: "infra/helm/charts/ot-bridge/templates/networkpolicy.yaml"
      provides: "NetworkPolicy data-diode anti-OT-write per ot-bridge"
      contains: "policyTypes"
    - path: ".github/workflows/helm-smoke-test.yml"
      provides: "CI required check con k3d + helm install + helm test"
      contains: "AbsaOSS/k3d-action"
    - path: "infra/k3d/ci-config.yaml"
      provides: "Config k3d cluster per CI (1 server, no traefik)"
  key_links:
    - from: "infra/helm/sft-stack/Chart.yaml"
      to: "infra/helm/charts/* + upstream charts"
      via: "dependencies entries"
      pattern: "repository:"
    - from: "infra/helm/charts/ot-bridge/templates/networkpolicy.yaml"
      to: "NATS pod selector"
      via: "egress to app.kubernetes.io/name=nats"
      pattern: "matchLabels"
---

<objective>
Costruire lo skeleton Helm production-ready (D-17): 8 chart per-servizio con Deployment/Service/HPA/PDB/NetworkPolicy/Ingress/SA/RBAC, umbrella chart con dependencies upstream (PG/Qdrant/NATS/Langfuse) e locali, NetworkPolicy data-diode per ot-bridge (D-18 anticipa SEC-06), SealedSecrets workflow documentato (D-19), smoke test CI su k3d (D-20). Soddisfa Phase Success Criterion #5: Helm chart deploya su cluster Kubernetes locale senza errore.

Purpose: avere helm chart "production-ready" già in Fase 1 (D-17 esplicito utente) significa che ogni fase successiva non deve riscrivere infrastruttura, solo aggiungere container image references e environment specifics. La NetworkPolicy data-diode anticipata in `ot-bridge` rende il test SEC-06 in Fase 11 una semplice verifica funzionale.

Output: workspace Helm valido, `helm template sft-stack` produce manifest validi, `helm-smoke-test.yml` come required check.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-foundation-monorepo/01-CONTEXT.md
@.planning/phases/01-foundation-monorepo/01-RESEARCH.md
@CLAUDE.md
@.planning/phases/01-foundation-monorepo/01-01-SUMMARY.md
@.planning/phases/01-foundation-monorepo/01-02-SUMMARY.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent pods -> ot-bridge pod | confine OT/IT critico; verso non consentito (data-diode) |
| sealed-secrets controller -> repo | secrets cifrati committati richiedono controller live nel cluster |
| umbrella chart -> upstream chart | rischio drift versione upstream con licenza/CVE inattesi |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-04 | Elevation of Privilege | container runtime con UID 0 | mitigate | ogni Deployment template applica `podSecurityContext.runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`, `fsGroup: 1000`, `seccompProfile.type: RuntimeDefault` (D-17); validato in helm template lint |
| T-1-05 | Elevation of Privilege | agent compromesso che tenta di scrivere su OT (ot-bridge) | mitigate | NetworkPolicy in chart `ot-bridge`: ingress DENIES `app.kubernetes.io/component=agent`; egress ALLOW solo verso NATS (port 4222) + DNS (port 53); anticipa SEC-06 (D-18) |
| T-1-03 | Information Disclosure | secret in plaintext nel chart values | mitigate | SealedSecrets workflow documentato (D-19); template `sealed-secrets-example.yaml` come pattern; `values.yaml` riferisce secret name, mai value plaintext; kubeseal CLI standardizzato |
| T-1-SC | Tampering | upstream chart drift (Bitnami postgresql, qdrant, langfuse) | accept | `Chart.yaml` dependencies con range `"16.x.x"` etc.; `helm dependency update` produce `Chart.lock` committato per riproducibilità (Open Question 3 in RESEARCH) |
</threat_model>

<tasks>

<task id="1-06-01" wave="4" type="auto">
  <name>Task 1: Chart api-gateway, orchestrator, factory-ui (con tutti i template production-ready)</name>
  <files>infra/helm/charts/api-gateway/**, infra/helm/charts/orchestrator/**, infra/helm/charts/factory-ui/**</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 7: Helm Umbrella Chart, righe ~951-1046; PodSecurityContext template righe ~1035-1046)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-16 chart per-servizio + umbrella; D-17 production-ready)
  </read_first>
  <action>
    Per CIASCUNO dei tre chart (`api-gateway`, `orchestrator`, `factory-ui`) creare in `infra/helm/charts/<name>/`:

    1. `Chart.yaml`:
       ```yaml
       apiVersion: v2
       name: <name>
       description: Smart Factory Transformation - <name> service chart
       type: application
       version: 0.1.0
       appVersion: "0.1.0"
       ```

    2. `values.yaml` minimo ma documentato:
       ```yaml
       replicaCount: 1
       image:
         repository: ghcr.io/fedcal/sft-<name>
         pullPolicy: IfNotPresent
         tag: ""   # default to Chart appVersion
       imagePullSecrets: []
       nameOverride: ""
       fullnameOverride: ""
       serviceAccount:
         create: true
         annotations: {}
         name: ""
       podAnnotations: {}
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
       service:
         type: ClusterIP
         port: 8080   # 8080 per backend; per factory-ui usare 4000 (SSR)
       ingress:
         enabled: false   # production opt-in
         className: "nginx"
         hosts: []
         tls: []
       resources:
         limits: { cpu: 500m, memory: 512Mi }
         requests: { cpu: 100m, memory: 128Mi }
       autoscaling:
         enabled: false
         minReplicas: 1
         maxReplicas: 5
         targetCPUUtilizationPercentage: 80
       podDisruptionBudget:
         enabled: true
         minAvailable: 1
       networkPolicy:
         enabled: true
       nodeSelector: {}
       tolerations: []
       affinity: {}
       ```

    3. `templates/_helpers.tpl` con i tipici helper Helm (`<name>.fullname`, `<name>.labels`, `<name>.selectorLabels`, `<name>.serviceAccountName`). Generabile con `helm create <name>` come baseline e poi pulito.

    4. `templates/deployment.yaml` con:
       - `apiVersion: apps/v1`, `kind: Deployment`
       - `metadata.name: {{ include "<name>.fullname" . }}`
       - `spec.replicas: {{ .Values.replicaCount }}` (omesso se `autoscaling.enabled`)
       - `spec.selector.matchLabels: {{ include "<name>.selectorLabels" . | nindent 6 }}`
       - `spec.template.metadata.labels: {{ include "<name>.labels" . | nindent 8 }}` con label `app.kubernetes.io/component: <component>` dove component = `gateway` per api-gateway, `orchestrator` per orchestrator, `ui` per factory-ui
       - `spec.template.spec.serviceAccountName: {{ include "<name>.serviceAccountName" . }}`
       - `spec.template.spec.securityContext: {{- toYaml .Values.podSecurityContext | nindent 8 }}`
       - `containers[0]`: name, image, imagePullPolicy, port 8080 (o 4000 per factory-ui), securityContext da values, resources da values, env vars placeholder, readinessProbe + livenessProbe su `/health` (placeholder)

    5. `templates/service.yaml` standard ClusterIP su port `.Values.service.port`.

    6. `templates/hpa.yaml` con `{{- if .Values.autoscaling.enabled }}` guard.

    7. `templates/pdb.yaml` con `{{- if .Values.podDisruptionBudget.enabled }}`.

    8. `templates/networkpolicy.yaml` con `{{- if .Values.networkPolicy.enabled }}`: per `api-gateway` e `orchestrator` policy default-deny + ingress allowed da `factory-ui` (label match) e namespace `monitoring`; per `factory-ui` ingress consentito da ingress-nginx namespace.

    9. `templates/ingress.yaml` con guard `{{- if .Values.ingress.enabled }}` (api-gateway e factory-ui hanno ingress sensato; orchestrator no).

    10. `templates/serviceaccount.yaml` con guard `{{- if .Values.serviceAccount.create }}`.

    11. `templates/rbac.yaml` con Role + RoleBinding minimi (es. `get/list/watch` su configmaps nel namespace; nessun cluster-role).

    12. `templates/tests/test-connection.yaml` (per `helm test`): Pod che esegue `wget -qO- http://<service-name>:<port>/health`.

    Helper modello per generare in batch: usare `helm create <name>` come base in directory temporanea e poi normalizzare i template (rimuovere defaults non desiderati come autoscaling/hpa.yaml che helm-create lascia disabilitato di default; cambiare port da 80 a 8080).
  </action>
  <acceptance_criteria>
    - `infra/helm/charts/api-gateway/Chart.yaml` esiste e contiene `version: 0.1.0`
    - `infra/helm/charts/api-gateway/templates/deployment.yaml` esiste e contiene `runAsNonRoot: true` (via reference a values.podSecurityContext)
    - `infra/helm/charts/orchestrator/templates/networkpolicy.yaml` esiste e contiene `policyTypes`
    - `infra/helm/charts/factory-ui/templates/ingress.yaml` esiste e contiene `{{- if .Values.ingress.enabled }}`
    - `helm lint infra/helm/charts/api-gateway/` exits 0
    - `helm lint infra/helm/charts/orchestrator/` exits 0
    - `helm lint infra/helm/charts/factory-ui/` exits 0
    - `helm template api-gateway infra/helm/charts/api-gateway/ | grep -c "runAsNonRoot: true"` >= 1
  </acceptance_criteria>
</task>

<task id="1-06-02" wave="4" type="auto">
  <name>Task 2: Chart ot-bridge con NetworkPolicy data-diode + 4 chart agents-*</name>
  <files>infra/helm/charts/ot-bridge/**, infra/helm/charts/agents-ops/**, infra/helm/charts/agents-mnt/**, infra/helm/charts/agents-trn/**, infra/helm/charts/agents-scm/**</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 7: NetworkPolicy data-diode righe ~994-1033; Open Question 4 k3d NetworkPolicy enforcement)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-18 NetworkPolicy ot-bridge anticipa SEC-06)
  </read_first>
  <action>
    Creare chart `infra/helm/charts/ot-bridge/` con la stessa struttura del task 1 MA con `templates/networkpolicy.yaml` ESATTO come da RESEARCH Pattern 7 (righe 994-1033):
    ```yaml
    {{- if .Values.networkPolicy.enabled }}
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: {{ include "ot-bridge.fullname" . }}-data-diode
      labels: {{- include "ot-bridge.labels" . | nindent 4 }}
    spec:
      podSelector:
        matchLabels: {{- include "ot-bridge.selectorLabels" . | nindent 6 }}
      policyTypes:
        - Ingress
        - Egress
      egress:
        # Allowed: pubblicare su NATS
        - to:
            - podSelector:
                matchLabels:
                  app.kubernetes.io/name: nats
          ports:
            - protocol: TCP
              port: 4222
        # Allowed: DNS resolution
        - to: []
          ports:
            - protocol: UDP
              port: 53
            - protocol: TCP
              port: 53
      ingress:
        # Allowed: connessione FROM simulatori OPC-UA (component=simulator)
        - from:
            - podSelector:
                matchLabels:
                  app.kubernetes.io/component: simulator
          ports:
            - protocol: TCP
              port: 4840
        # Esplicitamente NESSUNA rule per ingress dal layer agenti
        # (component=agent label viene DENY by default)
    {{- end }}
    ```
    Aggiungere a `ot-bridge/values.yaml` `podLabels.app.kubernetes.io/component: ot-bridge` e port 4840 nel service. Aggiungere commento header al `networkpolicy.yaml`:
    ```
    # NetworkPolicy data-diode: anticipa SEC-06 (Fase 11). Garantisce che il bridge OT->IT
    # pubblichi solo verso NATS (egress) e accetti connessioni solo dai simulatori OPC-UA
    # (component=simulator). Nessuna regola ingress consente al layer agenti
    # (component=agent) di raggiungere ot-bridge - implementa il principio data-diode (D-18).
    # ATTENZIONE: il smoke test CI usa k3d con flannel CNI di default che NON enforce
    # NetworkPolicy. Test funzionale completo arriva in Fase 11 con Calico CNI.
    ```

    Creare i 4 chart `agents-{ops,mnt,trn,scm}/` ESATTAMENTE come `api-gateway` (task 1) ma con:
    - `Chart.yaml`: name = `agents-ops` (etc), description specifica cluster
    - `values.yaml`: `replicaCount: 4` di default (1 agent per replica come placeholder; in realtà ogni cluster ha 4 agenti come app separate, quindi si potrebbe avere `replicaCount: 1` per ogni agente e helm subchart per ciascun agente — per Fase 1 mantenere singolo Deployment "cluster-stack" con 4 replicas come placeholder, e nota in README che la decomposizione fine arriverà con D-03 quando i singoli agenti saranno deployati)
    - `templates/deployment.yaml`: label `app.kubernetes.io/component: agent` (per matchare la NetworkPolicy di ot-bridge che li DENY-by-default)
    - `templates/networkpolicy.yaml` con `app.kubernetes.io/component: agent` come pod selector; egress ALLOWED verso NATS (4222), Postgres (5432), Qdrant (6333), Langfuse (3000); ingress consentito solo dal pod orchestrator e da api-gateway.
    - `README.md` minimo che indica "Skeleton chart Phase 1; subchart per-agent decomposition arriva in Fase 6-9".

    Aggiungere a TUTTI i deployment dei chart agents la env var `OT_BRIDGE_WRITE_DISABLED=true` come ulteriore difesa applicativa (cintura + bretelle del data-diode).
  </action>
  <acceptance_criteria>
    - `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` esiste
    - `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` contiene `app.kubernetes.io/component: simulator`
    - `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` contiene `app.kubernetes.io/name: nats`
    - `infra/helm/charts/ot-bridge/templates/networkpolicy.yaml` NON contiene `app.kubernetes.io/component: agent` in nessuna regola di ingress (i.e. agent layer non listed -> deny by absence)
    - 4 chart `agents-{ops,mnt,trn,scm}/Chart.yaml` esistono
    - `helm lint infra/helm/charts/ot-bridge/` exits 0
    - `helm lint infra/helm/charts/agents-ops/` exits 0
    - `helm template ot-bridge infra/helm/charts/ot-bridge/ | grep -c "data-diode"` >= 1
  </acceptance_criteria>
</task>

<task id="1-06-03" wave="4" type="auto">
  <name>Task 3: Umbrella chart sft-stack + values-ci.yaml + Helm smoke test workflow + SealedSecrets docs</name>
  <files>infra/helm/sft-stack/Chart.yaml, infra/helm/sft-stack/values.yaml, infra/helm/sft-stack/values-ci.yaml, infra/helm/sft-stack/templates/sealed-secrets-example.yaml, infra/helm/sft-stack/README.md, infra/helm/sealed-secrets-pub-key.pem.placeholder, infra/k3d/ci-config.yaml, .github/workflows/helm-smoke-test.yml, docs/operations/helm-deploy.md, docs/operations/sealed-secrets.md, Makefile</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 7 umbrella Chart.yaml righe ~953-993; Pattern 10 SealedSecrets righe ~1266-1300; Pitfall 5 SealedSecrets controller install order)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-19 SealedSecrets, D-20 ingress-nginx + k3d smoke test)
  </read_first>
  <action>
    Creare `infra/helm/sft-stack/Chart.yaml` con `dependencies:` per gli 8 chart locali (`file://../charts/<name>`) E 5 upstream:
    ```yaml
    apiVersion: v2
    name: sft-stack
    description: Smart Factory Transformation - Umbrella Chart
    type: application
    version: 0.1.0
    appVersion: "0.1.0"
    dependencies:
      - name: api-gateway
        version: "0.1.0"
        repository: "file://../charts/api-gateway"
      - name: ot-bridge
        version: "0.1.0"
        repository: "file://../charts/ot-bridge"
      - name: orchestrator
        version: "0.1.0"
        repository: "file://../charts/orchestrator"
      - name: agents-ops
        version: "0.1.0"
        repository: "file://../charts/agents-ops"
      - name: agents-mnt
        version: "0.1.0"
        repository: "file://../charts/agents-mnt"
      - name: agents-trn
        version: "0.1.0"
        repository: "file://../charts/agents-trn"
      - name: agents-scm
        version: "0.1.0"
        repository: "file://../charts/agents-scm"
      - name: factory-ui
        version: "0.1.0"
        repository: "file://../charts/factory-ui"
      - name: postgresql
        version: "16.x.x"
        repository: "https://charts.bitnami.com/bitnami"
        condition: postgresql.enabled
      - name: qdrant
        version: "1.x.x"
        repository: "https://qdrant.github.io/qdrant-helm"
        condition: qdrant.enabled
      - name: nats
        version: "1.x.x"
        repository: "https://nats-io.github.io/k8s/helm/charts/"
        condition: nats.enabled
      - name: langfuse
        version: "1.x.x"
        repository: "https://langfuse.github.io/langfuse-k8s"
        condition: langfuse.enabled
      - name: ingress-nginx
        version: "4.x.x"
        repository: "https://kubernetes.github.io/ingress-nginx"
        condition: ingress-nginx.enabled
    ```
    NOTA: lasciare i range `*.x.x`; `helm dependency update` produrrà `Chart.lock` che il CI committerà via PR review.

    Creare `infra/helm/sft-stack/values.yaml` con:
    - `postgresql.enabled: true`, `auth.postgresPassword: ""` (placeholder, da SealedSecret in prod), `primary.persistence.size: 20Gi`
    - `qdrant.enabled: true`
    - `nats.enabled: true`, `nats.jetstream.enabled: true`
    - `langfuse.enabled: true` (default; può essere disabilitato in dev)
    - `ingress-nginx.enabled: false` (opt-in)
    - Sezioni overrides per ognuno degli 8 chart locali (es. `api-gateway: { replicaCount: 2, autoscaling: { enabled: true } }`)
    - Commenti puntuali su ogni gruppo

    Creare `infra/helm/sft-stack/values-ci.yaml` minimal per smoke test:
    ```yaml
    postgresql: { enabled: false }   # esterno per CI; smoke test non boot DB
    qdrant: { enabled: false }
    nats: { enabled: false }
    langfuse: { enabled: false }
    ingress-nginx: { enabled: false }
    api-gateway:
      replicaCount: 1
      image: { repository: nginx, tag: "1.27-alpine" }   # placeholder funzionante per smoke test
      autoscaling: { enabled: false }
      podDisruptionBudget: { enabled: false }
      ingress: { enabled: false }
    ot-bridge: { ... stesso pattern ... }
    orchestrator: { ... }
    factory-ui: { ... }
    agents-ops: { replicaCount: 1, image: { repository: nginx, tag: "1.27-alpine" } }
    agents-mnt: { ... }
    agents-trn: { ... }
    agents-scm: { ... }
    ```
    Lo scopo è che il smoke test installi un chart che effettivamente avvia container (nginx come placeholder service, ascolta su 80; aggiustare ports di conseguenza per `helm test` connection).

    Creare `infra/helm/sft-stack/templates/sealed-secrets-example.yaml` come pattern (commentato, opt-in) che mostra come includere SealedSecret riferiti dai sotto-chart.

    Creare `infra/helm/sealed-secrets-pub-key.pem.placeholder` (file vuoto con un commento `# Placeholder. Replace with actual cluster public cert via: kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem`) — NON committare la chiave pubblica reale finché non c'è un cluster reale; placeholder per documentare il workflow.

    Creare `infra/k3d/ci-config.yaml`:
    ```yaml
    apiVersion: k3d.io/v1alpha5
    kind: Simple
    metadata:
      name: sft-test
    servers: 1
    agents: 0
    options:
      k3s:
        extraArgs:
          - arg: --disable=traefik
            nodeFilters: [server:*]
          - arg: --disable=metrics-server
            nodeFilters: [server:*]
    ```

    Creare `.github/workflows/helm-smoke-test.yml`:
    ```yaml
    name: Helm Smoke Test
    on:
      pull_request:
        paths:
          - 'infra/helm/**'
          - 'infra/k3d/**'
          - '.github/workflows/helm-smoke-test.yml'
      push:
        branches: [main]
    jobs:
      helm-test:
        runs-on: ubuntu-latest
        timeout-minutes: 20
        steps:
          - uses: actions/checkout@v4
          - name: Setup helm
            uses: azure/setup-helm@v4
            with:
              version: v3.16.0
          - name: Setup k3d
            uses: AbsaOSS/k3d-action@v2
            with:
              cluster-name: sft-test
              args: --config infra/k3d/ci-config.yaml
          - name: Wait for k3d ready
            run: kubectl wait --for=condition=ready node --all --timeout=60s
          - name: Install SealedSecrets controller (Pitfall 5)
            run: |
              helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
              helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
                --namespace kube-system --wait --timeout 2m
          - name: Helm lint all charts
            run: |
              for chart in infra/helm/charts/*; do
                helm lint "$chart"
              done
              helm lint infra/helm/sft-stack/
          - name: Helm dependency update
            run: helm dependency update infra/helm/sft-stack/
          - name: Helm install dry-run
            run: |
              helm install sft-test infra/helm/sft-stack/ \
                --values infra/helm/sft-stack/values-ci.yaml \
                --dry-run
          - name: Helm install (real)
            run: |
              helm install sft-test infra/helm/sft-stack/ \
                --values infra/helm/sft-stack/values-ci.yaml \
                --timeout 5m \
                --wait
          - name: Kubectl wait for pods
            run: kubectl wait --for=condition=ready pod --all --namespace default --timeout=120s
          - name: Helm test
            run: helm test sft-test --logs
          - name: Print pod status on failure
            if: failure()
            run: |
              kubectl get pods --all-namespaces
              kubectl describe pods --all-namespaces
              kubectl logs --all-containers=true -l app.kubernetes.io/instance=sft-test
    ```

    Creare `docs/operations/helm-deploy.md` che documenta:
    - Architettura umbrella + per-service (D-16)
    - Production-ready features per chart (D-17)
    - Comandi locali: `helm dependency update infra/helm/sft-stack/`, `helm template sft-test infra/helm/sft-stack/ -f infra/helm/sft-stack/values-ci.yaml | less`, `make helm-test`
    - Linkare `branch-protection.md`

    Creare `docs/operations/sealed-secrets.md` che documenta il workflow kubeseal (D-19) esatto come da RESEARCH righe 1268-1300:
    - Bootstrap controller nel cluster (UNA volta)
    - Fetch chiave pubblica (`kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem`)
    - Per ogni nuovo secret: `kubectl create secret ... --dry-run=client -o yaml | kubeseal --format yaml --cert ... > sealed-secret.yaml`
    - Disaster recovery: backup chiave privata controller (riferimento `kubectl get secret -n kube-system sealed-secrets-key -o yaml > backup.yaml`)
    - Rotation procedure (riferimento upstream).

    Aggiornare `Makefile` per implementare `helm-test`:
    ```
    helm-test:
    	@command -v helm >/dev/null || (echo "helm non trovato: brew install helm o https://helm.sh/docs/intro/install/" && exit 1)
    	@command -v k3d >/dev/null || (echo "k3d non trovato; per CI verrà installato via AbsaOSS/k3d-action" && exit 1)
    	helm dependency update infra/helm/sft-stack/
    	for chart in infra/helm/charts/*; do helm lint "$$chart"; done
    	helm lint infra/helm/sft-stack/
    	helm install sft-test infra/helm/sft-stack/ --values infra/helm/sft-stack/values-ci.yaml --dry-run
    ```
  </action>
  <acceptance_criteria>
    - `infra/helm/sft-stack/Chart.yaml` esiste e contiene `dependencies:` con almeno 8 chart locali + 4 upstream
    - `infra/helm/sft-stack/values-ci.yaml` esiste e disabilita postgresql/qdrant/nats/langfuse per smoke test
    - `infra/k3d/ci-config.yaml` esiste e contiene `--disable=traefik`
    - `.github/workflows/helm-smoke-test.yml` esiste e contiene `AbsaOSS/k3d-action@v2`
    - `.github/workflows/helm-smoke-test.yml` contiene step Install SealedSecrets controller PRIMA di helm install (Pitfall 5)
    - `.github/workflows/helm-smoke-test.yml` contiene `helm test sft-test`
    - `docs/operations/helm-deploy.md` esiste e contiene "umbrella"
    - `docs/operations/sealed-secrets.md` esiste e contiene "kubeseal"
    - `Makefile` target `helm-test` ora esegue comandi helm reali
    - `python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/helm-smoke-test.yml','infra/helm/sft-stack/Chart.yaml','infra/helm/sft-stack/values.yaml','infra/k3d/ci-config.yaml']]"` exits 0
  </acceptance_criteria>
</task>

</tasks>

<verification>
1. `for chart in infra/helm/charts/*; do helm lint "$chart"; done` exits 0
2. `helm lint infra/helm/sft-stack/` exits 0
3. `helm dependency update infra/helm/sft-stack/` exits 0 e produce Chart.lock
4. `helm install --dry-run sft-test infra/helm/sft-stack/ --values infra/helm/sft-stack/values-ci.yaml` exits 0
5. `helm template sft-test infra/helm/sft-stack/ -f infra/helm/sft-stack/values-ci.yaml | grep -c "runAsNonRoot: true"` >= 8 (uno per chart locale)
6. `helm template sft-test infra/helm/sft-stack/ -f infra/helm/sft-stack/values-ci.yaml | grep -c "kind: NetworkPolicy"` >= 1 (ot-bridge data-diode)
7. CI workflow `.github/workflows/helm-smoke-test.yml` da `gh workflow run helm-smoke-test.yml` deve eseguire e completare exit 0 in CI.
</verification>

<success_criteria>
- 8 chart per-servizio production-ready (HPA, PDB, NetworkPolicy, RBAC, runAsNonRoot) — D-17
- Umbrella chart con dependencies upstream e locali — D-16
- NetworkPolicy data-diode in ot-bridge — D-18 (anticipa SEC-06)
- SealedSecrets workflow documentato — D-19
- Smoke test CI passa su k3d — D-20, Phase Success Criterion #5
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-06-SUMMARY.md` quando done.
</output>
