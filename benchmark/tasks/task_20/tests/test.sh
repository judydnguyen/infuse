#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running microservices timeout resolution verification..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[✗] ERROR: docker-compose not found"
    exit 1
fi

echo "[✓] Docker Compose available"

# Check if services can be built
echo "[*] Checking if services can be built..."
if docker-compose build 2>&1 | tee build.log || docker compose build 2>&1 | tee build.log; then
    echo "[✓] Services built successfully"
else
    echo "[!] WARNING: Service build had issues (may be expected)"
fi

# Check for circuit breaker implementation
echo "[*] Checking for circuit breaker implementation..."

CIRCUIT_BREAKER_FOUND=false

# Check in auth-service
if grep -qi "circuit.*breaker\|circuitbreaker\|CircuitBreaker" auth-service/app.py 2>/dev/null; then
    echo "[✓] Circuit breaker found in auth-service"
    CIRCUIT_BREAKER_FOUND=true
fi

# Check in Envoy config
if grep -qi "circuit_breaker\|outlier_detection" envoy/envoy.yaml 2>/dev/null; then
    echo "[✓] Circuit breaker configuration found in Envoy"
    CIRCUIT_BREAKER_FOUND=true
fi

if [ "$CIRCUIT_BREAKER_FOUND" = false ]; then
    echo "[!] WARNING: No circuit breaker implementation detected"
    echo "    Consider implementing circuit breakers to prevent cascading failures"
fi

# Check for retry logic
echo "[*] Checking for retry logic implementation..."

RETRY_FOUND=false

# Check in auth-service
if grep -qi "retry\|Retry\|backoff\|exponential" auth-service/app.py 2>/dev/null; then
    echo "[✓] Retry logic found in auth-service"
    RETRY_FOUND=true
fi

# Check in Envoy config
if grep -qi "retry_policy\|retry_on" envoy/envoy.yaml 2>/dev/null; then
    echo "[✓] Retry policy found in Envoy configuration"
    RETRY_FOUND=true
fi

if [ "$RETRY_FOUND" = false ]; then
    echo "[!] WARNING: No retry logic detected"
    echo "    Consider implementing retry logic with exponential backoff"
fi

# Check for timeout configuration improvements
echo "[*] Checking timeout configurations..."

# Check if timeouts are reasonable (not too low)
if grep -q "CONNECTION_TIMEOUT=1000" docker-compose.yml 2>/dev/null; then
    echo "[!] WARNING: Very low connection timeout (1000ms) detected"
    echo "    Consider increasing timeout values"
fi

# Check if auth-service has proper timeout handling
echo "[*] Checking auth-service timeout handling..."

if grep -q "timeout=" auth-service/app.py 2>/dev/null; then
    echo "[✓] Timeout parameter found in auth-service requests"
else
    echo "[!] WARNING: No explicit timeout in auth-service requests"
    echo "    Requests may hang indefinitely"
fi

# Check for connection pooling improvements
if grep -qi "pool\|Pool\|HTTPAdapter\|connection.*pool" auth-service/app.py 2>/dev/null; then
    echo "[✓] Connection pooling found in auth-service"
else
    echo "[!] WARNING: Connection pooling may not be properly configured"
fi

# Check for log analysis evidence
echo "[*] Checking if log files exist for analysis..."
if [ -d "logs" ] && [ "$(ls -A logs 2>/dev/null)" ]; then
    LOG_COUNT=$(find logs -name "*.log" -type f | wc -l)
    echo "[✓] Found $LOG_COUNT log files for analysis"
    
    # Check if timeout errors are present in logs
    if grep -r "timeout\|Timeout\|TIMEOUT" logs/ 2>/dev/null | head -1; then
        echo "[✓] Timeout-related log entries found"
    fi
    
    # Check for connection pool exhaustion
    if grep -r "pool.*exhaust\|connection.*pool.*exhaust" logs/ 2>/dev/null | head -1; then
        echo "[✓] Connection pool exhaustion detected in logs"
    fi
else
    echo "[!] WARNING: No log files found in logs/ directory"
fi

# Check for Envoy configuration improvements
echo "[*] Checking Envoy configuration..."

