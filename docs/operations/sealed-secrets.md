# SealedSecrets Workflow

Guida completa per la gestione dei secrets cifrati con [SealedSecrets (Bitnami)](https://github.com/bitnami-labs/sealed-secrets) nel progetto Smart Factory Transformation (D-19).

## Perché SealedSecrets

I `Secret` Kubernetes sono codificati in base64 ma non cifrati: committarli nel repository esporrebbe credenziali in chiaro a chiunque acceda al repo.

**SealedSecrets** risolve questo con crittografia asimmetrica RSA:
- Il controller nel cluster possiede la **chiave privata** (non esce mai dal cluster)
- La **chiave pubblica** viene distribuita tramite `kubeseal --fetch-cert` ed è sicura da versionare
- I `SealedSecret` committati nel repo sono decrittabili **solo** dal controller nel cluster specifico

Scelta coerente con il modello single-tenant on-prem di SFT. ESO/Vault rinviati a v2 per scenari multi-cluster.

## Bootstrap Controller (UNA VOLTA PER CLUSTER)

```bash
# 1. Aggiungere repo
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update sealed-secrets

# 2. Installare il controller (namespace kube-system)
helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
  --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller \
  --wait \
  --timeout 5m

# 3. Verificare che il controller sia running
kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets
```

## Installare kubeseal CLI

```bash
# Linux (amd64)
curl -L "https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.0/kubeseal-0.27.0-linux-amd64.tar.gz" \
  | tar -xz -C /usr/local/bin kubeseal
chmod +x /usr/local/bin/kubeseal

# macOS (Homebrew)
brew install kubeseal

# Verifica
kubeseal --version
```

## Ottenere la Chiave Pubblica del Cluster

```bash
# Fetch della chiave pubblica dal controller
kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem

# Committare la chiave pubblica (SICURO — non contiene la chiave privata)
git add infra/helm/sealed-secrets-pub-key.pem
git commit -m "chore: add sealed-secrets public key for cluster"
```

> **Nota:** il file `infra/helm/sealed-secrets-pub-key.pem.placeholder` nel repo è solo un segnaposto
> per documentare il workflow. Sostituirlo con la chiave reale del cluster.

## Cifrare un Nuovo Secret

### Pattern Standard

```bash
# 1. Creare il Secret come dry-run (non applicato al cluster)
kubectl create secret generic <secret-name> \
  --from-literal=<key>=<value> \
  --namespace <namespace> \
  --dry-run=client -o yaml \
| kubeseal \
    --format yaml \
    --cert infra/helm/sealed-secrets-pub-key.pem \
> infra/helm/sft-stack/templates/sealed-<secret-name>.yaml

# 2. Committare il SealedSecret (SICURO)
git add infra/helm/sft-stack/templates/sealed-<secret-name>.yaml
git commit -m "chore: add sealed secret for <descrizione>"
```

### Esempio: Credenziali PostgreSQL

```bash
kubectl create secret generic postgresql-credentials \
  --from-literal=postgres-password=SUPER_SECRET_PASSWORD \
  --namespace default \
  --dry-run=client -o yaml \
| kubeseal \
    --format yaml \
    --cert infra/helm/sealed-secrets-pub-key.pem \
> infra/helm/sft-stack/templates/sealed-postgresql-credentials.yaml
```

### Esempio: API Key per Agente

```bash
kubectl create secret generic agent-api-keys \
  --from-literal=openai-api-key=sk-... \
  --from-literal=langfuse-secret=ls-... \
  --namespace default \
  --dry-run=client -o yaml \
| kubeseal \
    --format yaml \
    --cert infra/helm/sealed-secrets-pub-key.pem \
> infra/helm/sft-stack/templates/sealed-agent-api-keys.yaml
```

### Cifrare da File

```bash
# Da file con contenuto binario (es. certificati TLS)
kubectl create secret generic tls-cert \
  --from-file=tls.crt=certs/server.crt \
  --from-file=tls.key=certs/server.key \
  --namespace default \
  --dry-run=client -o yaml \
| kubeseal \
    --format yaml \
    --cert infra/helm/sealed-secrets-pub-key.pem \
> infra/helm/sft-stack/templates/sealed-tls-cert.yaml
```

## Verificare il Deploy

```bash
# Il controller decripta il SealedSecret e crea il Secret corrispondente
kubectl get sealedsecrets -n default
kubectl get secrets -n default

# Verificare che il Secret sia stato creato correttamente
kubectl describe secret <secret-name> -n default
```

## Disaster Recovery — Backup Chiave Privata

> **CRITICO:** Se la chiave privata del controller viene persa, tutti i SealedSecret esistenti
> diventano **indecifrabili**. Fare backup IMMEDIATO dopo il bootstrap.

```bash
# Backup della chiave privata (TENERE OFFLINE / in un vault sicuro)
kubectl get secret -n kube-system sealed-secrets-key \
  -o yaml > backup-sealed-secrets-key.yaml

# ATTENZIONE: questo file contiene la chiave privata del cluster.
# NON committarlo nel repository. Conservarlo in un luogo sicuro (password manager,
# vault fisico, HSM, backup offline cifrato).
```

Per ripristinare:

```bash
# Restore della chiave privata in un nuovo cluster
kubectl apply -f backup-sealed-secrets-key.yaml
kubectl rollout restart deployment/sealed-secrets-controller -n kube-system
```

## Rotation dei SealedSecret

La rotation è necessaria quando si sospetta che la chiave privata sia compromessa.

```bash
# 1. Backup della chiave privata corrente (vedi sopra)

# 2. Forzare la generazione di una nuova chiave
kubectl label secret -n kube-system sealed-secrets-key \
  sealedsecrets.bitnami.com/sealed-secrets-key=compromised

# 3. Riavviare il controller per generare nuova chiave
kubectl rollout restart deployment/sealed-secrets-controller -n kube-system

# 4. Aggiornare infra/helm/sealed-secrets-pub-key.pem con la nuova chiave
kubeseal --fetch-cert > infra/helm/sealed-secrets-pub-key.pem

# 5. Ri-cifrare TUTTI i SealedSecret con la nuova chiave pubblica
# (ripetere per ogni SealedSecret nel repository)
```

> Per procedura completa di rotation: [bitnami-labs/sealed-secrets#rotation](https://github.com/bitnami-labs/sealed-secrets#secret-rotation)

## Riferimento Threat Model

| Minaccia | Mitigazione |
|----------|-------------|
| T-1-03: secrets in plaintext nel chart | SealedSecrets cifra con RSA asymmetrico; `values.yaml` riferisce solo il nome del secret, mai il valore |
| Compromissione chiave privata controller | Backup offline chiave privata (questa guida); rotation procedure upstream |
| Accesso al `backup-sealed-secrets-key.yaml` | Conservare offline / vault fisico; **NON committare nel repository** |

## Integrazione con Helm Chart

I `SealedSecret` si integrano come template normali in `infra/helm/sft-stack/templates/`:

```yaml
# infra/helm/sft-stack/templates/sealed-postgresql-credentials.yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: postgresql-credentials
  namespace: {{ .Release.Namespace }}
spec:
  encryptedData:
    postgres-password: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...  # output kubeseal
  template:
    metadata:
      name: postgresql-credentials
    type: Opaque
```

Il controller decritterà il `SealedSecret` e creerà il `Secret` corrispondente automaticamente.

## Pitfall Noto (Pitfall 5)

Il controller SealedSecrets **deve essere installato PRIMA** di `helm install sft-stack`.
Se il CRD `SealedSecret` non esiste nel cluster, Helm fallisce con:

```
Error: no matches for kind "SealedSecret" in version "bitnami.com/v1alpha1"
```

Il workflow CI `helm-smoke-test.yml` gestisce questo correttamente installando il controller
nel step "Install SealedSecrets controller" PRIMA di "Helm install".

## Riferimenti

- [bitnami-labs/sealed-secrets](https://github.com/bitnami-labs/sealed-secrets) — docs ufficiali
- [helm-deploy.md](helm-deploy.md) — guida deploy generale
- [infra/helm/sft-stack/templates/sealed-secrets-example.yaml](../../infra/helm/sft-stack/templates/sealed-secrets-example.yaml) — template pattern
- [01-CONTEXT.md D-19](../../.planning/phases/01-foundation-monorepo/01-CONTEXT.md) — decisione architetturale
