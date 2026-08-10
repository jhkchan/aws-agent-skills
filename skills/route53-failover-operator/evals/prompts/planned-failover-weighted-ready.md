# Eval prompt: planned-failover-weighted-ready

Plan the following Route 53 planned weighted failover operation and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: planned-failover
FQDN: api.example.com
Hosted zone: Z2ABCDEFGHIJK

```json
{
  "CurrentRecordSets": [
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"blue",
     "Weight":100,"TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
     "HealthCheckId":"h-blue123"},
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"green",
     "Weight":0,"TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
     "HealthCheckId":"h-abcdef1234"}
  ],
  "HealthCheckStatus": {
    "h-blue123": "Healthy (3 checker regions)",
    "h-abcdef1234": "Healthy (3 checker regions)"
  },
  "SecondaryReachability": {
    "10.0.1.10:443 TCP probe": "OK"
  },
  "TestDnsAnswer": {
    "resolver_1.1.1.1": "10.0.0.10 (blue, as expected)"
  },
  "CloudWatchAlarms": {
    "api-example-failover": "OK (on AWS/Route53 HealthCheckStatus for h-blue123)"
  },
  "CrossAccount": "Hosted zone in account 111111111111 (same as operator). No cross-account grant needed."
}
```
