---
acl_level: public
asset: jet dyeing machine
asset_family: dyeing
audience: operations
created_in_phase: 2
estimated_duration_min: 40
hazard_level: medium
id: SOP-DYE-005
lang: it
prerequisites:
- SOP-DYE-001
related_glossary:
- tintura
- bagno_colorante
- jet_dyeing
- solidita_colore
- screziatura
role: technician
status: reviewed
tags:
- dyeing
- wash
- post-process
- technician
title: Procedura di lavaggio post-tintura e scarico bagno esausto
version: '1.0'
---

# Procedura di lavaggio post-tintura e scarico bagno esausto

## Scope

Questa SOP descrive la procedura di lavaggio post-tintura (saponaggio, risciacquo e trattamento finale) da eseguire nella macchina **jet_dyeing** al termine del ciclo tintoriale, prima dello scarico del **bagno_colorante** esausto e dello scarico del tessuto. Un lavaggio post-tintura efficace rimuove il colorante non fissato, gli ausiliari chimici residui e i prodotti di idrolisi, garantendo la **solidita_colore** richiesta e prevenendo la **screziatura** da migrazione colorante in fase di asciugatura.

La procedura si applica alla tintura su tessuti cellulosici (cotone, lino, viscosa) con coloranti reattivi, e su tessuti sintetici con coloranti disperse. Non si applica alla tintura in navetta o a processi di tintura in continuo (pad-batch): quelli seguono procedure specifiche.

Attenzione: i prodotti chimici del **bagno_colorante** esausto (coloranti, ausiliari, sali) richiedono gestione conformemente alla normativa ambientale locale prima dello scarico in fognatura industriale.

## Prerequisites

- Il ciclo tintoriale principale e' completato (temperatura di processo raggiunta e mantenuta per il tempo previsto dalla Recipe Sheet).
- Il campione di controllo a meta' ciclo (se previsto) ha dato esito conforme.
- Il sistema di trattamento acque reflue del sito e' operativo e disponibile a ricevere il **bagno_colorante** esausto.
- Il tecnico ha accesso alle schede SDS dei prodotti chimici usati e conosce le procedure di emergenza per sversamenti.

## Tools and PPE

- pHmetro digitale calibrato (per verifica pH scarico)
- Termometro digitale (per verifica temperatura bagni di risciacquo)
- Contenitore di raccolta campione bagno (250 mL, per analisi pre-scarico se richiesta)
- Guanti resistenti ai prodotti chimici categoria III (nitrile)
- Grembiule impermeabile
- Occhiali protettivi anti-schizzo
- Maschera semi-facciale FFP2 (per vapori chimici durante operazioni ad alta temperatura)

## Step-by-step Procedure

1. **Eseguire il primo risciacquo a caldo.** Al termine del ciclo tintoriale, scaricare il **bagno_colorante** principale (se la Recipe Sheet prevede scarico prima del saponaggio). Riempire la macchina **jet_dyeing** con acqua calda a 80°C (rapporto bagno identico al ciclo principale). Far circolare il tessuto per 10 minuti. Scaricare. Questo risciacquo rimuove la maggior parte del colorante non fissato e dei sali.

2. **Eseguire il saponaggio.** Riempire con acqua a 90-95°C (per coloranti reattivi) o a 70°C (per disperse). Aggiungere il detergente di saponaggio (tipicamente 1-2 g/L di detergente non ionico, come indicato dalla Recipe Sheet). Far circolare per 20 minuti a temperatura. Il saponaggio e' critico per la **solidita_colore**: rimuove il colorante non fissato che causerebbe cessione in uso.

3. **Eseguire il secondo risciacquo a caldo.** Scaricare il bagno di saponaggio. Riempire con acqua calda a 70-80°C. Far circolare 10 minuti. Scaricare. Questo risciacquo elimina il detersivo residuo che potrebbe interferire con i successivi trattamenti.

4. **Eseguire il risciacquo a freddo finale.** Riempire con acqua a temperatura ambiente (20-30°C). Far circolare 10 minuti. Misurare il pH del bagno di risciacquo con il pHmetro: deve essere compreso tra 6 e 8 (indicativo di neutralizzazione completa degli ausiliari alcalini o acidi). Se il pH e' fuori range: eseguire un secondo risciacquo a freddo.

