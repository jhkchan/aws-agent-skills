# Baseline (no-skill) — missing-cmk-and-key-schema

> This is the response a model produces **without** the skill definition.
> It blindly issues a create-table command without flagging the missing
> partition-key design rationale or the missing CMK ARN — exactly the
> prerequisites the skill is designed to catch. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create your orders table:

```bash
aws dynamodb create-table --table-name orders-prod \
  --attribute-definitions AttributeName=orderId,AttributeType=S \
  --key-schema AttributeName=orderId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true,SSEType=KMS
```

You'll need to specify the KMS key when prompted. After creation, you
can enable PITR and deletion protection:

```bash
aws dynamodb update-continuous-backups --table-name orders-prod \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
aws dynamodb update-table --table-name orders-prod --deletion-protection-enabled
```

orderId as the partition key should work fine for orders.
