#!/usr/bin/env python3
"""
scripts/nats-bootstrap-streams.py

Idempotent JetStream stream bootstrap per svc-ot-bridge + Phase 4 audit substrate.

Crea (o aggiorna se esistente) i JetStream streams:
    SENSOR_EVENTS  — sensor.events.> + sensor.alarms.>  retention=WorkQueue max_age=7d
    AUDIT_OT       — audit.ot.>                         retention=Limits    max_age=30d
    AUDIT_STREAM   — audit.actions.> + hitl.approvals.> + hitl.governor.>
                     retention=Limits max_age=90d  (Phase 4 D-56 + HITL-05)
    QUALITY_STREAM — quality.events.>                   retention=Limits    max_age=7d
                     (Phase 6 D-QI-01: QualityInspector durable consumer
                     qi-consumer ack_policy=EXPLICIT max_deliver=5 ack_wait=30s)

Idempotency (Pitfall 3 mitigation):
    try: add_stream(config) except BadRequestError: update_stream(config)
    Idempotente su re-run — config viene sincronizzata se divergente.

Usage:
    python3 scripts/nats-bootstrap-streams.py [--server URL] [--dry-run]

    Env fallback: NATS_URL (default: nats://localhost:4222)

Exit codes:
    0  — stream creati/aggiornati con successo (o --dry-run completato)
    1  — errore di connessione o configurazione

Examples:
    python3 scripts/nats-bootstrap-streams.py --dry-run
    python3 scripts/nats-bootstrap-streams.py --server nats://nats:4222
    NATS_URL=nats://nats:4222 python3 scripts/nats-bootstrap-streams.py
"""

import argparse
import asyncio
import os
import pathlib
import sys

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent


