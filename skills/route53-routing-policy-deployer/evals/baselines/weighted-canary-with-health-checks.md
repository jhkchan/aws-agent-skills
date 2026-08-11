# Baseline (no-skill) — weighted-canary-with-health-checks

> This is the response a model produces **without** the skill definition.
> It creates the two weighted records but omits health checks, posts them
> as separate change-batches (non-atomic), and sets TTL to 300 (too slow
> for a canary). Generated for with-skill-vs-baseline comparison.

---

To create a weighted routing policy:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2DABCDEFGHIJK \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com.",
        "Type": "A",
        "SetIdentifier": "primary",
        "Weight": 90,
        "TTL": 300,
        "ResourceRecords": [{"Value": "10.0.0.10"}]
      }
    }]
  }'

aws route53 change-resource-record-sets \
  --hosted-zone-id Z2DABCDEFGHIJK \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com.",
        "Type": "A",
        "SetIdentifier": "canary",
        "Weight": 10,
        "TTL": 300,
        "ResourceRecords": [{"Value": "10.0.0.20"}]
      }
    }]
  }'
```

That sets up your 90/10 weighted canary.
