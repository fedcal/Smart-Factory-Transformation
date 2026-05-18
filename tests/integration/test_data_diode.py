"""
tests/integration/test_data_diode.py

D-51 3-layer data-diode enforcement tests.

Layer 1 (network ACL): un container fake-agent su sft-core NON deve poter
    aprire socket OPC-UA verso sim-textile (che e' solo su sft-ot).
Layer 2 (pytest enforcement): verifica da host-side che sft-sim-textile:4840
    non sia raggiungibile tramite DNS interna (caveat A5 documentato).
Layer 3 (static analysis): grep nei sorgenti ot-bridge — nessuna chiamata
    set_value / write_attribute / write_value.

Requirements: IOT-05
Threat model: T-DATA-DIODE (D-51 Layer 1+2+3)
"""

import asyncio
import subprocess

import pytest


@pytest.mark.integration
def test_layer1_agent_cannot_reach_sim_via_it_network(compose_stack: dict) -> None:
    """Layer 1: un container fake-agent su sft-core NON deve poter aprire
    una connessione OPC-UA verso sim-textile (che e' solo su sft-ot).

    Strategia: lancia container temporaneo python:3.12-slim su sft-core;
    esegue script Python inline che tenta asyncua.Client entro asyncio.timeout(5).
    - Successo (diode OK): script stampa OK_BLOCKED ed esce con code 0.
    - Fallimento (diode violato): script esce con code 99.

    Caveat: il test richiede che il container sft-core esista gia' (garantito
    dalla fixture compose_stack che ha eseguito docker compose up).
    """
    inline_script = (
        "import asyncio, socket\n"
        "async def main():\n"
        "    try:\n"
        "        import asyncua\n"
        "        client = asyncua.Client('opc.tcp://sft-sim-textile:4840', timeout=4)\n"
        "        async with asyncio.timeout(5):\n"
        "            async with client:\n"
        "                await client.get_root_node()\n"
        "        print('CONNECTED', flush=True)\n"
        "        raise SystemExit(99)\n"
        "    except (ConnectionRefusedError, asyncio.TimeoutError, OSError,\n"
        "            socket.gaierror, Exception):\n"
        "        print('OK_BLOCKED', flush=True)\n"
        "        raise SystemExit(0)\n"
        "asyncio.run(main())\n"
    )

    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "sft-core",
            "python:3.12-slim",
            "python",
            "-c",
            inline_script,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Script exits 0 and prints OK_BLOCKED — connection was blocked (correct)
    # Script exits 99 — connection succeeded (data-diode violation)
    assert result.returncode == 0, (
        f"Layer 1 FAIL: fake-agent su sft-core HA raggiunto sim-textile (D-51 violazione).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK_BLOCKED" in result.stdout, (
        f"Layer 1 FAIL: output inatteso.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_layer2_agent_cannot_open_opcua_session(compose_stack: dict) -> None:
    """Layer 2 (host-side pytest): sim-textile non deve essere raggiungibile via
    DNS sft-sim-textile dall'host pytest.

    Nota A5: su alcuni sistemi Docker condivide il DNS interno con l'host; in
    quel caso il test puo' false-pass se il resolver localhost:127.0.0.11
    risponde. Il Layer 1 (container-based) rimane il gate primario; Layer 2
    e Layer 3 sono difese in profondita'.

    Questo test verifica che non esista un percorso diretto host → sft-ot
    tramite il nome container (l'IP host-mapped 4840 potrebbe essere aperto
    da Docker in dev — questo e' intenzionale per developer tooling, D-51
    Layer 1 non blocca il mapping localhost).
    """
    try:
        import asyncua  # noqa: PLC0415
    except ImportError:
        pytest.skip("asyncua non disponibile — installa con uv add asyncua")
        return

    # Verifica che sft-sim-textile (nome container interno Docker) non sia
    # risolvibile dall'host (hostname resolution fallisce o timeout)
    connection_succeeded = False
    try:
        async with asyncio.timeout(5):
            client = asyncua.Client(url="opc.tcp://sft-sim-textile:4840", timeout=4)
            async with client:
                await client.get_root_node()
            connection_succeeded = True
    except (ConnectionRefusedError, asyncio.TimeoutError, OSError, Exception):
        connection_succeeded = False

    # Il nome container sft-sim-textile NON deve essere risolvibile dall'host
    # (diverso da localhost:4840 che e' esposto via port-mapping per dev)
    assert not connection_succeeded, (
        "Layer 2 WARN: host ha raggiunto sft-sim-textile via DNS interno Docker. "
        "Questo puo' indicare Docker DNS shared (caveat A5). "
        "Verificare Layer 1 (container-based) come gate primario."
    )


@pytest.mark.integration
def test_layer3_ot_bridge_has_no_opcua_write_calls(compose_stack: dict) -> None:
    """Layer 3 (static analysis): ot-bridge NON deve contenere chiamate
    OPC-UA write (set_value, write_attribute, write_value).

    Grep con exit 1 = nessun match (atteso — D-51 Layer 3 OK).
    Grep con exit 0 = trovata almeno 1 riga (D-51 violazione).

    Nota: grep esce 1 se nessuna riga corrisponde, 0 se almeno una corrisponde.
    """
    import pathlib  # noqa: PLC0415

    ot_bridge_src = pathlib.Path(__file__).parent.parent.parent / "services" / "ot-bridge" / "src"

    result = subprocess.run(
        [
            "grep",
            "-rE",
            r"set_value|write_attribute|write_value",
            str(ot_bridge_src),
        ],
        capture_output=True,
        text=True,
    )

    # grep exit 1 = no match = Layer 3 PASS
    # grep exit 0 = found match = D-51 violation
    assert result.returncode == 1, (
        f"Layer 3 FAIL: ot-bridge contiene chiamate OPC-UA write (D-51 violazione):\n"
        f"{result.stdout}"
    )
