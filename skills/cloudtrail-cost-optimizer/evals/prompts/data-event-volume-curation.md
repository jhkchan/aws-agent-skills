# Eval prompt: data-event-volume-curation

Optimise the following CloudTrail configuration for cost. Walk the
data-event-curation decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

TrailName: aws-organizational-trail-data-event-volume-curation
IsOrganizationTrail: true
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

Event selectors:
  - ManagementEvents: true
  - S3 data events: All Buckets (ReadWriteType: All)
  - Lambda data events: disabled

S3 data event volume by bucket (last 30 days):
  - financial-records/:        12,000,000 events/month (HIGH audit value)
  - pii-data/:                 4,500,000 events/month  (HIGH audit value)
  - transaction-logs/:         8,200,000 events/month  (HIGH audit value)
  - cdn-access-logs/:         47,000,000 events/month  (LOW audit value)
  - elb-access-logs/:         38,000,000 events/month  (LOW audit value)
  - cloudtrail-logs/:         22,000,000 events/month  (LOW audit value)
  - backup-prod/:             10,000,000 events/month  (LOW audit value)
  - audit-archive/:             800,000 events/month   (LOW audit value)

Total data events/month: 142,500,000
High-value data events/month: 24,700,000 (17%)
Low-value data events/month: 117,800,000 (83%)

Region: us-east-1
