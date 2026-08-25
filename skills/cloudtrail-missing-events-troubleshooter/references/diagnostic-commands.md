# Diagnostic Commands — cloudtrail-missing-events-troubleshooter

## Pre-flight gather-info command block (trail state)

```bash
# Trail configuration (S3BucketName, S3KeyPrefix, IsMultiRegionTrail,
# IsOrganizationTrail, KmsKeyId, CloudWatchLogsLogGroupArn)
aws cloudtrail describe-trails --trail-name-list <trail> --output json

# Trail delivery status (IsLogging, LatestDeliveryTime,
# LatestCloudWatchLogsDeliveryTime, LatestDigestDeliveryTime)
aws cloudtrail get-trail-status --name <trail> --output json

# Event selectors (ManagementEvents, DataEvents, ReadWriteType,
# ExcludeManagementEventSources, AdvancedEventSelectors)
aws cloudtrail get-event-selectors --trail-name <trail> --output json

# S3 bucket policy and KMS key state (if KmsKeyId is set)
aws s3api get-bucket-policy --bucket <bucket> --output json
aws kms describe-key --key-id <kms-key-id> --output json

# Recent lookup-events to confirm the specific missing API
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=<service>.amazonaws.com \
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s) --output json
```

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`start-logging`, `stop-logging`, `update-trail`,
  `put-event-selectors`, `put-insight-selectors`, `enable-kms-key`),
  emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as probes.
- **`start-logging`** is safe; trail resumes delivery within ~5 min.
- **`stop-logging`** is disruptive; trail stops capturing immediately.
- **`update-trail`** may break downstream consumers (Athena,
  GuardDuty, SIEM). Confirm downstream impact.
- **`put-event-selectors`** enabling data events incurs cost
  ($0.10 per 100,000 events). Confirm cost impact.
- **Bucket policy edits** affect every consumer of the bucket.
  Tighten policy gradually; never deny-by-default without confirming
  no other service depends on the bucket.

## Remediation guidance

### For TRAIL_DISABLED
Identify who called StopLogging via `lookup-events`; restart via
`aws cloudtrail start-logging --name <trail>`; if IaC-created, ensure
the template includes `enable_logging = true` (Terraform) to prevent
recurrence.

### For BUCKET_POLICY_BLOCKING
Add the canonical CloudTrail bucket policy statement
(`cloudtrail.amazonaws.com` principal with `s3:GetBucketAcl`,
`s3:ListBucket`, `s3:PutObject` and the `bucket-owner-full-control`
condition). For org trails, ensure the Resource ARN covers the org
ID (`o-<org-id>/*`). Verify with `aws s3 ls` within ~15 min.

### For KMS_KEY_DISABLED
Re-enable the key: `aws kms enable-key --key-id <id>`. If the key is
`PendingDeletion` (within the deletion window), migrate the trail to
a new key via `update-trail --kms-key-id <new-arn>`.

### For DATA_EVENTS_NOT_ENABLED
Add the data-event selector for the expected data source (S3, Lambda,
DynamoDB). Confirm the cost impact with the operator before enabling.
Verify with `lookup-events` 10-15 minutes after the change.

### For ORG_TRAIL_SHADOWS_MEMBER
Accept that events are in the org trail bucket (recommended for
centralized audit). If member-local delivery is required, keep both
trails — the org trail delivers to the org bucket and the member
trail delivers to the member bucket.

### For MULTI_REGION_SCOPE_GAP
Convert via `aws cloudtrail update-trail --name <trail>
--is-multi-region-trail`. Verify with `lookup-events --region
<other-region>`.

### For EVENT_SELECTOR_READONLY
Convert `ReadWriteType` to `All` via `put-event-selectors
--event-selectors '[{"ReadWriteType": "All",
"IncludeManagementEvents": true}]'`.

### For CW_LOGS_DELIVERY_DELAYED
Verify `CloudWatchLogsRoleArn` on the trail; verify the role trusts
`cloudtrail.amazonaws.com` and has `logs:CreateLogStream`,
`logs:PutLogEvents`; verify the log group exists.

### For LAKE_EDS_QUERY_ISSUE
Verify the EDS event selectors match the events being queried;
verify billing mode has query budget; verify EDS region matches.

### For SERVICE_NOT_IN_REGION
Cross-reference the AWS CloudTrail docs for the service-region
combination. If the service logs in us-east-1 only, query
`lookup-events --region us-east-1`.

### For LOG_FILE_PREFIX_ERROR
Read `S3KeyPrefix` from `describe-trails`; list the correct prefix:
`aws s3 ls s3://<bucket>/<S3KeyPrefix>/AWSLogs/<account>/CloudTrail/`.
