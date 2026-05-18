---
id: SOP-LOOM-005
title: Pulizia e ripristino telaio post-evento di difettosità seriale
version: "1.0"
lang: it
asset: telaio
asset_family: weaving
role: technician
hazard_level: medium
estimated_duration_min: 45
prerequisites:
  - SOP-LOOM-001
  - SOP-LOOM-002
related_glossary:
  - telaio
  - tessitura
  - rottura_filo
  - difetto_catena
  - mispick
  - densita_trama
  - liccio
  - subbio
tags:
  - maintenance
  - weaving
  - cleanup
  - post-event
  - technician
audience: maintenance
status: draft-unreviewed
created_in_phase: 2
---

# Pulizia e ripristino telaio post-evento di difettosità seriale

## Scope

Questa SOP descrive la procedura di pulizia sistematica e ripristino delle condizioni operative del **telaio** a seguito di un evento di difettosità seriale: un periodo di produzione in cui si sono verificati **rottura_filo** multipli, **mispick** ripetuti, o **difetto_catena** estesi su un segmento significativo di tessuto (>10 m). L'obiettivo è rimuovere residui di filo, detriti di fibra e depositi di cera o olio accumulati durante l'evento, ripristinare le condizioni meccaniche nominali e verificare la qualità del tessuto prodotto prima di rientrare in produzione normale.

La procedura si applica dopo eventi di difettosità che richiedono fermo macchina per diagnosi (non per la singola **rottura_filo** gestita da SOP-LOOM-001). Non si applica alla manutenzione preventiva programmata: quella segue il piano di manutenzione macchina specifico.

## Prerequisites

- Il **telaio** è in stato di fermo pianificato; l'evento di difettosità è stato documentato nel registro macchina.
- Il tecnico ha identificato la causa primaria dell'evento (tensione, qualità filato, meccanismo) e ha già eseguito la correzione della causa.
- Il reparto qualità è stato allertato per la valutazione del tessuto prodotto durante l'evento.
- DPI completi: guanti antitaglio, occhiali protettivi, maschera antipolvere FFP2.

## Tools and PPE

- Aspiratore per polvere tessile (con filtro HEPA per fibre fini)
- Pennello per pulizia a secco (setole rigide, per rimozione fiocchi)
- Panno privo di pelucchi (per pulizia superfici metalliche)
- Spray di pulizia per componenti tessili (non corrosivo, specifico per metalli e ceramiche)
- Olio lubrificante (tipologia specificata dal costruttore del **telaio**)
- **Calibro_digitale** (per verifica integrità componenti meccanici post-pulizia)
- Guanti antitaglio categoria II
- Occhiali protettivi
- Maschera FFP2 (per polvere di fibra fine)

## Step-by-step Procedure

1. **Documentare lo stato iniziale.** Prima di iniziare la pulizia, fotografare o annotare la posizione e la quantità di residui di filo visibili (fiocchi di fibra, residui di **trama** rotta, accumuli di cera cursore). Questo permette di monitorare l'efficacia della pulizia e correlare accumuli anomali con la causa dell'evento.

2. **Rimuovere i residui grossolani dall'area dei licci.** Con il **telaio** fermo, rimuovere manualmente con pinzette o dita tutti i frammenti di filo visibili nelle maglie del **liccio**, tra i denti del pettine (**cassa_battente**) e nella guida di inserzione **trama**. Non usare aria compressa in questa fase: rischio di disperdere fibre negli organi sensibili.

3. **Aspirare la polvere di fibra accumulata.** Con l'aspiratore HEPA, procedere dall'alto verso il basso: prima la zona del **subbio** di **ordito** e del sistema di svolgimento, poi la zona dei **liccio**, poi la **cassa_battente** e la zona di raccolta tessuto. Attenzione a non aspirare fili tesi di **ordito** che potrebbero rompersi se aspirati.

4. **Pulire il pettine della cassa battente.** Con il pennello a secco, rimuovere i residui di fibra accumulati tra i denti del pettine. Un pettine sporco aumenta l'attrito sulla **trama** e può causare **rottura_filo** di trama e difetti di **densita_trama**. Se i depositi sono ostinati: spruzzare il detergente specifico e pulire con panno privo di pelucchi.

