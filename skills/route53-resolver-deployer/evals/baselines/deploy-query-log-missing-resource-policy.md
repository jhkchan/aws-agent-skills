# Baseline (no-skill) response: deploy-query-log-missing-resource-policy

This file captures what a generic assistant produces WITHOUT the
route53-resolver-deployer skill loaded.

---

To enable query logging, run:

```bash
aws route53resolver put-resolver-query-log-config \
  --name prod-query-logs-cw \
  --destination-arn arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/prod

aws route53resolver associate-resolver-query-log-config \
  --resolver-query-log-config-id <id> \
  --resource-id vpc-0abc123
```

Your DNS queries will now be logged to CloudWatch.
