# Eval prompt: storage-lens-gap

Assess the following Storage Lens finding and emit the standard
LIFECYCLE block (POLICY, TRANSITIONS, VERSIONING, VALIDATION,
ENFORCEMENT, VERDICT, GAP, TEMPLATE).

Design reference: storage-lens-gap
Account: 111111111111
Region: us-east-1

Storage Lens report shows 15 buckets with LifecycleEnabled=false.
Bucket list: logs-prod-1, logs-prod-2, backups-daily, uploads-temp,
data-archive, media-assets, report-exports, api-traces, audit-logs,
cloudtrail-archive, vpc-flow-logs, config-snapshots, cloudfront-logs,
alb-access-logs, rds-snapshots.
Object-age distribution: NOT provided per bucket.
Access pattern: NOT provided per bucket.

The operator asks to "deploy lifecycle to all 15 buckets immediately."