5. **Ispezionare e pulire le maglie dei licci.** Ogni maglia del **liccio** deve scorrere liberamente senza attrito. Residui di fibra incrostati o cera cursore solidificata nelle maglie causano attrito asimmetrico e **rottura_filo** di **ordito** ricorrenti. Pulire con pennello; se la maglia è danneggiata o la superficie di contatto è rugosa, segnalare per sostituzione del **liccio**.

6. **Verificare e lubrificare i punti di lubrificazione previsti.** Identificare i punti di lubrificazione del **telaio** secondo il manuale di manutenzione (tipicamente: cuscinetti del **subbio**, guide di inserzione, meccanismo di cambio passo). Applicare 2-3 gocce di olio lubrificante specificato. Non over-lubrificare: l'olio in eccesso contamina il filo di **ordito** e causa **aloni** sul tessuto.

7. **Verificare l'integrità meccanica dei componenti chiave.** Con il **calibro_digitale**, verificare:
   - Spessore denti del pettine (usura eccessiva causa difetti di **densita_trama**)
   - Stato delle maglie del **liccio** (deformazione riduce la libertà di movimento)
   - Allineamento laterale del **subbio** (tolleranza tipica < 0.5 mm su 2 m di larghezza)
   Segnalare eventuali componenti fuori tolleranza nella lista manutenzione straordinaria.

8. **Eseguire un ciclo di prova e verificare la qualità.** Riavviare il **telaio** a velocità ridotta (60%) per 15 m di tessuto. Eseguire ispezione visiva in continuo del tessuto prodotto: assenza di **difetto_catena**, **mispick**, irregolarità di **densita_trama**. Portare a velocità di regime solo dopo verifica positiva. Registrare i risultati nel log macchina.

## Verification

- L'ispezione visiva delle prime 15 m di tessuto dopo il ripristino non evidenzia **difetto_catena**, **mispick** o irregolarità di **densita_trama** rispetto al tessuto prodotto prima dell'evento.
- Il tasso di **rottura_filo** nei 30 minuti successivi all'intervento non supera la soglia normale dell'articolo.
- Tutti i componenti ispezionati sono entro tolleranza o sono stati segnalati per sostituzione programmata.
- La pulizia eseguita, i componenti ispezionati e l'esito del ciclo di prova sono registrati nel registro macchina.

## Troubleshooting

**La difettosità seriale riprende entro pochi minuti dal riavvio:**
- La causa primaria dell'evento non è stata completamente corretta. Fermare il **telaio** e riesaminare: tensione **ordito** (SOP-LOOM-002), qualità del filo di **trama** in bobina, o anomalia meccanica residua. Non proseguire la produzione se la difettosità si ripresenta con la stessa frequenza.

**Accumulo anomalo di polvere di fibra rilevato durante la pulizia:**
- Un accumulo superiore alla norma per il ciclo di produzione indica un problema di qualità del filato (eccesso di fibre corte, **neps**) o una velocità di produzione troppo elevata per l'articolo in corso. Registrare e segnalare al responsabile di reparto.

**Componente meccanico trovato fuori tolleranza durante la verifica:**
- Non riavviare il **telaio** senza aver eseguito la sostituzione o senza autorizzazione esplicita del responsabile manutenzione. La produzione su un **telaio** con componenti fuori tolleranza genera difettosità strutturale che compromette l'intera partita.

## References

- Glossario IT tessile: [telaio](../../docs/docs/glossary.md#telaio), [liccio](../../docs/docs/glossary.md#liccio), [difetto_catena](../../docs/docs/glossary.md#difetto_catena)
- SOP correlate: SOP-LOOM-001 (rottura filo ordito), SOP-LOOM-002 (deriva tensione ordito), SOP-QLT-001 (ispezione qualita')
- Standard di riferimento: ISO 5247 (terminologia tessile), manuale tecnico costruttore telaio
