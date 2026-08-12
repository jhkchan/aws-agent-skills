# Eval prompt: already-optimized-org-setup

Optimise the following CloudTrail configuration for cost. Walk all seven
optimization dimensions (consolidation, data_events, lifecycle, lake,
logs, kms_sns_insights, athena) and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

TrailName: trail-already-optimized-org-setup
IsOrganizationTrail: true
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

Event selectors:
  - ManagementEvents: true
  - S3 data events: 3 high-value buckets only (financial-records/,
    pii-data/, transaction-logs/) — 24,700,000 events/month
  - Lambda data events: disabled

S3 log bucket: org-cloudtrail-logs-us-east-1
S3 lifecycle policy:
  - 30 days → INTELLIGENT_TIERING
  - 90 days → GLACIER_IR
  - 180 days → DEEP_ARCHIVE
  - 365 days → EXPIRE

KMS: 1 shared CMK (alias/cloudtrail-org-cmk)
SNS: 1 topic (org-cloudtrail-notifications)
Insights: enabled on org-management account only
CloudWatch Logs: not configured (S3-only)
CloudTrail Lake: not configured
Athena: partition projection enabled on cloudtrail_logs table

Metrics (last 90 days):
  - Monthly cost: $487.30 (stable)
  - All dimensions within expected ranges

Region: us-east-1
