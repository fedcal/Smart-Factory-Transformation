---
id: SOP-DYE-003
title: Verifica tono e approvazione lotto tintoriale
version: "1.0"
lang: it
asset: jet dyeing machine
asset_family: dyeing
role: quality-manager
hazard_level: low
estimated_duration_min: 30
prerequisites:
  - SOP-DYE-001
related_glossary:
  - delta_e
  - spettrofotometro
  - deviazione_tono
  - solidita_colore
  - tintura
  - ispezione_rotolo
tags:
  - dyeing
  - shade-verification
  - quality
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Verifica tono e approvazione lotto tintoriale

## Scope

Questa SOP descrive la procedura di verifica del tono e di approvazione finale di un lotto tintoriale prima del rilascio al reparto successivo (finissaggio o magazzino). La verifica include la misurazione colorimetrica con **spettrofotometro**, il confronto con lo standard approvato e la verifica dell'uniformita' di tono tra i rotoli del lotto.

La procedura si applica a ogni lotto tintoriale completato, indipendentemente dall'articolo o dal colore. La decisione di approvazione spetta al responsabile qualita' o a un ispettore di qualita' autorizzato. Un lotto con **deviazione_tono** superiore alla tolleranza concordata non puo' essere rilasciato senza autorizzazione esplicita del responsabile qualita'.

## Prerequisites

- Il lotto tintoriale e' completato e i rotoli sono asciutti (flat dry o tumble dry secondo procedura).
- Il campione standard approvato (o la Recipe Sheet con i valori L*, a*, b* target) e' disponibile in laboratorio.
- Lo **spettrofotometro** e' calibrato (verifica giornaliera su piastra bianca e nera eseguita e documentata).
- I campioni di tessuto sono stati prelevati dall'inizio, meta' e fine di ogni rotolo del lotto (o secondo il piano di campionamento aziendale).

## Tools and PPE

