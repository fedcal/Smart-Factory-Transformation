---
id: SOP-QLT-002
title: Rilevamento e registrazione rotture filo durante ispezione tessuto
version: "1.0"
lang: it
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 25
prerequisites:
  - SOP-QLT-001
related_glossary:
  - rottura_filo
  - ispezione_rotolo
  - difetto_catena
  - tavolo_ispezione
  - controllo_qualita_tessile
  - sistema_quattro_punti
tags:
  - quality
  - inspection
  - broken-end
  - detection
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Rilevamento e registrazione rotture filo durante ispezione tessuto

## Scope

Questa SOP descrive la metodologia specializzata per il rilevamento e la registrazione sistematica delle **rottura_filo** riparate (rincorsi) visibili durante l'**ispezione_rotolo** del tessuto finito. La **rottura_filo** riparata si manifesta come un nodo o una discontinuita' di colore/struttura nel filo di **ordito**, distinguibile dai difetti di **trama** e classificabile secondo il sistema a quattro punti.

Questa specializzazione e' necessaria perche' le **rottura_filo** riparate tendono ad essere sottovalutate nell'ispezione generale (il rincorso appare integro a prima vista) ma sono spesso associate a **difetto_catena** latenti che si manifestano solo in fase di finissaggio o di tintura.

La procedura si applica all'**ispezione_rotolo** su **tavolo_ispezione** con retroilluminazione, per tessuti grezzi o finiti con densita' superiore a 18 fili/cm (sopra questa densita' le **rottura_filo** riparate sono meno visibili ad occhio nudo a velocita' standard).

## Prerequisites

- L'**ispezione_rotolo** base (SOP-QLT-001) e' in corso o e' stata completata per il rotolo in esame.
- Il **tavolo_ispezione** e' attrezzato con retroilluminazione a LED di intensita' ≥ 600 lux (intensita' elevata necessaria per l'individuazione di rincorsi sottili).
- Il rapporto di ispezione base (SOP-QLT-001) e' disponibile con i difetti gia' registrati.
- DPI: guanti in cotone sottile, occhiali da lettura o lente di ingrandimento (se necessario).

## Tools and PPE

- **Tavolo_ispezione** con retroilluminazione ad alta intensita' (≥ 600 lux)
- Lente di ingrandimento 3x-5x (per verifica rincorsi dubbi in tessuti fini)
- Righello o metro flessibile (per posizione e dimensione del rincorso)
- Pennarello a gessetto o nastro colorato (per marcatura rincorsi significativi)
- Modulo di rapporto difetti (integrato con il rapporto SOP-QLT-001)
- Guanti in cotone sottile

## Step-by-step Procedure

1. **Impostare la velocita' di scorrimento ottimale per la rilevazione.** Ridurre la velocita' di scorrimento del tessuto a ≤ 15 m/min (vs. 20 m/min standard). Per tessuti con **densita_trama** > 25 picks/cm o **titolo_filato** > Nm 60: ridurre a ≤ 10 m/min. La velocita' ridotta e' necessaria per permettere all'occhio di individuare i rincorsi sottili.

2. **Posizionare correttamente l'illuminazione.** Verificare che la retroilluminazione copra uniformemente l'intera larghezza del tessuto in scorrimento. Per tessuti scuri: integrare con una luce radente laterale (angolo 30-45 gradi rispetto al piano del tessuto) che evidenzia le irregolarita' superficiali dei rincorsi.

3. **Riconoscere la firma visiva di una rottura_filo riparata.** La **rottura_filo** riparata si riconosce per:
   - Nodo visibile nel filo di **ordito** (punto di discontinuita' strutturale, piu' spesso di 1.3-2x il diametro del filo)
   - Leggera variazione di colore nel filo di **ordito** riparato (il filo di riserva puo' avere una torsione o un lotto leggermente diverso)
   - Asimmetria di tensione nell'**ordito** adiacente (il filo riparato puo' essere piu' lasco o piu' teso)
   - Presenza di **difetto_catena** nelle 5-10 cm adiacenti al punto di rincorso

