# Tessitura

La **tessitura** è il processo di interlacciamento dei fili di **ordito** e di **trama** per produrre il tessuto piatto. Il **telaio** è la macchina centrale: i fili di **ordito** disposti sul **subbio** vengono incrociati con i fili di **trama** inseriti dal meccanismo di inserzione, compattati dalla **cassa_battente** fino alla **densita_trama** programmata.

## Process flow

```mermaid
flowchart LR
    accDescr: "Flusso tessitura: subbio ordito alimenta il telaio, i licci formano il passo, la cassa battente compatta la trama, il tessuto grezzo esce sul rotolo."
    A[Subbio ordito] --> B[Apertura passo - licci]
    B --> C[Inserzione trama]
    C --> D[Battuta - cassa battente]
    D --> E[Tessuto grezzo]
    E --> F[Controllo rottura filo]
    F --> G[Avvolgimento rotolo]
```

## Asset coinvolti

- **telaio** — Picanol OptiMax / Toyota JAT810 a rapier; parametri operativi: 600-900 picks/min, tensione ordito 10-30 N per cotone medio
- **subbio** — Cilindro di svolgimento ordito; capacità tipica 600-1200 m di ordito in cotone Nm 40-60
- **liccio** — Cornici metalliche con maglie per la formazione del passo; numero cornici 4-16 in funzione dell'armatura
- **cassa_battente** — Meccanismo oscillante per compattazione trama; frequenza 10-15 Hz correlata a velocità picks/min
- **conta_trama** — Dispositivo ottico per verifica **densita_trama** ogni 10 cm di tessuto

## KPI

- **oee** (%) — range tipico 65-75% in tessitura europea; formula: Disponibilità × Prestazione × Qualità
- **densita_trama** (picks/cm) — range 18-32 picks/cm per tessuti cotone-lana standard; formula: conteggio fili trama per cm
- **mtbf** (ore) — range 80-200 ore per telaio rapier moderno; indica affidabilità intrinseca macchina
- **mttr** (ore) — range 0.5-2 ore per **rottura_filo** e **mispick**; misura efficienza manutenzione correttiva

## Pain point

- **rottura_filo** frequente — Un tasso superiore a 5 **rottura_filo**/ora/**telaio** segnala problemi di tensione o qualità **titolo_filato**; ogni arresto comporta perdita di efficienza e rischio di **difetto_catena** se il rincorso non è preciso.
- Variabilità **densita_trama** — Fluttuazione della **densita_trama** anche di ±1 pick/cm causa difetti di densità e righe orizzontali (**rigatura**) visibili nell'ispezione finale; origine spesso nel meccanismo della **cassa_battente**.
- **mispick** ricorrente — Un **mispick** ogni 10 m è al limite dell'accettabilità; il difetto richiede declassamento del rotolo o riparazione manuale, con impatto diretto sull'**oee** del reparto.
- Cambio **subbio** non pianificato — La sostituzione del **subbio** richiede 30-60 minuti di fermo macchina; la pianificazione preventiva del cambio **subbio** è critica per mantenere l'**oee** nelle finestre di turno.

!!! note "Mantis context"
    Mantis tesse principalmente blend cotone/lana (70/30) e cotone/lino per il segmento outdoor. La **densita_trama** target è 22-26 picks/cm. I telai operano su turni 3×8h; il sabato mattina è dedicato a manutenzione preventiva e cambio subbio programmato. Il rumore in reparto supera i 98 dB(A): gli **otoprotettori** SNR 30 dB sono obbligatori.

## Riferimenti

- [Glossario: tessitura, telaio, subbio, densita_trama](../../glossary.md)
- [Procedure SOP — Loom](../../sop/index.md)
