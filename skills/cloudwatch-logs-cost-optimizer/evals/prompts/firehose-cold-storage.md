# Eval prompt: firehose-cold-storage

Optimise the following CloudWatch Logs log group for cost. Walk the
Firehose S3 cold-storage migration decision framework and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

LogGroupName: /audit/firehose-cold-storage
RetentionInDays: 730 (2 years, compliance-mandated SOC2)
Region: us-east-1
StoredBytes: 12,000 GB

Metrics (last 30 days):
  - IncomingBytes avg: 16.7 GB/day (500 GB/month)
  - IncomingLogEvents avg: 3,000,000/day

Cost Explorer (last month):
  - Logs ingestion: $250.00 (500 GB × $0.50)
  - Logs storage: $360.00 (12,000 GB × $0.03)
  - Total: $610.00/month

Workload context: SOC2 audit logs. Compliance mandates 2-year
retention. Logs are queried rarely (1-2 times/quarter) via Athena on
an export bucket for compliance audits. The team has already confirmed
S3 + Athena meets their query needs.
