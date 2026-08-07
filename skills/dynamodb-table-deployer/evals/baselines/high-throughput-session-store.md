# Baseline (no-skill) — high-throughput-session-store

> This is the response a model produces **without** the skill definition.
> It lists some AWS CLI commands but misses the partition-key shaping
> rationale, the sparse GSI pattern for userId lookup, the on-demand
> burst-bucket caveat, the NEW_AND_OLD_IMAGES stream view choice, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Here's how to create a session store DynamoDB table:

1. Create the table:
```bash
aws dynamodb create-table --table-name prod-sessions \
  --attribute-definitions AttributeName=sessionId,AttributeType=S AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=sessionId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

2. Add a GSI on userId:
```bash
aws dynamodb update-table --table-name prod-sessions \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"gsi_by_userId","KeySchema":[{"AttributeName":"userId","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}}]'
```

3. Enable encryption:
```bash
aws dynamodb update-table --table-name prod-sessions \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/prod-dynamodb-key
```

4. Enable TTL:
```bash
aws dynamodb update-time-to-live --table-name prod-sessions \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt
```

5. Enable streams:
```bash
aws dynamodb update-table --table-name prod-sessions \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE
```

6. Enable PITR:
```bash
aws dynamodb update-continuous-backups --table-name prod-sessions \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

That should cover everything for a session store.
