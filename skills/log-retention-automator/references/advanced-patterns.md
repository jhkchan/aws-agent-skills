# Advanced patterns — log-retention-automator

Expert-knowledge deep dives and edge cases moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — three facts that drive the design

- **Retention is per-log-group.** There is no account-level default.
  Every log group created without an explicit retention policy stays
  Never Expire indefinitely. This is the single largest source of
  unintended CloudWatch Logs cost in AWS accounts.
- **Auto-retention on CreateLogGroup** closes the gap: an EventBridge
  rule on the `CreateLogGroup` API call triggers a Lambda (or SSM
  Automation) that applies the tag-derived retention within seconds of
  creation. Without this, new log groups remain Never Expire until the
  next manual sweep.
- **S3 Firehose export replaces Never Expire for compliance.** Logs
  that must be retained beyond the maximum 3653-day (10-year) CloudWatch
  tier — or logs where the per-GB CloudWatch ingest + storage cost
  exceeds S3 storage cost — should be streamed to S3 via Kinesis
  Firehose. CloudWatch retention then becomes the "hot query" window
  (e.g., 90d) while S3 holds the compliance archive (indefinite).

## Step 0: Expert knowledge — non-obvious CloudWatch Logs behaviors

These behaviors change the automation design if ignored:

- **`put-retention-policy` is eventually consistent.** After the API
  returns success, `describe-log-groups` may still show the old
  `retentionInDays` for several seconds. Use a 5-second sleep before
  verifying.

- **Log groups created by AWS services (Lambda, ECS, CloudTrail) are
  NOT auto-tagged.** The tag-based retention map will miss these
  unless an EventBridge rule applies a default or the auto-retention
  Lambda fires on `CreateLogGroup`.

- **Shortening retention triggers asynchronous bulk deletion.** 500 GB
  of logs with retention changed from 365d to 7d begins deleting within
  seconds. No confirmation, no undo. Logs are permanently gone.

- **`delete-retention-policy` resets to Never Expire.** This removes
  the retention policy entirely — accidental calls cause unbounded
  growth.

- **Subscription filters (limit 2 per log group since 2024) and
  metric filters survive retention changes.** Retention controls data
  lifecycle, not pipelines. But deleting a log group destroys both.

- **Metric filters are evaluated at ingestion time.** Changing
  retention does not affect already-emitted metrics. Inventory metric
  filters before any destructive log group operation.

- **Firehose buffers for at least 60 seconds (or 5 MB).** Logs in the
  last buffer window before expiry may not reach S3. Use a retention
  window at least 1 day longer than the Firehose buffer.

- **Cross-account subscription filter delivery does NOT carry source
  retention.** The destination applies its own retention. Always
  configure retention on BOTH source and destination.

## Step 9: multi-account StackSet rollout CLI

```bash
aws cloudformation create-stack-set \
  --stack-set-name cw-log-retention-automation \
  --template-body file://retention-automation.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment 'Enabled=true,RetainStacksOnAccountRemoval=false' \
  --capabilities CAPABILITY_IAM

aws cloudformation create-stack-instances \
  --stack-set-name cw-log-retention-automation \
  --deployment-targets OrganizationalUnitIds='["r-xxxx"]' \
  --regions '["us-east-1","us-west-2"]'
```

## Recent AWS features (2024-2026)

- **Subscription filter limit increased to 2 per log group (2024):**
  Previously limited to 1. Now a log group can fan out to both a
  Firehose archival pipeline AND a real-time Lambda processor. This
  simplifies the "archive + process" dual-pipeline pattern.

- **CloudWatch Logs data protection (2024-2025):** Masking of
  sensitive data (PII, credentials) at ingestion. Complementary to
  retention — data protection runs before logs are stored, so
  retention policies apply to already-masked data.

- **Firehose Direct Put for CloudWatch Logs (2024):** Firehose can
  now natively accept CloudWatch Logs subscription filter data
  without an intermediary Lambda. Reduces cost and latency for the
  archival pipeline.

- **CloudWatch Logs account-level policies (2024-2025):** AWS
  introduced account-level data protection policies. While not a
  full account-level retention default, it indicates AWS is moving
  toward account-level log governance. Monitor for a future
  account-level retention feature.

- **Organizations-wide log archive (2025-2026):** AWS launched a
  service-linked approach for centralized log archival across an
  Organizations fleet, reducing the need for custom cross-account
  Lambda sweeps. Evaluate as an alternative to the StackSet pattern.

- **CloudWatch Logs Insights query scheduling (2025):** Scheduled
  saved queries with S3 export. Useful for periodic compliance
  reports from log data before it expires.
