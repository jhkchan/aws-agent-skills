# Eval prompt: health-check-failing-failover

Diagnose the Route 53 failover routing failure for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: DNS failover routing always returns the SECONDARY record. The
PRIMARY record exists in the zone but is never served. The PRIMARY ALB
is confirmed healthy via direct `curl`.

```text
Domain: app.example.com
HostedZoneId: Z5GHIJKLMNO

Failover records (list-resource-record-sets):
  A PRIMARY:
    Value: dualstack.alb-primary.us-east-1.elb.amazonaws.com
    Failover: PRIMARY
    HealthCheckId: abc123def456
  A SECONDARY:
    Value: dualstack.alb-secondary.us-west-2.elb.amazonaws.com
    Failover: SECONDARY

Health check config (get-health-check abc123def456):
  Type: HTTPS
  FullyQualifiedDomainName: app.example.com
  ResourcePath: /health
  Port: 443

Health check status (get-health-check-status):
  Status: Unhealthy
  StatusReport.Reason: "The health check endpoint returned a 404"

ALB direct test:
  curl -sI https://dualstack.alb-primary.us-east-1.elb.amazonaws.com/health
  HTTP/2 200
```

The health check monitors `app.example.com` (the Route 53 record name
itself) instead of the ALB endpoint directly. This creates a circular
dependency: the health check depends on the record being served, but
the record is suppressed because the health check is unhealthy.
