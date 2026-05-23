"""svc-agents-scheduler — APScheduler-driven AnomalyDetector cron (OPS-04).

Lifecycle is intentionally separated from the orchestrator process so
scheduler restarts do not bounce LangGraph and so we never end up with
N orchestrator replicas firing the same cron in parallel (Pitfall §5).
"""

__version__ = "0.1.0"
