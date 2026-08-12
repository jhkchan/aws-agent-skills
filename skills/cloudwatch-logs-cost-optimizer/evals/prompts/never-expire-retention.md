# Eval prompt: never-expire-retention

Optimise the following CloudWatch Logs log group for cost. Walk the
retention decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

LogGroupName: /aws/lambda/never-expire-retention
RetentionInDays: 0 (Never expire)
Region: us-east-1
StoredBytes: 10,080 GB (12 months accumulated)

Metrics (last 30 days):
  - IncomingBytes avg: 28 GB/day (840 GB/month)
  - IncomingLogEvents avg: 12,000,000/day

Cost Explorer (last month, AmazonCloudWatch):
  - Logs ingestion: $420.00
  - Logs storage: $302.40
  - Total: $722.40/month (excluding Insights)

Workload context: Lambda application logs for an order processing
service. Operational debugging window is 7-14 days. No compliance
mandate requiring long retention. Team uses Logs Insights for ad-hoc
investigation (less than 10 queries/month).
