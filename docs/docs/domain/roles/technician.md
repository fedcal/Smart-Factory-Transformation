# Tecnico manutentore

Il tecnico manutentore è responsabile della manutenzione preventiva e correttiva di tutte le macchine tessili del sito. Opera sia in modalità pianificata (programmi di manutenzione periodica) sia in modalità di emergenza su chiamata dell'operatore o del capoturno. Il tecnico ha competenze meccaniche, elettriche e pneumatiche sui principali asset: **telaio**, **filatoio_anello**, **jet_dyeing** e **impianto_finissaggio**.

## Responsabilità

- Esecuzione dei piani di manutenzione preventiva (calibrazione **fuso**, sostituzione **liccio**, pulizia **carda**, verifica **misuratore_tensione_ordito**)
- Intervento correttivo su guasto: diagnosi, smontaggio, sostituzione componenti, test post-riparazione
- Gestione del magazzino ricambi: verifica disponibilità spare parts critici, segnalazione riordino al capoturno
- Aggiornamento della documentazione di manutenzione: **mtbf**, **mttr** per macchina, registro interventi
- Supporto all'operatore per classificazione di difetti complessi (**difetto_catena**, **screziatura**, **pilling**)

## Interazione tipica con asset e processi

Il tecnico interagisce con tutti i processi produttivi ma dedica il 60-70% del tempo al reparto **tessitura** (cambio **subbio**, calibrazione **liccio**, regolazione **cassa_battente**). Usa il **calibro_digitale** per misurare tolleranze meccaniche e il **durometro** per verificare usura guarnizioni in gomma su **jet_dyeing** e **impianto_finissaggio**. In **filatura**, esegue calibrazione **fuso** ogni 500 ore operative e controlla l'equilibrio degli anelli rotanti con **igrometro** per verificare le condizioni ambientali del reparto.

## Decisione critica giornaliera

La decisione critica del tecnico è: riparare on-the-spot o attendere il fermo programmato. Un guasto al **telaio** durante il turno produttivo può richiedere 30-90 minuti di riparazione; se il componente da sostituire non è a magazzino, il fermo si prolunga. Il tecnico decide se tentare un workaround temporaneo (riduzione velocità, bypass sensore non critico) per completare il turno, oppure se fermare definitivamente e attendere il ricambio. La soglia è: se il rischio di danni secondari è alto (es. **difetto_catena** progressivo su ordito), si ferma.

## Pain point

- Diagnosi su guasto intermittente — I guasti intermittenti al sistema di rilevamento **rottura_filo** o al sistema di controllo **densita_trama** sono i più difficili da diagnosticare; il tecnico deve replicare le condizioni di guasto durante il turno, con il rischio di produrre scarti nel frattempo.
- Disponibilità spare parts — La mancanza di ricambi critici (anelli **filatoio_anello**, ugelli **jet_dyeing**) è la causa principale di **mttr** elevato; il sistema di gestione ricambi è spesso manuale e soggetto a errori di stock.
- Documentazione interventi — La compilazione del registro manutenzione è percepita come burocrazia; la mancanza di dati storici strutturati rende impossibile il calcolo affidabile di **mtbf** e **mttr** per macchina, penalizzando la pianificazione manutenzione predittiva.

!!! note "Mantis context"
    Il team manutenzione Mantis è composto da 3-4 tecnici che coprono turni mattino e pomeriggio; il turno notte è coperto in reperibilità. Le macchine critiche (telai rapier) hanno **mtbf** target di 150 ore e **mttr** target di 1.5 ore. La manutenzione del sabato mattina è il momento di intervento programmato per cambi **subbio** multipli e calibrazioni **fuso**.

## Riferimenti

- [Glossario: telaio, filatoio_anello, mtbf, mttr](../../glossary.md)
- [Ruolo correlato: Operatore](operator.md)
- [Ruolo correlato: Capoturno](shift-supervisor.md)
