# Eval prompt: cert-mismatch-https-health-check

Diagnose the Route 53 health check failure for the following
configuration. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: Route 53 health check `hc-cert-mismatch` reports unhealthy.
The endpoint at `10.0.1.10:443` (fronted by a public ALB) is reachable
from within the VPC via `curl -k`. DNS failover should redirect to the
secondary, but the primary record is still being served because the
health check has not yet flipped on all regions.

```text
HealthCheckId: hc-cert-mismatch
Type: HTTPS
FullyQualifiedDomainName: health.example.com
IPAddress: 10.0.1.10 (public via ALB)
Port: 443
EnableSNI: true
RequestInterval: 30
FailureThreshold: 3
ResourcePath: /

RoutingPolicy: FAILOVER
PrimaryRecord: api.example.com (Failover: PRIMARY, HealthCheckId: hc-cert-mismatch)
SecondaryRecord: api.example.com (Failover: SECONDARY)
TTL: 60

Certificate on the endpoint (openssl s_client):
  subject: CN=api.example.com
  SAN: [api.example.com, www.example.com]
  "health.example.com" is NOT in the SAN list

Health check status (get-health-check-status):
  All 15+ regions reporting unhealthy
  StatusReason: "The SSL certificate failed validation"
```

The HTTPS health check validates the TLS certificate against the FQDN
(`health.example.com`), but the endpoint serves a certificate for
`api.example.com` / `www.example.com`. The health check correctly
reports unhealthy due to certificate name mismatch. Identify the
certificate mismatch as the root cause.
