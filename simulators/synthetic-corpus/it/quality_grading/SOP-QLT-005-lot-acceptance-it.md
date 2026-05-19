---
acl_level: public
asset: inspection table
asset_family: quality_grading
audience: operations
created_in_phase: 2
estimated_duration_min: 60
hazard_level: low
id: SOP-QLT-005
lang: it
prerequisites:
- SOP-QLT-001
- SOP-QLT-004
related_glossary:
- accettazione_lotto
- aql
- livello_qualita_accettabile
- ispezione_4_punti
- lotto_tintoriale
role: quality-manager
status: reviewed
tags:
- quality
- acceptance
- inspection
title: Procedura di accettazione lotto
version: '1.0'
---

# Procedura di accettazione lotto

## Scope

Questa SOP descrive la procedura di **accettazione_lotto** per un lotto di tessuto finito o semilavorato destinato alla consegna interna (reparto successivo) o alla spedizione al cliente. La procedura integra i risultati dell'**ispezione_4_punti** (SOP-QLT-001) e del rapporto di **deviazione_tono** (SOP-QLT-004) in una decisione formale di accettazione o rifiuto del lotto secondo il **livello_qualita_accettabile** (AQL) concordato.

La procedura si applica a tutti i lotti tintoriali che hanno superato la fase di ispezione tessuto e verifica tonale e per i quali e' richiesta una decisione formale di accettazione prima del rilascio. Il risultato e' un documento di accettazione lotto (Lot Acceptance Record, LAR) firmato dal responsabile qualita', che costituisce il documento di rilascio officiale del lotto.

Il livello **aql** di riferimento e' definito per ogni articolo/cliente nelle specifiche di fornitura. In assenza di specifiche cliente, si applica l'**aql** standard aziendale (2.5% per difetti maggiori, 4.0% per difetti minori). La decisione finale segue le tavole di campionamento AQL (ISO 2859-1 o MIL-STD-105E).

## Prerequisites

- L'ispezione tessuto (SOP-QLT-001) e' completata per tutti i rotoli del lotto con rapporti firmati.
- Il rapporto di **deviazione_tono** (SOP-QLT-004) e' disponibile se il lotto ha avuto non conformita' cromatiche.
- I dati di **ispezione_4_punti** (punteggio per rotolo, classificazione, numero difetti per tipo) sono consolidati in un foglio di riepilogo lotto.
- La specifica **aql** applicabile all'articolo e al cliente e' disponibile (da sistema gestionale o da anagrafica articolo).
- Il responsabile qualita' e' disponibile per la revisione e firma del LAR.

## Tools and PPE

- Foglio di riepilogo lotto (aggregazione dati da SOP-QLT-001 per tutti i rotoli)
- Tavole di campionamento AQL (ISO 2859-1 / MIL-STD-105E) o software equivalente
- Rapporti di ispezione singoli rotoli (SOP-QLT-001)
- Rapporto **deviazione_tono** (SOP-QLT-004) se disponibile
- Modulo LAR (Lot Acceptance Record) aziendale
- Calcolatrice o foglio di calcolo per calcolo **aql**
- Guanti in cotone sottile (per eventuale re-ispezione campioni fisici)

## Step-by-step Procedure

1. **Consolidare i dati di ispezione del lotto.** Raccogliere i rapporti di **ispezione_4_punti** (SOP-QLT-001) per tutti i rotoli del lotto. Compilare il foglio di riepilogo lotto con: numero rotolo, lunghezza ispezionata (m), punteggio totale difetti, punteggio per 100 m, classificazione rotolo (Prima / Seconda / Rifilo), numero difetti per tipologia (mispick, rottura filo riparata, difetto catena, difetto trama, macchie, buchi, altro). Verificare che tutti i rotoli del lotto abbiano un rapporto di ispezione firmato.

