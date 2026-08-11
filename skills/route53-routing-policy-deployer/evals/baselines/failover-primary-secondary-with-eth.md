# Baseline (no-skill) — failover-primary-secondary-with-eth

> This is the response a model produces **without** the skill definition.
> It uses `Type: CNAME` for the alias (wrong — alias must be `A`), sets
> `EvaluateTargetHealth: false` (defeats DNS-level failover), and omits
> the PRIMARY health check. Generated for with-skill-vs-baseline
> comparison.

---

For DR failover, you can use a CNAME to the ALB as PRIMARY:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z4DABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"CREATE","ResourceRecordSet":{"Name":"dr.example.com.","Type":"CNAME","SetIdentifier":"primary","Failover":"PRIMARY","TTL":300,"ResourceRecords":[{"Value":"my-alb-12345.us-east-1.elb.amazonaws.com"}]}},
      {"Action":"CREATE","ResourceRecordSet":{"Name":"dr.example.com.","Type":"A","SetIdentifier":"secondary","Failover":"SECONDARY","TTL":300,"ResourceRecords":[{"Value":"10.99.0.20"}]}}
    ]
  }'
```

The DNS will resolve to the ALB normally and fall back to 10.99.0.20
if the ALB is unreachable.
