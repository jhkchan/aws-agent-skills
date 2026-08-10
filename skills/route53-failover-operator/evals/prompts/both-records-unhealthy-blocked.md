# Eval prompt: both-records-unhealthy-blocked

Diagnose the following Route 53 failover scenario and emit the
standard VERDICT block.

Operation: diagnose-failover
FQDN: api.example.com
Hosted zone: Z2ABCDEFGHIJK

```json
{
  "CurrentRecordSets": [
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"primary",
     "Failover":"PRIMARY","TTL":60,
     "ResourceRecords":[{"Value":"10.0.0.10"}],
     "HealthCheckId":"h-primary"},
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"secondary",
     "Failover":"SECONDARY","TTL":60,
     "ResourceRecords":[{"Value":"10.0.1.10"}],
     "HealthCheckId":"h-secondary"}
  ],
  "HealthCheckStatus": {
    "h-primary": "Unhealthy (Connection timed out, all 3 checker regions)",
    "h-secondary": "Unhealthy (No response from server, all 3 checker regions)"
  },
  "TestDnsAnswer": {
    "resolver_1.1.1.1": "Returns 10.0.0.10 AND 10.0.1.10 (both — Route 53 last-resort)"
  },
  "IndependentProbes": {
    "10.0.0.10:443 TCP": "TIMEOUT",
    "10.0.1.10:443 TCP": "CONNECTION REFUSED"
  }
}
```
