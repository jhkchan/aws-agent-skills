# Baseline (no-skill) — compliance-audit-log-table

> This is the response a model produces **without** the skill definition.
> It produces generic CLI commands but misses the composite partition-key
> rationale (tenantId#yyyy-mm), the absence-of-TTL regulatory decision,
> the explicit autoscaling registration on the base table, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

To create an audit log table:

1. Create the table with provisioned capacity:
```bash
aws dynamodb create-table --table-name audit-events-prod \
  --attribute-definitions AttributeName=eventId,AttributeType=S \
  --key-schema AttributeName=eventId,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=10000,WriteCapacityUnits=10000 \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/audit-kms-key
```

2. Enable deletion protection:
```bash
aws dynamodb update-table --table-name audit-events-prod --deletion-protection-enabled
```

3. Enable PITR:
```bash
aws dynamodb update-continuous-backups --table-name audit-events-prod \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

For autoscaling you can configure it in the console. Items should not
expire because this is an audit log.
