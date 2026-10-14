I trained up a local repro under `/app` with `docker-compose.yml`, an `auth-service`, a `user-service`, and scattered logs under `logs/`.

Problem:
- `auth-service` intermittently times out calling `user-service`
- Logs are spread across multiple containers and local log files
- Service mesh uses Envoy (simulate at least one proxy hop)

You must:
1) Analyze logs across all containers and `/app/logs/*.log` to identify the likely root cause(s).
2) Measure network/HTTP latency between `auth-service` and `user-service` from within the compose network.
3) Check for connection pool exhaustion / too-low timeouts in `auth-service` HTTP client config.
4) Implement a fix that includes:
   - sane request timeout
   - bounded retries with exponential backoff + jitter
   - circuit breaker behavior (fail fast when user-service is unhealthy)
   - connection pooling tuned to avoid exhaustion
5) Keep changes minimal and scoped to this repo. Do not delete services.

Output requirements:
- Implement the fix in code/config so it is effective when running `docker compose up`.
- Add/modify any needed config files (Envoy config, app config).
- Ensure services log actionable errors (timeout vs 5xx vs breaker-open).