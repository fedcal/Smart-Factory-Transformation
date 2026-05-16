# Release Workflow — Smart Factory Transformation

> **EN Summary:** This repo uses [Changesets](https://github.com/changesets/changesets) for semantic versioning of the 3 publishable SDK packages (`sft-agents`, `sft-domain`, `sft-contracts`). PyPI publish is **deferred** beyond v1; the workflow emits git tags + GitHub Releases only.

---

## Come funziona il release

Il monorepo usa Changesets per gestire il versioning semantico dei 3 SDK Python pubblicabili:

| Pacchetto | Ruolo |
|-----------|-------|
| `sft-agents` | Core SDK: interfacce Agent/Tool/Memory/Policy e LangGraph runtime adapter |
| `sft-domain` | Domain models tessitura: tassonomia difetti, asset registry, glossario IT/EN |
| `sft-contracts` | Single source of truth: modelli Pydantic condivisi fra servizi Python e frontend Angular |

---

## Aggiungere un changeset

Quando un PR introduce una modifica che merita un bump di versione dei pacchetti SDK:

```bash
npx changeset
```

Il prompt interattivo chiede:
1. **Quali pacchetti** sono stati modificati (usa spazio per selezionare)
2. **Il tipo di bump** per ciascun pacchetto
3. **Una breve descrizione** della modifica (diventa parte del CHANGELOG)

Il comando crea un file `.changeset/<nome-casuale>.md` da committare insieme al PR.

### Tipi di bump

| Tipo | Quando usarlo | Esempio |
|------|---------------|---------|
| `patch` | Bugfix, fix documentazione interna | `0.1.0` → `0.1.1` |
| `minor` | Nuova feature backward-compatible | `0.1.0` → `0.2.0` |
| `major` | Breaking change all'API pubblica | `0.1.0` → `1.0.0` |

### Esempio di changeset

```markdown
---
"sft-agents": minor
"sft-domain": patch
"sft-contracts": patch
---

Add new Tool interface to sft-agents (sft-domain and sft-contracts adapt internal types).
```

---

## I 3 SDK sono `linked`

I 3 SDK sono configurati come `linked` in `.changeset/config.json`. Questo significa che bumpano
**sempre alla stessa versione**. Se il changeset specifica bump diversi per pacchetti diversi,
viene usato il bump più alto per tutti e tre.

Esempio: `sft-agents: minor` + `sft-domain: patch` → tutti e tre ricevono `minor`.

---

## Flow di release completo

```
Developer PR                         main branch                     Release
    │                                     │                              │
    ├─ modifica codice                     │                              │
    ├─ npx changeset → .changeset/xxx.md  │                              │
    ├─ commit + push                       │                              │
    └─ merge PR ─────────────────────────►│                              │
                                          │                              │
                                     release.yml detecta changesets      │
                                          │                              │
                                     crea PR "chore(release): version packages"
                                          │    - aggiorna package.json   │
                                          │    - aggiorna __version__.py │
                                          │    - aggiorna pyproject.toml │
                                          │    - aggiorna CHANGELOG.md   │
                                          │                              │
                                 Maintainer merge PR di release          │
                                          │                              │
                                     release.yml detecta merge ─────────►│
                                                                    crea tag v<X.Y.Z>
                                                                    crea GitHub Release
                                                                    (con changelog)
```

### Step by step

1. **Sviluppatore** apre un PR con codice + `.changeset/<random>.md`
2. **PR merged** su `main`
3. **Workflow** `release.yml` rileva changeset non consumati → crea una PR di release
   - Titolo: `chore(release): version packages`
   - Aggiorna `package.json`, `__version__.py`, `pyproject.toml`, `CHANGELOG.md`
4. **Maintainer** fa review e merge della PR di release
5. **Workflow** rileva il merge della PR di release → crea:
   - Tag git `v<X.Y.Z>`
   - GitHub Release con il changelog dei changeset consumati
6. **PyPI publish**: NON automatico (vedere sezione seguente)

---

## PyPI publish: DEFERRED

La pubblicazione su PyPI è **rinviata** oltre v1. Il workflow `release.yml` nella versione
attuale esegue solo:

```bash
echo 'PyPI publish deferred — emitting tags+release only'
```

Come script `publish`, che è un no-op effettivo.

**Quando sarà abilitato:** La pubblicazione su PyPI verrà abilitata quando `sft-agents` avrà
una superficie API pubblica stabile, probabilmente dopo Phase 4. In quel momento lo script
`release` in `package.json` verrà aggiornato per eseguire `uv build && uv publish` per
ciascuno dei 3 pacchetti.

---

## Versioning automatico: package.json → `__version__.py`

Il comando `npm run version-packages` esegue:

```bash
changeset version && python3 scripts/sync-python-versions.py
```

Lo script `scripts/sync-python-versions.py` aggiorna:
- `packages/*/src/<module>/__version__.py` → `__version__ = "X.Y.Z"`
- `packages/*/pyproject.toml` → campo `version = "X.Y.Z"`

In questo modo `package.json`, `__version__.py` e `pyproject.toml` rimangono sempre
sincronizzati dopo ogni bump di versione.

---

## Troubleshooting

### La PR di release non viene creata

Verifica:
1. Il workflow ha i permessi corretti: `contents: write` e `pull-requests: write`
2. Il `GITHUB_TOKEN` è disponibile (impostato automaticamente da GitHub Actions)
3. Esistono changeset non consumati in `.changeset/` (file `.md` diversi da `README.md`)

```bash
# Verifica locale
npx changeset status
```

### CHANGELOG.md non sincronizzato con `__version__.py`

Rieseguire manualmente la sincronizzazione:

```bash
python3 scripts/sync-python-versions.py
git add packages/*/src/*/__version__.py packages/*/pyproject.toml
git commit -m "chore: sync version files"
```

### Changeset files ignorati da git

Il `.gitignore` esclude `.changeset/*.md` per default (prevenire commit accidentali di
bozze). Se vuoi committare un changeset specifico, usa:

```bash
git add -f .changeset/<nome-file>.md
```

Oppure aggiungi una negation nel `.gitignore`:

```
!.changeset/<nome-file>.md
```

---

## Note di sicurezza

- Non includere secret, password, token o dati sensibili nelle descrizioni dei changeset
- Le release notes sono **pubbliche** nella GitHub Release
- Il workflow usa `GITHUB_TOKEN` con permessi minimi (`contents: write`, `pull-requests: write`)
- Nessun permesso `id-token: write` (non richiesto finché PyPI è deferred)
