---
id: SOP-LOOM-003
title: Rimozione e risoluzione inceppamento navetta su telaio a proiettile
version: "1.0"
lang: it
asset: telaio
asset_family: weaving
role: operator
hazard_level: medium
estimated_duration_min: 20
prerequisites:
  - SOP-LOOM-001
related_glossary:
  - telaio
  - tessitura
  - inceppamento_navetta
  - cassa_battente
  - trama
  - mispick
tags:
  - troubleshooting
  - weaving
  - shuttle-jam
  - operator
audience: operations
status: reviewed
created_in_phase: 2
---

# Rimozione e risoluzione inceppamento navetta su telaio a proiettile

## Scope

Questa SOP descrive la procedura di intervento rapido per la rimozione dell'**inceppamento_navetta** su un **telaio** a proiettile (projectile loom). L'inceppamento si verifica quando il proiettile non completa la corsa di inserzione della **trama** e si ferma all'interno del passo dell'**ordito**, causando l'arresto automatico della macchina e il rischio di **mispick** o danno alla catena di **ordito**.

La procedura si applica a inceppamenti singoli del proiettile nella zona di inserzione. Non si applica a guasti al meccanismo di lancio (picking mechanism) o a danni strutturali alla **cassa_battente**: in questi casi il tecnico di reparto deve essere allertato immediatamente. La mancata rimozione corretta del proiettile inceppato può causare difetti multipli di **trama** e danneggiare il **liccio**.

## Prerequisites

- Il **telaio** è in stato di arresto automatico (segnalazione luminosa e sonora attiva).
- L'operatore ha completato il training su sicurezza macchine tessili e conosce la posizione degli organi di fermo manuale del telaio.
- Sono disponibili: gancio di estrazione proiettile, torcia di ispezione, guanti antitaglio.
- Il pannello di controllo è accessibile e mostra l'allarme di inceppamento con codice diagnostico.

## Tools and PPE

- Gancio di estrazione proiettile (specifico per il modello di **telaio** in uso, normalmente fornito dal costruttore)
- Torcia di ispezione LED
- Guanti antitaglio categoria II (la manipolazione del proiettile presenta bordi affilati)
- **Calibro_digitale** (opzionale, per verifica integrità proiettile dopo estrazione)
- Occhiali protettivi

## Step-by-step Procedure

1. **Verificare l'arresto completo del telaio.** Controllare il pannello di controllo: lo stato deve essere STOP con allarme inceppamento attivo. Non introdurre le mani nella zona di inserzione **trama** finché il **telaio** non è in arresto completo e il volano (flywheel) ha decelerato.

2. **Localizzare il proiettile inceppato.** Aprire il pannello laterale di accesso alla zona di inserzione. Illuminare con la torcia per individuare la posizione esatta del proiettile nella guida di inserzione o nel passo dell'**ordito**. Verificare che il proiettile non sia visibilmente deformato.

3. **Liberare il proiettile con il gancio di estrazione.** Inserire il gancio di estrazione nel foro posteriore del proiettile (non tirare dal filo di **trama** avvolto — rischio di rottura e **mispick** multiplo). Estrarre con movimento lineare lungo l'asse di inserzione, senza angolazione. Applicare una forza progressiva e costante; se il proiettile non cede alla prima trazione, verificare se è bloccato da un filo di **ordito** avvolto.

4. **Rimuovere il proiettile dalla guida.** Una volta estratto, posizionare il proiettile nell'apposito contenitore di stoccaggio. Ispezionare visivamente il proiettile per deformazioni, graffi profondi o bordi scheggiati: un proiettile danneggiato deve essere rimosso dal ciclo e segnalato per sostituzione.

5. **Ispezionare la zona di inserzione.** Verificare che non siano rimasti frammenti di filo di **trama** nel passo dell'**ordito** o nella guida di inserzione. Rimuovere con pinzette qualsiasi residuo di filo. Controllare che i fili di **ordito** nella zona dell'inceppamento non abbiano subito danni (taglio parziale, allentamento dalla maglia del **liccio**).

6. **Verificare l'integrità del filo di trama.** Rimuovere il filo di **trama** danneggiato dall'area dell'inceppamento: tagliare il residuo a circa 5 cm dall'inserzione interrotta. Il sistema ripartirà con un nuovo ciclo di inserzione al riavvio.

7. **Richiudere i pannelli di accesso e verificare le condizioni di riavvio.** Chiudere e bloccare il pannello laterale. Verificare sul pannello di controllo che l'allarme di inceppamento sia stato resettato (pulsante RESET). Eseguire un ciclo lento (jog) per 2-3 passate di **trama** prima del riavvio a velocità normale.

8. **Registrare l'evento.** Annotare sul registro macchina: data, ora, numero di inceppamenti nel turno, condizioni di estrazione, stato proiettile (conforme / segnalato per sostituzione), operatore.

## Verification

- Il **telaio** riprende il funzionamento a velocità normale senza nuovi allarmi di inceppamento.
- L'ispezione visiva delle prime 5 m di tessuto prodotto dopo il riavvio non evidenzia **mispick** o irregolarità di **trama** nella zona di ripresa.
- Il proiettile estratto è stato iscritto nel registro stato proiettili (conforme/da sostituire).
- Il tasso di inceppamenti nel turno è registrato nel log macchina per il monitoraggio trend.

## Troubleshooting

**Il proiettile non si estrae con il gancio standard:**
- Verificare che il proiettile non sia bloccato da un filo di **ordito** avvolto più volte: in questo caso, tagliare il filo con forbici da taglio tessile (non tirare) prima di tentare l'estrazione.
- Se il proiettile è fisicamente deformato e incastrato nella guida: non forzare oltre. Fermare il tentativo e allertare il tecnico; forzare un proiettile deformato può danneggiare la guida di inserzione.

**L'allarme di inceppamento si ripresenta entro pochi minuti dal riavvio:**
- Verificare il sistema di lancio (picking mechanism): un meccanismo di lancio usurato genera forza di inserzione insufficiente, causando inceppamenti ricorrenti. Escalation al tecnico per ispezione del picking mechanism.
- Controllare il titolo e la tensione del filo di **trama** in bobina: un filo troppo grosso o eccessivamente torto aumenta la resistenza di inserzione.

**Residui di filo di trama visibili nel tessuto nelle righe adiacenti all'inceppamento:**
- Ispezionare il tessuto nelle 30 cm precedenti all'arresto per rilevare **mispick** latenti. Se presenti: marcare la zona per ispezione qualità e classificare secondo SOP-QLT-001.

## References

- Glossario IT tessile: [telaio](../../docs/docs/glossary.md#telaio), [trama](../../docs/docs/glossary.md#trama), [mispick](../../docs/docs/glossary.md#mispick)
- SOP correlate: SOP-LOOM-001 (rottura filo ordito), SOP-LOOM-002 (deriva tensione ordito), SOP-QLT-003 (analisi mispick)
- Standard di riferimento: ISO 5247 (terminologia tessile), manuale tecnico costruttore telaio
