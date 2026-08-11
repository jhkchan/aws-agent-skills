# Eval prompt: dns-failover-ttl-stale-record

Diagnose the Route 53 DNS failover problem for the following
configuration. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: After the primary endpoint went down at T+0, DNS did not
switch to the secondary until T+7 minutes. The health check flipped
to unhealthy at T+90s (as expected with RequestInterval: 30,
FailureThreshold: 3), but clients continued hitting the old primary
IP for several more minutes due to DNS TTL caching.

```text
HealthCheckId: hc-ttl-stale
Type: HTTP
RequestInterval: 30
FailureThreshold: 3
IPAddress: 54.210.1.10
Port: 80
HealthCheckStatus: Unhealthy (flipped at T+90s)

RoutingPolicy: FAILOVER
PrimaryRecord: app.example.com (HealthCheckId: hc-ttl-stale)
SecondaryRecord: app.example.com (Failover: SECONDARY)
TTL: 300

DNS resolution verification:
  dig @8.8.8.8 app.example.com +short:
    T+0s:   54.210.1.10 (primary — expected)
    T+90s:  54.210.1.10 (primary — HC flipped but DNS cached)
    T+300s: 54.210.1.10 (primary — TTL not yet expired on 8.8.8.8)
    T+360s: 54.210.2.20 (secondary — TTL expired, new record served)

  dig @<authoritative-ns> app.example.com +short:
    T+90s: 54.210.2.20 (secondary — Route 53 updated the record)
```

The authoritative servers switched at T+90s (when the health check
flipped), but public resolvers cached the old record for the full TTL
of 300 seconds. The total failover time was ~390 seconds (90s
detection + 300s TTL). Identify the DNS TTL as the dominant factor
in the delayed failover.
