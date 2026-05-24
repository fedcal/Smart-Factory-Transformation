---
phase: 11-observability-evaluation-security-hardening
plan: 05
type: rate-limit-scaling-doc
closes: AR-01, AR-07
status: documentation-only
redis-implemented: false
created: 2026-05-25
---

# Rate Limit Scaling — Path Evolutivo verso Redis (AR-01, AR-07)

Documento DOCUMENTATION-ONLY: descrive il rate-limiter in-process attuale (Phase 10)
e il path futuro verso un backend distribuito Redis (`RATE_LIMIT_BACKEND=redis`).

**NOTA CRITICA:** Il backend Redis NON è implementato in v1.0. Questo documento
descrive l'architettura target per una release futura. Il limiter in-process
Phase 10 rimane l'implementazione attiva.

Chiude:
- **AR-01** (T-10-02-04): rate-limiting completo come middleware FastAPI → documentato qui.
- **AR-07** (WR-05): rate-limit multi-worker non distribuito → documentato qui.

---

## Stato Attuale — Rate Limiter In-Process (Phase 10)

### Implementazione

Il rate-limiter attuale usa una struttura dati `deque` in-memoria per tracciare gli
alert per principal:

| Componente | Valore | File |
|------------|--------|------|
| `_ALERT_RATE_LIMIT` | 12 alert/ora per principal | `apps/api-gateway/src/svc_api_gateway/routers/sse.py` |
| `_alert_rate_state` | `defaultdict(deque)` — stato per principal | `apps/api-gateway/src/svc_api_gateway/routers/sse.py` |
| Sliding window | Rimuove entry più vecchie di 3600s prima di ogni check | `apps/api-gateway/src/svc_api_gateway/routers/sse.py:rate_limit` |
| Warning multi-worker | `RuntimeWarning` se `WEB_CONCURRENCY > 1` | `apps/api-gateway/src/svc_api_gateway/lifespan.py` |

### Limitazione (AR-07)

Il limiter in-process non è distribuito: se il gateway viene avviato con
`WEB_CONCURRENCY > 1` (Gunicorn multi-worker), ogni worker mantiene il proprio stato
separato. Di conseguenza un principal può ricevere fino a `N × 12` alert per ora
(dove N = numero di worker), aggirando il rate limit.

Questa limitazione è documentata e accettata per Phase 10 dev-mode (AR-07).
La produzione richiede `--workers 1` oppure il backend Redis descritto di seguito.

---

## Path Evolutivo — Backend Redis (Futuro)

### Architettura Target

```
                     ┌─────────────────────────────────────────┐
                     │           API Gateway                    │
                     │                                          │
                     │  Worker 1  Worker 2  Worker N            │
                     │     │          │         │               │
                     │     └──────────┴─────────┘               │
                     │                │                         │
                     │         RateLimiter.check()              │
                     │                │                         │
                     └────────────────┼────────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │        Redis          │
                          │   INCRBY + EXPIRE     │
                          │  (sliding window)     │
                          └──────────────────────┘
```

### Variabile di Configurazione

```bash
# infra/compose/.env.example (sezione futura)
RATE_LIMIT_BACKEND=redis          # "memory" (default) | "redis"
RATE_LIMIT_REDIS_URL=redis://redis:6379/1
RATE_LIMIT_WINDOW_SECONDS=3600
RATE_LIMIT_MAX_ALERTS=12
```

### Implementazione Target (pseudocodice — NON implementato)

```python
# DOCUMENTAZIONE ARCHITETTUALE — NON è codice eseguibile

class RedisRateLimiter:
    """Rate limiter distribuito via Redis INCRBY + EXPIRE.
    
    Pattern sliding window con chiave: f"rl:{principal_id}:{window_bucket}"
    dove window_bucket = int(time.time() // WINDOW_SECONDS)
    """
    
    def __init__(self, redis_url: str, limit: int, window_s: int) -> None:
        # self._redis = aioredis.from_url(redis_url)
        ...

    async def check(self, principal_id: str) -> bool:
        """Ritorna True se il principal è entro il limite, False se superato.
        
        Usa INCRBY + EXPIRE atomico (MULTI/EXEC o script Lua) per evitare
        race condition tra worker.
        """
        # key = f"rl:{principal_id}:{current_window_bucket}"
        # count = await self._redis.incr(key)
        # if count == 1:
        #     await self._redis.expire(key, window_s)
        # return count <= self.limit
        ...
```

### Dipendenze da Installare (richiede verifica legittimità)

Prima di installare, verificare la legittimità dei pacchetti su PyPI:

| Pacchetto | URL PyPI | Note |
|-----------|----------|------|
| `redis` | https://pypi.org/project/redis/ | Client Redis ufficiale (non `aioredis` deprecato) |
| `limits` | https://pypi.org/project/limits/ | Libreria rate-limit con backend Redis opzionale |

**ATTENZIONE:** Non installare pacchetti prima di aver verificato la legittimità.
Il GSD executor blocca gli install non verificati (checkpoint `blocking-human`).

### Migration Plan

1. **Prerequisito:** Redis già nel docker-compose (sezione "Core Services" in `.env.example`).
2. **Step 1:** Aggiungere `redis` come dipendenza runtime nel `pyproject.toml` di `svc-api-gateway`.
3. **Step 2:** Implementare `RedisRateLimiter` in `apps/api-gateway/src/svc_api_gateway/security/rate_limiter.py`.
4. **Step 3:** Aggiungere `RATE_LIMIT_BACKEND` al lifespan: se `redis`, inizializzare `RedisRateLimiter`; altrimenti fallback in-memory.
5. **Step 4:** Rimuovere il `RuntimeWarning` di `lifespan.py` (non più necessario).
6. **Step 5:** Test di integrazione con Redis Testcontainer.

---

## Accettazione Formale del Rischio (AR-01, AR-07)

Questo documento è la closure documentale dei seguenti rischi accettati:

| Risk ID | Stato | Questo documento | Data closure |
|---------|-------|-----------------|--------------|
| AR-01 (T-10-02-04) | DOCUMENTATO | Sezione "Path Evolutivo Redis" + var `RATE_LIMIT_BACKEND` | 2026-05-25 |
| AR-07 (WR-05) | DOCUMENTATO | Sezione "Limitazione multi-worker" + warning `lifespan.py` | 2026-05-25 |

Entrambi i rischi sono accettati per Phase 10 / v1.0 dev-mode.
Il backend Redis è la soluzione target per deployment multi-worker in produzione.
