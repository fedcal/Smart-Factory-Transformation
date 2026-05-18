---
id: SOP-DYE-004
title: Verifica solidita' colore a lavaggio e sfregamento
version: "1.0"
lang: it
asset: jet dyeing machine
asset_family: dyeing
role: quality-manager
hazard_level: low
estimated_duration_min: 90
prerequisites:
  - SOP-DYE-001
  - SOP-DYE-003
related_glossary:
  - solidita_colore
  - delta_e
  - spettrofotometro
  - tintura
  - deviazione_tono
tags:
  - dyeing
  - fastness
  - quality
  - quality-manager
audience: quality
status: draft-unreviewed
created_in_phase: 2
---

# Verifica solidita' colore a lavaggio e sfregamento

## Scope

Questa SOP descrive le procedure di test della **solidita_colore** per i tessuti tinti, con focus sui test di solidita' al lavaggio (ISO 105-C06) e allo sfregamento (ISO 105-X12). La **solidita_colore** misura la resistenza del colore alle sollecitazioni fisiche e chimiche durante l'uso del tessuto e ne determina l'idoneita' al mercato di destinazione.

La procedura si applica ai test di accettazione di lotto (campione per ogni lotto tintoriale) e ai test di sviluppo colore in laboratorio. Non si applica ai test di solidita' alla luce (ISO 105-B02) che richiedono apparecchiature specifiche (Xenotest): quelli seguono una procedura separata.

Il mancato rispetto delle soglie minime di **solidita_colore** causa il rifiuto del lotto e impone la rettifica tintoriale o il declassamento dell'articolo.

## Prerequisites

- Il campione di tessuto tinto e' asciutto e condizionato (ISO 139: 65±5% RH, 20±2°C, minimo 4 ore).
- I tessuti di accompagnamento multi-fibra (ISO 105-F10 o equivalente) sono disponibili in laboratorio.
- Lo **spettrofotometro** e' calibrato.
- Il laboratorio dispone di apparecchiatura di lavaggio standard (Launder-Ometer o apparecchiatura conforme ISO 105-C06) e del dinamometro a sfregamento (Crockmeter ISO 105-X12).
- Detersivo di riferimento ISO (IEC-A o ECE senza agente sbiancante ottico, a seconda del test).

## Tools and PPE

- Apparecchiatura di lavaggio ISO 105-C06 (Launder-Ometer o equivalente)
- Crockmeter ISO 105-X12 (manuale o motorizzato)
- **Spettrofotometro** da banco per misurazione **delta_e** post-test
- Scala dei grigi ISO 105-A02 (per valutazione visiva della perdita di colore e dello staining)
- Bilancia di precisione (0.01 g) per pesata detersivo
- Termometro di controllo vasca (per verifica temperatura lavaggio)
- Forbici, ago e filo per la preparazione degli assemblati
- Guanti in lattice (per evitare contaminazione da sebo durante la preparazione campioni)

## Step-by-step Procedure

1. **Preparare il campione composito per il test di solidita' al lavaggio.** Ritagliare un campione di 10×4 cm dal tessuto in esame. Cucire un tessuto di accompagnamento multi-fibra ISO 105-F10 (o due tessuti mono-fibra secondo la norma: uno del substrato principale, uno in cotone) al campione lungo uno dei lati da 4 cm. Il campione composito ha dimensioni totali 10×10 cm.

2. **Eseguire il test di lavaggio ISO 105-C06.** Inserire il campione composito in una capsula Launder-Ometer con la soluzione detergente standard (concentrazione per il metodo selezionato — tipicamente C1S: 4 g/L ECE senza OBA, 40°C, 30 minuti, 10 sfere di acciaio). Avviare il ciclo. Al termine: risciacquare in acqua fredda e asciugare i componenti separati (campione principale + tessuto di accompagnamento) su piano piatto a temperatura ambiente.

3. **Valutare la perdita di colore sul campione principale.** Confrontare il campione post-lavaggio con un campione non lavato dello stesso tessuto sotto luce D65. Valutare usando la scala dei grigi ISO 105-A02: un punteggio di 4-5 indica solidita' buona; 3 e' il limite minimo accettabile per la maggior parte degli articoli di abbigliamento; 1-2 indica solidita' insufficiente.

