# Diagnostic commands — CloudTrail Cost Optimizer

Pre-flight data-gate commands, per-dimension apply CLI, and pre-remediation
safety checks moved out of SKILL.md for progressive disclosure. Load on demand.

## Pre-flight: required data sources (moved from SKILL.md)

**Required data sources** (summarized — see reference for full CLI):
1. Trail configurations: `aws cloudtrail describe-trails`
2. Event selectors (data/management): `aws cloudtrail get-event-selectors`
3. Insights selectors: `aws cloudtrail get-insights-selectors`
4. Org structure: `aws organizations describe-organization`, `list-accounts`
5. S3 lifecycle policy on log bucket: `aws s3api get-bucket-lifecycle-configuration`
6. S3 bucket size (CloudTrail prefix): `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name BucketSizeBytes`
7. CloudTrail Lake EDS config: `aws cloudtrail list-event-data-stores`
8. KMS key configuration: `aws kms describe-key`
9. Cost Explorer CloudTrail spend: `aws ce get-cost-and-usage` filtered by `Service=AWS CloudTrail`

## Step 1 — org trail creation and member trail deletion CLI (moved from SKILL.md)

**Org trail creation (one-time):**
```bash
aws cloudtrail create-trail \
  --name aws-organizational-trail \
  --s3-bucket-name org-cloudtrail-logs-us-east-1 \
  --is-organization-trail \
  --is-multi-region-trail \
  --kms-key-id alias/cloudtrail-org-cmk \
  --enable-log-file-validation
```

**Deletion of redundant member trails (after verifying consumers):**
```bash
aws cloudtrail delete-trail --name member-trail-us-east-1
```

## Step 3 — S3 lifecycle apply CLI (moved from SKILL.md)

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket org-cloudtrail-logs-us-east-1 \
  --lifecycle-configuration file://cloudtrail-lifecycle.json
```

## Step 4 — EDS event-category filter CLI (moved from SKILL.md)

**EDS configuration with event-category filter:**
```bash
aws cloudtrail update-event-data-store \
  --event-data-store <eds-id> \
  --advanced-event-selectors '[{"Name":"ManagementOnly","FieldSelectors":[
    {"Field":"eventCategory","Equals":["Management"]}]}]'
```

## Step 5 — disable CloudWatch Logs delivery CLI (moved from SKILL.md)

**Disabling CloudWatch Logs delivery:**
```bash
aws cloudtrail update-trail \
  --name aws-organizational-trail \
  --no-cloud-watch-logs-log-group-arn
```

## Step 6 — disable Insights CLI (moved from SKILL.md)

**Disabling Insights on low-risk trails:**
```bash
aws cloudtrail stop-insights-logging --name aws-organizational-trail
```

## Pre-flight safety checks (run before any remediation CLI, moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Verify org trail coverage before deleting member trails.** Org trail
  must be RUNNING and capturing all member-account events before any
  member trail deletion.
- **Snapshot existing event selectors before curating.** Restore is a
  re-apply of the prior selector JSON.
- **Test lifecycle policy on a single prefix first** (e.g.,
  `AWSLogs/<one-account>/`) before org-wide rollout.
- **Confirm S3 Object Lock (COMPLIANCE mode) is enforced before
  disabling log file integrity validation.** Object Lock provides
  equivalent tamper-evidence; governance mode is bypassable by root.
- **CloudTrail Lake EDS changes are immediate.** Export historical data
  first if re-query may be needed.
- **KMS key changes require updating the trail's KMS key policy.**
  Sharing a CMK requires the policy to allow all trail-writing accounts.
- **Insights disabling is irreversible for historical data.** Anomalies
  in the disabled window will not be retroactively detected.
- **Bulk-operation limit:** Process at most 5 trails per batch. Sort by
  estimated savings, verify each batch before proceeding. Abort if any
  trail shows event ingestion drop post-change.
