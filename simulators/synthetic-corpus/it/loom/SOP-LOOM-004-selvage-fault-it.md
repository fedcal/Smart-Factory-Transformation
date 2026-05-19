---
acl_level: internal
asset: telaio
asset_family: weaving
audience: maintenance
created_in_phase: 2
estimated_duration_min: 35
hazard_level: low
id: SOP-LOOM-004
lang: it
prerequisites:
- SOP-LOOM-001
- SOP-LOOM-002
related_glossary:
- telaio
- tessitura
- cimosa
- difetto_orlatura
- liccio
- ordito
- densita_trama
role: technician
status: reviewed
tags:
- troubleshooting
- weaving
- selvage
- technician
title: Diagnosi e ripristino difetto di cimosa su telaio rapier
version: '1.0'
---

# Diagnosi e ripristino difetto di cimosa su telaio rapier

## Scope

Questa SOP descrive la procedura diagnostica e correttiva per i **difetto_orlatura** (selvage fault) su un **telaio** a rapier. Il difetto di **cimosa** si manifesta come irregolarità ai bordi laterali del tessuto: orlatura allentata, fili di **ordito** bordo non interlacciati correttamente, irregolarità di **densita_trama** ai margini, oppure bordo sfilacciato dopo il taglio dell'orlatura.

La procedura è destinata al tecnico di reparto, in quanto richiede la regolazione dei licci bordo, del meccanismo di orlatura e dei tensionatori laterali. Non si applica a difetti di orlatura causati da problemi del sistema di taglio cimosa (tucking device): in quel caso seguire la procedura specifica macchina del costruttore.

Il **difetto_orlatura** prolungato su più di 2 m continuativi causa declassamento del rotolo; l'identificazione precoce e la correzione tempestiva sono critiche.

## Prerequisites

- Il **telaio** è in stato di fermo pianificato (preferibilmente durante cambio turno o cambio articolo).
- Il tecnico ha accesso alla documentazione tecnica (manuale del costruttore, parametri di regolazione liccio bordo).
- I valori di tensione **ordito** bordo sono reperibili dal foglio articolo (MES o cartaceo).
- DPI: guanti antitaglio, occhiali protettivi.

## Tools and PPE

- Torcia di ispezione LED
- **Calibro_digitale** (per verifica passo **liccio** bordo e tensione fili orlatura)
- Chiave di regolazione tensione laterale (specifica macchina)
- Specchio di ispezione angolato (per verifica zona difficile di accesso)
- Guanti antitaglio categoria I
- Occhiali protettivi

## Step-by-step Procedure

1. **Ispezionare il bordo tessuto sul rotolo in produzione.** Prima di fermare la macchina, osservare i 2-3 m di tessuto già avvolto nel rotolo per caratterizzare il difetto: regolare o casuale, monolaterale o bilaterale, associato a specifici **liccio** o esteso sull'intera larghezza della cimosa. Fotografare o annotare la tipologia.

2. **Fermare il telaio in posizione di diagnosi.** Portare il **telaio** in posizione di fermata con il passo aperto (metà ciclo) per avere visibilità sui licci bordo e sui fili di **ordito** della cimosa. Usare la funzione jog per posizionare la macchina.

3. **Ispezionare i fili di ordito di cimosa.** Verificare visivamente la tensione dei fili di **ordito** bordo rispetto ai fili centrali. Un'asimmetria di tensione visibile (fili bordo più laschi o più tesi degli adiacenti) indica un problema di regolazione tensionatore bordo o un filo di **ordito** bordo con titolo diverso.

4. **Verificare i licci bordo (temple e liccio cimosa).** Controllare le maglie del **liccio** dedicato alla cimosa: maglie danneggiate o segate dal filo di **ordito** generano attrito asimmetrico e causano il **difetto_orlatura**. Sostituire le maglie danneggiate.

5. **Controllare il dispositivo di orlatura (tucking device o temple).** Verificare che il temple (pressore laterale del tessuto) eserciti una pressione uniforme su entrambi i bordi. Una pressione ridotta causa sfilacciatura del bordo; una pressione eccessiva causa irregolarità di **densita_trama** ai margini. Regolare secondo i valori del manuale.

6. **Regolare la tensione dei fili di cimosa.** Identificare il tensionatore bordo specifico (solitamente un sistema a molla o peso separato dal tensionatore principale). Regolare incrementalmente (5% alla volta) e misurare la tensione con il **calibro_digitale** applicato ai fili bordo. Target: tensione bordo non superiore a +20% rispetto alla tensione media dell'ordito centrale.

7. **Eseguire un ciclo di prova a velocità ridotta.** Riavviare il **telaio** a velocità ridotta (60% della velocità nominale) per 20 m di tessuto. Ispezionare il bordo prodotto: la **cimosa** deve essere uniforme, senza allentamento o sfilacciatura. Se il difetto persiste: ripetere la diagnosi dal punto 3.

8. **Riprendere la produzione a velocità normale e registrare.** Portare il **telaio** a velocità di regime dopo la verifica positiva a velocità ridotta. Annotare sul registro macchina: tipo di difetto, causa identificata, regolazione effettuata, tecnico, data.

## Verification

- Ispezione visiva dei 10 m di tessuto prodotti dopo l'intervento: il bordo della **cimosa** è uniforme, senza allentamento, sfilacciatura o irregolarità di **densita_trama** ai margini.
- La tensione dei fili di **ordito** bordo rientra entro +20% rispetto alla tensione media dei fili centrali (verificata con lo strumento tensiometro).
- Il **difetto_orlatura** non si ripresenta nei 30 minuti successivi all'intervento.
- L'intervento è registrato nel registro macchina con causa identificata e azione correttiva.

## Troubleshooting

**Il difetto di cimosa persiste dopo la regolazione del tensionatore bordo:**
- Verificare se il filo di **ordito** bordo ha un titolo diverso da quelli centrali (errore in fase di orditura). Misurare con **calibro_digitale**: se la differenza è >10% del titolo nominale, il problema è a monte (orditura) e non risolvibile in fase di **tessitura** senza cambio subbio.
- Controllare che il numero di fili di **ordito** nella cimosa corrisponda ai parametri dell'articolo in produzione.

**Sfilacciatura continua del bordo anche dopo regolazione del temple:**
- Ispezionare il dispositivo di taglio cimosa (knife o tucking needle): una lama usurata o un ago piegato causa irregolarità di taglio che si manifesta come sfilacciatura. Sostituire la lama o l'ago.
- Verificare che l'orlatura venga effettuata correttamente da entrambi i lati (problema unilaterale vs bilaterale aiuta a isolare il lato difettoso).

**Difetto orlatura solo su un lato, non sull'altro:**
- Problema probabilmente monolaterale nel tensionatore bordo o nel liccio cimosa di un solo lato. Ripetere la diagnosi concentrandosi sul lato affetto.

## References

- Glossario IT tessile: [cimosa](../../docs/docs/glossary.md#cimosa), [difetto_orlatura](../../docs/docs/glossary.md#difetto_orlatura), [liccio](../../docs/docs/glossary.md#liccio)
- SOP correlate: SOP-LOOM-001 (rottura filo ordito), SOP-LOOM-002 (deriva tensione ordito), SOP-QLT-001 (ispezione qualita' tessuto)
- Standard di riferimento: ISO 5247 (terminologia tessile), manuale tecnico costruttore telaio
