---
acl_level: public
asset: jet dyeing machine
asset_family: dyeing
audience: operations
created_in_phase: 2
estimated_duration_min: 60
hazard_level: low
id: SOP-DYE-002
lang: it
prerequisites:
- SOP-DYE-001
related_glossary:
- tintura
- delta_e
- spettrofotometro
- bagno_colorante
- deviazione_tono
- solidita_colore
role: technician
status: reviewed
tags:
- dyeing
- color-matching
- procedure
- technician
title: Procedura di abbinamento colore per tintura campionario
version: '1.0'
---

# Procedura di abbinamento colore per tintura campionario

## Scope

Questa SOP descrive la procedura di abbinamento cromatico (**color matching**) per la produzione di campioni tintoriali in fase di sviluppo colore o per la rettifica di partite fuori tolleranza. L'obiettivo è raggiungere un valore di **delta_e** CMC inferiore alla soglia concordata rispetto allo standard di riferimento (tipicamente <1.0 per campionario, <0.5 per campione approvazione cliente).

La procedura si applica alla tintura in scala laboratorio (campioni da 50-200 g di tessuto) o in macchina campionaria (**jet_dyeing** di piccola capacità), con cicli iterativi di misurazione e correzione colorimetrica. Non sostituisce la ricetta industriale definitiva (Recipe Sheet): l'output di questa procedura è la ricetta campionaria da validare in produzione.

## Prerequisites

- Il campione standard di colore è disponibile (scheda colore cliente o campione fisico approvato).
- Il laboratorio tintoria ha emesso una ricetta di partenza basata su previsione computazionale (color matching software) o su ricetta storica per colori simili.
- Lo **spettrofotometro** è calibrato (verifica su piastra bianca standard eseguita in giornata).
- Il substrato da tingere (tipo fibra, titolo, struttura tessile) è identico al substrato del campione standard.

## Tools and PPE

- **Spettrofotometro** da banco (apertura d8 o d/8, illuminante D65, osservatore 10°)
- Macchina campionaria o becker da laboratorio (capacità 50-500 mL per campioni)
- Bilancia analitica (risoluzione 0.001 g per coloranti; 0.01 g per ausiliari)
- pHmetro digitale calibrato
- Bagni di dissoluzione colorante (becher graduati da 100 mL)
- Software di color matching (o tabelle di correzione colorante empiriche)
- Occhiali protettivi anti-schizzo
- Guanti resistenti ai prodotti chimici categoria III

## Step-by-step Procedure

1. **Tingere il primo campione con la ricetta di partenza.** Preparare il **bagno_colorante** seguendo la ricetta di partenza emessa dal laboratorio (concentrazione colorante, ausiliari, pH, ciclo termico). Tingere il campione di substrato (50-100 g) in macchina campionaria. Asciugare il campione secondo il metodo standard (flat dry 60°C, 15 minuti).

2. **Misurare il delta_e del primo campione.** Posizionare il campione tinto sullo **spettrofotometro** e misurare in tre punti (bordo, centro, bordo opposto). Registrare i valori L*, a*, b* e calcolare il **delta_e** CMC rispetto allo standard. Un **delta_e** CMC > 3.0 al primo tentativo indica che la ricetta di partenza necessita di una correzione significativa.

3. **Analizzare la direzione della deviazione.** Confrontare i valori L*, a*, b* del campione con lo standard:
   - L* più basso: campione più scuro → ridurre la concentrazione totale di colorante del 5-15%.
   - a* positivo (+ rosso) in eccesso: ridurre il componente rosso o aumentare il componente verde della ricetta.
   - b* positivo (+ giallo) in eccesso: ridurre il componente giallo o aggiustare il rapporto tra i coloranti della triplice.
   Utilizzare il software di color matching per calcolare la correzione o applicare la tabella di correzione empirica del laboratorio.

4. **Preparare e tingere il campione corretto.** Applicare la correzione calcolata alla ricetta. Tingere un secondo campione sullo stesso substrato. Asciugare e misurare nuovamente. Se il **delta_e** CMC è <1.5: passare alla verifica di solidità. Se >1.5: ripetere la correzione dal punto 3 (massimo 3 iterazioni prima di consultare il responsabile tintoria).

