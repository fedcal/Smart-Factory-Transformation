---
acl_level: internal
asset: ring spinning frame
asset_family: spinning
audience: maintenance
created_in_phase: 2
estimated_duration_min: 25
hazard_level: low
id: SOP-SPN-004
lang: it
prerequisites:
- SOP-SPN-001
- SOP-SPN-002
related_glossary:
- filatura
- slub
- irregolarita_filato
- neps
- titolo_filato
- filatoio_anello
- stiro
role: technician
status: reviewed
tags:
- quality
- spinning
- slub-control
- monitoring
- technician
title: Monitoraggio e controllo slub nel filatoio ad anello
version: '1.0'
---

# Monitoraggio e controllo slub nel filatoio ad anello

## Scope

Questa SOP descrive la procedura di monitoraggio e controllo della presenza di **slub** nel filo prodotto dal **filatoio_anello**. Lo **slub** e' un ispessimento localizzato del filo causato da una concentrazione di fibre; costituisce un difetto di **filatura** che si manifesta nel tessuto come un rigonfiamento irregolare visibile e classificabile nel sistema di ispezione a quattro punti.

La procedura si applica al monitoraggio in produzione (spot-check periodico con Uster Tester o valutazione visiva) e all'analisi causa quando il tasso di **slub** supera la soglia di accettazione. Non si applica alla produzione di fili artisan-slub (fili volutamente irregolari): quella segue ricette di stiro specifiche.

Lo **slub** eccessivo e' spesso il primo indicatore di problemi di qualita' della materia prima (fibra corta o contaminata) o di usura dei cilindri di **stiro**.

## Prerequisites

- Un campione di filo prelevato dal **filatoio_anello** in produzione e' disponibile per la valutazione.
- Il valore di riferimento di CVm% e **slub** (count/km) per l'articolo in produzione e' disponibile nel foglio articolo.
- Lo Uster Tester (se disponibile) e' calibrato e operativo.
- DPI: guanti da lavoro, occhiali protettivi.

## Tools and PPE

