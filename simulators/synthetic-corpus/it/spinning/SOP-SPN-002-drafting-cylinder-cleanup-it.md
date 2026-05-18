---
id: SOP-SPN-002
title: Pulizia cilindri di stiro del filatoio ad anello
version: "1.0"
lang: it
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: low
estimated_duration_min: 40
prerequisites:
  - SOP-SPN-001
related_glossary:
  - filatura
  - filatoio_anello
  - stiro
  - cilindro_stiro
  - irregolarita_filato
  - titolo_filato
tags:
  - maintenance
  - spinning
  - cleanup
  - cylinder
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Pulizia cilindri di stiro del filatoio ad anello

## Scope

Questa SOP descrive la procedura di pulizia periodica dei **cilindro_stiro** (drafting cylinders) del **filatoio_anello**. I cilindri di **stiro** sono i componenti che allungano progressivamente il nastro di fibra (sliver o roving) riducendo il **titolo_filato** fino al valore target; il loro stato superficiale ha un impatto diretto sull'**irregolarita_filato** e sulla frequenza di **rottura_filo**.

La pulizia e' raccomandata ogni 250-500 ore di produzione (a seconda della qualita' della fibra lavorata) o ogni volta che il tasso di **irregolarita_filato** (CVm%) supera la soglia di allerta del 10% rispetto al valore di riferimento dell'articolo. La procedura si applica sia ai cilindri rivestiti in gomma (apron) sia ai cilindri metallici di pressione.

## Prerequisites

- Il **filatoio_anello** e' in stato di fermo pianificato (cambio turno, cambio articolo).
- Il tecnico ha accesso al kit di pulizia specifico per la tipologia di rivestimento dei cilindri (specifiche del costruttore).
- I valori di durezza degli apron (in Shore A) del turno precedente sono noti (se disponibili dal registro manutenzione).
- DPI: guanti da lavoro (non antitaglio — necessita' di sensibilita' tattile), occhiali protettivi.

## Tools and PPE

- Pennello per pulizia cilindri (setole morbide specifiche per tessile)
- Soluzione detergente per cilindri (specifica per gomma e metallo, non corrosiva, senza silicone)
- Panno privo di pelucchi
- **Durometro** Shore A (per verifica durezza degli apron in gomma dopo pulizia)
- **Calibro_digitale** (per verifica diametro cilindri)
- Estrattore apron (per la rimozione in sicurezza degli apron dalla coppia di cilindri)
- Guanti da lavoro (non antitaglio)
- Occhiali protettivi

## Step-by-step Procedure

1. **Fermare la sezione di macchina assegnata.** Identificare la sezione di **filatoio_anello** da pulire. Fermare l'alimentazione del nastro e abbassare i cilindri di pressione (se il modello dispone di sollevamento pneumatico). Non separare fisicamente i cilindri senza aver fermato la macchina e l'alimentazione.

2. **Rimuovere il nastro residuo dai cilindri.** Tagliare il roving o il nastro alimentato ai cilindri di **stiro** con forbici (non tirare: rischio di sfilacciatura e contaminazione). Raccogliere i residui di fibra nella benna di scarto fibra.

3. **Pulire i cilindri metallici superiori.** Applicare la soluzione detergente su un panno privo di pelucchi e pulire la superficie dei cilindri metallici (tipicamente acciaio inox o cromo) con un movimento rotatorio. Particolare attenzione ai bordi laterali dove si accumulano fibre intrappolate. Asciugare con panno pulito asciutto.

4. **Rimuovere e pulire gli apron in gomma.** Con l'estrattore apron, rimuovere gli apron dalla coppia di cilindri inferiori (procedura standard: sollevare con l'estrattore senza forzare lateralmente). Pulire gli apron con la soluzione detergente specifica (non usare detergenti con solventi che degradano la gomma). Ispezionare la superficie: crepe, tagli o indurimento (Shore A > 65) indicano necessita' di sostituzione.

5. **Verificare la durezza degli apron con il durometro.** Misurare la durezza Shore A degli apron in 3 punti (bordo sinistro, centro, bordo destro). Range accettabile tipico: 45-65 Shore A (verificare con il dato del costruttore). Un apron con durezza fuori range causa stiro irregolare e aumento dell'**irregolarita_filato**.

6. **Pulire le asce inferiori (lower apron cradle).** Pulire le guide inferiori (cradle) sulle quali scorrono gli apron: depositi di fibra e cera sulle guide creano attrito non uniforme che si riflette sull'**irregolarita_filato**. Usare pennello e soluzione detergente.

7. **Rimontare gli apron e verificare il tensionamento.** Rimontare gli apron sulla coppia di cilindri. Verificare che l'apron sia centrato e che il tensionamento sia uniforme lungo tutta la larghezza. Un apron mal tensionato o decentrato causa irregolarita' di stiro e **rottura_filo**.

8. **Eseguire un ciclo di prova e misurare il CVm%.** Dopo la pulizia, riavviare la sezione e produrre un campione di filo di almeno 200 m. Misurare il CVm% con lo Uster Tester (se disponibile) o valutare visivamente il campione di filo avvolto in bobina. Il CVm% deve essere uguale o inferiore al valore di riferimento dell'articolo.

## Verification

- Gli apron in gomma hanno durezza Shore A nel range specificato dal costruttore (tipicamente 45-65 Shore A).
- Il **calibro_digitale** conferma che il diametro dei cilindri metallici e' entro la tolleranza nominale (+/- 0.05 mm rispetto al valore tabellato).
- Il CVm% del filo prodotto nella prova post-pulizia e' conforme al valore di riferimento dell'articolo.
- Gli apron sostituiti o segnalati per sostituzione sono stati registrati nel modulo di manutenzione macchina.

## Troubleshooting

**Il CVm% non migliora dopo la pulizia:**
- Verificare il **rapporto_stiro** impostato per l'articolo: un rapporto di **stiro** eccessivo causa irregolarita' strutturale non risolvibile con la pulizia. Confrontare con i parametri nominali dell'articolo.
- Controllare la qualita' del nastro di alimentazione (sliver): un nastro gia' irregolare non puo' essere corretto dal sistema di stiro. Richiedere un campione di nastro al reparto carda o pettinatura per analisi.

**L'apron si rompe o si deforma durante la rimozione:**
- Non riutilizzare un apron rotto: sostituirlo. Verificare che l'estrattore apron sia del tipo corretto per il modello di macchina; l'uso di un estrattore errato causa danni meccanici all'apron durante la rimozione.

**Depositi di cera sui cilindri metallici resistenti alla pulizia normale:**
- La cera del cursore (ring traveller wax) puo' contaminarsi sui cilindri di stiro se il sistema di lubrificazione cursore e' mal regolato. Pulire con un solvent non aggressivo (es. isopropanolo) applicato con panno: non spruzzare direttamente sulla macchina. Verificare la regolazione del sistema di lubrificazione cursore.

## References

- Glossario IT tessile: [filatura](../../docs/docs/glossary.md#filatura), [stiro](../../docs/docs/glossary.md#stiro), [cilindro_stiro](../../docs/docs/glossary.md#cilindro_stiro)
- SOP correlate: SOP-SPN-001 (calibrazione fusi), SOP-SPN-003 (regolazione rotaia anelli), SOP-SPN-004 (controllo slub)
- Standard di riferimento: ISO 5247 (terminologia tessile), documentazione tecnica costruttore filatoio
