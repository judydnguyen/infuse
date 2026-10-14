## Problem

`auth-service` has intermittent timeout errors when calling `user-service`. Skim the following files to understand the current state:

- `README.md` — architecture overview and known issues
- `./auth-service/app.py` — auth service code (note: `MAX_CONNECTIONS=10`, `CONNECTION_TIMEOUT=1000ms`)
- `./user-service/app.py` — user service code (note: ~30% random delay on queries)
- `docker-compose.yml` — resource limits and env vars
- `envoy/envoy.yaml` — service mesh config

## Task

Implement at least **2 of the following 4 fixes**:

1. **Circuit Breaker** — add to `auth-service/app.py` or `envoy/envoy.yaml`
2. **Retry with backoff** — add to `auth-service/app.py` or `envoy/envoy.yaml`
3. **Timeout increase** — raise `CONNECTION_TIMEOUT` in `docker-compose.yml` or service code
4. **Connection pool increase** — raise `MAX_CONNECTIONS` above 10 in `docker-compose.yml`
