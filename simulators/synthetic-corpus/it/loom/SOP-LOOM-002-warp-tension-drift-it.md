---
id: SOP-LOOM-002
title: Diagnosi e correzione deriva tensione ordito
version: "1.0"
lang: it
asset: telaio
asset_family: weaving
role: technician
hazard_level: medium
estimated_duration_min: 30
prerequisites:
  - SOP-LOOM-001
related_glossary:
  - telaio
  - ordito
  - subbio
  - liccio
  - misuratore_tensione_ordito
  - rottura_filo
  - densita_trama
  - tessitura
tags:
  - troubleshooting
  - weaving
  - tension
  - preventive
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Diagnosi e correzione deriva tensione ordito

## Scope

Questa SOP descrive la procedura diagnostica e correttiva per la deriva progressiva della tensione del filo di **ordito** su un **telaio** rapier o projectile. La deriva si manifesta come incremento o decremento graduale della tensione oltre la soglia di tolleranza del ±15% rispetto al valore nominale, rilevato dal **misuratore_tensione_ordito** o diagnosticato dalla comparsa di **difetto_catena** nel tessuto.

La procedura è destinata al tecnico di reparto (non all'operatore di produzione) in quanto richiede l'accesso ai parametri di regolazione del sistema di svolgimento **subbio** e l'uso di strumenti di misura.

Non si applica a rotture improvvise di filo singolo (vedi SOP-LOOM-001) né a guasti elettromeccanici del sistema di svolgimento (escalation al manutentore).

## Prerequisites

- Il **telaio** è in stato di fermo pianificato o durante il cambio turno (non interrompere la produzione in corso senza giustificazione).
- Il tecnico ha accesso al pannello di regolazione del sistema di svolgimento (chiave di manutenzione livello 2).
- È disponibile il valore nominale di tensione ordito per l'articolo in produzione (reperibile dal foglio produzione o dal sistema MES).
- Strumenti di misura disponibili e calibrati.
- DPI: guanti antitaglio, occhiali protettivi se si lavora in prossimità del **subbio** rotante.

## Tools and PPE

- **Misuratore_tensione_ordito** portatile (tipo tensiometro a presa diretta su filo)
- **Calibro_digitale** per verifica spessore filo o componenti meccanici
- Chiave per regolazione freno **subbio** (specifico per modello macchina)
- Torcia di ispezione LED
- Foglio di registrazione parametri (o tablet con accesso MES)
- Guanti antitaglio categoria I
- Occhiali protettivi

## Step-by-step Procedure

1. **Misurare la tensione attuale.** Con il **telaio** in ciclo lento (jog), applicare il **misuratore_tensione_ordito** su tre posizioni rappresentative della larghezza del subbio (bordo sinistro, centro, bordo destro). Registrare i tre valori in N. Range tipico industria per cotone Nm 30-60: 10-25 N per filo.

2. **Confrontare con il valore nominale.** Calcolare lo scarto percentuale: `scarto% = (misurato - nominale) / nominale × 100`. Se lo scarto è compreso in ±15%: la tensione è nella tolleranza, procedere alla sezione Troubleshooting per cause alternative. Se lo scarto supera ±15%: procedere al punto 3.

3. **Identificare la causa della deriva.** Verificare:
   - **Diametro del subbio:** un subbio quasi esaurito ha diametro ridotto, che a parità di freno produce tensione aumentata. Misurare il diametro residuo con il **calibro_digitale**. Diametro < 200 mm su subbio nominale 800 mm indica esaurimento imminente.
   - **Stato del freno subbio:** verificare l'usura delle guarnizioni di attrito e la pulizia della superficie di contatto (olio, residui di filo).
   - **Stato del sistema di recupero tensione (compensatore):** verificare che il braccio compensatore si muova liberamente e che il peso/molla di richiamo sia intatto.

4. **Correzione per deriva da variazione diametro subbio (causa più frequente).** Regolare il freno del **subbio** incrementando o riducendo la tensione di serraggio secondo la tabella di regolazione macchina. Effettuare la regolazione in incrementi del 5% e misurare nuovamente la tensione dopo ogni step. Obiettivo: rientrare in ±10% del nominale.

5. **Correzione per freno subbio sporco o usurato.** Fermare il **telaio** e bloccare il **subbio** meccanicamente. Pulire la superficie di attrito con panno asciutto. Se le guarnizioni di attrito mostrano usura (spessore < 3 mm o sede irregolare): sostituire le guarnizioni secondo procedura specifica macchina e registrare l'intervento.

6. **Correzione per compensatore bloccato o malfunzionante.** Verificare la libertà di movimento del braccio compensatore a telaio fermo. Se bloccato: rimuovere residui di filo o polvere con aria compressa. Se il componente è danneggiato: notifica al manutentore e sospensione della produzione dell'articolo corrente.

7. **Eseguire un ciclo di prova.** Dopo la correzione, riavviare il **telaio** a velocità normale per 50 m di tessuto. Misurare nuovamente la tensione ogni 10 m. Verificare che la deriva si sia stabilizzata e che il tessuto non presenti **difetto_catena** o variazioni di **densita_trama**.

8. **Registrare l'intervento.** Annotare su registro macchina o MES: data, ora, valore tensione pre/post correzione, causa identificata, azione correttiva, tecnico responsabile.

## Verification

- La tensione misurata su bordo sinistro, centro e bordo destro del **subbio** rientra entro ±10% del valore nominale dell'articolo in produzione.
- Il **misuratore_tensione_ordito** non riporta allarmi nei successivi 30 minuti di produzione.
- L'ispezione visiva del tessuto prodotto nelle ultime 10 m non evidenzia **difetto_catena** o variazioni di **densita_trama** rispetto al tessuto prodotto prima della deriva.
- Il parametro di freno **subbio** è stato registrato nel foglio di manutenzione macchina.
- Il tasso di **rottura_filo** nei 30 minuti successivi all'intervento non supera la soglia normale dell'articolo (tipicamente < 3 rotture/ora per cotone shirting standard).

## Troubleshooting

**La tensione non si stabilizza dopo la correzione del freno:**
- Verificare che il sistema di retroazione automatica della tensione (se presente: elettronica di controllo) non stia compensando in direzione opposta alla correzione manuale. Consultare il manuale macchina per la modalità di override manuale.
- Controllare i cuscinetti del **subbio**: rumori anomali o gioco laterale indicano usura. Escalation al manutentore.

**La deriva si manifesta solo in una zona laterale del tessuto (asimmetrica):**
- Controllare singolarmente la tensione dei fili di **ordito** ai bordi usando il tensiometro punto per punto.
- Verificare l'allineamento del **liccio** corrispondente alla zona affetta: un **liccio** fuori sede lateralmente genera tensione asimmetrica.
- Verificare che il subbio sia montato perfettamente perpendicolare all'asse macchina (tolleranza tipica: < 0.5 mm di disallineamento su 2 m di larghezza).

**Deriva ripetuta con ciclo < 2 ore:**
- Documentare la frequenza di deriva e aprire un ordine di manutenzione preventiva per revisione completa del sistema di svolgimento **subbio** (freno, compensatore, sensore tensione).
- Valutare se l'articolo in produzione ha una tensione nominale al limite delle specifiche macchina.

**Il tessuto presenta rigature orizzontali periodiche (barre):**
- Le barre periodiche con periodo regolare (tipicamente ogni 20-100 cm) sono spesso causate da variazione di tensione sincronizzata con la frequenza di rotazione del **subbio**: verificare eccentricità del subbio o irregolarità del freno.

## References

- Glossario IT tessile: [ordito](../../docs/docs/glossary.md#ordito), [subbio](../../docs/docs/glossary.md#subbio), [misuratore_tensione_ordito](../../docs/docs/glossary.md#misuratore_tensione_ordito)
- SOP correlate: SOP-LOOM-001 (rottura filo singolo), SOP-QLT-001 (ispezione qualita' tessuto)
- Standard di riferimento: ISO 5247 (terminologia tessile), manuale tecnico costruttore telaio
