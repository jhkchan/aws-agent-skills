# Traffic Policy and Resilience Reference

Load this reference when planning or executing weighted routes, retry
policies, timeout policies, or circuit breaking. The procedures below
cover canary/blue-green routing, retry/timeout semantics, and circuit
breaker configuration.

## Decision tree — routing strategy

| Scenario | Use | Why |
|---|---|---|
| Progressive rollout (low-risk config change) | **Canary 95/5 → 90/10 → 50/50 → 0/100** | Observe at each stage; auto-rollback on 5xx |
| High-risk change (new dependency, schema migration) | **Canary 99/1 → 90/10 → 50/50 → 0/100** | Internal-test traffic first; 60+ min observation |
| Incompatible API contract break | **Blue/Green 100/0 → 0/100** | Cannot progressively serve both versions; instant cutover |
| A/B testing (header-based) | **HTTP route `headers` match** | Route specific traffic class to v2; rest to v1 |
| Database connection pooling | **TCP route + connection pool** | TCP for non-L7; connection pool caps concurrent connections |
| gRPC service routing | **gRPC route `serviceName`/`methodName`** | Required for gRPC; HTTP match does not work |

## Weighted route procedure (canary)

**When to use:** progressive rollout of a new version.

**Pre-checks:**
1. Both virtual nodes exist with valid Cloud Map service discovery.
2. Cloud Map health checks pass for both versions' endpoints.
3. Snapshot current route via `describe-route --output json`.
4. Metrics dashboard ready (5xx rate, p99 latency, request count).

**Command sequence (90/10 canary):**
```bash
aws appmesh update-route \
  --mesh-name prod-checkout-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-service-v1", "weight": 90},
          {"virtualNode": "checkout-service-v2", "weight": 10}
        ]
      }
    }
  }'
```

**Rollback:**
```bash
aws appmesh update-route ... --spec '<previous weights from snapshot>'
```

There is no automatic rollback in App Mesh. Always snapshot first.

## Retry policy

**Applies to:** HTTP and gRPC routes only. TCP routes do not support
retries.

**HTTP retry events:**
- `gateway-error`: 502, 503, 504
- `5xx`: any 5xx response
- `reset`: connection reset
- `connect-failure`: TCP connection failed
- `refused-stream`: HTTP/2 stream refused
- `retriable-status-codes`: explicit list of status codes
- `retriable-headers`: header-based retry trigger

**gRPC retry events:**
- `cancelled`
- `deadline-exceeded`
- `internal`
- `resource-exhausted`
- `unavailable`

**Starting points:**
- API frontend: 3 retries, 2s perRetry, retry on `gateway-error`,
  `5xx`
- API backend: 2 retries, 1s perRetry, retry on `gateway-error`,
  `connect-failure`
- Streaming/WebSocket: 0 retries (idempotency not guaranteed)

**WARNING:** retries multiply load on downstreams during incidents.
A 3-retry policy triples the load on an already-failing downstream.
Pair with circuit breaking (outlier detection) to auto-eject
unhealthy endpoints.

## Timeout policy

**Two fields:**
- `per_request_timeout` (`requestTimeoutMillis`): max RTT for a
  single request, including retries.
- `idle_timeout` (`idleTimeoutMillis`): max time a connection can
  be idle before being closed.

**Starting points:**
- API frontend: request 5s, idle 300s
- API backend: request 2s, idle 60s
- Streaming/WebSocket: request disabled (or 1h), idle 1h
- Database proxy: request 10s, idle 30s

**WARNING:** `per_request_timeout` must be greater than the retry
`perRetryTimeoutMillis` * `maxRetries` — otherwise the request times
out before all retries complete.

Example: 3 retries * 2s perRetry = 6s minimum. Set
`per_request_timeout` to 7-10s to allow all retries.

## Circuit breaking procedure

**Two axes:**
- **Connection pool** (per-listener): caps concurrent connections,
  pending requests, total requests, retries.
- **Outlier detection** (per-listener): ejects unhealthy endpoints
  from the load-balancing pool.

