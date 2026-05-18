---
id: SOP-SPN-001
title: Calibrazione e verifica fusi filatoio ad anello
version: "1.0"
lang: it
asset: ring spinning frame
asset_family: spinning
role: technician
hazard_level: low
estimated_duration_min: 25
prerequisites: []
related_glossary:
  - filatura
  - filatoio_anello
  - fuso
  - irregolarita_filato
  - titolo_filato
  - stiro
  - igrometro
  - calibro_digitale
tags:
  - maintenance
  - spinning
  - calibration
  - preventive
  - technician
audience: maintenance
status: reviewed
created_in_phase: 2
---

# Calibrazione e verifica fusi filatoio ad anello

## Scope

Questa SOP descrive la procedura di calibrazione e verifica periodica dei **fuso** sul **filatoio_anello** nell'ambito della manutenzione preventiva del reparto **filatura**. L'obiettivo e' mantenere la concentricita' e la verticalita' dei fusi entro le tolleranze costruttive, prevenendo l'insorgere di vibrazioni anomale, **irregolarita_filato** e **rottura_filo** eccessiva.

La verifica e' raccomandata ogni 500 ore di produzione o a seguito di segnalazioni ripetute di vibrazioni o difettosita' del filo in zone specifiche della macchina. La procedura si applica ai fusi a rotazione singola (tipo anello-cursore standard). Non si applica ai rotori del filatoio open-end (procedura specifica distinta).

## Prerequisites

