# Baseline (no-skill) response: flow-logs-not-enabled

This file captures what a generic assistant produces WITHOUT the
nat-gateway-traffic-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, VPC Flow Logs
requirement gate, per-service traffic analysis dependency, NEED_MORE_INFO
classification).

---

Your VPC has two NAT Gateways costing about $93/month. Without VPC Flow
Logs enabled, it's hard to know what traffic is going through them. You
should enable Flow Logs so you can see which AWS services the traffic
is going to.

Once you have Flow Logs data, you can figure out if creating VPC
endpoints for S3, DynamoDB, or other services would save you money.

To enable Flow Logs:

```
aws ec2 create-flow-logs --resource-ids vpc-flow-logs-not-enabled \
  --resource-type VPC --traffic-type ALL \
  --log-group-name /vpc/flowlogs/vpc-flow-logs-not-enabled \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/flowlogs
```

After a week of collecting data, check which services are using the
most NAT traffic and create endpoints for those. S3 and DynamoDB
endpoints are free, so those would be a good start.
