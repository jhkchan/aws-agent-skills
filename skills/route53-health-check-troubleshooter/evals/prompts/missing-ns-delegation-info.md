# Eval prompt: missing-ns-delegation-info

Diagnose the Route 53 DNS failover problem for the following scenario.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: DNS failover is not working for `example.com`. The primary
endpoint is down but clients are still being directed to it. The
secondary should be taking over.

```text
Domain: example.com
Hosted zone: not provided
Health check ID: not provided
Routing policy: not provided
Record TTL: not provided
NS delegation status: not provided
get-health-check-status output: not provided

Missing context:
  - Hosted zone ID: not provided
  - Health check config (type, interval, threshold): not provided
  - Health check status (healthy/unhealthy): not provided
  - Routing policy (FAILOVER / WEIGHTED / LATENCY): not provided
  - Record TTL on the primary and secondary: not provided
  - dig NS example.com output: not provided
```

Without the health check ID, routing policy, record TTL, hosted zone
ID, and NS delegation status, it is impossible to distinguish a health
check config issue, a routing policy association issue, a DNS TTL
caching issue, or an NS delegation problem. Emit INSUFFICIENT_DATA
with the specific missing fields needed to proceed.
