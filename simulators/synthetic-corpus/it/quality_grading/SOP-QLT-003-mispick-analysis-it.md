---
id: SOP-QLT-003
title: Analisi e classificazione difetti mispick nel tessuto
version: "1.0"
lang: it
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 20
prerequisites:
  - SOP-QLT-001
related_glossary:
  - mispick
  - difetto_trama
  - ispezione_rotolo
  - tavolo_ispezione
  - densita_trama
  - controllo_qualita_tessile
tags:
  - quality
  - inspection
  - mispick
  - analysis
  - quality-manager
audience: quality
status: reviewed
created_in_phase: 2
---

# Analisi e classificazione difetti mispick nel tessuto

## Scope

Questa SOP descrive la procedura specializzata di rilevamento, analisi e classificazione dei **mispick** (passate di trama mancanti, doppie o mal inserite) durante l'**ispezione_rotolo** del tessuto. Il **mispick** e' il difetto di **tessitura** piu' frequente e puo' manifestarsi in tre forme principali: filo di **trama** mancante (caduta di trama), filo di **trama** doppio (due passate in una sola apertura), o filo di **trama** mal inserito (trama non interlacciata correttamente con l'**ordito**).

La distinzione tra le tipologie di **mispick** e' fondamentale per la diagnosi del problema al telaio: tipologie diverse indicano cause meccaniche diverse. La SOP fornisce le chiavi di lettura per la diagnosi di processo oltre alla semplice classificazione visiva.

La procedura si applica all'ispezione su **tavolo_ispezione** con retroilluminazione per tutti i substrati.

## Prerequisites

- L'**ispezione_rotolo** base (SOP-QLT-001) e' in corso o completata.
- Il valore di **densita_trama** target e la tolleranza (picks/cm ± toleranza) per l'articolo in esame sono disponibili.
- Il **tavolo_ispezione** con retroilluminazione e' operativo.
- DPI: guanti in cotone sottile, righello millimetrico.

## Tools and PPE

- **Tavolo_ispezione** con retroilluminazione ad intensita' regolabile
- Lente di ingrandimento 5x (per analisi del tipo di mispick)
- Conta-fili (picker glass — lente di ingrandimento con griglia millimetrica per conteggio **densita_trama**)
- Righello o metro flessibile (per misura posizione e dimensione del difetto)
- Pennarello a gessetto o nastro (per marcatura difetti sul bordo)
- Modulo rapporto difetti

## Step-by-step Procedure

1. **Identificare il mispick durante lo scorrimento sul tavolo.** Il **mispick** si riconosce durante lo scorrimento per:
   - Riga orizzontale visibile nel tessuto (a retroilluminazione): indica assenza di filo di **trama** (caduta di trama)
   - Riga orizzontale piu' spessa del normale: indica doppia passata di **trama**
   - Discontinuita' orizzontale con filamento di **trama** non interlacciato: indica inserzione mal riuscita
   Fermare il tessuto al rilevamento del **mispick** e procedere all'analisi.

2. **Classificare la tipologia di mispick.** Con la lente 5x e retroilluminazione, analizzare la struttura del difetto:
   - **Mispick tipo 1 (trama mancante):** una o piu' passate di **trama** assenti — la retroilluminazione mostra una riga trasparente orizzontale. Causa tipica al telaio: filo di **trama** rotto durante l'inserzione senza attivazione del rilevatore.
   - **Mispick tipo 2 (doppia trama):** due fili di **trama** nella stessa battuta — il tessuto e' piu' spesso in quel punto. Causa tipica: errore del meccanismo di inserzione (doppia alimentazione).
   - **Mispick tipo 3 (trama non interlacciata):** il filo di **trama** e' presente ma non interlacciato correttamente con alcuni fili di **ordito** — visibile come un filo "galleggiante". Causa tipica: passo non completamente aperto al momento dell'inserzione (**liccio** lento o mal sincronizzato).

3. **Misurare la lunghezza del difetto.** Con il righello, misurare la lunghezza del **mispick** nella direzione della **trama** (larghezza del difetto nel tessuto). Classificare per punteggio secondo il sistema a quattro punti (SOP-QLT-001). Misurare anche quante passate consecutive sono interessate (es. singola passata mancante vs. 3 passate mancanti consecutive).

4. **Verificare la densita' di trama nella zona del difetto.** Con il conta-fili, contare il numero di fili di **trama** per cm nelle zone a 5 cm e a 10 cm dal **mispick**. Confrontare con il valore target dell'articolo. Una variazione di **densita_trama** nelle zone adiacenti al **mispick** indica una perturbazione del meccanismo di inserzione che puo' estendersi oltre il punto visibile del difetto.

5. **Registrare il mispick con tipologia e causa diagnostica.** Nel modulo di rapporto difetti, inserire: posizione, dimensione, punteggio quattro punti, tipologia (1/2/3), numero di passate consecutive interessate, eventuali variazioni di **densita_trama** nelle zone adiacenti.

6. **Identificare la distribuzione dei mispick nel rotolo.** Calcolare la frequenza di **mispick** per 100 m e la loro distribuzione: regolare (ricorrente a intervalli fissi) o casuale. Un **mispick** ricorrente a intervalli regolari suggerisce un problema meccanico ciclico al telaio (es. meccanismo di inserzione con usura periodica). Un pattern casuale indica problemi intermittenti (filo di **trama** fragile, qualita' variabile della bobina).

7. **Compilare il report di analisi mispick.** Aggiungere al rapporto base (SOP-QLT-001) la sezione di analisi **mispick**: conteggio per tipologia (1/2/3), frequenza/100 m, distribuzione (regolare/casuale), eventuale pattern regolare con passo indicato. Questa informazione e' essenziale per il reparto **tessitura** nella diagnosi della causa meccanica.

8. **Comunicare la diagnosi al reparto tessitura (se la frequenza supera la soglia).** Se il conteggio **mispick** supera la soglia aziendale (tipicamente >2/100 m per articoli standard) o se e' stato identificato un pattern regolare: comunicare al capotecnico del reparto **tessitura** il rapporto di analisi con la tipologia diagnosticata. La tipologia di **mispick** orienta direttamente la diagnosi meccanica.

## Verification

- Tutti i **mispick** del rotolo sono classificati per tipologia (1/2/3) e registrati con posizione e punteggio.
- La frequenza di **mispick** per 100 m e' calcolata e riportata nel rapporto.
- Se la frequenza supera la soglia, il reparto **tessitura** e' stato informato con il rapporto di analisi tipologica.
- La classificazione finale del rotolo tiene conto correttamente del punteggio totale **mispick**.

## Troubleshooting

**Non e' possibile distinguere tra mispick tipo 1 e tipo 3 con la lente 5x:**
- Applicare retroilluminazione radente da un lato del tessuto: il **mispick** tipo 3 (filo galleggiante) mostra un filo fisicamente presente che non segue il pattern di interlacciamento; il **mispick** tipo 1 mostra assenza completa di filo. Se il dubbio persiste: prelevare un campione di 5x5 cm per analisi al microscopio ottico.

**Il mispick e' visibile in retroilluminazione ma non in luce diretta:**
- Si tratta di un **mispick** "leggero" (filo di **trama** presente ma non correttamente interlacciato in una o poche maglie di **ordito**). E' comunque classificabile e va registrato. La retroilluminazione e' il metodo standard per questi difetti sottili.

**La frequenza di mispick varia significativamente tra la prima e la seconda meta' del rotolo:**
- Indica un cambiamento di condizioni durante la produzione: cambio bobina di **trama**, variazione di tensione nel **telaio**, o inizio di usura di un componente meccanico. Registrare la posizione di cambio nel rapporto per aiutare la diagnosi temporale al reparto **tessitura**.

## References

- Glossario IT tessile: [mispick](../../docs/docs/glossary.md#mispick), [difetto_trama](../../docs/docs/glossary.md#difetto_trama), [ispezione_rotolo](../../docs/docs/glossary.md#ispezione_rotolo)
- SOP correlate: SOP-QLT-001 (ispezione tessuto 4 punti), SOP-LOOM-003 (inceppamento navetta), SOP-LOOM-005 (pulizia post-evento)
- Standard di riferimento: AATCC 96 (Four-Point System), ISO 4660 (classificazione difetti tessili)
