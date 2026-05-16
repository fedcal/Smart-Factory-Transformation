# Changesets — Smart Factory Transformation

Questo monorepo usa [Changesets](https://github.com/changesets/changesets) per il versioning semantico dei 3 SDK Python pubblicabili.

## Cos'è un changeset?

Un changeset è un file Markdown in questa cartella (`.changeset/`) che descrive:
1. **Quali pacchetti** sono stati modificati
2. **Il tipo di bump** (`patch`, `minor`, `major`)
3. **Una breve descrizione** da inserire nel CHANGELOG

## Pacchetti versionati

| Pacchetto | Descrizione |
|-----------|-------------|
| `sft-agents` | Core SDK: Agent/Tool/Memory/Policy interfaces e LangGraph runtime adapter |
| `sft-domain` | Textile domain models: defect taxonomy, asset registry, IT/EN glossary |
| `sft-contracts` | Single source of truth: Pydantic models condivisi fra servizi Python e frontend Angular |

## Polyglot policy

Questo monorepo emette release per i 3 SDK Python (sft-agents, sft-domain, sft-contracts).
Changesets gestisce: bump version in `packages/*/package.json`, generazione CHANGELOG.md,
creazione tag git, creazione GitHub Release.

**PyPI publish: DEFERRED oltre v1** — La pubblicazione effettiva su PyPI verrà abilitata quando
l'SDK ha superficie API stabile (probabilmente post-Phase 4). Fino ad allora il workflow emette
SOLO tag git + GitHub Release.

Le app Python (orchestrator, api-gateway, agenti) e le app/lib Angular NON sono pubblicate:
vivono in `apps/` e sono buildate come container.

## Come aggiungere un changeset

Quando il tuo PR introduce una modifica che merita un bump version dei pacchetti SDK:

```bash
npx changeset
```

Segui il prompt interattivo. Verranno chiesti:
- Quale/i pacchetti modificare
- Il tipo di bump (`patch`, `minor`, `major`)
- Una descrizione (finisce nel CHANGELOG)

Il comando crea un file `.changeset/<random-name>.md` che va committato insieme al PR.

## Tipi di bump

| Tipo | Quando usarlo |
|------|---------------|
| `patch` | Bugfix, fix di documentazione interna |
| `minor` | Nuova feature backward-compatible |
| `major` | Breaking change all'API pubblica |

## I 3 SDK sono `linked`

I 3 SDK sono configurati come `linked` in `.changeset/config.json`. Questo significa che bumpano
**sempre alla stessa versione**. Se modifichi solo `sft-agents`, anche `sft-domain` e
`sft-contracts` riceveranno un bump di pari livello (o superiore). Questo garantisce coerenza
fra i 3 componenti dello stack SDK.

## Flow di release completo

1. Sviluppatore apre un PR con una nuova feature + crea `.changeset/<name>.md`
2. Il PR viene merged su `main`
3. Il workflow `.github/workflows/release.yml` rileva i changeset non consumati
4. Il workflow crea automaticamente una PR di release ("chore(release): version packages") con:
   - `package.json` aggiornati per i 3 SDK
   - `CHANGELOG.md` aggiornati
   - `__version__.py` aggiornati via `scripts/sync-python-versions.py`
5. Il maintainer fa review e merge la PR di release
6. Il workflow rileva il merge e crea il tag `v<X.Y.Z>` + GitHub Release con changelog
7. **PyPI publish: NON automatico** — vedere sezione "Polyglot policy" sopra

## Note di sicurezza

- Non includere secret o dati sensibili nelle descrizioni dei changeset
- Le release notes sono pubbliche (visibili nella GitHub Release)
- Il workflow usa `GITHUB_TOKEN` con permessi minimi (`contents: write`, `pull-requests: write`)
