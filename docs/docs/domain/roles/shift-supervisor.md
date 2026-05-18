# Capoturno

Il capoturno coordina l'intero turno produttivo (8h), gestendo le priorità di produzione, l'allocazione degli operatori, gli interventi del tecnico manutentore e le comunicazioni con la direzione. È il punto di escalation Tier 2 per tutte le anomalie che l'operatore non riesce a risolvere autonomamente. In un sistema agenticola basato su **hitl**, il capoturno è il referente primario delle interruzioni che richiedono approvazione umana.

## Responsabilità

- Pianificazione e assegnazione degli operatori alle macchine in funzione del piano di produzione giornaliero
- Supervisione dell'**oee** del turno in tempo reale: monitoraggio fermi macchina, **mttr** interventi, avanzamento produzione vs piano
- Gestione delle escalation operative: decide se intervenire con manutenzione correttiva urgente, fermare un lotto, o rinegoziare le priorità con la pianificazione
- Passaggio di consegne strutturato al capoturno successivo: status macchine, anomalie aperte, lotti in corso, ricambi ordinati
- Approvazione delle decisioni **hitl** di Tier 2 generate dalla piattaforma agentica: ordini di manutenzione non pianificati, declassamenti lotto, fermi linea

## Interazione tipica con asset e processi

Il capoturno non opera direttamente sulle macchine ma monitora tutti i processi (**tessitura**, **filatura**, **orditura**, **tintura**, **finissaggio**) tramite il sistema di supervisione. Interagisce con il responsabile qualità per le decisioni sui lotti con **deviazione_tono** o **mispick** sistematici. Coordina il tecnico manutentore per i cambi **subbio** e le calibrazioni pianificate nel turno. Riceve notifiche dalla piattaforma agentica (tramite **nats** o dashboard) per anomalie che superano le soglie di autonomia operatore.

## Decisione critica giornaliera

La decisione critica è: fermare un **telaio** o un impianto di **tintura** in caso di anomalia che supera la soglia di intervento autonomo. Il capoturno valuta l'impatto sul piano di consegna, il rischio di difetti progressivi (es. **rigatura** su lotto in corso) e la disponibilità del tecnico per intervento immediato. Deve bilanciare: consegnare il lotto in ritardo vs consegnare un lotto difettoso, con impatto diverso su cliente e **oee** settimanale.

## Pain point

- Passaggio di consegne — Il passaggio di consegne tra turni è spesso orale o su registro cartaceo; la mancanza di un log strutturato di anomalie, fermi e decisioni causa perdita di contesto e ripetizione di errori tra turni successivi.
- **oee** non visibile in tempo reale — Il capoturno non ha accesso a un cruscotto **oee** aggiornato in tempo reale per macchina; la stima della performance del turno è basata su conta pezzi manuale e confronto con piano, con ritardo di 1-2 ore.
- Sovraccarico decisioni **hitl** — Quando più macchine generano contemporaneamente alert e richieste di approvazione, il capoturno deve gestire un flusso di interruzioni che interrompe il coordinamento ordinario del turno, aumentando il rischio di decisioni affrettate su anomalie critiche come **difetto_catena** o **deviazione_tono**.

!!! note "Mantis context"
    Mantis ha 3 capoturno che si alternano nel ciclo 3×8h. Il turno notte (22-6h) opera con supervisione ridotta: il capoturno coordina da remoto su chiamata per i fermi urgenti. Il passaggio di consegne mattina (6h) è il momento più critico: vengono condivise le priorità lotto, i lotti con waiver qualità e lo stato degli interventi di manutenzione in corso.

## Riferimenti

- [Glossario: hitl, oee, audit_trail](../../glossary.md)
- [Ruolo correlato: Operatore](operator.md)
- [Ruolo correlato: Tecnico manutentore](technician.md)
- [Ruolo correlato: Responsabile qualità](quality-manager.md)
