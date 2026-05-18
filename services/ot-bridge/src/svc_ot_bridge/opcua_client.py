"""asyncua subscribe-only client per svc-ot-bridge (D-51 Layer 3).

Si connette a OPC-UA server (sim-textile) e subscribes alle DataChangeNotification.
Le notifiche sono passate a una asyncio.Queue per handoff verso il worker loop (Pitfall 1).

D-51 Layer 3: SUBSCRIBER ONLY.
CI gate: grep di pattern write-API su services/ot-bridge/src/ deve exit 1 (zero match).
Questo file e' subscribe-only, nessuna write API.

Pitfall 1 mitigation: il callback datachange_notification NON fa lavoro pesante.
Solo queue.put_nowait((node, val, data)) — il parsing avviene nel worker task.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from asyncua import Client

from sft_assets._loader import load_assets

logger = structlog.get_logger(__name__)

UTC = timezone.utc


class OpcUaSubscriber:
    """Subscriber asyncua che si connette a OPC-UA e invia notifiche alla queue.

    Design:
        - Si connette a opc.tcp://sim-textile:4840 (D-50)
        - Crea subscription con publishing_interval=50ms, samples_per_publish=10 (Pitfall 1)
        - Per ogni (asset, tag) subscribes al Variable node tramite namespace+BrowsePath
        - datachange_notification → queue.put_nowait (callback leggero, Pitfall 1)
        - queue.full() → drop + audit log (esplicito, non silenzioso)

    D-51 Layer 3: ZERO chiamate write API (solo subscribe). Verificato da CI grep gate.

    Usage:
        queue = asyncio.Queue(maxsize=10000)
        subscriber = OpcUaSubscriber(url="opc.tcp://sim-textile:4840", queue=queue)
        await subscriber.start()
        # ... worker drains queue ...
        await subscriber.close()
    """

    def __init__(
        self,
        url: str,
        queue: asyncio.Queue,
        publishing_interval_ms: int = 50,
        samples_per_publish: int = 10,
    ) -> None:
        """Inizializza il subscriber.

        Args:
            url: OPC-UA endpoint (es. "opc.tcp://sim-textile:4840", env OPCUA_URL).
            queue: asyncio.Queue per handoff eventi al worker loop (Pitfall 1).
            publishing_interval_ms: Intervallo pubblicazione subscription in ms (Pitfall 1 = 50).
            samples_per_publish: Sample per messaggio di pubblicazione (Pitfall 1 = 10).
        """
        self._url = url
        self._queue = queue
        self._publishing_interval_ms = publishing_interval_ms
        self._samples_per_publish = samples_per_publish
        self._client: Any = None
        self._subscription: Any = None
        # Mappa nodeid → (asset_id, tag_id) per risoluzione nel worker
        self._nodeid_map: dict[str, tuple[str, str]] = {}

    async def start(self) -> None:
        """Connette al server OPC-UA e crea le subscriptions per tutti gli asset/tag.

        Risolve i Variable nodes tramite namespace urn:mantis:<family>:<asset_id>
        e BrowseName <tag_id>. Popola self._nodeid_map per il worker.

        Raises:
            ConnectionError: Se la connessione OPC-UA fallisce.
        """
        self._client = Client(url=self._url)
        await self._client.connect()
        logger.info("opcua_client_connected", url=self._url)

        assets = load_assets()

        # Crea la subscription con publishing_interval e samples_per_publish (Pitfall 1)
        self._subscription = await self._client.create_subscription(
            self._publishing_interval_ms,
            self,
        )

        # Subscribe a tutti i nodi Variable per asset/tag nel registry
        for asset in assets:
            if asset.status != "active":
                continue
            for tag in asset.tags:
                try:
                    # Risolvi il namespace index tramite namespace URI
                    ns_idx = await self._client.get_namespace_index(asset.opcua_namespace)
                    # Costruisci il BrowsePath: <asset_id>/<tag_id>
                    browse_path = f"{asset.asset_id}/{tag.tag_id}"
                    # Naviga al nodo tramite root browse path
                    var_node = self._client.get_node(f"ns={ns_idx};s={browse_path}")
                    await self._subscription.subscribe_data_change(var_node)
                    # Registra mapping nodeid → (asset_id, tag_id)
                    node_id_str = str(var_node.nodeid)
                    self._nodeid_map[node_id_str] = (asset.asset_id, tag.tag_id)
                    logger.debug(
                        "subscribed_node",
                        asset_id=asset.asset_id,
                        tag_id=tag.tag_id,
                        node_id=node_id_str,
                    )
                except Exception as exc:
                    logger.warning(
                        "subscription_failed",
                        asset_id=asset.asset_id,
                        tag_id=tag.tag_id,
                        error=str(exc),
                    )

        logger.info(
            "opcua_subscriptions_created",
            total_nodes=len(self._nodeid_map),
            publishing_interval_ms=self._publishing_interval_ms,
        )

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        """Callback OPC-UA per DataChangeNotification.

        CRITICAL (Pitfall 1): questo callback NON deve fare lavoro pesante.
        Solo queue.put_nowait() — il parsing/normalizzazione avviene nel worker task.

        Se la queue e' piena: drop esplicito + log (non silenzioso, D-51 audit trail).

        Args:
            node: asyncua Node oggetto.
            val: Valore letto dal nodo.
            data: DataChangeNotification con SourceTimestamp e StatusCode.
        """
        try:
            self._queue.put_nowait((node, val, data))
        except asyncio.QueueFull:
            logger.error(
                "opcua_queue_full_drop",
                node_id=str(node.nodeid),
                queue_size=self._queue.maxsize,
                event_type="queue_overflow",
            )
            # Drop esplicito — Phase 11 gestira' back-pressure e alerting

    async def get_node_identity(self, node: Any) -> tuple[str, str] | None:
        """Risolve asset_id e tag_id dato un asyncua Node.

        Args:
            node: asyncua Node oggetto dalla notifica.

        Returns:
            Tupla (asset_id, tag_id) o None se nodo sconosciuto.
        """
        node_id_str = str(node.nodeid)
        return self._nodeid_map.get(node_id_str)

    async def close(self) -> None:
        """Cancella la subscription e disconnette dal server OPC-UA."""
        if self._subscription is not None:
            try:
                await self._subscription.delete()
            except Exception as exc:
                logger.warning("subscription_delete_error", error=str(exc))
        if self._client is not None:
            await self._client.disconnect()
            logger.info("opcua_client_disconnected")
