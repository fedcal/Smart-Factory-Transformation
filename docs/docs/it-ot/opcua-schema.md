# Schema OPC-UA

Documentazione del namespace OPC-UA del simulatore `sim-textile` (Phase 3).

**Riferimento:** `simulators/sim-textile/` — OPC-UA server asyncua `asyncua.Server`

---

## Endpoint

| Attributo       | Valore                                       |
|-----------------|----------------------------------------------|
| URI endpoint    | `opc.tcp://sim-textile:4840/sft-textile/`    |
| Hostname        | `sim-textile` (nome servizio Docker, rete `ot-network`) |
| Porta           | `4840` (OPC-UA standard)                     |
| Discovery URL   | `opc.tcp://sim-textile:4840`                 |

!!! warning "Accesso limitato alla ot-network"
    L'endpoint OPC-UA è accessibile **solo** da `ot-bridge` sulla rete Docker `ot-network`.
    I client sulla rete `it-network` (agenti, strumenti) non possono raggiungere direttamente
    il server OPC-UA — questo è il comportamento atteso del data-diode (D-51).

---

## Security policy (A-018)

| Attributo        | Valore PoC Phase 3               | Target Phase 11               |
|------------------|----------------------------------|-------------------------------|
| Security Policy  | `NoSecurity`                     | `Basic256Sha256`              |
| Message Security | None                             | `SignAndEncrypt`              |
| Authentication   | Anonymous (nessuna credenziale)  | X.509 certificate             |
| Motivazione PoC  | A-018: ambiente simulato, nessun dato reale | Phase 11 security hardening |

!!! note "Assumption A-018"
    La policy `NoSecurity` è esplicita per il PoC Phase 3. L'hardening a
    `Sign+Encrypt` con certificati X.509 è pianificato in Phase 11 (deployment
    su infrastruttura reale).

---

## Namespace pattern

5 namespace registrati, uno per famiglia di asset:

| Namespace URI              | Famiglia    | Indice NS |
|----------------------------|-------------|-----------|
| `urn:mantis:loom`          | loom        | 2         |
| `urn:mantis:spinning`      | spinning    | 3         |
| `urn:mantis:warping`       | warping     | 4         |
| `urn:mantis:dyeing`        | dyeing      | 5         |
| `urn:mantis:finishing`     | finishing   | 6         |

**BrowsePath:** `<family>/<asset_id>/<tag_id>`

Esempi:

```
loom/LOOM-01/warp_tension
loom/LOOM-01/pick_density
spinning/SPIN-01/spindle_speed
dyeing/DYE-01/bath_temperature
finishing/STEN-01/fabric_tension
```

---

## Variable nodes

Ogni tag è esposto come variable node OPC-UA:

| Attributo        | Valore                                             |
|------------------|----------------------------------------------------|
| `NodeId`         | `ns=<family_ns_idx>;s=<asset_id>/<tag_id>`         |
| `BrowseName`     | `<ns_idx>:<tag_id>`                                |
| `VariantType`    | `Double` (tutti i tag numerici)                    |
| `Writable`       | `False` — data-diode protocol-level (D-51 Layer 0) |
| `AccessLevel`    | `CurrentRead` (0x01)                               |
| `UserAccessLevel`| `CurrentRead` (0x01)                               |

!!! info "Data-diode Layer 0"
    La proprietà `Writable = False` a livello di variable node è il Layer 0 del
    data-diode (D-51). L'enforcement completo usa 3 layer:
    Layer 1 (Docker network ACL) + Layer 2 (pytest) + Layer 3 (grep static-analysis).

---

## Esempio Python client

```python
import asyncio
import asyncua

async def read_warp_tension() -> float:
    async with asyncua.Client("opc.tcp://sim-textile:4840/sft-textile/") as client:
        # Recupera l'indice del namespace loom
        ns_idx = await client.get_namespace_index("urn:mantis:loom")

        # Naviga la gerarchia BrowsePath
        var = await client.nodes.objects.get_child([
            f"{ns_idx}:loom",
            f"{ns_idx}:LOOM-01",
            f"{ns_idx}:warp_tension"
        ])

        # Lettura valore corrente (Double)
        value = await var.read_value()
        return float(value)

asyncio.run(read_warp_tension())
```

!!! warning "Solo dalla ot-network"
    Questo client funziona solo se eseguito da un container sulla rete `ot-network`
    (es. `ot-bridge`). Da `it-network` la connessione fallirà — comportamento corretto
    del data-diode.

---

## Struttura oggetti OPC-UA

```
Objects/
├── loom/                          # ns=2 — namespace urn:mantis:loom
│   ├── LOOM-01/
│   │   ├── warp_tension           # ns=2;s=LOOM-01/warp_tension  (Double, 10Hz)
│   │   ├── pick_density           # ns=2;s=LOOM-01/pick_density  (Double, 1Hz)
│   │   ├── creel_speed            # ns=2;s=LOOM-01/creel_speed   (Double, 5Hz)
│   │   ├── broken_pick_count      # ns=2;s=LOOM-01/broken_pick_count (Double, 1Hz)
│   │   └── loom_temperature       # ns=2;s=LOOM-01/loom_temperature  (Double, 2Hz)
│   ├── LOOM-02/ ...
│   └── LOOM-12/
├── spinning/                      # ns=3 — namespace urn:mantis:spinning
│   ├── SPIN-01/ ...
│   └── SPIN-08/
├── warping/                       # ns=4 — namespace urn:mantis:warping
│   ├── WARP-01/ ...
│   └── WARP-04/
├── dyeing/                        # ns=5 — namespace urn:mantis:dyeing
│   ├── DYE-01/ ...
│   └── DYE-04/
└── finishing/                     # ns=6 — namespace urn:mantis:finishing
    ├── STEN-01/
    └── STEN-02/
```

---

## Data-diode enforcement (D-51)

Il data-diode è implementato a 3 layer:

**Layer 1 — Docker network ACL:**

```yaml
# infra/compose/sim.yml (estratto)
services:
  sim-textile:
    networks: [ot-network]        # SOLO ot-network
  ot-bridge:
    networks: [ot-network, it-network]  # bridge — unico container su entrambe
  nats:
    networks: [it-network]        # SOLO it-network
  timescaledb:
    networks: [it-network]        # SOLO it-network
```

**Layer 2 — pytest enforcement:**

```python
# tests/integration/test_data_diode.py
async def test_agent_cannot_reach_sim_textile():
    """Un container sulla it-network NON deve raggiungere sim-textile."""
    with pytest.raises((ConnectionRefusedError, asyncio.TimeoutError, OSError)):
        async with asyncio.timeout(5):
            async with asyncua.Client("opc.tcp://sim-textile:4840") as client:
                await client.get_root_node()
```

**Layer 3 — grep static-analysis CI:**

```bash
# .github/workflows/ci.yml — step "Validate IT/OT artifacts"
! grep -rE "(set_value|write_attribute|write_value)" services/ot-bridge/src/
```

Vedi i test completi in `tests/integration/test_data_diode.py` nel repository.

---

*Riferimenti: [Schema ingest](ingest-schema.md) | [Panoramica IT/OT](index.md)*
