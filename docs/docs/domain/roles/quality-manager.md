# Responsabile qualità

Il responsabile qualità supervisiona il sistema di controllo qualità tessile dell'intero sito, dalla ricezione delle materie prime (**titolo_filato** in ingresso) all'accettazione del lotto finito. È proprietario del processo di ispezione 4-point grading, della tassonomia dei difetti e delle decisioni di lotto (accettazione, declassamento, rifiuto). Interagisce con tutti i reparti produttivi e con i fornitori di filato e coloranti.

## Responsabilità

- Definizione e manutenzione degli standard di qualità: tolleranze **delta_e**, **densita_trama**, **irregolarita_filato** per ogni articolo in produzione
- Supervisione dell'**ispezione_rotolo** sul **tavolo_ispezione**: formazione degli ispettori, calibrazione del metodo, gestione delle discrepanze inter-ispettore
- Gestione della tassonomia dei difetti: classificazione sistematica di **mispick**, **slub**, **difetto_catena**, **deviazione_tono**, **aloni**, **screziatura**, **pilling**, **difetto_orlatura**
- Decisione di lotto: accettazione, declassamento seconda scelta, ritintura, rifiuto totale su base dati **delta_e** e punteggio ispezione 4 punti
- Reporting mensile agli stakeholder: **oee** qualità, tasso difetti per articolo, andamento **mttr** ripristino qualità

## Interazione tipica con asset e processi

Il responsabile qualità opera principalmente nel reparto ispezione finale ma interviene upstream quando un difetto sistematico indica un problema di processo. Usa il **spettrofotometro** per la verifica **delta_e** su campioni di tessuto tinto e interagisce con il reparto **tintura** per analizzare cause di **deviazione_tono** tra lotti. Collabora con il tecnico manutentore quando un difetto sistematico (**rigatura**, **difetto_catena**) origina da un guasto meccanico al **telaio** o alla **cassa_battente**.

## Decisione critica giornaliera

La decisione critica è: accettare, declassare o rifiutare un lotto in presenza di misure di **delta_e** o punteggio ispezione ai limiti della tolleranza. Un lotto al limite può essere accettato con waiver del cliente, declassato (vendita a prezzo ridotto), inviato a ritintura o rifiutato. Ogni decisione ha un impatto economico diretto; il responsabile qualità bilancia il rischio di resi vs il costo di ritintura o di perdita del lotto, coordinandosi con la direzione commerciale per i lotti su ordine cliente critico.

## Pain point

- **deviazione_tono** difficile da anticipare — La **deviazione_tono** tra rotoli dello stesso lotto emerge all'**ispezione_rotolo** finale, quando il **bagno_colorante** è già esausto e il rimedio è solo la ritintura; la mancanza di monitoraggio **delta_e** inline durante il ciclo tintoriale è il gap principale.
- Classificazione difetti inconsistente — La classificazione di difetti borderline (**slub** 4 mm vs 5 mm, **pilling** grado 3 vs 3.5) varia tra ispettori; la variabilità inter-ispettore produce decisioni di lotto incoerenti che generano contestazioni dal cliente.
- Tracciabilità **neps** e **irregolarita_filato** in ingresso — La qualità del **titolo_filato** acquistato da fornitori esterni non è sempre verificata all'arrivo; un lotto di filato con **irregolarita_filato** elevata (CVm% >12%) genera difetti **slub** visibili solo dopo tessitura e tintura, quando il danno è già irreversibile.

!!! note "Mantis context"
    La qualità Mantis opera con tolleranza **delta_e** CMC <1.0 per produzione e <0.5 per campionario stagionale destinato a buyer outdoor. L'**ispezione_rotolo** è eseguita al 100% per i lotti destinati al segmento premium; per i lotti standard, campionamento 10%. Il responsabile qualità partecipa al passaggio di consegne del turno notte-mattino per i lotti con waiver in corso.

## Riferimenti

- [Glossario: ispezione_rotolo, delta_e, sistema_quattro_punti, difetto_trama](../glossary.md)
- [Ruolo correlato: Capoturno](shift-supervisor.md)
- [Ruolo correlato: Tecnico manutentore](technician.md)
