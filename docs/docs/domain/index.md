# Dominio: analisi tessile manifatturiera

Questa sezione documenta il dominio della manifattura tessile italiana di medie dimensioni, con riferimento al caso Mantis Textile Group. L'analisi è organizzata in pagine processo — unità di retrieval naturali per gli agenti RAG di Phase 5 — e pagine ruolo, che supportano il filtraggio del retrieval per persona operativa.

Lo scopo è duplice: fornire una reference open-source riusabile per il settore tessile manifatturiero italiano e offrire il substrato di conoscenza che alimenterà gli agenti della piattaforma (OperatorAssistant, MaintenanceCoach, QualityInspector, ecc.).

!!! note "Mantis context"
    Mantis Textile Group è un'azienda tessile italiana di medie dimensioni, attiva nel segmento abbigliamento outdoor e sportswear. Produce tessuti tecnici in blend cotone/lana/lino su turni 3×8h. Il sito produttivo dispone di reparti tessitura, orditura, tintura e finissaggio in un unico stabilimento lombardo.

## Mappa ad alto livello

```mermaid
flowchart LR
    accDescr: "Flusso produttivo tessile: orditura → tessitura → tintura → finissaggio, con filatura a monte."
    A[Filatura] --> B[Orditura]
    B --> C[Tessitura]
    C --> D[Tintura]
    D --> E[Finissaggio]
```

> Processo vs asset_family. I 5 *processi* (weaving/spinning/warping/dyeing/finishing) sono i flussi produttivi lineari definiti dalla decisione D-21. L'attributo `asset_family` dei SOP estende quel set con `quality_grading` — uno scope d'ispezione trasversale che opera su tutti i processi (4-point grading, broken-end detection, ecc., per D-27) e non è un processo a sé stante. L'ispezione qualità interviene in modo trasversale su ogni fase del flusso, non sequenzialmente dopo il finissaggio. Vedi `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` per l'enum completo (6 valori).

## Pagine processo

Le cinque pagine processo documentano il flusso produttivo lineare, ciascuna con diagramma Mermaid, asset coinvolti, KPI e pain point:

- [Filatura](processes/spinning.md)
- [Orditura](processes/warping.md)
- [Tessitura](processes/weaving.md)
- [Tintura](processes/dyeing.md)
- [Finissaggio](processes/finishing.md)

## Pagine ruolo

Le quattro pagine ruolo descrivono le figure operative che interagiscono con processi e asset, con focus sulle decisioni critiche e sui pain point quotidiani:

- [Operatore](roles/operator.md)
- [Tecnico manutentore](roles/technician.md)
- [Responsabile qualità](roles/quality-manager.md)
- [Capoturno](roles/shift-supervisor.md)