5. **Verificare la solidita' colore del campione approvato.** Sul campione con **delta_e** CMC <1.0, eseguire il test di solidita' al lavaggio ISO 105-C06 (metodo C1S, 40°C, 30 minuti con agente detergente standard). Misurare il **delta_e** post-lavaggio: deve restare <1.0 per solidita' accettabile a livello campionario.

6. **Documentare la ricetta finale campionaria.** Compilare la scheda ricetta campionaria: substrato, data, coloranti (nome commerciale, concentrazione % s.p.s.), ausiliari, pH, ciclo termico, risultato delta_e pre/post lavaggio, firma tecnico. Questa scheda è la base per la successiva Recipe Sheet industriale.

7. **Sottoporre il campione all'approvazione.** Se il **delta_e** CMC <1.0 e la solidita' colore è conforme: registrare il campione come approvato nel sistema campionario e archiviare la ricetta. Se il cliente richiede un secondo campione (passo 2 approvazione): ripetere il ciclo di tintura con la ricetta definitiva e confrontare i due campioni (delta_e campione1/campione2 deve essere <0.5 per garantire riproducibilita').

8. **Trasferire la ricetta al reparto produzione.** Inviare la scheda ricetta campionaria al responsabile tintoria per la trasposizione in Recipe Sheet industriale (adattamento volumi, macchine e cicli termici a scala produzione).

## Verification

- Il campione finale ha **delta_e** CMC <1.0 rispetto allo standard (o <0.5 per approvazione cliente — verificare il requisito specifico dell'ordine).
- Il test di solidita' al lavaggio ISO 105-C06 dà risultato conforme (**deviazione_tono** post-lavaggio misurata con **spettrofotometro** entro tolleranza).
- La ricetta campionaria è compilata, firmata e archiviata nel sistema documentale del laboratorio.
- Nessuna **screziatura** o **deviazione_tono** visuale visibile sul campione in condizioni di luce D65 standard.

## Troubleshooting

**Il delta_e non scende sotto 1.5 dopo 3 iterazioni di correzione:**
- Verificare che il substrato utilizzato sia identico per tipo fibra, titolo e struttura al substrato dello standard: differenze di substrato rendono il color matching computazionale inaffidabile.
- Controllare che lo **spettrofotometro** sia calibrato correttamente: ri-eseguire la calibrazione su piastra bianca e nera prima delle misure critiche.
- Consultare il responsabile tintoria per una revisione della famiglia colorante: alcuni abbinamenti L*, a*, b* non sono raggiungibili con la triplice colorante standard del laboratorio.

**Il campione mostra solidita' colore insufficiente (delta_e post-lavaggio >1.5):**
- La causa piu' probabile e' un fissaggio incompleto del colorante: verificare il pH del bagno di fissazione e la temperatura di processo. Per coloranti reattivi, aumentare la dose di alcali di fissaggio del 10% e ripetere il ciclo.
- Se il problema persiste: considerare il cambio di famiglia colorante verso coloranti con migliore affinita' al substrato.

**La misurazione spettrofotometrica e' instabile (variazione >0.3 unita' tra le tre misure):**
- Il campione probabilmente non e' sufficientemente piano o presenta variazione di **deviazione_tono** superficiale. Fissarlo con nastro sul portacampioni dello **spettrofotometro** senza tensione. Se la variazione persiste: valutare la presenza di **screziatura** strutturale nel campione.

## References

- Glossario IT tessile: [delta_e](../../docs/docs/glossary.md#delta_e), [spettrofotometro](../../docs/docs/glossary.md#spettrofotometro), [tintura](../../docs/docs/glossary.md#tintura)
- SOP correlate: SOP-DYE-001 (preparazione bagno colorante), SOP-DYE-003 (verifica solidita' colore), SOP-QLT-004 (report deviazione tonale)
- Standard di riferimento: ISO 105-C06 (solidita' colore al lavaggio), ISO 105-A02 (scala dei grigi), CIE Lab D65
