# Baseline (no-skill) — weighted-without-health-check

> This is the response a model produces **without** the skill definition.
> It applies the weighted routing without health checks, leaving the
> canary target dead-traffic-prone with no alarm. Generated for with-
> skill-vs-baseline comparison.

---

Sure, here's the weighted routing:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z3DABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"CREATE","ResourceRecordSet":{"Name":"api.example.com.","Type":"A","SetIdentifier":"primary","Weight":90,"TTL":300,"ResourceRecords":[{"Value":"10.0.0.10"}]}},
      {"Action":"CREATE","ResourceRecordSet":{"Name":"api.example.com.","Type":"A","SetIdentifier":"canary","Weight":10,"TTL":300,"ResourceRecords":[{"Value":"10.0.0.20"}]}}
    ]
  }'
```

That gives you a 90/10 weighted split.
