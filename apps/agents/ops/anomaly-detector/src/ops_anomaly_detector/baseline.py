"""Baseline lookup helper for the AnomalyDetector agent (Plan 06-06).

The baseline registry returned by ``sft_domain.ops.anomaly.load_anomaly_baselines``
is keyed by ``(asset_family, sensor_id)`` (per the YAML schema in
``packages/sft-domain/anomaly_baselines.yaml``). When operators need to
override the family baseline for a specific machine (e.g. an aging LOOM-07
that calibrates tighter than the loom family band), they extend the same
dict with a key of shape ``(machine_id, sensor_id)`` — the lookup helper
below prefers the machine-specific entry when present.

This avoids a second YAML loader and keeps the baseline registry a single,
immutable dict that the agent receives by injection (testable, no global
mutable state — Pitfall §3 single-source-of-truth).
"""

from __future__ import annotations

from collections.abc import Mapping

from sft_domain.ops.anomaly import AnomalyBaseline

#: Type alias documenting the registry shape: tuple of two non-empty strings
#: (either ``(asset_family, sensor_id)`` for family baselines or
#: ``(machine_id, sensor_id)`` for per-machine overrides) → ``AnomalyBaseline``.
BaselineRegistry = Mapping[tuple[str, str], AnomalyBaseline]


def select_baseline(
    baselines: BaselineRegistry,
    *,
    asset_family: str,
    sensor_id: str,
    machine_id: str | None = None,
) -> AnomalyBaseline | None:
    """Return the most specific baseline for ``(asset_family|machine_id, sensor_id)``.

    Priority (most specific wins):

        1. ``(machine_id, sensor_id)`` — per-machine override
        2. ``(asset_family, sensor_id)`` — per-asset-family baseline
        3. ``None`` — caller should log ``missing_baseline`` and skip the row

    Args:
        baselines: Immutable registry as returned by
            ``load_anomaly_baselines`` (optionally extended with per-machine
            overrides — same key shape).
        asset_family: Family identifier from the asset registry
            (e.g. ``"loom"``, ``"spinning"``, ``"dyeing"``).
        sensor_id: Sensor / tag identifier (e.g. ``"warp_tension"``).
        machine_id: Specific asset_id (e.g. ``"LOOM-07"``); ``None`` skips
            the override lookup.

    Returns:
        The matching ``AnomalyBaseline``, or ``None`` when neither key is
        present in the registry.

    Raises:
        ValueError: If ``asset_family`` or ``sensor_id`` is empty — the
            caller has passed garbage that would mask a real lookup miss.
    """
    if not asset_family:
        raise ValueError("asset_family must be a non-empty string")
    if not sensor_id:
        raise ValueError("sensor_id must be a non-empty string")

    if machine_id:
        override = baselines.get((machine_id, sensor_id))
        if override is not None:
            return override

    return baselines.get((asset_family, sensor_id))


__all__ = ["BaselineRegistry", "select_baseline"]
