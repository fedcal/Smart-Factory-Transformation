---
id: SOP-QLT-004
title: Redazione rapporto deviazione tonale su lotto tintoriale
version: "1.0"
lang: it
asset: inspection table
asset_family: quality_grading
role: quality-manager
hazard_level: low
estimated_duration_min: 30
prerequisites:
  - SOP-QLT-001
  - SOP-DYE-003
related_glossary:
  - deviazione_tono
  - delta_e
  - spettrofotometro
  - solidita_colore
  - ispezione_rotolo
  - controllo_qualita_tessile
tags:
  - quality
  - inspection
  - shade-deviation
  - reporting
  - quality-manager
audience: quality
status: reviewed
created_in_phase: 2
---

# Redazione rapporto deviazione tonale su lotto tintoriale

## Scope

Questa SOP descrive la procedura di redazione del rapporto formale di **deviazione_tono** (shade deviation report) per un lotto tintoriale che ha superato la soglia di **delta_e** accettata o che mostra variazioni cromatiche inter-rotolo o intra-rotolo al di sopra della tolleranza concordata.

Il rapporto di **deviazione_tono** e' il documento formale che:
- Traccia la natura e la dimensione del problema cromatico
- Fornisce al reparto tintoria le informazioni di diagnosi
- Costituisce la base per la decisione di azione correttiva (rettifica, ricoloritura, deroga, declassamento)
- Serve come evidenza documentale per contestazioni cliente

La procedura si applica a lotti con **delta_e** CMC >1.0 o con difetti di **screziatura** visibili classificati come non conformi nel processo di verifica tonale (SOP-DYE-003).

## Prerequisites

- Il lotto ha gia' superato la verifica tono (SOP-DYE-003) con esito NON CONFORME o CONDIZIONALE.
- I dati di misurazione colorimetrica (valori L*, a*, b* per campione) sono disponibili dal rapporto SOP-DYE-003.
- Il campione standard di riferimento e' disponibile in laboratorio.
- Lo **spettrofotometro** e' calibrato.
- Il modulo di rapporto **deviazione_tono** (aziendale o standardizzato) e' disponibile.

## Tools and PPE

