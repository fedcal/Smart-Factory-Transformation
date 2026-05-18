# Integration Tests — IT/OT Simulation Layer (Phase 3)

Test di integrazione per la verifica runtime del data-diode (D-51), del roundtrip E2E
sim-textile → ot-bridge → NATS → TimescaleDB, e della gerarchia subject NATS (D-52).

## Prerequisiti

- Docker disponibile e avviato (`docker info` deve ritornare exit 0)
- Stack IT/OT avviato: `make up-it-ot` (prima esecuzione richiede ~3-5 min per build immagini)
- Migration TimescaleDB applicata: `make migrate-timescale`
- NATS streams bootstrapped: `make bootstrap-nats`

## Avvio rapido

```bash
# Avvia tutto in un solo comando (up + migrate + bootstrap + test + down)
make integration-test

# Solo smoke load (IOT-10 gate)
make smoke-load
```

## Elenco test

| File | Req. | Cosa verifica |
|------|------|---------------|
| `test_data_diode.py` | IOT-05 | D-51 3-layer: Layer 1 container fake-agent su sft-core NON raggiunge sim-textile; Layer 2 host-side pytest; Layer 3 grep static analysis |
| `test_opcua_browseable.py` | IOT-02 | OPC-UA server ha ≥5 namespace `urn:mantis:<family>`, variabile non-writable (protocol-level diode) |
| `test_nats_subjects.py` | IOT-04 | JetStream stream `SENSOR_EVENTS` esiste; subject format `sensor.events.<family>.<asset_id>.<tag_id>` verificato |
| `test_e2e_sim_to_timescale.py` | IOT-06 | Roundtrip sim → bridge → NATS → Timescale: ≥1 row in `sensor_events` entro 1 minuto |

## Smoke load test

| File | Req. | Scenario |
|------|------|----------|
| `../load/test_ingestion_smoke.py` | IOT-10 | 1k msg/s × 10s; assert p99 < 200ms |

## Note sugli edge case

### D-51 Layer 1 (Docker network ACL)

Il test `test_layer1_agent_cannot_reach_sim_via_it_network` lancia un container temporaneo
`python:3.12-slim` sulla rete `sft-core` e tenta di aprire una sessione OPC-UA verso
`sft-sim-textile:4840`. La connessione deve fallire (hostname non risolvibile O timeout) in
quanto `sim-textile` è solo su `sft-ot`.

**GitHub Actions context:** In CI i test girano nello stesso docker daemon del runner
(docker-in-docker non richiesto — `ubuntu-latest` ha docker disponibile). Il container
fake-agent usa `--network sft-core` che è definito dalla `docker compose up` precedente.

### D-51 Layer 2 (caveat A5 — Docker DNS shared)

Il Layer 2 (`test_layer2_agent_cannot_open_opcua_session`) verifica da host pytest che
`sft-sim-textile:4840` non sia raggiungibile. Su alcuni sistemi Docker condivide il DNS
interno con l'host (`127.0.0.11` resolver), il che potrebbe far risolvere il nome. Se il
test Layer 2 passa inaspettatamente (senza timeout), il Layer 1 (container-based) rimane
il gate primario. Il Layer 3 (grep static analysis) è indipendente dall'ambiente runtime.

Fonte: RESEARCH.md §Pitfall 4, Assumption A5.

### Isolamento dei test

Ogni test dipende dalla fixture `compose_stack` (session-scoped in `tests/conftest.py`)
che gestisce il ciclo di vita docker compose. I test non avviano né fermano il compose
individualmente — questo è responsabilità della fixture.
