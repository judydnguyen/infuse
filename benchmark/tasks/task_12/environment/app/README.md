# Microservices Platform - Timeout Resolution Task

This Docker Compose setup contains 8 microservices with intermittent timeout issues between auth-service and user-service.

## Architecture

- **auth-service**: Authentication service that calls user-service
- **user-service**: User management service with slow database queries
- **product-service**: Product catalog service
- **order-service**: Order processing service
- **payment-service**: Payment processing service
- **inventory-service**: Inventory management service
- **notification-service**: Notification service
- **gateway-service**: API gateway
- **envoy**: Service mesh proxy

## Known Issues

1. **Connection Pool Exhaustion**: auth-service has only 10 max connections
2. **Low Timeouts**: CONNECTION_TIMEOUT=1000ms is too low
3. **No Circuit Breakers**: Services lack circuit breaker patterns
4. **No Retry Logic**: No exponential backoff or retry mechanisms
5. **Resource Constraints**: user-service limited to 256M memory
6. **Slow Database Queries**: user-service has 30% failure rate with random delays
7. **Insufficient Connection Pool**: user-service has only 5 DB connections
8. **Missing Envoy Configuration**: No circuit breakers or retry policies in Envoy

## Task Goal

Identify the root cause of intermittent timeouts and implement:
- Circuit breakers to prevent cascading failures
- Retry logic with exponential backoff
- Proper timeout configurations
- Connection pool size adjustments
- Envoy service mesh configuration improvements

## Running the Services

```bash
docker-compose up --build
```

## Analyzing Logs

Logs are available in the `logs/` directory and can be analyzed across all containers:

```bash
# View all timeout errors
grep -r "timeout" logs/

# View connection pool issues
grep -r "pool.*exhaust" logs/

# Check service-specific logs
docker-compose logs auth-service
docker-compose logs user-service
```

## Testing

```bash
# Test auth service
curl http://localhost:8080/api/auth/validate/1

# Check service health
curl http://localhost:5000/health  # auth-service
curl http://localhost:5000/health  # user-service (if exposed)
```
