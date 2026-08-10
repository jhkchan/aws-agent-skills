# Baseline (no-skill) response: failback-to-primary-completed

This file captures what a generic assistant produces WITHOUT the
route53-failover-operator skill loaded.

---

To fail back to the primary, swap the records back so 10.0.0.10 is
PRIMARY again:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"primary","Failover":"PRIMARY","TTL":60,
        "ResourceRecords":[{"Value":"10.0.0.10"}],
        "HealthCheckId":"h-restored"}},
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"secondary","Failover":"SECONDARY","TTL":60,
        "ResourceRecords":[{"Value":"10.0.1.10"}]}}
    ]
  }'
```

After the change, test that the primary is serving traffic with
`dig api.example.com`.
