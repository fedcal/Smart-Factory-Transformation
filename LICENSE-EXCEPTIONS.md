# License Exceptions

Questo file documenta le eccezioni alle licenze approvate esplicitamente per dipendenze
al di fuori dell'allowlist standard definita in `infra/license/trivy.yaml`.

**Ogni eccezione richiede approvazione esplicita prima dell'uso in produzione.**
L'allowlist standard del progetto (`notice` in trivy.yaml) include: MIT, Apache-2.0,
BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0, PSF-2.0, Python-2.0, 0BSD.
Licenze `reciprocal` (MPL-2.0, LGPL-2.1, LGPL-3.0) generano warning senza bloccare la build.
Licenze `forbidden` (GPL-*, AGPL-*, SSPL-1.0, BUSL-1.1) bloccano la build **a meno che
non appaiano in questa tabella con approvazione documentata**.

---

## Eccezioni Approvate

| Package | Version | License | Reason | Approved Date | Approver | Scope |
|---------|---------|---------|--------|---------------|----------|-------|
| minio | container cgr.dev/chainguard/minio:latest | AGPL-3.0 | Usato as-is via container upstream come dipendenza Langfuse v3. AGPL applica solo se modifichiamo il binary. Distribuiamo via Helm chart con default upstream senza modifiche al codice MinIO. Compatibile single-tenant on-premise (no SaaS hosting / no public network service trigger). Vedi: https://www.gnu.org/licenses/agpl-3.0.en.html#section13 | 2026-05-16 | Federico | runtime (Langfuse object storage) |

---

## Processo per Aggiungere una Nuova Eccezione

### Requisiti per l'approvazione

Prima di aggiungere una riga a questa tabella, il richiedente deve:

1. **Verificare il tipo di utilizzo**: il pacchetto viene usato as-is, viene modificato,
   o viene eseguito come servizio accessibile via rete da terze parti?
2. **Valutare il rischio legale**: consultare `docs/legal/license-compatibility.md`
   (da creare in Fase 2) per la matrice di compatibilità licenze.
3. **Documentare la motivazione tecnica**: perche' non esiste un'alternativa con licenza
   permissiva equivalente (MIT/Apache-2.0)?
4. **Identificare lo scope**: la dipendenza e' solo in build/dev (transitive dev-only)?
   O arriva nel runtime distribuito (deploy on-prem)?

### Campi obbligatori

| Campo | Descrizione |
|-------|-------------|
| Package | Nome esatto del pacchetto o dell'immagine container |
| Version | Versione esatta o range approvato (pinned preferito) |
| License | Identificatore SPDX della licenza (es. AGPL-3.0, GPL-3.0-only) |
| Reason | Motivazione tecnica e legale: come viene usata, perche' e' compatibile |
| Approved Date | Data di approvazione in formato ISO 8601 (YYYY-MM-DD) |
| Approver | Nome e cognome del responsabile che approva |
| Scope | `build` / `test` / `runtime` con descrizione del contesto di utilizzo |

### Template PR per nuova eccezione

```markdown
## License Exception Request

**Package:** <nome-pacchetto>
**Version:** <versione>
**License:** <SPDX-identifier>

### Motivazione

<Spiegare perche' il pacchetto e' necessario e non sostituibile con alternativa permissiva>

### Analisi compatibilita'

<Descrivere il tipo di utilizzo (as-is, modificato, SaaS) e perche' la licenza e' compatibile
con Apache-2.0 del progetto in questo contesto>

### Scope

<build | test | runtime> — <contesto specifico>

### Alternativa valutata

<Alternativa con licenza permissiva e perche' non adottata>
```

### Chi approva

- **Eccezioni LGPL/MPL** (reciprocal): un maintainer puo' approvare con review del codice
- **Eccezioni AGPL/GPL** (forbidden): richiede review da almeno 2 maintainer
  e documentazione dell'analisi legale nel corpo della PR
- **Eccezioni SSPL/BUSL** (forbidden): richiede approvazione del lead maintainer
  e analisi esplicita del modello di distribuzione (SaaS vs on-prem)

---

*Ultimo aggiornamento: 2026-05-16*
*Maintainer: Federico Calo*
