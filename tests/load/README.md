# IT/OT Load Tests — tests/load/

Load test harness per la pipeline di ingest NATS JetStream → TimescaleDB (Phase 3 IOT-10).

## Test disponibili

### Smoke (1k×10s) — sempre in CI

| Attributo   | Valore               |
|-------------|----------------------|
| File        | `test_ingestion_smoke.py` |
| Rate target | 1.000 msg/s          |
| Durata      | 10 secondi           |
| Threshold   | p99 < 200ms (IOT-10) |
| Marker      | `@pytest.mark.load_smoke` |
| CI          | Sempre eseguito (step "Run IT/OT load test (smoke 1k×10s)") |

**Esecuzione locale:**
```bash
make smoke-load
# oppure:
uv run pytest tests/load/test_ingestion_smoke.py -v -m load_smoke
```

---

### Full (5k×60s) — gated da PR-label o flag

| Attributo       | Valore                           |
|-----------------|----------------------------------|
| File            | `test_ingestion_throughput.py`   |
| Rate target     | 5.000 msg/s                      |
| Durata          | 60 secondi steady-state (NO ramp-up) |
| Threshold       | p99 < 200ms + ≥285.000 eventi (IOT-10 full) |
| Marker          | `@pytest.mark.load_full`         |
| CI              | Gated da PR-label `load-test`    |
| Runtime stimato | ~75s su GitHub Actions standard runner (4 CPU / 16GB RAM) |

**Esecuzione locale:**
```bash
make load-test-full
# oppure:
uv run pytest tests/load/test_ingestion_throughput.py -v -m load_full --full-load-test
```

**Esecuzione in CI:** aggiungere il label `load-test` alla PR. Il workflow CI eseguirà
automaticamente il test e stamperà il report nella log:

```
FULL LOAD: total=300213, p50=12ms, p99=87ms, rate=5003/s
```

---

## Asset mix D-48

Il full test usa il mix asset realistico specificato in D-48:

| Family    | Quota | Asset (Phase 3) | Tag per asset | Rate stimato |
|-----------|-------|-----------------|---------------|--------------|
| Loom      | 60%   | 12 LOOM         | 5             | ~3.000 msg/s |
| Spinning  | 20%   | 8 SPIN          | 5             | ~1.000 msg/s |
| Dyeing    | 10%   | 4 DYE           | 6             |   ~500 msg/s |
| Finishing | 5%    | 2 STEN          | 6             |   ~250 msg/s |
| Warping   | 5%    | 4 WARP          | 5             |   ~250 msg/s |

**Nota amplificazione Phase 3:** il registry contiene 30 asset reali (non 100 telai come in produzione).
Il harness amplifica pubblicando round-robin sugli stessi asset_id per raggiungere il rate target.
Questo è valido per misurare il bottleneck I/O TimescaleDB, NON per simulare 100 telai reali.

---

## Payload e vincoli

- **Payload:** 256-512 byte JSON `{asset_id, asset_family, tag_id, timestamp_utc, value, unit, quality_code, source, server_received_ts}`
- **Steady-state:** nessun ramp-up — il sistema deve essere stabile dal secondo zero
- **Harness:** custom asyncio nativo (asyncpg.Pool min=10 max=20, statement_cache_size=0)
- **NO Locust/k6:** overhead HTTP non realistico vs NATS native path (D-48)

---

## Threshold IOT-10

| Metrica              | Threshold   | Note                                        |
|----------------------|-------------|---------------------------------------------|
| p99 ingest latency   | < 200ms     | Misura worst-case oldest event dal DB       |
| Total events         | >= 285.000  | 95% del target (5000/s × 60s × 0.95)       |

Se p99 >= 200ms: documentare in PR description + considerare COPY batch fallback
(RESEARCH §Pattern 4 — asyncpg binary COPY ~10x superiore a executemany).

---

## Architettura harness

```
Publisher harness (asyncio)
│
├── NATS JetStream publish
│   └── subject: sensor.events.<family>.<asset_id>.<tag_id>
│
├── ot-bridge (servizio Docker)
│   └── subscribe NATS → asyncpg batch write → TimescaleDB
│
└── Misura p99:
    SELECT oldest_ms FROM sensor_events WHERE timestamp_utc > start_dt
    (worst-case lag = p99 approssimato lato publisher)
```