4. **Classificare ogni rottura_filo riparata.** Per ogni rincorso individuato, assegnare il punteggio secondo il sistema a quattro punti (SOP-QLT-001). In aggiunta al punteggio standard, classificare la qualita' del rincorso:
   - **Rincorso accettabile:** nodo pulito, variazione visiva minima, nessun **difetto_catena** adiacente
   - **Rincorso borderline:** nodo visibile ma contenuto (<2x il diametro del filo), leggera variazione cromatica nella zona di ripresa
   - **Rincorso non accettabile:** nodo grossolano (>2x diametro), **difetto_catena** esteso, discontinuita' strutturale visibile a 1 m di distanza

5. **Registrare i rincorsi nel rapporto di ispezione.** Per ogni rincorso individuato, aggiungere al modulo di rapporto difetti: posizione longitudinale, posizione laterale, punteggio sistema a quattro punti, classificazione qualita' rincorso, tipologia difetto associato (es. **difetto_catena** se presente). Marcare con nastro visibile i rincorsi classificati "non accettabile".

6. **Calcolare la frequenza di rincorsi per 100 m e per larghezza.** A fine ispezione del rotolo: calcolare il numero di rincorsi per 100 m lineari e per metro di larghezza. Un valore > 3 rincorsi/100 m lineari e' spesso indicativo di problemi sistematici nel processo di **tessitura** (tensione **ordito** instabile, liccio usurato, filato di bassa qualita').

7. **Valutare la correlazione con la decisione di classificazione lotto.** I rincorsi "non accettabili" contribuiscono al punteggio totale di **sistema_quattro_punti** e possono portare al declassamento del rotolo. Segnalare al responsabile qualita' se la frequenza di rincorsi supera la soglia aziendale: e' un indicatore di processo che richiede escalation al reparto **tessitura**.

8. **Completare il rapporto integrando i dati rincorsi con la classificazione base.** Finalizzare il rapporto di **ispezione_rotolo** includendo il conteggio e la classificazione dei rincorsi. La classificazione finale del rotolo (Prima / Seconda / Rifilo) tiene conto sia del punteggio totale che della frequenza di rincorsi non accettabili.

## Verification

- I rincorsi "non accettabili" sono marcati fisicamente sul rotolo e registrati nel rapporto con posizione e classificazione.
- La frequenza di rincorsi per 100 m e' calcolata e riportata nel rapporto.
- Se la frequenza supera la soglia aziendale, il responsabile qualita' e il capotecnico del reparto **tessitura** sono stati informati.
- La classificazione finale del rotolo tiene conto correttamente dei rincorsi nel punteggio totale.

## Troubleshooting

**Il rincorso e' visibile con retroilluminazione ma non ad occhio nudo a luce normale:**
- I rincorsi "trasparenti" sono rincorsi di qualita' elevata (filo di riserva identico al filo originale, nodo minimo). Sono classificabili come "accettabili" se non c'e' variazione cromatica associata. Registrare comunque la posizione per il tracking della frequenza di processo.

**Impossibile distinguere un rincorso da un variazione naturale del titolo del filo:**
- Se il dubbio persiste dopo ispezione con lente 5x e luce radente: applicare la regola del beneficio del dubbio conservativo — classificare come rincorso borderline. In fase di contestazione di lotto, il campione specifico del punto dubbio potra' essere analizzato al microscopio.

**Frequency elevata di rincorsi concentrata in una zona laterale del tessuto:**
- Indica probabile problema in un **liccio** specifico o in un gruppo di fili di **ordito** con tensione anomala. Annotare la zona laterale nel rapporto (es. "rincorsi concentrati tra cm 40 e 60 dal bordo sinistro") per consentire la diagnosi al reparto **tessitura**.

## References

- Glossario IT tessile: [rottura_filo](../../docs/docs/glossary.md#rottura_filo), [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo), [difetto_catena](../../docs/docs/glossary.md#difetto_catena)
- SOP correlate: SOP-QLT-001 (ispezione tessuto 4 punti), SOP-LOOM-001 (rottura filo ordito), SOP-LOOM-002 (deriva tensione ordito)
- Standard di riferimento: AATCC 96 (Four-Point System), ISO 4660 (classificazione difetti tessili)
