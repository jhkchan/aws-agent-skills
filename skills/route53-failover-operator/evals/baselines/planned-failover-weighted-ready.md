# Baseline (no-skill) response: planned-failover-weighted-ready

This file captures what a generic assistant produces WITHOUT the
route53-failover-operator skill loaded.

---

To shift traffic from blue to green, update the weighted records:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"blue","Weight":0,
        "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}]}},
      {"Action":"UPSERT","ResourceRecordSet":{
        "Name":"api.example.com.","Type":"A",
        "SetIdentifier":"green","Weight":100,
        "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}]}}
    ]
  }'
```

After the change, verify with `dig api.example.com` to confirm traffic
is going to green.
