---
id: SOP-QLT-001
title: Ispezione tessuto con sistema di classificazione a quattro punti
version: "1.0"
lang: it
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 20
prerequisites: []
related_glossary:
  - ispezione_rotolo
  - controllo_qualita_tessile
  - tavolo_ispezione
  - difetto_trama
  - slub
  - mispick
  - difetto_catena
  - rottura_filo
tags:
  - quality
  - inspection
  - four-point
  - grading
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Ispezione tessuto con sistema di classificazione a quattro punti

## Scope

Questa SOP descrive la procedura di **ispezione_rotolo** del tessuto finito mediante il sistema di classificazione a quattro punti (Four-Point System, standard AATCC 96 / ISO 4660 per classificazione commerciale). Il sistema assegna un punteggio ai difetti in base alla loro dimensione nella direzione del tessuto (ordito o trama) indipendentemente dalla gravita' intrinseca.

La procedura si applica all'ispezione di accettazione del tessuto finito prima della spedizione o prima del confezionamento. Si applica a tutti i substrati (cotone, poliestere, blend) prodotti internamente. L'esito dell'ispezione determina la classificazione del rotolo (Prima qualita' / Seconda qualita' / Rifilo) e la decisione di lotto (CONFORME / NON CONFORME).

Il **controllo_qualita_tessile** tramite il sistema a quattro punti e' il metodo standard adottato per la classificazione commerciale nella tessitura europea.

## Prerequisites

- Il rotolo di tessuto da ispezionare e' identificato con etichetta di lotto e numero d'ordine.
- Il **tavolo_ispezione** e' pulito, funzionante (illuminazione posteriore diffusa attiva, motore di avanzamento tessuto verificato).
- L'ispettore ha completato il training sul riconoscimento visivo dei difetti tessili.
- La velocita' massima di scorrimento del tessuto sul tavolo e' impostata a ≤ 20 m/min per cotone e blend (ridurre a ≤ 15 m/min per tessuti scuri o a superficie lucida).
- Il modulo di rapporto difetti (cartaceo o digitale) e' disponibile.

## Tools and PPE

- **Tavolo_ispezione** con illuminazione posteriore diffusa e avanzamento motorizzato
- Righello o metro flessibile (per misura posizione e dimensione difetti)
- Pennarello a gessetto o nastro adesivo colorato per marcatura difetti
- Modulo rapporto difetti (o tablet con software di ispezione)
- Calcolatrice o foglio di calcolo per punteggio totale
- **Calibro_digitale** (opzionale, per verifica spessore in presenza di difetti da **slub**)
- Occhiali da vista o lente di ingrandimento (se necessario per difetti fini)
- Guanti in cotone sottile (per evitare contaminazione da sebo della superficie tessile su tessuti bianchi o chiari)

## Step-by-step Procedure

1. **Preparare il tavolo e caricare il rotolo.** Caricare il rotolo sul portarotolo del **tavolo_ispezione** con il tessuto che scorre a 45° verso l'ispettore. Verificare che il tessuto non abbia tensioni anomale durante lo scorrimento (pieghe longitudinali indicano tensione laterale non uniforme — correggere il posizionamento del rotolo).

2. **Impostare la velocita' di scorrimento.** Impostare la velocita' a ≤ 20 m/min (15 m/min per tessuti scuri). Avviare lo scorrimento e verificare che l'illuminazione posteriore diffusa permetta di vedere in controluce i difetti da filo singolo (**rottura_filo**, **slub**).