- **Spettrofotometro** da banco (calibrato, apertura d8, D65)
- Campione standard di riferimento (approvato dal cliente o dalla direzione qualita')
- Campioni del lotto non conforme (uno per rotolo, prelevati in posizione standard)
- Lightbox D65 per valutazione visiva
- Scala dei grigi ISO 105-A02
- Guanti in cotone sottile

## Step-by-step Procedure

1. **Raccogliere tutti i dati di misurazione disponibili.** Recuperare dal rapporto SOP-DYE-003 i valori L*, a*, b* e **delta_e** CMC per ogni campione del lotto. Se i dati sono incompleti (non tutti i rotoli sono stati campionati): eseguire le misurazioni aggiuntive prima di procedere alla redazione del rapporto.

2. **Costruire la matrice di deviazione del lotto.** Organizzare i dati in una matrice: rotolo × posizione (inizio, meta', fine) × **delta_e** CMC. Calcolare:
   - **delta_e** medio del lotto
   - **delta_e** massimo del lotto (rotolo e posizione)
   - Range di variazione inter-rotolo (delta_e_max - delta_e_min)
   - Rotoli e posizioni che superano la soglia di accettazione

3. **Caratterizzare la direzione della deviazione.** Analizzare i valori L*, a*, b* per determinare la direzione della **deviazione_tono**:
   - L* ridotto (campione piu' scuro dello standard): eccesso di colorante o fissazione troppo alta
   - a* in eccesso (piu' rosso): sbilanciamento della triplice colorante verso il componente rosso
   - b* in eccesso (piu' giallo): profilo termico di processo non ottimale per il colorante usato
   La direzione della deviazione e' essenziale per orientare l'azione correttiva del reparto tintoria.

4. **Classificare il tipo di non conformita'.** In base alla matrice:
   - **Deviazione uniforme:** tutti i rotoli hanno lo stesso **delta_e** nella stessa direzione — indica un errore sistematico nella ricetta o nel processo (dosaggio colorante, pH, profilo termico)
   - **Deviazione inter-rotolo:** i rotoli hanno **delta_e** diversi tra loro — indica variabilita' nel processo macchina (temperatura non uniforme tra cicli, variazione del rapporto **bagno_colorante**)
   - **Deviazione intra-rotolo:** inizio e fine dello stesso rotolo hanno **delta_e** diverso — indica deriva durante il ciclo (variazione di pH o temperatura nel corso del ciclo)

5. **Documentare la valutazione visiva su lightbox.** Posizionare il campione piu' critico del lotto e il campione standard sulla lightbox D65. Valutare visivamente e annotare nel rapporto: se la **deviazione_tono** e' visibile, da quale distanza (cm), e se e' uniforme o a chiazze (**screziatura** puntiforme vs. **deviazione_tono** omogenea).

6. **Definire l'azione correttiva raccomandata.** In base al tipo di non conformita' e alla dimensione del **delta_e**, indicare nel rapporto l'azione raccomandata:
   - **delta_e** 1.0-1.5, deviazione uniforme: rettifica tintoriale in macchina (bagno correttivo con colorante nella direzione opposta alla deviazione)
   - **delta_e** 1.5-2.5, deviazione inter-rotolo: ricoloritura separata per rotolo o per gruppo omogeneo
   - **delta_e** >2.5 o **screziatura** strutturale: ricoloritura completa o declassamento; valutare economicamente con il responsabile commerciale
   - Deviazione entro 1.0-1.2 e non visiva: proposta di deroga al cliente con documentazione colorimetrica allegata

7. **Compilare il rapporto formale di deviazione tonale.** Strutturare il rapporto secondo il format aziendale includendo: numero lotto, articolo, data di tintura, cliente (se noto), valori colorimetrici tabellati, matrice di deviazione, tipo di NC classificato, valutazione visiva, azione correttiva raccomandata, firma del responsabile qualita'.

8. **Distribuire il rapporto e avviare il processo di azione correttiva.** Inviare il rapporto al responsabile tintoria (per azione correttiva tecnica) e al responsabile commerciale (se il lotto e' destinato a un cliente con standard definiti contrattualmente). Aggiornare lo stato del lotto nel sistema gestionale: QUARANTENA + azione correttiva in corso.

## Verification

- Il rapporto di **deviazione_tono** e' compilato con tutte le sezioni richieste (matrice, tipo NC, azione raccomandata).
- L'azione correttiva raccomandata e' coerente con il tipo di non conformita' diagnosticato.
- Il rapporto e' stato distribuito a tutti i destinatari previsti e la ricezione e' confermata.
- Lo stato del lotto nel sistema gestionale e' aggiornato con il numero del rapporto NC.

## Troubleshooting

**I valori L*, a*, b* misurati sono incoerenti tra campioni dello stesso rotolo (variazione >0.5 unita'):**
- Verificare le condizioni di misura: stesso operatore, stesso **spettrofotometro**, stessa apertura d8. Se la variabilita' persiste: il tessuto ha una **screziatura** strutturale (non e' una questione di misurazione). Documentare la **screziatura** come difetto aggiuntivo rispetto alla **deviazione_tono** uniforme.

**Non e' possibile determinare la direzione della deviazione (deviazione "grigia" — solo L* fuori range, a* e b* nella norma):**
- Una deviazione puramente in L* (solo intensita', nessuna deriva tono) indica un problema di concentrazione totale colorante (troppo o troppo poco). L'azione correttiva e' piu' semplice: solo correzione della concentrazione nella stessa triplice colorante.

**Il cliente non accetta la proposta di deroga e richiede la ricoloritura:**
- Documentare la risposta del cliente nel rapporto NC. Avviare la procedura di ricoloritura. Verificare che la macchina di ricoloritura sia lavata internamente prima di inserire il tessuto (rischio di contaminazione da colorante precedente).

## References

- Glossario IT tessile: [deviazione_tono](../../docs/docs/glossary.md#deviazione_tono), [delta_e](../../docs/docs/glossary.md#delta_e), [screziatura](../../docs/docs/glossary.md#screziatura)
- SOP correlate: SOP-DYE-003 (verifica tono lotto), SOP-DYE-002 (abbinamento colore), SOP-QLT-001 (ispezione tessuto)
- Standard di riferimento: CIE L*a*b* D65, ISO 105-A02 (scala dei grigi), ISO 105-A03 (scala degli staining)
