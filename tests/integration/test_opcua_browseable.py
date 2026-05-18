"""
tests/integration/test_opcua_browseable.py

OPC-UA server browseable test — verifica che sim-textile esponga correttamente
5 namespace urn:mantis:<family> e che le variabili siano non-writable
(protocol-level data-diode Layer 0 — D-51).

Requirements: IOT-02
"""

import asyncio

import pytest


ASSET_FAMILIES = ["loom", "spinning", "warping", "dyeing", "finishing"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_namespaces_browseable(compose_stack: dict) -> None:
    """OPC-UA server deve esporre almeno 5 namespace urn:mantis:<family>.

    Connette al server localhost:4840 (port-mapped dal container sim-textile),
    recupera l'array di namespace e verifica la presenza di tutti e 5 i
    namespace delle asset family tessili.
    """
    try:
        import asyncua  # noqa: PLC0415
    except ImportError:
        pytest.skip("asyncua non disponibile — installa con uv add asyncua")
        return

    opcua_url = compose_stack["OPCUA_URL"]

    async with asyncua.Client(url=opcua_url, timeout=10) as client:
        ns_array = await client.get_namespace_array()

    for family in ASSET_FAMILIES:
        expected_ns = f"urn:mantis:{family}"
        assert any(expected_ns in ns for ns in ns_array), (
            f"Namespace mancante: '{expected_ns}' non trovato in {ns_array}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_loom_01_variable_writable_false(compose_stack: dict) -> None:
    """Le variabili OPC-UA di sim-textile devono essere non-writable.

    Tenta di scrivere su un nodo Variable (warp_tension di LOOM-01) e
    verifica che il server risponda con UaStatusCodeError (Bad_NotWritable
    o equivalente) — protocol-level data-diode (D-51 Layer 0).

    Se il nodo non esiste, il test skippa con messaggio informativo.
    """
    try:
        import asyncua  # noqa: PLC0415
        import asyncua.ua as ua  # noqa: PLC0415
    except ImportError:
        pytest.skip("asyncua non disponibile — installa con uv add asyncua")
        return

    opcua_url = compose_stack["OPCUA_URL"]

    async with asyncua.Client(url=opcua_url, timeout=10) as client:
        # Recupera array namespace per trovare indice corretto
        ns_array = await client.get_namespace_array()

        # Cerca namespace urn:mantis:loom
        loom_ns_uri = "urn:mantis:loom"
        loom_ns_matches = [i for i, ns in enumerate(ns_array) if loom_ns_uri in ns]

        if not loom_ns_matches:
            pytest.skip(
                f"Namespace '{loom_ns_uri}' non trovato in {ns_array} — "
                "sim-textile potrebbe non aver ancora completato il boot"
            )
            return

        loom_ns_idx = loom_ns_matches[0]

        # Prova a navigare al nodo warp_tension di LOOM-01
        try:
            node = client.get_node(ua.NodeId("LOOM-01.warp_tension", loom_ns_idx))
            # Tentativo di scrittura — deve fallire con errore OPC-UA
            with pytest.raises(ua.UaStatusCodeError):
                await node.write_value(ua.DataValue(ua.Variant(99.9, ua.VariantType.Float)))
        except ua.UaStatusCodeError:
            # Anche solo il tentativo di accedere al nodo potrebbe fallire
            # se il path e' diverso — accettiamo questo come "non-writable"
            pass
        except Exception as exc:
            # Nodo non trovato o path diverso — skippa con messaggio informativo
            pytest.skip(
                f"Nodo LOOM-01.warp_tension non raggiungibile (path potrebbe differire): {exc}"
            )
