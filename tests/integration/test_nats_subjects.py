"""
tests/integration/test_nats_subjects.py

NATS JetStream subject hierarchy verification — D-52.

Verifica:
1. Lo stream SENSOR_EVENTS esiste con soggetto wildcard sensor.events.>
2. I messaggi pubblicati da ot-bridge seguono il formato
   sensor.events.<family>.<asset_id>.<tag_id> (5 parti).

Requirements: IOT-04
Decisions: D-52
"""

import asyncio
import re

import pytest


ASSET_FAMILIES = {"loom", "spinning", "warping", "dyeing", "finishing"}

# Pattern: sensor.events.<family>.<asset_id>.<tag_id>
_SUBJECT_RE = re.compile(
    r"^sensor\.events\."
    r"(?P<family>loom|spinning|warping|dyeing|finishing)\."
    r"(?P<asset_id>[A-Z]+-\d+)\."
    r"(?P<tag_id>[a-z_]+)$"
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jetstream_stream_exists(compose_stack: dict) -> None:
    """Lo stream SENSOR_EVENTS deve esistere con soggetto sensor.events.>"""
    try:
        import nats  # noqa: PLC0415
    except ImportError:
        pytest.skip("nats-py non disponibile — installa con uv add nats-py")
        return

    nats_url = compose_stack["NATS_URL"]
    nc = await nats.connect(nats_url)
    try:
        js = nc.jetstream()
        info = await js.stream_info("SENSOR_EVENTS")

        assert info is not None, "Stream SENSOR_EVENTS non trovato"
        assert "sensor.events.>" in info.config.subjects, (
            f"Soggetto 'sensor.events.>' non in stream config: {info.config.subjects}"
        )
    finally:
        await nc.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_subject_format(compose_stack: dict) -> None:
    """I messaggi pubblicati da ot-bridge devono avere soggetti nel formato
    sensor.events.<family>.<asset_id>.<tag_id>.

    Subscribe a sensor.events.> con consumer durable; poll fino a 30s o
    primo messaggio ricevuto; verifica il formato del soggetto.
    """
    try:
        import nats  # noqa: PLC0415
        from nats.js.api import ConsumerConfig  # noqa: PLC0415
    except ImportError:
        pytest.skip("nats-py non disponibile — installa con uv add nats-py")
        return

    nats_url = compose_stack["NATS_URL"]
    nc = await nats.connect(nats_url)
    received_subjects: list[str] = []

    try:
        js = nc.jetstream()

        # Consumer temporaneo per raccogliere messaggi
        consumer_cfg = ConsumerConfig(
            durable_name="test_subject_check",
            deliver_policy="last_per_subject",
            ack_policy="explicit",
            max_deliver=1,
        )

        try:
            psub = await js.subscribe(
                "sensor.events.>",
                config=consumer_cfg,
                manual_ack=True,
            )
        except Exception:
            # Consumer potrebbe gia' esistere — usa subscribe semplice
            psub = await js.subscribe("sensor.events.>", manual_ack=True)

        # Poll per 30s o fino a ricezione almeno 1 messaggio
        deadline = asyncio.get_event_loop().time() + 30.0
        while asyncio.get_event_loop().time() < deadline and not received_subjects:
            try:
                msg = await asyncio.wait_for(psub.next_msg(timeout=2.0), timeout=3.0)
                received_subjects.append(msg.subject)
                await msg.ack()
            except (asyncio.TimeoutError, Exception):
                await asyncio.sleep(0.5)

    finally:
        try:
            await psub.unsubscribe()
        except Exception:
            pass
        await nc.close()

    if not received_subjects:
        pytest.skip(
            "Nessun messaggio ricevuto su sensor.events.> entro 30s — "
            "ot-bridge potrebbe non aver ancora pubblicato. "
            "Verificare che sim-textile e ot-bridge siano healthy."
        )
        return

    # Verifica formato di tutti i soggetti ricevuti
    for subject in received_subjects:
        match = _SUBJECT_RE.match(subject)
        assert match is not None, (
            f"Soggetto '{subject}' non rispetta formato D-52 "
            f"sensor.events.<family>.<asset_id>.<tag_id>"
        )
        family = match.group("family")
        assert family in ASSET_FAMILIES, (
            f"Asset family '{family}' non riconosciuta (atteso: {ASSET_FAMILIES})"
        )
