# OPC-UA Schema

Documentation of the OPC-UA namespace of the `sim-textile` simulator (Phase 3).

**Reference:** `simulators/sim-textile/` — OPC-UA server via `asyncua.Server`

---

## Endpoint

| Attribute       | Value                                        |
|-----------------|----------------------------------------------|
| Endpoint URI    | `opc.tcp://sim-textile:4840/sft-textile/`    |
| Hostname        | `sim-textile` (Docker service name, `ot-network`) |
| Port            | `4840` (OPC-UA standard)                     |
| Discovery URL   | `opc.tcp://sim-textile:4840`                 |

!!! warning "Access limited to ot-network"
    The OPC-UA endpoint is accessible **only** by `ot-bridge` on the Docker `ot-network`.
    Clients on the `it-network` (agents, tools) cannot directly reach the OPC-UA server —
    this is the intended data-diode behavior (D-51).

---

## Security policy (A-018)

| Attribute        | PoC Phase 3 value                | Phase 11 target               |
|------------------|----------------------------------|-------------------------------|
| Security Policy  | `NoSecurity`                     | `Basic256Sha256`              |
| Message Security | None                             | `SignAndEncrypt`              |
| Authentication   | Anonymous (no credentials)       | X.509 certificate             |
| PoC rationale    | A-018: simulated environment, no real data | Phase 11 security hardening |

!!! note "Assumption A-018"
    The `NoSecurity` policy is explicit for the Phase 3 PoC. Hardening to
    `Sign+Encrypt` with X.509 certificates is planned in Phase 11 (deployment
    on real infrastructure).

---

## Namespace pattern

5 registered namespaces, one per asset family:

| Namespace URI              | Family      | NS index  |
|----------------------------|-------------|-----------|
| `urn:mantis:loom`          | loom        | 2         |
| `urn:mantis:spinning`      | spinning    | 3         |
| `urn:mantis:warping`       | warping     | 4         |
| `urn:mantis:dyeing`        | dyeing      | 5         |
| `urn:mantis:finishing`     | finishing   | 6         |

**BrowsePath:** `<family>/<asset_id>/<tag_id>`

Examples:

```
loom/LOOM-01/warp_tension
loom/LOOM-01/pick_density
spinning/SPIN-01/spindle_speed
dyeing/DYE-01/bath_temperature
finishing/STEN-01/fabric_tension
```

---

## Variable nodes

Each tag is exposed as an OPC-UA variable node:

| Attribute        | Value                                              |
|------------------|----------------------------------------------------|
| `NodeId`         | `ns=<family_ns_idx>;s=<asset_id>/<tag_id>`         |
| `BrowseName`     | `<ns_idx>:<tag_id>`                                |
| `VariantType`    | `Double` (all numeric tags)                        |
| `Writable`       | `False` — data-diode protocol-level (D-51 Layer 0) |
| `AccessLevel`    | `CurrentRead` (0x01)                               |
| `UserAccessLevel`| `CurrentRead` (0x01)                               |

!!! info "Data-diode Layer 0"
    The `Writable = False` property at the variable node level is Layer 0 of the
    data-diode (D-51). Full enforcement uses 3 layers:
    Layer 1 (Docker network ACL) + Layer 2 (pytest) + Layer 3 (grep static-analysis).

---

## Python client example

```python
import asyncio
import asyncua

async def read_warp_tension() -> float:
    async with asyncua.Client("opc.tcp://sim-textile:4840/sft-textile/") as client:
        # Get the loom namespace index
        ns_idx = await client.get_namespace_index("urn:mantis:loom")

        # Navigate the BrowsePath hierarchy
        var = await client.nodes.objects.get_child([
            f"{ns_idx}:loom",
            f"{ns_idx}:LOOM-01",
            f"{ns_idx}:warp_tension"
        ])

        # Read current value (Double)
        value = await var.read_value()
        return float(value)

asyncio.run(read_warp_tension())
```

!!! warning "ot-network only"
    This client only works when executed from a container on the `ot-network`
    (e.g., `ot-bridge`). From `it-network` the connection will fail — this is
    the correct data-diode behavior.

---

## OPC-UA objects structure

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

The data-diode is implemented in 3 layers:

**Layer 1 — Docker network ACL:**

```yaml
# infra/compose/sim.yml (excerpt)
services:
  sim-textile:
    networks: [ot-network]        # ot-network ONLY
  ot-bridge:
    networks: [ot-network, it-network]  # bridge — only container on both networks
  nats:
    networks: [it-network]        # it-network ONLY
  timescaledb:
    networks: [it-network]        # it-network ONLY
```

**Layer 2 — pytest enforcement:**

```python
# tests/integration/test_data_diode.py
async def test_agent_cannot_reach_sim_textile():
    """A container on it-network MUST NOT reach sim-textile."""
    with pytest.raises((ConnectionRefusedError, asyncio.TimeoutError, OSError)):
        async with asyncio.timeout(5):
            async with asyncua.Client("opc.tcp://sim-textile:4840") as client:
                await client.get_root_node()
```

**Layer 3 — CI grep static-analysis:**

```bash
# .github/workflows/ci.yml — step "Validate IT/OT artifacts"
! grep -rE "(set_value|write_attribute|write_value)" services/ot-bridge/src/
```

See full tests in `tests/integration/test_data_diode.py` in the repository.

---

*References: [Ingest Schema](ingest-schema.md) | [IT/OT Overview](index.md)*