- Uster Tester (analizzatore di regolarita' del filo — se disponibile in laboratorio)
- Bobina di campionamento filo (almeno 200 m di filo per test statisticamente significativo)
- Lente di ingrandimento 5x (per valutazione visiva **slub** in assenza di Uster Tester)
- Lightbox (per ispezione filo su fondo nero o bianco)
- **Calibro_digitale** (per misura spessore **slub** individuali >5 mm)
- Guanti da lavoro
- Occhiali protettivi

## Step-by-step Procedure

1. **Prelevare il campione di filo.** Prelevare una bobina campione direttamente dal **filatoio_anello** in produzione (preferibilmente da 3-5 posizioni distribuite lungo la macchina, per valutare la variabilita' tra posizioni). Registrare il numero di posizione, l'ora di prelievo, il **titolo_filato** e l'articolo in produzione.

2. **Valutazione strumentale con Uster Tester (se disponibile).** Avvolgere il campione sull'organo del Uster Tester e avviare l'analisi (velocita' tipica: 400 m/min per cotone Nm 30-80). Il report fornisce: CVm% (variazione di titolo), indice U%, conta **slub** (count/km) e **neps** (count/km). Confrontare con i valori di riferimento dell'articolo: CVm% <12% per filato pettinato medio, **slub** <5/km per articoli shirting.

3. **Valutazione visiva alternativa (senza Uster Tester).** Avvolgere il filo campione su una cartella di cartone nera (per filo chiaro) o bianca (per filo scuro) a spirali regolari, senza tensione. Ispezionare con lente 5x e lightbox: contare gli **slub** visibili su 10 m di filo e moltiplicare per 100 per ottenere la stima in count/km. Uno **slub** e' classificato come maggiore se il diametro supera 2x il diametro normale del filo (verificare con **calibro_digitale**).

4. **Identificare la distribuzione degli slub.** Verificare se gli **slub** sono concentrati in zone specifiche della macchina (posizioni adiacenti con alto conteggio) o distribuiti uniformemente. Concentrazione zonale indica un problema locale (cilindro di stiro, apron, guida nastro). Distribuzione uniforme indica un problema di materia prima (fibra corta o **neps** eccessivi nel nastro di alimentazione).

5. **Analizzare la causa degli slub in eccesso.** Per concentrazione zonale: ispezionare i **cilindro_stiro** e gli apron delle posizioni interessate (SOP-SPN-002). Verificare se l'apron e' rigido (Shore A > 65) o deteriorato. Per distribuzione uniforme: prelevare un campione di nastro di alimentazione (roving o sliver) e valutarne la regolarita' visiva. Se il nastro e' irregolare: segnalare al reparto carda o pettinatura.

6. **Eseguire l'azione correttiva.** In base alla causa identificata:
   - Problema cilindri/apron: procedere con SOP-SPN-002 (pulizia) per le posizioni interessate.
   - Problema materia prima: mettere in quarantena il lotto di nastro sospetto e notificare il responsabile di produzione per la valutazione dell'approvvigionamento alternativo.
   - Problema parametri stiro (rapporto stiro): correggere i parametri seguendo la scheda tecnica dell'articolo e verificare che il cambiamento sia effettuato in modo coordinato su tutta la macchina.

7. **Verificare il miglioramento.** Dopo l'azione correttiva, prelevare un nuovo campione dalle stesse posizioni. Ripetere la valutazione (strumentale o visiva). Confrontare il count di **slub** pre/post azione: deve mostrare un miglioramento statisticamente significativo (riduzione > 30% del count).

8. **Documentare e segnalare.** Compilare il modulo di controllo qualita' in filatura: data, articolo, posizioni campionate, valori CVm% e **slub** pre/post azione, causa identificata, azione eseguita, firma tecnico. Segnalare al responsabile qualita' se il problema non e' stato risolto dopo l'azione correttiva.

## Verification

- Il count di **slub** post-azione e' entro la soglia di accettazione dell'articolo (<5/km per articoli shirting standard, o valore specifico del foglio articolo).
- Il CVm% post-azione e' conforme al valore di riferimento.
- Nessuna concentrazione zonale di **slub** e' visibile nella valutazione visiva del campione post-azione.
- Il modulo di controllo qualita' e' compilato e archiviato.

## Troubleshooting

**Il count di slub non migliora dopo la pulizia dei cilindri:**
- Verificare la qualita' del nastro di alimentazione: prelevare 5 m di roving e avvolgere su cartella per valutazione visiva. Se il nastro mostra barre periodiche o **neps** visibili: il problema e' a monte del **filatoio_anello** (carda o pettinatrice) e non risolvibile con la manutenzione del filatoio.
- Controllare il **rapporto_stiro** impostato: un rapporto troppo alto per il tipo di fibra causa la frammentazione delle fibre corte in **slub**. Ridurre il rapporto del 5% e reverificare.

**Lo slub e' presente ma solo in una zona ristretta della macchina (3-5 fusi consecutivi):**
- Causa molto probabile: un apron danneggiato o una maglia del guidanastro rotta nella zona specifica. Ispezionare visivamente tutti i componenti dello stadio di stiro nelle posizioni interessate.

**Il Uster Tester segnala slub ma la valutazione visiva non li rileva:**
- Lo Uster Tester rileva **slub** anche con diametro 1.5x il nominale, non visibili ad occhio nudo. Questi sono classificati come "slub thin" e sono comunque rilevanti per il tessuto finale. Procedere con l'analisi causa normalmente.

## References

- Glossario IT tessile: [slub](../../docs/docs/glossary.md#slub), [irregolarita_filato](../../docs/docs/glossary.md#irregolarita_filato), [filatura](../../docs/docs/glossary.md#filatura)
- SOP correlate: SOP-SPN-001 (calibrazione fusi), SOP-SPN-002 (pulizia cilindri stiro), SOP-QLT-002 (rilevamento rottura filo)
- Standard di riferimento: ISO 5247 (terminologia tessile), USTER STATISTICS (riferimenti CVm% per tipo filato)
