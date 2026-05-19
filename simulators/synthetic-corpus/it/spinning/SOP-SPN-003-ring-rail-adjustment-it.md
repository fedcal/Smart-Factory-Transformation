---
acl_level: internal
asset: ring spinning frame
asset_family: spinning
audience: maintenance
created_in_phase: 2
estimated_duration_min: 35
hazard_level: low
id: SOP-SPN-003
lang: it
prerequisites:
- SOP-SPN-001
related_glossary:
- filatura
- filatoio_anello
- fuso
- anello_rotante
- irregolarita_filato
- titolo_filato
role: technician
status: reviewed
tags:
- maintenance
- spinning
- ring-rail
- adjustment
- technician
title: Regolazione rotaia anelli del filatoio ad anello
version: '1.0'
---

# Regolazione rotaia anelli del filatoio ad anello

## Scope

Questa SOP descrive la procedura di regolazione e verifica della rotaia degli anelli (ring rail) del **filatoio_anello**. La rotaia degli anelli supporta gli anelli cursori (**anello_rotante**) su cui scorre il cursore (traveller) che alimenta il filo al **fuso**; il suo movimento verticale oscillante determina la distribuzione del filo sulla spola e la conicita' delle spire.

Una rotaia mal regolata o usurata causa:
- Distribuzione non uniforme del filo sulla spola (conicita' irregolare)
- Variazione periodica del **titolo_filato** (barre nel filo ogni N cm corrispondenti alla corsa della rotaia)
- Aumento del tasso di **rottura_filo** nella zona di avvolgimento

La verifica e' raccomandata ogni 500 ore di produzione o in seguito a segnalazioni di irregolarita' nel pattern di avvolgimento.

## Prerequisites

- Il **filatoio_anello** e' in stato di fermo pianificato (cambio turno o fine partita).
- Il tecnico ha accesso al manuale di regolazione della rotaia anelli (valori nominali di corsa, parallelismo, altezza) del costruttore specifico.
- Strumenti di misura disponibili e calibrati.
- DPI: guanti da lavoro, occhiali protettivi.

## Tools and PPE

- Livella di precisione (risoluzione 0.01 mm/m) per verifica parallelismo rotaia
- **Calibro_digitale** per verifica distanza rotaia-guida e clearance fuso
- Chiave di regolazione rotaia (specifica per il modello macchina)
- Torcia di ispezione LED
- Guanti da lavoro
- Occhiali protettivi

## Step-by-step Procedure

1. **Verificare il parallelismo della rotaia anelli.** Con il **filatoio_anello** fermo e la rotaia in posizione di partenza (punto inferiore della corsa), posizionare la livella di precisione sulla rotaia in tre punti: bordo sinistro, centro, bordo destro. Registrare la deviazione dal piano orizzontale in ciascun punto. Tolleranza tipica: deviazione < 0.2 mm/m su tutta la larghezza della macchina. Una deviazione superiore indica cedimento delle guide laterali della rotaia.

2. **Verificare la corsa verticale della rotaia.** Utilizzando un comparatore o un righello millimetrico, misurare la corsa verticale della rotaia (distanza tra il punto piu' basso e il punto piu' alto dell'oscillazione). Confrontare con il valore nominale della macchina per l'articolo in produzione. La corsa determina la lunghezza della spira di avvolgimento: una corsa ridotta causa spole con meno filo per livello, aumentando i cambi spola.

3. **Verificare la centralita' degli anelli rispetto ai fusi.** Con il **calibro_digitale**, misurare la distanza tra il centro dell'anello cursore (**anello_rotante**) e il centro del **fuso** corrispondente in 5 posizioni campione distribuite lungo la macchina. Tolleranza tipica: decentramento < 0.3 mm. Un anello decentrato rispetto al **fuso** genera attrito asimmetrico del cursore e aumenta l'**irregolarita_filato**.

4. **Ispezionare le guide laterali della rotaia.** Controllare visivamente le guide laterali (colonne di scorrimento della rotaia) per usura, deformazione o accumuli di fibra. Un'usura eccessiva delle guide causa gioco laterale nella corsa della rotaia, che si traduce in variazione periodica del **titolo_filato** (barre). Pulire le guide con panno privo di pelucchi.

5. **Regolare la rotaia per correggere le deviazioni rilevate.** Se il parallelismo e' fuori tolleranza: regolare le viti di livellamento laterali (tipicamente 2 per lato per macchine da 1000-1500 posizioni). Regolare in incrementi di 0.05 mm e reverificare dopo ogni incremento. Se la centralita' degli anelli e' fuori tolleranza: correggere la posizione laterale della rotaia tramite le guide di posizionamento.

6. **Verificare il sistema di movimentazione della rotaia.** Controllare la catena o cinghia di movimentazione verticale della rotaia: una cinghia allentata causa variazione irregolare della velocita' di oscillazione, che genera barre nel filo. Tensione corretta della cinghia: verificare con il metodo indicato nel manuale (tipicamente deflessione < 5 mm sotto carico di 10 N).

7. **Eseguire un ciclo di prova a velocita' ridotta.** Riavviare il **filatoio_anello** a velocita' ridotta (50-60% della velocita' nominale) per almeno 10 minuti. Osservare il pattern di avvolgimento sulle spole: il filo deve distribuirsi uniformemente sulla spola con conicita' regolare. Nessuna barra visibile sul filo avvolto.

8. **Portare a velocita' di regime e registrare.** Portare gradualmente il **filatoio_anello** a velocita' nominale. Verificare che il tasso di **rottura_filo** nei primi 15 minuti non superi la soglia normale. Registrare: deviazioni riscontrate, regolazioni effettuate, data, tecnico.

## Verification

- La livella di precisione sulla rotaia (in posizione di riposo) mostra una deviazione < 0.2 mm/m su tutta la larghezza macchina.
- La centralita' degli anelli rispetto ai fusi e' entro 0.3 mm su 5 posizioni campione.
- Le spole prodotte nel ciclo di prova mostrano un pattern di avvolgimento uniforme senza barre visibili.
- Il tasso di **rottura_filo** nei 15 minuti post-regolazione e' conforme alla soglia normale dell'articolo.

## Troubleshooting

**La rotaia si inclina progressivamente durante la produzione (deriva del parallelismo):**
- Le viti di livellamento si allentano per vibrazione: applicare vernice di blocco (Loctite o equivalente) dopo la regolazione, seguendo il manuale del costruttore. Se il problema persiste, le guide laterali potrebbero essere usurate: escalation al manutentore per verifica strutturale.

**Il filo mostra barre periodiche con passo uguale alla corsa della rotaia:**
- Questo indica un difetto nella movimentazione della rotaia (cinghia allentata o guida con gioco eccessivo). Verificare la tensione della cinghia di movimentazione e il gioco laterale nelle guide: ripetere dal punto 4 e 6.

**Uno o piu' anelli risultano decentrati rispetto al fuso ma la regolazione non e' possibile con le viti standard:**
- Probabile deformazione permanente della rotaia in quella zona: segnalare al responsabile manutenzione per valutare la sostituzione del segmento di rotaia interessato.

## References

- Glossario IT tessile: [filatoio_anello](../../docs/docs/glossary.md#filatoio_anello), [anello_rotante](../../docs/docs/glossary.md#anello_rotante), [fuso](../../docs/docs/glossary.md#fuso)
- SOP correlate: SOP-SPN-001 (calibrazione fusi), SOP-SPN-002 (pulizia cilindri stiro), SOP-SPN-005 (lubrificazione preventiva)
- Standard di riferimento: ISO 5247 (terminologia tessile), documentazione tecnica costruttore filatoio
