# Eval: ad-tech-event-ingest

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ad-tech ingest with sparse GSI (INCLUDE projection) + Streams for OpenSearch zero-ETL

## Prompt

Provision a DynamoDB table named "ad-events-prod" in us-east-1 for
real-time ad-tech event ingest. Events arrive at 50k/sec, bursty.
Partition key: adId (high cardinality). Sort key: eventTimestamp
(ISO 8601 — for time-range queries). Need a sparse GSI
"gsi_unprocessed_events" with partitionKey=status ("PENDING"),
sortKey=eventTimestamp, INCLUDE projection on "bidAmount" and
"advertiserId" attributes. TTL on "expiresAt" attribute (events
expire after 7 days). Streams NEW_AND_OLD_IMAGES for OpenSearch
zero-ETL indexing. SSE-KMS with customer CMK alias/adtech-kms-key.
PITR on. Tags: Environment=production, Workload=ad-tech.
Account ID: 123456789012.
