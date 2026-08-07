# Baseline (no-skill) — cost-optimized-ia-table

> This is the response a model produces **without** the skill definition.
> It misses the Standard-IA table class entirely (defaults to STANDARD),
> uses provisioned capacity (paying for minimum capacity the table does
> not need), and omits the cost-optimization rationale. Generated for
> with-skill-vs-baseline comparison.

---

To create an archive table:

```bash
aws dynamodb create-table --table-name historical-orders-archive \
  --attribute-definitions AttributeName=orderId,AttributeType=S \
  --key-schema AttributeName=orderId,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/archive-kms-key \
  --deletion-protection-enabled
```

Then enable TTL and PITR:

```bash
aws dynamodb update-time-to-live --table-name historical-orders-archive \
  --time-to-live-specification Enabled=true,AttributeName=retainUntil
aws dynamodb update-continuous-backups --table-name historical-orders-archive \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

That should work for your archive use case.
