# Diagnostic Commands (load on demand) — CloudWatch Logs Cost Optimizer

Pre-flight data-gate sources, per-step CLI listings, and pre-flight safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight: data gate — prose, required data sources, ground-truth rule (moved from SKILL.md)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/cloudwatch-logs-pricing-and-retention.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Log group configuration + retention: `aws logs describe-log-groups`
2. Ingestion volume (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Logs --metric-name IncomingBytes`
3. PutLogEvents request count: `aws cloudwatch get-metric-statistics --namespace AWS/Logs --metric-name IncomingLogEvents`
4. Metric filters: `aws logs describe-metric-filters --log-group-name <name>`
5. Subscription filters: `aws logs describe-subscription-filters --log-group-name <name>`
6. Logs Insights query volume (CloudTrail): `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=StartQuery`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --service AmazonCloudWatch`

When CloudWatch metrics and Cost Explorer disagree, Cost Explorer is the
ground truth for actual charges — metrics inform the optimization lever,
Cost Explorer confirms the dollar impact.
---

## Step 1 — the retention sweep CLI (moved from SKILL.md)

**The retention sweep CLI:**
```bash
# List all log groups with Never expire (RetentionInDays absent or null)
aws logs describe-log-groups --output json | \
  jq '.logGroups[] | select(.retentionInDays == null or .retentionInDays == 0) |
      {logGroupName, storedBytes}'

# Set retention to 30 days
aws logs put-retention-policy \
  --log-group-name /aws/lambda/order-processor-prod \
  --retention-in-days 30
```
---

## Step 2 — creating a metric filter (moved from SKILL.md)

**Creating a metric filter:**
```bash
aws logs put-metric-filter \
  --log-group-name /aws/lambda/order-processor-prod \
  --filter-name ErrorCount \
  --filter-pattern '"ERROR"' \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=AppMetrics,metricValue=1,defaultValue=0
```
---

## Step 3 — CloudWatch agent buffer configuration (moved from SKILL.md)

**Agent configuration (JSON snippet):**
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/application.log",
            "log_group_name": "/app/application",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          }
        ]
      }
    },
    "log_stream_name": "{instance_id}",
    "batch_count": 10000,
    "batch_size": 1048576,
    "batch_wait_time": 60
  }
}
```
---

## Step 4 — Firehose delivery stream for log archival (moved from SKILL.md)

**Firehose delivery stream for log archival:**
```bash
aws firehose create-delivery-stream \
  --delivery-stream-name log-archive-stream \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::<acct>:role/firehose-s3-role,\
    BucketARN=arn:aws:s3:::log-archive-bucket,\
    Prefix=logs/,!BufferingSize=5,!BufferingInterval=300
```
---

## Step 7 — data protection policy CLI (moved from SKILL.md)

**CLI to create a data protection policy:**
```bash
aws logs put-account-policy \
  --policy-name pii-protection-policy \
  --policy-type DATA_PROTECTION_POLICY \
  --policy-document '{
    "Name": "pii-protection",
    "Version": "2021-08-01",
    "Identifiers": [
      {"Type": "EmailAddress"},
      {"Type": "Phone"},
      {"Type": "CreditCard"}
    ],
    "DeletionProtection": false
  }'
```
---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Retention changes delete data.** Setting retention from Never to 30
  days will delete logs older than 30 days within hours. Confirm the
  operator has verified no compliance or investigation need for older
  logs.
- **Metric filter creation is immediate.** Filters start processing new
  log events within seconds. Historical events are NOT backfilled.
- **Firehose delivery stream takes 5-10 minutes to become active.**
  Verify the stream is `ACTIVE` before relying on it for log delivery.
- **Subscription filter changes can break downstream consumers.**
  Removing a subscription filter stops delivery to Lambda/Kinesis. Verify
  no downstream service depends on the filter before modifying.
- **Data protection policy changes apply to NEW log events only.** Existing
  stored events are not retroactively masked.
- **Agent buffer changes require agent restart.** Update the agent config
  file, then `systemctl restart amazon-cloudwatch-agent`. Existing log
  streams are not interrupted.
- **VPC Flow Log destination changes are not retroactive.** New logs go
  to the new destination; existing logs remain in the old destination
  until their retention expires.
- **Bulk-operation limit:** Process at most 10 log groups per batch.
  Sort by `StoredBytes` (largest first), verify each batch before
  proceeding. Abort if any log group shows a spike in errors or missing
  data post-change.