4. **Valutare lo staining sul tessuto di accompagnamento.** Confrontare ogni striscia del tessuto di accompagnamento con un campione non trattato dello stesso tessuto. Valutare lo staining (cessione colore) usando la scala dei grigi o la scala degli staining (scala cromata) ISO 105-A03: un punteggio ≥3 sul cotone e' il limite minimo per articoli da abbigliamento.

5. **Misurare il delta_e strumentale post-lavaggio.** Con lo **spettrofotometro**, misurare il **delta_e** tra campione pre-lavaggio e post-lavaggio. Il valore strumentale integra la valutazione visiva della scala dei grigi e riduce la soggettivita'. Un **delta_e** CMC <1.0 post-lavaggio indica solidita' eccellente; 1.0-2.0 accettabile; >2.0 non conforme per articoli standard.

6. **Eseguire il test di solidita' allo sfregamento ISO 105-X12.** Montare il campione di tessuto (10×4 cm) sul Crockmeter con il tessuto da esaminare teso e piatto. Eseguire il test a secco (tessuto sfregante in cotone asciutto, condizionato) e il test a umido (tessuto sfregante inumidito: 100% acqua distillata, peso 9 N, 10 cicli di sfregamento in 10 secondi). Valutare lo staining sul tessuto di accompagnamento con la scala dei grigi: minimo accettabile grado 3 a secco, grado 2-3 a umido.

7. **Compilare il rapporto di solidita' colore.** Per ogni lotto testato, compilare la scheda: articolo, numero lotto, data, metodo di test, valori scala dei grigi (perdita colore + staining), **delta_e** strumentale, esito (CONFORME / NON CONFORME), firma. Archiviare nel sistema qualita'.

8. **Comunicare l'esito e avviare azioni correttive se necessario.** Se il test e' CONFORME: allegare il rapporto al bollettino di rilascio lotto. Se NON CONFORME: comunicare immediatamente al responsabile tintoria, bloccare il lotto e avviare l'analisi causa: scelta del colorante errata, fissaggio incompleto, saponaggio insufficiente post-tintura.

## Verification

- Il campione post-lavaggio ha punteggio scala dei grigi ≥3 per perdita colore e ≥3 per staining su cotone.
- Il **delta_e** CMC post-lavaggio e' <2.0 per articoli standard, <1.0 per articoli premium.
- Il test a sfregamento mostra staining ≥3 a secco e ≥2 a umido sulla scala dei grigi.
- Il rapporto di **solidita_colore** e' archiviato e allegato alla documentazione di lotto.

## Troubleshooting

**La solidita' al lavaggio e' insufficiente (scala dei grigi <3) per coloranti reattivi:**
- La causa piu' probabile e' un saponaggio post-tintura insufficiente: il colorante reattivo non fissato rimane sulla fibra e cede al primo lavaggio. Ripetere il ciclo di saponaggio (bagno fresco 90°C, 15 minuti, con 1-2 g/L di detergente non ionico) e ri-testare.
- Se la solidita' rimane insufficiente dopo saponaggio ripetuto: la causa e' probabilmente nel colorante o nella temperatura di fissaggio. Consultare il fornitore del colorante.

**Lo staining e' elevato sul tessuto di accompagnamento in poliestere (>grado 2):**
- Per tessuti misti con coloranti disperse per la componente sintetica: verificare che il ciclo di riduzione del colorante non fissato (reduction clearing) sia stato eseguito correttamente. I coloranti disperse non rimossi causano staining elevato su poliestere.

**Il risultato e' borderline (grado 3-) e la valutazione e' incerta:**
- Eseguire la valutazione da parte di un secondo ispettore qualificato indipendentemente e calcolare la media arrotondata. In caso di discordanza, applicare il punteggio inferiore.

## References

- Glossario IT tessile: [solidita_colore](../../docs/docs/glossary.md#solidita_colore), [delta_e](../../docs/docs/glossary.md#delta_e), [tintura](../../docs/docs/glossary.md#tintura)
- SOP correlate: SOP-DYE-001 (preparazione bagno colorante), SOP-DYE-003 (verifica tono lotto), SOP-QLT-004 (report deviazione tonale)
- Standard di riferimento: ISO 105-C06 (solidita' lavaggio), ISO 105-X12 (solidita' sfregamento), ISO 105-A02 (scala dei grigi)
