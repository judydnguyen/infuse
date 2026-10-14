#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running microservices timeout resolution tests..."

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "[✗] ERROR: docker-compose.yml not found"
    exit 1
fi

echo "[✓] docker-compose.yml found"

# Validate docker-compose.yml has expected services
EXPECTED_SERVICES=("auth-service" "user-service" "envoy")
for service in "${EXPECTED_SERVICES[@]}"; do
    if ! grep -q "$service" docker-compose.yml; then
        echo "[✗] ERROR: Required service $service not found in docker-compose.yml"
        exit 1
    fi
done
echo "[✓] Required services found in docker-compose.yml"

# Check for required improvements
IMPROVEMENTS=0

# Check 1: Circuit breaker (in code or Envoy config)
if grep -qi "circuit.*breaker\|circuitbreaker\|CircuitBreaker" auth-service/app.py 2>/dev/null || \
   grep -qi "circuit_breaker\|outlier_detection" envoy/envoy.yaml 2>/dev/null; then
    echo "[✓] Circuit breaker found"
    IMPROVEMENTS=$((IMPROVEMENTS + 1))
fi

# Check 2: Retry logic (in code or Envoy config)
if grep -qi "retry\|Retry\|backoff\|exponential" auth-service/app.py 2>/dev/null || \
   grep -qi "retry_policy\|retry_on" envoy/envoy.yaml 2>/dev/null; then
    echo "[✓] Retry logic found"
    IMPROVEMENTS=$((IMPROVEMENTS + 1))
fi

# Check 3: Timeout configuration improvements
if grep -q "timeout=" auth-service/app.py 2>/dev/null || \
   grep -qi "route_timeout\|per_try_timeout\|idle_timeout" envoy/envoy.yaml 2>/dev/null; then
    echo "[✓] Timeout configuration found"
    IMPROVEMENTS=$((IMPROVEMENTS + 1))
fi

# Check 4: Connection pool or timeout values improved
if grep -qi "MAX_CONNECTIONS.*[2-9][0-9]\|MAX_CONNECTIONS.*[1-9][0-9][0-9]" docker-compose.yml 2>/dev/null || \
   grep -q "CONNECTION_TIMEOUT=[2-9][0-9][0-9][0-9]\|CONNECTION_TIMEOUT=[1-9][0-9][0-9][0-9][0-9]" docker-compose.yml 2>/dev/null; then
    echo "[✓] Connection pool or timeout values improved"
    IMPROVEMENTS=$((IMPROVEMENTS + 1))
fi

# Require at least 2 improvements
if [ "$IMPROVEMENTS" -ge 2 ]; then
    echo "[✓] TEST TASK PASSED - Sufficient improvements detected ($IMPROVEMENTS/4)"
    exit 0
else
    echo "[✗] TEST TASK FAILED - Insufficient improvements ($IMPROVEMENTS/4, need at least 2)"
    echo "    Expected: circuit breakers, retry logic, timeout handling, or connection pool improvements"
    exit 1
fi
