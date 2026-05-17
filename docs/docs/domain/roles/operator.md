# Operatore

L'operatore è la figura di front-line che gestisce le macchine tessili (telai, filatoi, orditrici) nel corso del turno produttivo. Il suo ruolo è garantire la continuità della produzione, rilevare anomalie e decidere quando escalare l'intervento al tecnico manutentore. L'operatore interagisce direttamente con il HMI della macchina e con il sistema di monitoraggio basato su **opc_ua**.

## Responsabilità

- Avvio, conduzione e supervisione delle macchine assegnate al turno (telai, filatoi, orditrici)
- Monitoraggio continuo dei parametri operativi (tensione **ordito**, **densita_trama**, **irregolarita_filato**) tramite HMI e pannelli di controllo
- Rilevamento e classificazione dei difetti tessili (**rottura_filo**, **mispick**, **slub**, **neps**) durante la produzione
- Esecuzione delle manovre di rincorso filo e riallineamento **subbio** in caso di arresto macchina
- Compilazione del registro produzione turno: pezzi prodotti, fermi, anomalie, consumo **subbio**

## Interazione tipica con asset e processi

L'operatore lavora principalmente sui processi di **tessitura** e **filatura**. Interagisce con il **telaio** tramite HMI per impostare o leggere i parametri di **densita_trama** e velocità picks/min. Sul processo di **orditura**, verifica la tensione **ordito** sul **misuratore_tensione_ordito** e segnala anomalie al tecnico. Usa il **conta_trama** per verificare spot-check di densità durante il turno. In caso di difetto **mispick** o **difetto_catena** prolungato, contatta il capoturno per valutare l'arresto del lotto.

## Decisione critica giornaliera

La decisione critica dell'operatore è: fermare il **telaio** o continuare la produzione in presenza di **rottura_filo** o difetto nascente. Fermare costa tempo e abbassa l'**oee** del turno; non fermare rischia di amplificare il difetto su decine di metri di tessuto, portando a declassamento del rotolo. La regola pratica in uso è: se la **rottura_filo** supera 3 occorrenze in 15 minuti sullo stesso **telaio**, l'operatore ferma e allerta il tecnico; sotto soglia, rincorre e segnala nel registro.

## Pain point

- Rumore in reparto — Il livello sonoro in reparto **tessitura** supera i 95-105 dB(A); gli **otoprotettori** riducono la comunicazione verbale tra operatori, aumentando il rischio di errori nel coordinamento del turno.
- Diagnosi **rottura_filo** frequente — L'operatore è il primo a identificare la causa della **rottura_filo** (tensione, qualità **titolo_filato**, usura anello); senza strumenti di supporto diagnostico, la classificazione è empirica e inconsistente tra operatori diversi.
- Accesso a dati storici macchina — L'operatore non ha accesso diretto ai trend di **oee** e **mttr** per macchina; deve fare affidamento sul registro cartaceo o sulla memoria del turno precedente per contestualizzare le anomalie.

!!! note "Mantis context"
    Gli operatori Mantis gestiscono mediamente 4-6 telai rapier per turno nel reparto tessitura. Il turno mattutino (6-14h) include il passaggio a caldo delle istruzioni di produzione dal capoturno notte. L'esperienza media è 3-8 anni; il know-how sulle ricette di tensione **ordito** per blend cotone/lana è prevalentemente tacito e non documentato.

## Riferimenti

- [Glossario: operatore, telaio, rottura_filo, oee](../glossary.md)
- [Ruolo correlato: Tecnico manutentore](technician.md)
- [Ruolo correlato: Capoturno](shift-supervisor.md)