2. **Calcolare il punteggio aggregato del lotto.** Dal foglio di riepilogo, calcolare:
   - Punteggio medio lotto = (somma punteggi per 100 m di tutti i rotoli) / numero rotoli
   - Percentuale rotoli Prima qualita' = (rotoli Prima / totale rotoli) x 100
   - Percentuale rotoli Seconda qualita' = (rotoli Seconda / totale rotoli) x 100
   - Percentuale rotoli Rifilo = (rotoli Rifilo / totale rotoli) x 100

   | Classificazione rotoli | Soglia tipica per accettazione lotto |
   |------------------------|--------------------------------------|
   | Prima qualita'         | ≥ 80% dei rotoli                     |
   | Seconda qualita'       | ≤ 20% dei rotoli                     |
   | Rifilo                 | 0% (nessun rotolo rifilo ammesso)    |

3. **Determinare il livello di campionamento AQL.** In base alla dimensione del lotto (numero totale di rotoli), identificare il livello di campionamento AQL applicabile secondo le tavole ISO 2859-1 (livello di ispezione II standard). Determinare il numero di campioni da ispezionare (n) e i numeri di accettazione (Ac) e rifiuto (Re) per i livelli **aql** applicabili (2.5% per difetti maggiori, 4.0% per difetti minori).

   Esempio per lotto da 20-50 rotoli (lettera campionamento G):
   - n = 32 rotoli da ispezionare (o intera popolazione se lotto < 32)
   - Ac = 2 (accettazione se difetti trovati ≤ 2), Re = 3 (rifiuto se difetti trovati ≥ 3) per **aql** 2.5

4. **Eseguire l'ispezione di campionamento AQL (se non gia' coperta dalla SOP-QLT-001).** Se il numero di rotoli ispezionati in SOP-QLT-001 e' inferiore al campione richiesto dalle tavole AQL: selezionare casualmente i rotoli aggiuntivi da ispezionare e completare l'**ispezione_4_punti**. Per ogni rotolo campionato AQL, classificare i difetti trovati come:
   - **Difetto maggiore:** difetto che compromette la funzionalita' o l'aspetto del tessuto (buchi, strappi, macchie permanenti, difetti di trama > 150 mm)
   - **Difetto minore:** difetto che non compromette la funzionalita' ma riduce la qualita' percepita (macchie lavabili, piccoli difetti visibili < 75 mm, rincorsi accettabili)

5. **Integrare la verifica tonale nel giudizio di lotto.** Consultare il rapporto **deviazione_tono** (SOP-QLT-004) se disponibile. Classificare la situazione tonale del lotto:
   - **Conforme tonale:** tutti i rotoli entro il **livello_qualita_accettabile** cromatico (delta_E CMC ≤ 1.0 su tutti i campioni)
   - **Conforme condizionale:** delta_E tra 1.0 e 1.5 con deroga cliente accettata e documentata
   - **Non conforme tonale:** delta_E > 1.5 senza deroga cliente, o **screziatura** strutturale non accettata

   Un lotto "Non conforme tonale" non puo' essere accettato indipendentemente dal risultato dell'**ispezione_4_punti**.

6. **Applicare le regole di decisione AQL.** Confrontare il numero di difetti maggiori e minori trovati nel campione AQL con i numeri di accettazione e rifiuto delle tavole:
   - Difetti maggiori trovati ≤ Ac (AQL 2.5%) E difetti minori trovati ≤ Ac (AQL 4.0%): **LOTTO ACCETTATO**
   - Difetti maggiori trovati ≥ Re (AQL 2.5%) OPPURE difetti minori trovati ≥ Re (AQL 4.0%): **LOTTO RIFIUTATO**
   - Risultato al limite (Ac < trovati < Re): procedere con campionamento ridotto aggiuntivo o escalation al responsabile qualita' senior

7. **Redigere il Lot Acceptance Record (LAR).** Compilare il modulo LAR con: numero lotto, articolo, cliente (se noto), data di completamento ispezione, numero totale rotoli nel lotto, dimensione campione AQL ispezionato, numero difetti maggiori e minori trovati, risultato AQL (ACCETTATO / RIFIUTATO), situazione tonale (CONFORME / CONDIZIONALE / NON CONFORME), classificazione aggregata lotto (% Prima, % Seconda, % Rifilo), decisione finale (ACCETTATO / RIFIUTATO / QUARANTENA), firma e data del responsabile qualita'.

