# Eval prompt: calculated-hc-inverted-logic

Diagnose the Route 53 health check failure for the following
configuration. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: Route 53 calculated health check `hc-calc-inverted` reports
unhealthy even though both child health checks are healthy. DNS
failover is triggering to the secondary endpoint despite the primary
being fully operational.

```text
HealthCheckId: hc-calc-inverted
Type: CALCULATED
ChildHealthChecks: [hc-child-north, hc-child-south]
Inverted: true
HealthCheckStatus: Unhealthy

Child health checks:
  hc-child-north: Healthy (HTTPS, endpoint in us-east-1)
  hc-child-south: Healthy (HTTPS, endpoint in us-east-2)

RoutingPolicy: FAILOVER
PrimaryRecord: app.example.com (HealthCheckId: hc-calc-inverted)
SecondaryRecord: app.example.com (Failover: SECONDARY)
```

The calculated health check uses default AND logic (healthy when ALL
children are healthy). Both children are healthy, so the underlying
expression evaluates to healthy. But `Inverted: true` flips the
result to unhealthy, causing the calculated health check to report
unhealthy and triggering failover. Identify the inverted logic as the
root cause.