- **Spettrofotometro** da banco (apertura d8, illuminante D65, osservatore 10°)
- Portacampioni standardizzato (per garantire planarizzazione e pressione costante del campione)
- Modulo di rapporto tono (cartaceo o digitale nel sistema qualita')
- Scala dei grigi ISO 105-A02 (per valutazione visiva supplementare)
- Luce D65 standard (lightbox da valutazione colore) per ispezione visiva

## Step-by-step Procedure

1. **Preparare i campioni di tessuto per la misurazione.** Per ogni rotolo del lotto, prelevare campioni di 10×10 cm dall'inizio, dalla meta' e dalla fine del rotolo (3 campioni per rotolo). Appiattire ogni campione senza stiratura (la pressione dello stiro altera le proprieta' cromatiche superficiali). Condizionare per almeno 30 minuti in ambiente con umidita' 65±5% RH e temperatura 20±2°C (condizioni standard ISO 139).

2. **Misurare il campione standard di riferimento.** Posizionare il campione standard sul portacampioni dello **spettrofotometro** (doppio strato per opacizzazione). Eseguire 3 misurazioni ruotando il campione di 90° tra una misurazione e l'altra. Registrare i valori L*, a*, b* medi e verificare la ripetibilita' (deviazione tra misure <0.1 unita').

3. **Misurare i campioni del lotto.** Per ogni campione di produzione: posizionare sul portacampioni e misurare con lo stesso metodo (3 misurazioni a 90°). Calcolare il **delta_e** CMC o CIEDE2000 rispetto allo standard per ciascun campione.

4. **Valutare la distribuzione del delta_e all'interno del lotto.** Costruire la matrice di risultati: rotolo × posizione (inizio, meta', fine) × **delta_e**. Valutare:
   - **delta_e** massimo nel lotto: deve essere <1.0 (tolleranza tipica produzione), o <0.8 per articoli premium.
   - Differenza di **delta_e** tra inizio e fine dello stesso rotolo (uniformita' intra-rotolo): deve essere <0.5 per evitare **deviazione_tono** visibile all'interno del rotolo.
   - Differenza di **delta_e** tra rotoli del lotto (uniformita' inter-rotolo): variazione >0.8 tra rotoli diversi dello stesso lotto e' accettabile solo se i rotoli vengono destinati a partite separate.

5. **Eseguire la valutazione visiva su lightbox D65.** Posizionare il campione con il **delta_e** piu' alto e il campione standard sulla lightbox D65. Valutare visivamente in condizioni D65 e luce incandescente (metameria check): se la differenza e' visibile in entrambe le condizioni di luce, il lotto non puo' essere approvato come unica partita.

6. **Prendere la decisione di approvazione.** Applicare la griglia di decisione aziendale:
   - **delta_e** CMC <1.0, nessuna **deviazione_tono** visiva, uniformita' intra-rotolo OK → CONFORME: lotto approvato per rilascio.
   - **delta_e** CMC 1.0-2.0, **deviazione_tono** non visiva su D65 standard → CONFORMITA' CONDIZIONALE: richiedere autorizzazione scritta del cliente per eventuale rilascio con deroga.
   - **delta_e** CMC >2.0 o **deviazione_tono** visiva → NON CONFORME: bloccare il lotto, avviare analisi causa (SOP-DYE-002) e decidere azione correttiva (rettifica / ricoloritura / declassamento).

7. **Compilare il rapporto di approvazione tono.** Inserire nel sistema qualita': numero lotto, articolo, data, valori delta_e per ogni campione, decisione (CONFORME / CONDIZIONALE / NON CONFORME), firma del responsabile qualita'. Per lotti NON CONFORMI: aprire una non-conformita' nel sistema e indicare l'azione correttiva pianificata.

8. **Rilasciare o bloccare il lotto.** Per lotti conformi: emettere il bollettino di rilascio e aggiornare lo stato del lotto nel sistema gestionale (stato: CONFORME). Per lotti non conformi: apporre etichetta rossa di blocco su tutti i rotoli del lotto e segregare fisicamente nell'area di quarantena.

## Verification

- Tutti i campioni del lotto hanno **delta_e** CMC entro la tolleranza concordata (<1.0 per produzione standard).
- Il rapporto di approvazione tono e' compilato, firmato e archiviato nel sistema qualita'.
- I lotti non conformi sono fisicamente segregati e identificati con etichetta rossa.
- Lo stato del lotto e' aggiornato nel sistema gestionale (CONFORME / QUARANTENA / NON CONFORME).

## Troubleshooting

**La misurazione spettrofotometrica mostra valori non riproducibili (variazione >0.3 tra ripetizioni):**
- Verificare la planarizzazione del campione sul portacampioni: pieghe o spessori non uniformi causano variabilita' di misura. Tagliare un campione fresco dallo stesso punto e ripetere.
- Controllare la calibrazione dello **spettrofotometro**: se la deviazione persiste su campioni multipli, ri-eseguire la calibrazione.

**Il delta_e e' border-line (0.8-1.2) e la decisione e' incerta:**
- Richiedere un secondo confronto visivo da un secondo ispettore qualificato: in caso di discordanza >0.2 punti nel giudizio visivo, applicare la classificazione piu' conservativa.
- Valutare il contesto d'uso dell'articolo: un **delta_e** 1.1 per tessuto da tappezzeria e' meno critico dello stesso valore per articolo da abbigliamento in tinta unita.

**Lotto con delta_e conforme ma con deviazione visiva tra rotoli (metameria):**
- Questo indica che i rotoli hanno stesso **delta_e** rispetto allo standard ma diversa curva di riflettanza: problema di metameria da batch colorante diverso. Separare i rotoli per partita cromatica distinta e documentare nel rapporto.

## References

- Glossario IT tessile: [delta_e](../../docs/docs/glossary.md#delta_e), [deviazione_tono](../../docs/docs/glossary.md#deviazione_tono), [spettrofotometro](../../docs/docs/glossary.md#spettrofotometro)
- SOP correlate: SOP-DYE-001 (preparazione bagno colorante), SOP-DYE-002 (abbinamento colore), SOP-QLT-004 (report deviazione tonale)
- Standard di riferimento: ISO 105-A02 (scala grigi), CIE L*a*b* D65, ISO 139 (condizionamento tessile)
