# Baseline (no-skill) — ad-tech-event-ingest

> This is the response a model produces **without** the skill definition.
> It picks ALL projection for the GSI (write-amplification risk), misses
> the sparse-index pattern (the GSI would include ALL items, not just
> PENDING), uses NEW_IMAGE instead of NEW_AND_OLD_IMAGES (insufficient
> for OpenSearch zero-ETL diff), and omits the on-demand burst-bucket
> caveat. Generated for with-skill-vs-baseline comparison.

---

For an ad-tech event table:

1. Create the table:
```bash
aws dynamodb create-table --table-name ad-events-prod \
  --attribute-definitions \
    AttributeName=adId,AttributeType=S \
    AttributeName=eventTimestamp,AttributeType=S \
    AttributeName=status,AttributeType=S \
  --key-schema \
    AttributeName=adId,KeyType=HASH \
    AttributeName=eventTimestamp,KeyType=RANGE \
  --global-secondary-indexes '[{
    "IndexName":"gsi_unprocessed_events",
    "KeySchema":[{"AttributeName":"status","KeyType":"HASH"},{"AttributeName":"eventTimestamp","KeyType":"RANGE"}],
    "Projection":{"ProjectionType":"ALL"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/adtech-kms-key
```

2. Enable Streams:
```bash
aws dynamodb update-table --table-name ad-events-prod \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE
```

3. Enable TTL:
```bash
aws dynamodb update-time-to-live --table-name ad-events-prod \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt
```

4. Enable PITR:
```bash
aws dynamodb update-continuous-backups --table-name ad-events-prod \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

The GSI on status will let you query for PENDING events.