- Il **filatoio_anello** e' in stato di fermo pianificato (cambio turno o fermo manutenzione).
- Il tecnico ha accesso alla documentazione tecnica della macchina (foglio tolleranze fusi del costruttore).
- L'umidita' relativa del reparto e' rilevata dall'**igrometro** di reparto e rientra nel range operativo 55-65% RH (fuori range: la misura di concentricita' puo' essere influenzata dall'espansione termica).
- Strumenti di misura disponibili e calibrati.

## Tools and PPE

- **Calibro_digitale** (risoluzione 0.01 mm) per verifica diametro fuso e anello
- Comparatore centesimale su supporto magnetico (per verifica eccentricita' testa fuso)
- Strumento di misura verticalita' fuso (specifico per settore filatura — es. perno calibro verticale)
- Estrattore fusi (specifico per modello macchina, da kit manutenzione)
- Lubrificante a olio minerale bassa viscosita' (specificato dal costruttore della macchina)
- Panno pulizia privo di pelucchi
- Torcia di ispezione LED
- **Igrometro** (verifica condizioni ambiente al momento della misura)
- Guanti da lavoro (non antitaglio — necessita' di sensibilita' tattile nella manipolazione fusi)

## Step-by-step Procedure

1. **Registrare le condizioni ambientali.** Leggere l'**igrometro** di reparto e annotare temperatura (°C) e umidita' relativa (% RH). Range ottimale per misure precise: 20-25 °C, 55-65% RH. Se fuori range: registrare la deviazione e indicarla nel rapporto di calibrazione.

2. **Individuare i fusi da verificare.** Per una calibrazione programmata, verificare sistematicamente tutti i **fuso** della sezione di macchina assegnata (tipicamente 50-100 fusi per ciclo). Per una verifica spot da segnalazione: concentrarsi sui fusi nel range ±5 posizioni dalla zona segnalata.

3. **Pulizia preliminare del fuso.** Rimuovere residui di filo avvolto sul fuso con pinzette o dita (mai con cutter — rischio di graffiare la superficie). Pulire la superficie del fuso con panno asciutto privo di pelucchi. La superficie del fuso deve essere priva di olio in eccesso e depositi di cera di cursore.

4. **Verifica della concentricita' della testa del fuso.** Applicare il comparatore centesimale su supporto magnetico alla struttura della macchina, posizionando il tastatore sul diametro superiore del **fuso** (a circa 5 mm dalla sommita'). Far ruotare il fuso manualmente di 360° e registrare la variazione di lettura. Tolleranza massima: 0.05 mm di eccentricita' (verificare con il dato costruttore). Fusi con eccentricita' > 0.08 mm: segnalare per sostituzione.

5. **Verifica della verticalita' del fuso.** Applicare lo strumento di verticalita' (o perno calibro specifico) al **fuso** e verificare la deviazione angolare rispetto alla verticale. Tolleranza tipica industria: < 0.3 mm/100 mm di altezza fuso. Fusi con inclinazione > 0.5 mm/100 mm: regolare la base di supporto fuso (vite di registrazione) o segnalare per sostituzione se la deformazione e' permanente.

6. **Lubrificazione del fuso (se prevista in ciclo).** Applicare 2-3 gocce di olio lubrificante specificato dal costruttore nel punto di lubrificazione inferiore del **fuso** (cuscinetto o bronzina). Eccesso di olio contamina il filo di **filatura** e causa macchie sul tessuto finale. Non lubrificare la parte superiore del fuso (zona di contatto con filo e cursore).

7. **Verifica dell'anello cursore.** Controllare visivamente l'anello cursore associato al **fuso** in verifica. Segnali di usura da sostituire: anello ovalizzato (verificare con il **calibro_digitale** — tolleranza circolarita' tipica < 0.1 mm), superficie interna rigata o corrosa, segni di surriscaldamento (colore brunito). Un anello usurato aumenta l'**irregolarita_filato** e il tasso di **rottura_filo**.

8. **Registrare gli esiti.** Compilare il foglio di calibrazione (o inserire nel MES): numero macchina, numero posizione fuso, eccentricita' misurata, verticalita' misurata, stato anello, azione eseguita (nessuna / lubrificazione / segnalazione sostituzione). Firmare e datare il documento.

## Verification

- I fusi verificati e conformi non mostrano vibrazioni udibili o anomale al riavvio della macchina (verifica uditiva nei successivi 10 minuti di produzione).
- Il **titolo_filato** prodotto nei 30 minuti successivi alla calibrazione e' entro le specifiche (verifica su campione Uster Tester se disponibile, o ispezione visiva del rotolo prodotto).
- L'**irregolarita_filato** (CVm%) nei 30 minuti post-calibrazione non supera il valore limite specificato per l'articolo in produzione.
- I fusi segnalati per sostituzione sono stati inseriti nella lista di manutenzione straordinaria con priorita' e numero di posizione.
- Il modulo di calibrazione e' firmato e archiviato nel fascicolo macchina.

## Troubleshooting

**Il fuso mostra eccentricita' nel range 0.05-0.08 mm (zona grigia):**
- Verificare l'eccentricita' su 3 punti di altezza diversa del fuso. Se l'eccentricita' e' costante per tutta l'altezza: probabile deformazione permanente (sostituzione). Se varia solo in sommita': possibile deposito o danno localizzato alla testa — pulire e reverificare.

**Impossibile estrarre il fuso con l'estrattore standard:**
- Non forzare: il fuso puo' essere bloccato da ossidazione o da deformazione del supporto. Applicare penetrante (spray specifico, rispettando i tempi di attesa) e reverificare. Se ancora bloccato: escalation al manutentore senior.

**Vibrazione anomala persiste dopo la calibrazione di un fuso:**
- Verificare il cursore dell'anello: un cursore squilibrato o di massa errata genera vibrazioni anche con fuso concentrico. Sostituire il cursore con uno del numero specifico per il **titolo_filato** in produzione.
- Verificare che il giunto di trasmissione del gruppo di fusi (tangenziale) non abbia gioco eccessivo.

**Umidita' relativa fuori range durante la calibrazione (> 70% o < 40%):**
- Le misure di concentricita' rimangono valide (non influenzate dall'umidita'). Registrare la deviazione ambientale nel rapporto.
- Se l'umidita' e' cronicamente fuori range (> 70%): segnalare al responsabile impianti per verifica del sistema di condizionamento aria del reparto **filatura** (l'umidita' alta aumenta le **rottura_filo** da carica elettrostatica).

## References

- Glossario IT tessile: [fuso](../../docs/docs/glossary.md#fuso), [filatoio_anello](../../docs/docs/glossary.md#filatoio_anello), [irregolarita_filato](../../docs/docs/glossary.md#irregolarita_filato)
- SOP correlate: SOP-SPN-002 (pulizia cilindri stiro), SOP-SPN-003 (regolazione rotaia anelli)
- Standard di riferimento: ISO 5247 (terminologia tessile), documentazione tecnica costruttore filatoio
