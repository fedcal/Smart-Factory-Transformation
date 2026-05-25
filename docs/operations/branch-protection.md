# Branch Protection — `main`

Questo documento descrive la configurazione di branch protection richiesta sul branch `main`
per garantire che nessuna PR venga mergiata senza aver superato tutti i required check CI.

**Importante:** questa configurazione va applicata manualmente via GitHub UI o CLI dopo il
primo push su `main`. Non e' possibile automatizzarla via commit nel repo perche' richiede
permessi di admin sul repository.

---

## Required Status Checks

I seguenti check devono essere configurati come **required** su `main`:

| Check | Workflow | Descrizione |
|-------|----------|-------------|
| `license-scan / license-scan` | `.github/workflows/license-scan.yml` | Blocca licenze vietate (GPL/AGPL/SSPL/BUSL) — PLAT-05, D-15 |
| `pre-commit-check / pre-commit` | `.github/workflows/pre-commit-check.yml` | Linting, formatting, secret scanning |
| `ci / main` | `.github/workflows/ci.yml` | Nx affected build + test + lint |
| `helm-smoke-test / helm-test` | `.github/workflows/helm-smoke-test.yml` | Helm chart validity su k3d — plan 06 |

---

## Configurazione via GitHub UI

1. Aprire `https://github.com/<owner>/<repo>/settings/branches`
2. Cliccare **Add branch protection rule** (o edit se esiste gia')
3. In **Branch name pattern**: `main`
4. Abilitare le seguenti opzioni:

### Required pull request reviews

- [x] Require a pull request before merging
  - Required number of approvals: **1**
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners (se `.github/CODEOWNERS` esiste)

### Status checks

- [x] Require status checks to pass before merging
  - [x] Require branches to be up to date before merging
  - Aggiungere i seguenti status checks nella search box:
    - `license-scan / license-scan`
    - `pre-commit-check / pre-commit`
    - `ci / main`
    - `helm-smoke-test / helm-test`

### Conversazioni e push

- [x] Require conversation resolution before merging
- [x] Do not allow bypassing the above settings
- In **Restrict who can push to matching branches**: aggiungere il team `maintainers`

---

## Configurazione via GitHub CLI (`gh`)

```bash
gh api -X PUT repos/<owner>/<repo>/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "license-scan / license-scan",
      "pre-commit-check / pre-commit",
      "ci / main",
      "helm-smoke-test / helm-test"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": {
    "users": [],
    "teams": ["maintainers"],
    "apps": []
  },
  "required_conversation_resolution": true
}
EOF
```

Sostituire `<owner>` e `<repo>` con i valori reali (es. `your-org` e `Smart-Factory-Transformation`).

**Nota:** `enforce_admins: true` applica le regole anche agli admin. Se serve un canale
di emergenza per hotfix critico, si puo' impostare a `false` con delibera esplicita.

---

## Note operative

### Primo setup

I check `license-scan / license-scan` e `helm-smoke-test / helm-test` appariranno nella
search box di GitHub solo **dopo che il workflow e' stato eseguito almeno una volta** su
una PR. Il flow corretto per il primo setup e':

1. Aprire una PR di test (anche solo aggiungendo una riga a un `.md`)
2. Attendere che tutti i workflow girino e producano i loro check
3. Tornare nelle impostazioni branch protection e aggiungere i check dalla search box

### Aggiornare i required check

Se un workflow viene rinominato (es. `ci.yml` diventa `build-and-test.yml`), il nome del
check cambia. Aggiornare questa documentazione e le impostazioni su GitHub contestualmente.

### Bypass d'emergenza

In caso di hotfix critico su produzione che non puo' attendere la CI:
1. Un admin puo' temporaneamente disabilitare `enforce_admins` via GitHub UI
2. Documentare il bypass nel corpo del commit con tag `[hotfix]`
3. Riaprire una PR retroattiva entro 24h per far girare tutti i check

---

*Documento creato: 2026-05-16*
*Piano: Phase 1 / Plan 03 (license-scanner)*
*Requirement: PLAT-05, D-15*