**Command sequence:**
```bash
aws appmesh update-virtual-node \
  --mesh-name prod-checkout-mesh \
  --virtual-node-name checkout-service-v1 \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "connectionPool": {
        "http": {
          "maxConnections": 100,
          "maxPendingRequests": 50,
          "maxRequests": 200,
          "maxRetries": 3
        }
      },
      "outlierDetection": {
        "maxServerErrors": 5,
        "intervalMillis": 10000,
        "baseEjectionDurationMillis": 30000,
        "maxEjectionPercent": 50
      }
    }]
  }'
```

**Threshold semantics:**
- `maxConnections`: concurrent TCP connections to the listener.
  Exceeds → new connections queue.
- `maxPendingRequests`: HTTP/1.1 requests waiting for a connection.
  Exceeds → 503.
- `maxRequests`: total concurrent HTTP/2 requests. Exceeds → 503.
- `maxRetries`: concurrent retries. Exceeds → retry skipped.
- `maxServerErrors`: 5xx responses in `intervalMillis` window to
  trigger ejection.
- `baseEjectionDurationMillis`: minimum ejection time. Doubles on
  consecutive ejections.
- `maxEjectionPercent`: max fraction of endpoints ejected at once.
  Default 10%; set 50% for aggressive ejection.

## Common resilience misconfigurations

1. **Retry without circuit breaking:** retries multiply load on
   failing downstreams, cascading the failure. Always pair retries
   with outlier detection.

2. **`per_request_timeout` less than retry budget:** 3 retries * 2s
   perRetry = 6s; `per_request_timeout` 5s times out before retries
   complete. Fix: `per_request_timeout` >= retry budget + buffer.

3. **No `idle_timeout`:** long-lived connections (WebSocket, gRPC
   streaming) can pile up, exhausting the connection pool. Set
   `idle_timeout` to close idle connections.

4. **`maxEjectionPercent` too low (10%):** a 3-of-10 endpoint failure
   cannot trigger ejection of all 3 (would exceed 10%). Set 50% for
   aggressive ejection in incident scenarios.

5. **TCP route with retry policy:** TCP routes ignore retry policies.
   Use HTTP or gRPC for retry semantics; TCP only supports
   connection pool circuit breaking.

## Canary observability checklist

Before shifting weight from 90/10 to 100/0:
1. 5xx rate stable for 30+ minutes.
2. p99 latency within baseline range.
3. Cloud Map health checks pass for v2 endpoints.
4. No outlier detection ejections on v2 endpoints.
5. Rollback plan documented (snapshot weights, revert command ready).

If any check fails, hold at current weights or rollback.

## CLI boilerplate (moved from SKILL.md)

### Create a weighted route (canary: 90/10)

```bash
aws appmesh create-route \
  --mesh-name "prod-checkout-mesh" \
  --virtual-router-name "checkout-router" \
  --route-name "checkout-canary" \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-service-v1", "weight": 90},
          {"virtualNode": "checkout-service-v2", "weight": 10}
        ]
      },
      "retryPolicy": {
        "httpRetryEvents": ["gateway-error", "5xx"],
        "maxRetries": 3,
        "perRetryTimeoutMillis": 2000
      },
      "timeout": {
        "requestTimeoutMillis": 5000,
        "idleTimeoutMillis": 300000
      }
    }
  }'
```

For blue/green: swap weights to 100/0 (v1 full), then 0/100 (v2
full) over the deployment window.

### Configure circuit breaking (connection pool + outlier detection)

```bash
aws appmesh update-virtual-node \
  --mesh-name "prod-checkout-mesh" \
  --virtual-node-name "checkout-service-v1" \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "connectionPool": {
        "http": {"maxConnections": 100, "maxPendingRequests": 50, "maxRequests": 200, "maxRetries": 3}
      },
      "outlierDetection": {
        "maxServerErrors": 5,
        "intervalMillis": 10000,
        "baseEjectionDurationMillis": 30000,
        "maxEjectionPercent": 50
      }
    }]
  }'
```

