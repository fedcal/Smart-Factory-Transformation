"""asyncua OPC-UA server multi-namespace per sim-textile (IOT-02, D-50).

Setup server con un namespace per asset_family (urn:mantis:<family>).
Ogni Variable e' set_writable(False) — protocol-level data-diode (T-03-03-opcua-write).

Sicurezza:
    - NoSecurity policy (A-018 PoC; Phase 11 hardening: Sign+Encrypt)
    - set_writable(False) su ogni Variable (T-03-03-opcua-write)
    - import sft_assets.load_assets per generazione nodi OPC-UA

RESEARCH §Pattern 1 (lines 418-466): struttura setup_server con adattamenti D-50.
"""

from __future__ import annotations

import os

import structlog
from asyncua import Server, ua

from sft_assets import load_assets, load_tag_dict

logger = structlog.get_logger("sim-textile.server")


async def setup_server() -> tuple[Server, dict[tuple[str, str], "ua.Node"]]:
    """Crea e configura il server asyncua OPC-UA multi-namespace.

    Un namespace per asset_family (urn:mantis:<family>).
    Un Object node per asset, Variable nodes per ogni tag_id.
    Ogni Variable e' set_writable(False) per data-diode protocol-level (IOT-02).

    RESEARCH §Pattern 1 (lines 425-458): struttura adattata per D-50.

    Returns:
        Tupla (server, vars_map) dove vars_map e' dict[(asset_id, tag_id) -> Node].
    """
    server = Server()
    await server.init()

    # Endpoint da env o default (D-50)
    opcua_bind = os.environ.get("OPCUA_BIND", "opc.tcp://0.0.0.0:4840")
    endpoint = f"{opcua_bind}/sft-textile/"
    server.set_endpoint(endpoint)

    # A-018 PoC: NoSecurity (Phase 11 hardening: Sign+Encrypt)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    assets = load_assets()
    tag_dict = load_tag_dict()

    # Un namespace per asset_family (RESEARCH §Pattern 1 lines 434-442)
    family_to_ns_idx: dict[str, int] = {}
    family_root_nodes: dict[str, ua.Node] = {}

    for family in sorted({a.asset_family.value for a in assets}):
        uri = f"urn:mantis:{family}"
        idx = await server.register_namespace(uri)
        family_to_ns_idx[family] = idx
        family_root = await server.nodes.objects.add_folder(idx, family)
        family_root_nodes[family] = family_root
        logger.debug("namespace_registered", family=family, uri=uri, ns_idx=idx)

    # Un Object per asset, Variables per tag (RESEARCH §Pattern 1 lines 445-458)
    vars_map: dict[tuple[str, str], ua.Node] = {}

    for asset in assets:
        family_val = asset.asset_family.value
        idx = family_to_ns_idx[family_val]
        root = family_root_nodes[family_val]
        asset_obj = await root.add_object(idx, asset.asset_id)

        for tag_ref in asset.tags:
            tag_id = tag_ref.tag_id
            var = await asset_obj.add_variable(
                idx, tag_id, 0.0, varianttype=ua.VariantType.Double
            )
            # CRITICAL: set_writable(False) — protocol-level data-diode (T-03-03-opcua-write)
            await var.set_writable(False)
            vars_map[(asset.asset_id, tag_id)] = var

        logger.debug(
            "asset_nodes_created",
            asset_id=asset.asset_id,
            family=family_val,
            tag_count=len(asset.tags),
        )

    logger.info(
        "opcua_server_configured",
        endpoint=endpoint,
        asset_count=len(assets),
        variable_count=len(vars_map),
    )
    return server, vars_map