8. **Eseguire le azioni post-decisione.** In base alla decisione finale:
   - **ACCETTATO:** apporre etichette verdi di accettazione su tutti i rotoli del lotto, aggiornare lo stato lotto nel sistema gestionale (RILASCIATO), avviare il processo di spedizione o trasferimento interno
   - **RIFIUTATO:** segregare fisicamente il lotto nell'area di quarantena, apporre etichette rosse di blocco su tutti i rotoli, aprire una Non Conformita' nel sistema qualita' con riferimento al LAR, avviare la procedura di azione correttiva (rettifica, ricoloritura, scarto, declassamento)
   - **QUARANTENA (limite AQL):** segregare il lotto, sospendere la decisione, avviare campionamento aggiuntivo o revisione del responsabile qualita' senior entro 24 ore

## Verification

- Il LAR e' compilato in tutte le sezioni e firmato dal responsabile qualita'.
- Lo stato del lotto nel sistema gestionale e' aggiornato coerentemente con la decisione LAR (RILASCIATO / BLOCCO / QUARANTENA).
- I rotoli accettati sono fisicamente identificati con etichette verdi e i rifiutati con etichette rosse.
- Se il lotto e' stato rifiutato, la Non Conformita' e' aperta nel sistema qualita' con numero LAR di riferimento.
- Il LAR e' archiviato nel fascicolo di qualita' del lotto e accessibile per audit.

## Troubleshooting

**Il numero di rotoli ispezionati in SOP-QLT-001 e' inferiore al campione AQL richiesto (es. lotto da 100 rotoli con campione AQL richiesto di 50 ma solo 20 ispezionati):**
- Riprendere l'ispezione dei rotoli mancanti prima di procedere alla decisione LAR. Non e' possibile accettare un lotto senza aver raggiunto la dimensione minima del campione AQL. Se il tempo e' critico: contattare il responsabile qualita' senior per valutare se e' applicabile un piano di campionamento ridotto (ispezione di livello I invece di livello II) con documentazione della giustificazione.

**Il risultato AQL e' al limite (tra Ac e Re) e non e' possibile determinare chiaramente l'accettazione o il rifiuto:**
- Procedere con campionamento aggiuntivo (switching rules ISO 2859-1: passare al campionamento rafforzato se il lotto precedente era gia' borderline). Se il risultato del campionamento rafforzato e' ancora al limite: escalation obbligatoria al responsabile qualita' senior. Documentare il percorso decisionale nel LAR.

**Discordanza tra il giudizio qualitativo del cliente e il risultato AQL (il cliente rifiuta un lotto che ha passato l'AQL):**
- Documentare la contestazione del cliente nel LAR. Avviare una re-ispezione congiunta con il cliente su un campione concordato di rotoli. Se la re-ispezione conferma il risultato AQL: negoziare con il cliente l'eventuale applicazione di un **aql** piu' restrittivo nei contratti futuri. Se la re-ispezione rileva difetti non trovati nella prima ispezione: aprire una Non Conformita' interna per il processo di ispezione e rivalutare la formazione degli ispettori.

**Il lotto ha piu' del 20% di rotoli Seconda qualita' ma tutti i difetti sono minori:**
- La soglia del 20% per la Seconda qualita' e' un indicatore di qualita' del processo, non un criterio automatico di rifiuto AQL (il rifiuto AQL e' basato sul conteggio difetti del campione). Accettare il lotto se il risultato AQL e' ACCETTATO, ma documentare nel LAR la percentuale elevata di Seconda qualita' come segnale di processo da monitorare. Comunicare al reparto produzione per analisi delle cause.

## References

- Glossario IT tessile: [accettazione_lotto](../../docs/docs/glossary.md#accettazione_lotto), [aql](../../docs/docs/glossary.md#aql), [livello_qualita_accettabile](../../docs/docs/glossary.md#livello_qualita_accettabile), [ispezione_4_punti](../../docs/docs/glossary.md#ispezione_4_punti), [lotto_tintoriale](../../docs/docs/glossary.md#lotto_tintoriale)
- SOP correlate: SOP-QLT-001 (ispezione tessuto 4 punti), SOP-QLT-004 (rapporto deviazione tonale), SOP-DYE-003 (verifica tono lotto)
- Standard di riferimento: ISO 2859-1 (Attribute sampling plans), MIL-STD-105E (Sampling procedures and tables), AATCC 96 (Four-Point System), ISO 4660 (classificazione difetti tessili)