def _parse_args() -> argparse.Namespace:
    """Parsa gli argomenti CLI con argparse (Pattern S-4)."""
    parser = argparse.ArgumentParser(
        description=(
            "Idempotent JetStream bootstrap: crea SENSOR_EVENTS e AUDIT_OT streams. "
            "Usa try add_stream → fallback update_stream per idempotency (Pitfall 3)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--server",
        default=os.environ.get("NATS_URL", "nats://localhost:4222"),
        help="NATS server URL (default: NATS_URL env o nats://localhost:4222)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa la configurazione degli stream senza crearli. Exit 0.",
    )
    return parser.parse_args()


async def bootstrap(server: str, dry_run: bool) -> int:
    """Crea o aggiorna i JetStream streams.

    Args:
        server: URL NATS (es. "nats://nats:4222").
        dry_run: Se True, stampa la config e ritorna 0 senza modifiche.

    Returns:
        0 su successo, 1 su errore.
    """
    # Configurazioni stream come dizionari (no import nats necessario per dry-run)
    # In dry-run mode non ci connettiamo mai a NATS

    sensor_events_cfg = {
        "name": "SENSOR_EVENTS",
        "subjects": ["sensor.events.>", "sensor.alarms.>"],
        "retention": "WorkQueuePolicy",
        "max_age_days": 7,
        "storage": "FileStorage",
        "max_msgs_per_subject": -1,
        "discard": "DiscardPolicy.OLD",
    }

    audit_ot_cfg = {
        "name": "AUDIT_OT",
        "subjects": ["audit.ot.>"],
        "retention": "LimitsPolicy",
        "max_age_days": 30,
        "storage": "FileStorage",
    }

    # Phase 4 D-56 + HITL-05: dual-write audit replica + HITL push notifications
    # + governor alerts. 90-day retention enforced at stream level.
    audit_stream_cfg = {
        "name": "AUDIT_STREAM",
        "subjects": ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],
        "retention": "LimitsPolicy",
        "max_age_days": 90,
        "storage": "FileStorage",
        "max_msgs": -1,
        "max_bytes": -1,
        "discard": "DiscardPolicy.OLD",
        "num_replicas": 1,
    }

    # Phase 6 D-QI-01: QualityInspector durable JetStream consumer
    # (qi-consumer) on quality.events.>. 7-day retention (Pitfall §4 -
    # generous catch-up so qi-consumer never starves on cold start).
    quality_stream_cfg = {
        "name": "QUALITY_STREAM",
        "subjects": ["quality.events.>"],
        "retention": "LimitsPolicy",
        "max_age_days": 7,
        "storage": "FileStorage",
        "max_msgs": -1,
        "max_bytes": -1,
        "discard": "DiscardPolicy.OLD",
        "num_replicas": 1,
    }

    all_cfg_specs = [
        sensor_events_cfg,
        audit_ot_cfg,
        audit_stream_cfg,
        quality_stream_cfg,
    ]

    if dry_run:
        print("[dry-run] Stream configurations (would create/update):")
        print()
        for spec in all_cfg_specs:
            print(f"  Stream: {spec['name']}")
            print(f"    subjects: {spec['subjects']}")
            print(f"    retention: {spec['retention']}")
            print(f"    max_age_days: {spec['max_age_days']}")
            print(f"    storage: {spec['storage']}")
            print()
        print("SENSOR_EVENTS: would create/update")
        print("AUDIT_OT: would create/update")
        print("AUDIT_STREAM: would create/update")
        print("QUALITY_STREAM: would create/update")
        return 0

    # Importa nats solo se non dry-run (evita ModuleNotFoundError su ambienti dev)
    import nats
    from nats.js.api import (
        AckPolicy,
        ConsumerConfig,
        DiscardPolicy,
        RetentionPolicy,
        StorageType,
        StreamConfig,
    )

    # Costruisci StreamConfig objects reali.
    #
    # NOTE su `max_age`: nats-py 2.14 espone `max_age` in *secondi* (float)
    # nella StreamConfig dataclass; viene convertito a nanosecondi solo durante
    # la serializzazione JSON verso il server. Passare nanosecondi qui produce
    # un valore fuori range (~1e24) che il server rifiuta con
    # `BadRequestError code=400 err_code=10025 description='invalid JSON'`.
    cfg_sensor = StreamConfig(
        name="SENSOR_EVENTS",
        subjects=["sensor.events.>", "sensor.alarms.>"],
        retention=RetentionPolicy.WORK_QUEUE,
        max_age=7 * 24 * 3600,  # 7 giorni in secondi (Plan 04-04 fix Rule 3)
        storage=StorageType.FILE,
        max_msgs_per_subject=-1,
        discard=DiscardPolicy.OLD,
    )

    cfg_audit = StreamConfig(
        name="AUDIT_OT",
        subjects=["audit.ot.>"],
        retention=RetentionPolicy.LIMITS,
        max_age=30 * 24 * 3600,  # 30 giorni in secondi (Plan 04-04 fix Rule 3)
        storage=StorageType.FILE,
    )

    # Phase 4 D-56 + HITL-05: 90-day retention for audit dual-write replica
    # Subjects: audit.actions.<cluster>.<agent_id>, hitl.approvals.{new,resolved}.<tier>,
    # hitl.governor.alert — see packages/sft-agents/src/sft_agents/audit/subjects.py
    cfg_audit_stream = StreamConfig(
        name="AUDIT_STREAM",
        subjects=["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],
        retention=RetentionPolicy.LIMITS,
        max_age=90 * 24 * 3600,  # 90 giorni in secondi (nats-py 2.14 semantic)
        storage=StorageType.FILE,
        max_msgs=-1,
        max_bytes=-1,
        discard=DiscardPolicy.OLD,
        num_replicas=1,
    )

    # Phase 6 D-QI-01: QualityInspector input stream for QC events emitted by
    # sim-textile + operator API. 7-day retention (Pitfall §4 - generous
    # catch-up window). Stream MUST exist before sim-textile starts publishing.
    cfg_quality_stream = StreamConfig(
        name="QUALITY_STREAM",
        subjects=["quality.events.>"],
        retention=RetentionPolicy.LIMITS,
        max_age=7 * 24 * 3600,  # 7 giorni in secondi (nats-py 2.14 semantic)
        storage=StorageType.FILE,
        max_msgs=-1,
        max_bytes=-1,
        discard=DiscardPolicy.OLD,
        num_replicas=1,
    )

    all_configs = [cfg_sensor, cfg_audit, cfg_audit_stream, cfg_quality_stream]

    # Connessione reale
    try:
        nc = await nats.connect(server)
    except Exception as exc:
        print(f"ERROR: impossibile connettersi a {server}: {exc}", file=sys.stderr)
        return 1

    js = nc.jetstream()

    for cfg in all_configs:
        try:
            await js.add_stream(config=cfg)
            print(f"OK [{cfg.name}]: stream created")
        except nats.js.errors.BadRequestError:
            # Stream esiste con config diversa — update idempotente (Pitfall 3)
            try:
                await js.update_stream(config=cfg)
                print(f"OK [{cfg.name}]: stream updated (config synced)")
            except Exception as upd_exc:
                print(
                    f"ERROR [{cfg.name}]: update_stream failed: {upd_exc}",
                    file=sys.stderr,
                )
                await nc.close()
                return 1
        except Exception as exc:
            print(f"ERROR [{cfg.name}]: add_stream failed: {exc}", file=sys.stderr)
            await nc.close()
            return 1

    # Phase 6 D-QI-01: qi-consumer durable JetStream consumer (pull-based).
    # ack_policy=EXPLICIT + max_deliver=5 + ack_wait=30s per RESEARCH §Pattern 3.
    qi_consumer_cfg = ConsumerConfig(
        durable_name="qi-consumer",
        ack_policy=AckPolicy.EXPLICIT,
        max_deliver=5,
        ack_wait=30,                     # 30s
        filter_subject="quality.events.>",
        deliver_subject=None,            # pull-based (no deliver_subject)
    )
    try:
        await js.add_consumer("QUALITY_STREAM", config=qi_consumer_cfg)
        print("OK [QUALITY_STREAM/qi-consumer]: durable consumer created")
    except nats.js.errors.BadRequestError as exc:
        # Already exists — assume config matches (nats-py does not expose
        # update_consumer; manual reconciliation is left to operators).
        print(
            f"OK [QUALITY_STREAM/qi-consumer]: consumer already exists "
            f"(BadRequestError: {exc})"
        )
    except Exception as exc:
        print(
            f"ERROR [QUALITY_STREAM/qi-consumer]: add_consumer failed: {exc}",
            file=sys.stderr,
        )
        await nc.close()
        return 1

    await nc.close()
    return 0


def main() -> None:
    """Entry point principale — argparse + asyncio.run(bootstrap(...))."""
    args = _parse_args()
    exit_code = asyncio.run(bootstrap(server=args.server, dry_run=args.dry_run))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
