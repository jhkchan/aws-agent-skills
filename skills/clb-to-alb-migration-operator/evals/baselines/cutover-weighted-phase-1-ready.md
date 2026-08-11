# Baseline (no-skill) response: cutover-weighted-phase-1-ready

This file captures what a generic assistant produces WITHOUT the
clb-to-alb-migration-operator skill loaded.

---

For a weighted cutover, set up two Route 53 records with weights:

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Changes": [
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":95,"AliasTarget":{"DNSName":"dualstack.prod-web-clb-123.us-east-1.elb.amazonaws.com"}}},
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"alb","Weight":5,"AliasTarget":{"DNSName":"dualstack.prod-web-alb-456.us-east-1.elb.amazonaws.com"}}}
  ]
}'
```

Then monitor for a while and increase the ALB weight.
