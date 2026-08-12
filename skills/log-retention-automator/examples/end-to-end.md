# End-to-end usage scenario: log-retention-automator

A walkthrough showing the skill designing a complete log retention
automation rollout: tag-based retention for existing groups, an
EventBridge CreateLogGroup rule for new groups, and an S3 Firehose
archival pipeline for compliance logs. Demonstrates the full
Never Expire replacement strategy.

## Input (user prompt)

> Automate CloudWatch Logs retention across our production account.
> We have 200 log groups, 120 of which are Never Expire. We want
> tag-based retention (prod=90d, staging=30d, dev=7d, untagged=14d).
> Compliance logs (audit + CloudTrail) need 7-year retention with
> 90-day hot window in CloudWatch and S3 archival via Firehose. Also
> deploy auto-retention for new log groups.

```
Design reference: prod-log-retention-rollout
Account: 111111111111
Region: us-east-1

Existing state:
  200 log groups total
  120 at Never Expire
  80 at various existing retention (30d, 60d, 90d)
  Tag coverage: Environment tag on 160/200 groups

Tag map: Environment=prod -> 90d, staging -> 30d, dev -> 7d
Account default: 14d (for untagged groups)

Compliance log groups:
  /aws/lambda/audit-logger (5 GB/day)
  /aws/cloudtrail/management-events (20 GB/day)
  Required: 7-year retention
  Hot window: 90d in CloudWatch
  Cold: S3 via Firehose with Glacier lifecycle

New log groups: auto-apply via EventBridge CreateLogGroup rule
DLQ: SQS for failed auto-retention
Multi-account: not yet (single account deployment)
```

## Skill output

```text
RETENTION: prod-log-retention-rollout
LOG_GROUP: account-wide (200 groups) + compliance archival
POLICY:
  - Tag map: Environment=prod -> 90d, staging -> 30d, dev -> 7d, untagged -> 14d
  - Tier: 90/30/7/14 (all in allowed set)
  - Default: 14 days (account-level fallback for 40 untagged groups)
  - Compliance: 2557d (7-year tier) for audit + CloudTrail log groups
TRIGGER:
  - Existing: Batch put-retention-policy loop (200 groups, 0.2s rate limit)
  - New: EventBridge CreateLogGroup -> auto-retention-applier Lambda (default-first strategy)
  - Sweep: Daily scheduled Lambda for groups missed by EventBridge
ARCHIVAL: Firehose log-archive-compliance -> S3 com-company-log-archive-compliance
  - Buffer: 5MB / 300s, GZIP compression
  - S3 lifecycle: Standard(0d) -> Standard-IA(30d) -> Glacier(90d) -> Deep Archive(180d)
  - Firehose backup: enabled to com-company-log-archive-backup
  - Athena table: partitioned by year/month/day for compliance queries
VERDICT: AUTOMATION_DEPLOYED
GAP: None
NEVER_EXPIRE_GROUPS: 120 (will be resolved by batch sweep)
COST_EXPOSURE: ~$450/month in Never Expire storage (estimated 15 TB at $0.03/GB)
TEMPLATE:
  # 1. Batch apply to existing groups
  aws logs put-retention-policy --log-group-name /aws/lambda/prod-api --retention-in-days 90

  # 2. EventBridge rule for new groups
  aws events put-rule --name auto-retention-new-log-groups --event-pattern '{"source":["aws.logs"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"eventSource":["logs.amazonaws.com"],"eventName":["CreateLogGroup"]}}'

  # 3. Firehose archival for compliance logs
  aws firehose create-delivery-stream --delivery-stream-name log-archive-compliance --delivery-stream-type DirectPut --extended-s3-destination-configuration '{"RoleARN":"arn:aws:iam::111111111111:role/FirehoseS3Role","BucketARN":"arn:aws:s3:::com-company-log-archive-compliance","Prefix":"firehose/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/","BufferingHints":{"SizeInMBs":5,"IntervalInSeconds":300},"CompressionFormat":"GZIP"}'

  aws logs put-subscription-filter --log-group-name /aws/lambda/audit-logger --filter-name archive-to-firehose --filter-pattern "" --destination-arn arn:aws:firehose:us-east-1:111111111111:deliverystream/log-archive-compliance --role-arn arn:aws:iam::111111111111:role/CWLogsToFirehoseRole
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED.** The
tag-based sweep resolves all 120 Never Expire groups. The EventBridge
rule catches new groups. The Firehose pipeline handles 7-year
compliance with a 90-day hot window.

## What the skill caught that a generic assistant misses

1. **The Never Expire cost exposure.** A generic assistant sets
   retention without quantifying the waste. The skill calculates the
   $450/month cost exposure and flags it for before/after tracking.

2. **The untagged-group fallback.** A generic assistant assumes all
   groups are tagged. The skill identifies 40 untagged groups and
   applies the account-level default (14d) instead of skipping them.

3. **The default-first EventBridge strategy.** A generic assistant
   writes a Lambda that checks tags immediately on CreateLogGroup —
   which fails because tags aren't set yet. The skill applies the
   account default first and upgrades later via a TagResource rule.

4. **The daily sweep safety net.** A generic assistant deploys only
   the EventBridge rule. The skill adds a daily Lambda sweep to catch
   groups created through uncommon paths (direct API, IAM user).

5. **The Firehose buffer vs retention gap.** A generic assistant sets
   CloudWatch retention to exactly match the hot window. The skill
   notes that Firehose buffers for 5 minutes — logs in the last
   buffer window before expiry may not reach S3. The 90-day CloudWatch
   window provides buffer beyond the actual 89.5-day data guarantee.

6. **The compliance tier rounding.** A generic assistant may set
   2555 (7 years in days) which is NOT in the allowed tier set. The
   skill rounds to 2557 (the nearest allowed value).

7. **The S3 lifecycle policy.** A generic assistant sends logs to S3
   without lifecycle rules. The skill adds Standard-IA (30d), Glacier
   (90d), Deep Archive (180d) — reducing 7-year compliance storage
   cost by 90%+.

## Slash-command invocation

```
/aws:automate-log-retention
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate CloudWatch Logs retention"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate log retention"
# [Phase: Automate | Skills routed: log-retention-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover all log groups and their retention state
aws logs describe-log-groups \
  --output table \
  --query 'logGroups[*].[logGroupName,retentionInDays,storedBytes]' \
  --region us-east-1 --profile default

# Count Never Expire groups
aws logs describe-log-groups \
  --output json \
  --query 'length(logGroups[?retentionInDays==`null`])' \
  --region us-east-1 --profile default

# Check tags on a sample group
aws logs list-tags-log-group \
  --log-group-name /aws/lambda/prod-api \
  --region us-east-1 --profile default

# Check existing subscription filters
aws logs describe-subscription-filters \
  --log-group-name /aws/lambda/audit-logger \
  --region us-east-1 --profile default

# Check Firehose delivery stream status
aws firehose describe-delivery-stream \
  --delivery-stream-name log-archive-compliance \
  --query 'DeliveryStreamDescription.DeliveryStreamStatus' \
  --region us-east-1 --profile default

# Verify EventBridge rule is active
aws events describe-rule \
  --name auto-retention-new-log-groups \
  --region us-east-1 --profile default
```

Then paste the output into the skill for workflow design.
