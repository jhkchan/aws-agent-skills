# Eval prompt: workflow-and-log-cost-reduction

Optimise the following AWS Transfer Family server for cost. Walk the
managed-workflow cost (Step Functions per-file scaling) and CloudWatch
Logs volume decision frameworks and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

ServerId: s-workflow-and-log-cost-reduction
EndpointType: PUBLIC
Protocols: [SFTP]
Region: us-east-1
IdentityProviderType: SERVICE_MANAGED
Concurrency: 20 (configured), observed avg 5, p99 12
Users: 30 active

Managed workflow: 1 (post-upload, 7-step Step Functions)
  Steps: validation, virus-scan, transformation, enrichment,
    notification, archival, audit-logging
  executions: 5,000,000 files/month (small files, avg 50 KB)

Metrics (last 30 days):
  - ConcurrentSessions: avg 5, p95 12, p99 12
  - FilesIn: 5,000,000/month
  - FilesOut: 100,000/month
  - BytesIn: 250 GB/month (5M small files)
  - UserSessionsStarted: 12,000/month

CloudWatch Logs volume: 500 GB/month (one log event per file
transfer at INFO level)
Cost Explorer (Service=Transfer, last 30 days): $1,768.50

Workload context: data ingestion pipeline. Partners upload small
JSON files (avg 50 KB). The 7-step workflow processes each file.
The archival and audit-logging steps could be combined into one.
The virus-scan and validation steps could run in parallel. Logs
are currently at INFO level — reducing to WARNING would cut
volume by ~80%. Audit compliance requires only authentication and
error logging.