5. **Aggiungere il trattamento finale (se previsto dalla Recipe Sheet).** Per alcuni articoli e' previsto un trattamento finale nel bagno di risciacquo: fissativo cationico (per migliorare la solidita' al lavaggio dei reattivi), ammorbidente (per modificare l'handle del tessuto), o acidificazione finale (per portare il substrato a pH acido di conservazione). Aggiungere secondo le dosi della Recipe Sheet, far circolare 15 minuti, poi scaricare.

6. **Verificare il pH del bagno esausto finale prima dello scarico.** Con il pHmetro, misurare il pH del bagno che sta per essere scaricato in fognatura. Il range tipico accettabile per scarico in fognatura industriale e' pH 6-9 (verificare il limite specifico del sito con il responsabile ambientale). Se fuori range: aggiungere acido (pH troppo alto) o alcali (pH troppo basso) e ricontrollare.

7. **Procedere allo scarico del tessuto.** Aprire la porta della macchina **jet_dyeing** e scaricare il tessuto nel carro raccolta. Verificare che il tessuto sia distribuito uniformemente nel carro (non intrecciato) per evitare **screziatura** da pressione durante l'asciugatura. Registrare sul modulo di produzione: macchina, numero lotto, ricetta, ora fine ciclo, pH scarico, operatore.

8. **Eseguire la pulizia della macchina jet dyeing.** Al termine dello scarico del tessuto: sciacquare la macchina vuota con acqua fredda per rimuovere residui di colorante dalla vasca, dalle pareti interne e dagli ugelli. Ispezionare gli ugelli per occlusioni (residui di colorante o calcio): in caso di occlusione, procedere alla pulizia secondo la procedura di manutenzione specifica.

## Verification

- Il pH del risciacquo finale (campione prelevato prima dello scarico) e' compreso tra 6 e 8.
- Il tessuto non mostra **screziatura** visiva alla scarica (ispezione visiva nel carro raccolta).
- Il rapporto di **solidita_colore** eseguito su campione del lotto (SOP-DYE-004) conferma la solidita' conforme.
- Il modulo di produzione e' compilato con pH di scarico, orario e firma operatore.
- La macchina e' pulita e pronta per il ciclo successivo.

## Troubleshooting

**Il pH del risciacquo finale non scende sotto 9 dopo il risciacquo a freddo:**
- Aggiungere acido acetico (1-2 mL/L di soluzione 80%) al bagno di risciacquo finale e mescolare per 5 minuti. Rimisurare il pH. Non aggiungere acido forte (cloridrico, solforico) direttamente: rischio di danneggiamento del substrato.
- Se il problema persiste: verificare che il saponaggio precedente non contenesse un eccesso di alcali; aumentare la dose di risciacquo a caldo intermedio.

**Il tessuto mostra screziatura visiva alla scarica (aree scure e chiare):**
- La **screziatura** da pressione si forma se il tessuto si accavalla nel carro raccolta in condizioni di temperatura elevata (>60°C). In futuro: aspirare il carro a una temperatura inferiore o distribuire il tessuto con cura. Per il lotto in corso: stendere il tessuto su un rack e asciugare in posizione distesa per 30 minuti prima del completamento dell'asciugatura.

**L'ugello del jet dyeing e' parzialmente occluso (pressione circolazione ridotta):**
- Segnalare immediatamente al tecnico manutentore per pulizia ugelli prima del ciclo successivo. Un ugello occluso causa distribuzione non uniforme del bagno e **screziatura** strutturale nel prossimo lotto.

## References

- Glossario IT tessile: [tintura](../../docs/docs/glossary.md#tintura), [bagno_colorante](../../docs/docs/glossary.md#bagno_colorante), [solidita_colore](../../docs/docs/glossary.md#solidita_colore)
- SOP correlate: SOP-DYE-001 (preparazione bagno colorante), SOP-DYE-003 (verifica tono lotto), SOP-DYE-004 (test solidita' colore)
- Standard di riferimento: ISO 105-C06 (solidita' al lavaggio), ISO 5667 (campionamento acque reflue), schede SDS prodotti chimici usati
