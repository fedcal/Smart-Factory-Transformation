---
id: SOP-LOOM-001
title: Risoluzione guasto rottura filo di ordito
version: "1.0"
lang: it
asset: telaio
asset_family: weaving
role: operator
hazard_level: low
estimated_duration_min: 15
prerequisites: []
related_glossary:
  - rottura_filo
  - telaio
  - ordito
  - trama
  - liccio
  - tessitura
tags:
  - troubleshooting
  - weaving
  - broken-end
  - operator
audience: operations
status: draft-unreviewed
created_in_phase: 2
---

# Risoluzione guasto rottura filo di ordito

## Scope

Questa SOP descrive la procedura di intervento rapido a seguito di una **rottura_filo** di **ordito** su un **telaio** a rapier durante la **tessitura**. L'obiettivo è ridurre al minimo il tempo di fermo macchina ripristinando la continuità del filo e riavviando la produzione con qualità del tessuto conforme.

La procedura si applica a rotture singole di un filo di **ordito** che causano l'arresto automatico del telaio tramite rilevatore elettronico di rottura filo. Non si applica a rotture multiple simultanee (> 3 fili) o a guasti meccanici del telaio: in questi casi contattare il tecnico di reparto.

## Prerequisites

- L'operatore ha completato il training base su sicurezza macchine tessili.
- Il telaio è in stato di arresto automatico (segnalazione luminosa attiva).
- Sono disponibili: ago rincorso, filo di **ordito** di riserva del titolo corretto, forbici da taglio, pettine di rincorso.
- L'operatore indossa i DPI previsti: guanti antitaglio (categoria I), **otoprotettori** se in reparto ad alto rumore.

## Tools and PPE

- Ago rincorso (lunghezza 15-20 cm, sezione adeguata al titolo filato)
- Filo di **ordito** di riserva (stesso titolo e torsione del filato in produzione)
- Forbici da taglio tessile
- Pettine di rincorso o passa-filo
- **Calibro_digitale** (opzionale, per verifica titolo filo di riserva se dubbia)
- **Otoprotettori** SNR ≥ 28 dB (obbligatori se livello sonoro reparto > 85 dB(A))
- Guanti antitaglio categoria I

## Step-by-step Procedure

1. **Identificare la posizione della rottura.** Osservare la superficie del **telaio** e localizzare il filo di **ordito** mancante nella catena. Il rilevatore elettronico indica il numero di liccio coinvolto sul display di macchina.

2. **Mettere in sicurezza l'area di lavoro.** Verificare che il telaio sia in arresto completo (pannello di controllo: stato STOP). Non introdurre le mani nel meccanismo di **liccio** prima della verifica.

3. **Localizzare il capo del filo rotto.** Risalire il filo spezzato dal punto di rottura verso il **subbio** di ordito. In caso di filo rientrato nel subbio, estrarre 20-30 cm tirando delicatamente.

4. **Eseguire il rincorso del filo.** Inserire l'ago rincorso attraverso la maglia del **liccio** corrispondente e attraverso il dente del pettine (**cassa_battente**). Annodare il capo di **ordito** di riserva all'ago con nodo scorsoio. Tirare l'ago per far passare il filo attraverso liccio e pettine.

5. **Regolare la tensione del filo.** Applicare una tensione manuale al filo di rincorso paragonabile alla tensione visiva degli altri fili di **ordito** adiacenti. Un filo troppo lasco causerà difetti di **tessitura**; un filo troppo teso causerà una nuova rottura.

6. **Fissare il filo al tessuto.** Annodare il filo di **ordito** riparato al tessuto già prodotto (punto di ripresa) con nodo tessile. Tagliare il residuo a 2-3 cm dal nodo.

7. **Riavviare il telaio in modalità lenta.** Premere il pulsante di riavvio lento (jog) per 2-3 passate di **trama** verificando visivamente che il filo rincorso si integri correttamente nel tessuto senza formare **difetto_catena** o irregolarità di **densita_trama**.

8. **Riprendere la produzione a velocità normale.** Se le prime passate lente sono corrette, portare il telaio a velocità di regime.

## Verification

- Verifica visiva: assenza di **rottura_filo** nei successivi 20 m di tessuto prodotto.
- Verifica della superficie tessile: il filo rincorso non deve essere visibile come discontinuità di colore o struttura (assenza di **difetto_catena**).
- Verifica della **densita_trama**: confrontare visivamente con il tessuto prodotto prima dell'arresto; non devono essere evidenti variazioni di compattezza nella zona di ripresa.
- Il **conta_trama** (se installato) non deve segnalare anomalie nella zona di ripresa.
- Registrare l'intervento sul log macchina: data, ora, numero liccio, causa presunta (se identificata), operatore.

## Troubleshooting

**Il filo si rompe nuovamente entro pochi metri:**
- Verificare il titolo del filo di riserva: deve corrispondere al titolo nominale dell'ordito. Usare il **calibro_digitale** se disponibile.
- Controllare che il nodo di rincorso non sia posizionato in zona di attrito elevato (maglia liccio o dente pettine): riposizionare il punto di nodo a monte.
- Se si verificano più di 3 rotture consecutive nello stesso filo: escalation al tecnico di reparto (possibile difetto del fuso di provenienza o danneggiamento del liccio).

**Impossibile individuare il capo del filo rotto nel subbio:**
- Utilizzare la torcia di ispezione per illuminare il subbio di **ordito** dalla parte posteriore.
- Se il filo è completamente rientrato nel subbio, liberare manualmente 30-40 cm svolgendo il subbio con manovella di retroazione (seguire la procedura di sicurezza macchina specifica).

**Il telaio non riprende il funzionamento dopo il riavvio:**
- Verificare che non siano rimaste forbici o utensili nella zona del **liccio** o del pettine.
- Controllare il pannello di controllo per allarmi aggiuntivi (es. rottura **trama**, problema pressione aria jet, ecc.).
- Se l'allarme persiste, chiamare il tecnico: non forzare il riavvio.

**Il tessuto presenta rigature orizzontali nella zona di ripresa:**
- Probabilmente la tensione applicata al filo di rincorso era eccessiva. Allentare il nodo e ripetere il rincorso con tensione ridotta.
- Verificare che la **cassa_battente** non abbia subito variazioni di corsa durante l'arresto.

## References

- Glossario IT tessile: [rottura_filo](../../docs/docs/glossary.md#rottura_filo), [telaio](../../docs/docs/glossary.md#telaio), [ordito](../../docs/docs/glossary.md#ordito)
- SOP correlate: SOP-LOOM-002 (deriva tensione ordito), SOP-QLT-001 (ispezione qualita' tessuto)
- Standard di riferimento: ISO 5247 (terminologia tessile), UNI EN 388 (DPI guanti antitaglio)
