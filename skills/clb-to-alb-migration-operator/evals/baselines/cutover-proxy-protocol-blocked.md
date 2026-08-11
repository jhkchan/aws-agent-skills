# Baseline (no-skill) response: cutover-proxy-protocol-blocked

This file captures what a generic assistant produces WITHOUT the
clb-to-alb-migration-operator skill loaded.

---

To cut over DNS from the CLB to the ALB, update your Route 53 record:

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "app.example.com.",
      "Type": "A",
      "AliasTarget": {
        "DNSName": "dualstack.prod-game-alb-456.us-east-1.elb.amazonaws.com",
        "EvaluateTargetHealth": true
      }
    }
  }]
}'
```

Your targets are healthy so this should work fine.