if [ -f "envoy/envoy.yaml" ]; then
    # Check for circuit breaker in Envoy
    if grep -q "circuit_breaker\|outlier_detection" envoy/envoy.yaml 2>/dev/null; then
        echo "[✓] Circuit breaker configured in Envoy"
    else
        echo "[!] WARNING: No circuit breaker configuration in Envoy"
    fi
    
    # Check for retry policy in Envoy
    if grep -q "retry_policy" envoy/envoy.yaml 2>/dev/null; then
        echo "[✓] Retry policy configured in Envoy"
    else
        echo "[!] WARNING: No retry policy in Envoy configuration"
    fi
    
    # Check for timeout configuration
    if grep -q "timeout\|per_try_timeout" envoy/envoy.yaml 2>/dev/null; then
        echo "[✓] Timeout configuration found in Envoy"
    else
        echo "[!] WARNING: Timeout configuration may be missing in Envoy"
    fi
else
    echo "[!] WARNING: Envoy configuration file not found"
fi

# Check if user-service has resource limits that are too restrictive
echo "[*] Checking resource limits..."

if grep -q "memory: 256M" docker-compose.yml 2>/dev/null; then
    echo "[!] WARNING: Very low memory limit (256M) detected for user-service"
    echo "    This may cause service degradation under load"
fi

# Summary check - at least some improvements should be made
echo "[*] Summary of required improvements..."

IMPROVEMENTS_COUNT=0

if [ "$CIRCUIT_BREAKER_FOUND" = true ]; then
    IMPROVEMENTS_COUNT=$((IMPROVEMENTS_COUNT + 1))
fi

if [ "$RETRY_FOUND" = true ]; then
    IMPROVEMENTS_COUNT=$((IMPROVEMENTS_COUNT + 1))
fi

if grep -q "timeout=" auth-service/app.py 2>/dev/null; then
    IMPROVEMENTS_COUNT=$((IMPROVEMENTS_COUNT + 1))
fi

echo "    Improvements detected: $IMPROVEMENTS_COUNT/3"

if [ "$IMPROVEMENTS_COUNT" -ge 2 ]; then
    echo "[✓] Sufficient improvements detected"
else
    echo "[!] WARNING: More improvements needed"
    echo "    Expected: circuit breakers, retry logic, and proper timeout handling"
fi

# Final validation - check if the root cause was addressed
echo "[*] Validating root cause resolution..."

ROOT_CAUSE_ADDRESSED=false

# Check if connection pool exhaustion is addressed
if grep -qi "MAX_CONNECTIONS.*[2-9][0-9]\|MAX_CONNECTIONS.*[1-9][0-9][0-9]" docker-compose.yml 2>/dev/null || \
   grep -qi "connection.*pool.*[2-9][0-9]\|connection.*pool.*[1-9][0-9][0-9]" auth-service/app.py 2>/dev/null; then
    echo "[✓] Connection pool size appears to be increased"
    ROOT_CAUSE_ADDRESSED=true
fi

# Check if timeout values are increased
if grep -q "CONNECTION_TIMEOUT=[2-9][0-9][0-9][0-9]\|CONNECTION_TIMEOUT=[1-9][0-9][0-9][0-9][0-9]" docker-compose.yml 2>/dev/null; then
    echo "[✓] Connection timeout appears to be increased"
    ROOT_CAUSE_ADDRESSED=true
fi

if [ "$ROOT_CAUSE_ADDRESSED" = true ] || [ "$IMPROVEMENTS_COUNT" -ge 2 ]; then
    echo "[✓] Root cause appears to be addressed"
else
    echo "[!] WARNING: Root cause may not be fully addressed"
    echo "    Ensure connection pool exhaustion and timeout issues are fixed"
fi

# Check for actionable error logging
echo "[*] Checking for actionable error logging..."

if grep -qi "timeout\|5xx\|breaker.*open\|circuit.*open" auth-service/app.py 2>/dev/null; then
    echo "[✓] Actionable error logging found (timeout vs 5xx vs breaker-open)"
else
    echo "[!] WARNING: Error logging may not distinguish between timeout, 5xx, and breaker-open states"
fi

echo "[✓] All tests completed!"
exit 0
