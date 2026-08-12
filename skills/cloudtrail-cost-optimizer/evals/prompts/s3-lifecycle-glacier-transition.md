# Eval prompt: s3-lifecycle-glacier-transition

Optimise the following CloudTrail configuration for cost. Walk the
S3-lifecycle decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

TrailName: trail-s3-lifecycle-glacier-transition
IsOrganizationTrail: false (standalone account)
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

S3 log bucket: cloudtrail-logs-standalone-us-east-1
S3 lifecycle policy: NONE

S3 storage breakdown:
  - Total size: 850 GB
  - Older than 30 days: 620 GB
  - Older than 90 days: 410 GB
  - Older than 180 days: 180 GB
  - Storage class breakdown: 100% Standard

Metrics (last 90 days):
  - Average monthly growth: 95 GB
  - S3 GET requests on CloudTrail prefix: 42 (very low read volume)
  - No Object Lock configured

Region: us-east-1
