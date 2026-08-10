# Eval prompt: emergency-failover-ttl-too-high-blocked

Plan the following Route 53 emergency failover operation and emit the
standard VERDICT block.

Operation: emergency-failover
FQDN: api.example.com
Hosted zone: Z2ABCDEFGHIJK

```json
{
  "CurrentRecordSets": [
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"primary",
     "Failover":"PRIMARY","TTL":300,
     "ResourceRecords":[{"Value":"10.0.0.10"}],
     "HealthCheckId":"h-primary"},
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"secondary",
     "Failover":"SECONDARY","TTL":300,
     "ResourceRecords":[{"Value":"10.0.1.10"}]}
  ],
  "HealthCheckStatus": {
    "h-primary": "Unhealthy (reason: Connection timed out, 3 consecutive failures, all checker regions)"
  },
  "SecondaryReachability": {
    "10.0.1.10:443 TCP probe": "OK"
  },
  "TestDnsAnswer": {
    "resolver_1.1.1.1": "Returns 10.0.0.10 AND 10.0.1.10 (both — Route 53 last-resort)"
  }
}
```