3. **Ispezionare il tessuto e classificare i difetti.** Durante lo scorrimento, identificare ogni difetto visibile e assegnare il punteggio secondo la tabella del sistema a quattro punti:

   | Dimensione difetto nella direzione trama o ordito | Punti assegnati |
   |---------------------------------------------------|-----------------|
   | ≤ 75 mm (≤ 3 pollici)                             | 1 punto         |
   | > 75 mm e ≤ 150 mm (3-6 pollici)                 | 2 punti         |
   | > 150 mm e ≤ 230 mm (6-9 pollici)                | 3 punti         |
   | > 230 mm (> 9 pollici)                            | 4 punti (max)   |

   Un singolo difetto accumula al massimo 4 punti indipendentemente dalla sua lunghezza totale. Tipologie di difetti da riconoscere: **mispick** (trama mancante), **slub** (ispessimento filo), **difetto_catena** (striscia verticale), **difetto_trama** (irregolarita' orizzontale), **rottura_filo** riparata (nodo visibile), macchie, buchi, **aloni** da olio.

4. **Marcatura e registrazione difetti.** Per ogni difetto rilevato: fermare brevemente il tessuto, misurare la posizione longitudinale (distanza dall'inizio rotolo in cm o m) e la posizione laterale (distanza dal bordo sinistro in cm), dimensione nella direzione del difetto, tipologia, punteggio assegnato. Marcare con nastro adesivo visibile sul bordo del tessuto a livello del difetto.

5. **Calcolare il punteggio totale del rotolo.** A fine ispezione: sommare tutti i punti assegnati. Calcolare i "punti per 100 m lineari": `Punteggio/100m = (punti totali x 100) / lunghezza rotolo (m)`.

6. **Classificare il rotolo.** Applicare la griglia di accettazione dell'azienda (la soglia varia per articolo e mercato destinazione — verificare con il responsabile qualita'):
   - Soglia tipica industria Prima qualita': ≤ 28 punti/100 m lineari
   - Soglia tipica Seconda qualita': 29-40 punti/100 m lineari
   - Rifilo (taglio zone difettose): > 40 punti/100 m lineari o difetto concentrato in zona specifica

7. **Compilare il rapporto di ispezione.** Inserire nel modulo: numero rotolo/lotto, articolo, lunghezza ispezionata, numero difetti per tipo, punteggio totale, punteggio/100 m, classificazione, firma ispettore, data.

## Verification

- Il rapporto di ispezione e' compilato e firmato per ogni rotolo ispezionato.
- I rotoli classificati come Prima qualita' non superano la soglia di punteggio concordata con il cliente.
- I difetti marcati sul bordo del tessuto corrispondono agli entry nel modulo rapporto difetti (verifica a campione del 10% dei difetti segnalati).
- Il tasso di difetti per tipologia (es. % **mispick**, % **slub**) e' registrato nel sistema qualita' per il calcolo del trend mensile.
- I rotoli Non Conformi sono fisicamente separati dai conformi (area di segregazione) e identificati con etichetta rossa di blocco.

## Troubleshooting

**L'ispettore non riesce a vedere i difetti fini (slub < 3 mm) alla velocita' standard:**
- Ridurre la velocita' a 10 m/min per la porzione di tessuto critica.
- Verificare che l'illuminazione posteriore sia uniforme e di intensita' sufficiente (non meno di 400 lux sul piano di ispezione). Sostituire le lampade se la luminosita' e' calata.
- Per tessuti molto fini (titolo > Nm 80): considerare l'uso di lente di ingrandimento 3x.

**Difetto non classificabile con sicurezza (incertezza tipologia):**
- Arrestare il tessuto e ispezionare il difetto con luce frontale supplementare.
- Se ancora incerto: prelevare un campione di 5 cm x 5 cm e portarlo in laboratorio per classificazione microscopica.
- In caso di dubbio tra Prima e Seconda qualita': applicare sempre la classificazione conservativa (Seconda qualita').

**Il tessuto forma pieghe laterali durante l'ispezione:**
- Verificare l'allineamento del portarotolo sul **tavolo_ispezione**.
- Se le pieghe sono strutturali (presenti anche a velocita' minima): registrare come difetto di finissaggio (pieghe permanenti) e classificare di conseguenza.

**Punteggio totale molto prossimo alla soglia di accettazione (±2 punti):**
- Effettuare una seconda ispezione da parte di un secondo ispettore su una porzione campione del 20% della lunghezza.
- In caso di discordanza tra i due ispettori > 10% nel punteggio finale: richiedere arbitraggio del quality manager e documentare entrambe le letture.

## References

- Glossario IT tessile: [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo), [tavolo_ispezione](../../docs/docs/glossary.md#tavolo_ispezione), [slub](../../docs/docs/glossary.md#slub), [mispick](../../docs/docs/glossary.md#mispick)
- SOP correlate: SOP-LOOM-001 (rottura filo ordito), SOP-LOOM-002 (deriva tensione ordito), SOP-DYE-001 (preparazione bagno colorante)
- Standard di riferimento: AATCC 96 (Four-Point System), ISO 4660 (classificazione difetti tessili), UNI EN 388 (DPI)
