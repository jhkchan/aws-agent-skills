# Baseline (no-skill) response: emergency-failover-ttl-too-high-blocked

This file captures what a generic assistant produces WITHOUT the
route53-failover-operator skill loaded.

---

Since the primary is down, swap the PRIMARY and SECONDARY records to
point traffic at the secondary:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"primary","Failover":"PRIMARY","TTL":300,
        "ResourceRecords":[{"Value":"10.0.1.10"}],
        "HealthCheckId":"h-secondary"}},
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"secondary","Failover":"SECONDARY","TTL":300,
        "ResourceRecords":[{"Value":"10.0.0.10"}]}}
    ]
  }'
```

This will redirect traffic to the secondary endpoint.
