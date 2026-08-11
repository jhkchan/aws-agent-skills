# Eval prompt: circuit-breaking-paired-with-retry-ready

Configure circuit breaking on a virtual node that already has a
retry policy on its route. Plan the operation and emit the standard
VERDICT block.

Operation: configure-circuit-breaking
Mesh: prod-checkout-mesh
Virtual node: checkout-service-v1
Listener: HTTP port 8080
Connection pool: maxConnections 100, maxPendingRequests 50, maxRequests 200, maxRetries 3
Outlier detection: maxServerErrors 5, intervalMillis 10000, baseEjectionDurationMillis 30000, maxEjectionPercent 50
Existing retry policy on route: gateway-error + 5xx, 3 retries, 2s perRetry

```json
{
  "CircuitBreakingChecks": {
    "appmesh.describe-virtual-node.checkout-service-v1": {
      "exists": true,
      "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
      "listener": {"port": 8080, "protocol": "http"}
    },
    "appmesh.describe-route.checkout-canary": {
      "retryPolicy": {"httpRetryEvents": ["gateway-error", "5xx"], "maxRetries": 3, "perRetryTimeoutMillis": 2000},
      "timeout": {"requestTimeoutMillis": 5000, "idleTimeoutMillis": 300000}
    },
    "retry_budget_analysis": {
      "maxRetries_times_perRetry": 6,
      "per_request_timeout": 5,
      "request_times_out_before_retries_complete": true
    }
  }
}
```
