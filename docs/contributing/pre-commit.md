# Guida a pre-commit — Smart Factory Transformation

Questo progetto usa **[pre-commit](https://pre-commit.com/)** per eseguire quality gates automatici prima di ogni commit (linting Python, linting TypeScript, formattazione, controllo commit message, secret scanning).

Gli stessi hook vengono eseguiti in CI tramite `.github/workflows/pre-commit-check.yml` come required check su ogni PR verso `main`.

---

## Prerequisiti

- Python 3.12+ (il progetto usa `.python-version` per il pinning)
- Node.js 20+ (per eslint e prettier)
- `uv` 0.6+ (per dipendenze Python e mypy)
- `npm` 11+ (per dipendenze TypeScript)

Vedi [toolchain.md](toolchain.md) per le istruzioni di installazione complete.

---

## Installazione

### 1. Installare pre-commit

```bash
pip install pre-commit==4.6.0
```

Oppure tramite uv:

```bash
uv tool install pre-commit==4.6.0
```

### 2. Installare gli hook nel repository

```bash
pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg
```

Questo comando installa due tipi di hook:
- `pre-commit`: eseguito prima di ogni commit (ruff, mypy, eslint, prettier, gitleaks, ecc.)
- `commit-msg`: eseguito per validare il messaggio di commit (commitlint)

### 3. Verificare l'installazione

```bash
pre-commit run --all-files
```

Su un repository pulito (senza violazioni), tutti gli hook devono passare con exit code 0.

---

## Hook configurati

| Hook | Repo | Rev | Scopo |
|------|------|-----|-------|
| `ruff-format` | astral-sh/ruff-pre-commit | v0.11.10 | Formattazione Python |
| `ruff` | astral-sh/ruff-pre-commit | v0.11.10 | Linting Python (+ auto-fix) |
| `mypy-sft-packages` | local | — | Type checking strict su `packages/sft-*` |
| `eslint` | local | — | Linting TypeScript/Angular |
| `prettier` | pre-commit/mirrors-prettier | v3.5.3 | Formattazione TS/JSON/YAML/MD |
| `commitlint` | alessandrojcm/commitlint-pre-commit-hook | v9.18.0 | Validazione commit message |
| `gitleaks` | gitleaks/gitleaks | v8.24.2 | Secret scanning |
| `trailing-whitespace` | pre-commit/pre-commit-hooks | v5.0.0 | Spazi finali |
| `end-of-file-fixer` | pre-commit/pre-commit-hooks | v5.0.0 | Newline finale |
| `check-yaml` | pre-commit/pre-commit-hooks | v5.0.0 | Validita` YAML |
| `check-json` | pre-commit/pre-commit-hooks | v5.0.0 | Validita` JSON |
| `check-merge-conflict` | pre-commit/pre-commit-hooks | v5.0.0 | Marker conflitti git |
| `check-added-large-files` | pre-commit/pre-commit-hooks | v5.0.0 | File >1 MB |

---

## Utilizzo quotidiano

### Run manuale su tutti i file

```bash
pre-commit run --all-files
```

### Run su file specifici

```bash
pre-commit run --files packages/sft-agents/src/sft_agents/tool.py
```

### Run di un hook specifico

```bash
pre-commit run ruff --all-files
pre-commit run mypy-sft-packages --all-files
pre-commit run gitleaks --all-files
```

---

## Skip temporaneo (sconsigliato)

In casi eccezionali e giustificati, e` possibile saltare gli hook:

### Skip di tutti gli hook

```bash
git commit --no-verify -m "chore: emergency hotfix"
```

**Attenzione:** Il CI ri-eseguira` gli stessi hook. Un commit che bypassa pre-commit lokale fallira` comunque in CI.

### Skip di un hook specifico

```bash
SKIP=mypy-sft-packages git commit -m "feat(sft-agents): WIP — mypy fix in progress"
```

```bash
SKIP=eslint git commit -m "fix(ui-factory): temporary skip eslint for draft PR"
```

---

## Aggiornamento versioni hook

Per aggiornare i `rev:` nel `.pre-commit-config.yaml` alle ultime versioni:

```bash
pre-commit autoupdate
```

**Processo obbligatorio:** le modifiche ai `rev:` devono sempre passare per una PR con review. Non fare merge di `pre-commit autoupdate` senza verificare che tutti gli hook passino ancora su `main` dopo l'aggiornamento.

---

## Troubleshooting

### Reset della cache pre-commit

Se gli hook si comportano in modo inaspettato, pulire la cache:

```bash
pre-commit clean
```

Poi reinstallare gli hook:

```bash
pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg
```

### ESLint non trova `node_modules`

Se eslint fallisce con errore `Cannot find module`, rieseguire:

```bash
npm ci
```

### mypy non trova i moduli

Se mypy fallisce con `Module not found`, verificare che le dipendenze Python siano sincronizzate:

```bash
uv sync --all-packages
```

### gitleaks segnala un falso positivo

Se gitleaks blocca un file di fixture o documentazione legittimo, aggiungere il path alla sezione `[allowlist]` in `.gitleaks.toml`:

```toml
[allowlist]
  paths = [
    '''tests/license/.*''',
    '''il/tuo/path/fixture/.*''',
  ]
```

Aprire sempre una PR con la modifica e documentare la motivazione nel commento del PR.

### commitlint rifiuta il messaggio

Verificare che il messaggio segua il formato `<type>(<scope>): <subject>`. Consultare [commit-conventions.md](commit-conventions.md) per esempi.

Testare un messaggio senza fare commit:

```bash
echo "feat(sft-agents): add Tool base class" | npx commitlint
```

---

## CI integration

Il workflow `.github/workflows/pre-commit-check.yml` esegue `pre-commit run --all-files` su ogni PR verso `main` e su ogni push a `main`. E` configurato come **required status check** nel branch protection di `main`.

Se un hook fallisce in CI ma non lokalmente, verificare che le versioni degli strumenti siano allineate:
- Python: 3.12 (`.python-version`)
- Node.js: 20 (`.nvmrc`)
- uv: 0.6+ (`uv --version`)

---

## Riferimenti

- [pre-commit documentation](https://pre-commit.com/)
- [Configurazione hook](.../../.pre-commit-config.yaml)
- [Convenzioni commit](commit-conventions.md)
- [Gitleaks documentation](https://github.com/gitleaks/gitleaks)
