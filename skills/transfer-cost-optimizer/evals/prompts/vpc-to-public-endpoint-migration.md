# Eval prompt: vpc-to-public-endpoint-migration

Optimise the following AWS Transfer Family server for cost. Walk the
endpoint-type decision framework (PUBLIC vs VPC) and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ServerId: s-vpc-to-public-endpoint-migration
EndpointType: VPC
Protocols: [SFTP]
Region: us-east-1
IdentityProviderType: SERVICE_MANAGED
LoggingRole: arn:aws:iam::<acct>:role/TransferLogging
Concurrency: 10 (configured), observed avg 0.5, p95 2, p99 3
Users: 25 configured, 8 active in last 30 days

Managed workflow: 1 (post-upload, 5-step Step Functions)
  executions: 2,000,000 files/month

Metrics (last 30 days):
  - ConcurrentSessions: avg 0.5, p95 2, p99 3
  - FilesIn: 2,000,000/month
  - FilesOut: 500,000/month
  - BytesIn: 1,500 GB/month (outbound via NAT Gateway)
  - BytesOut: 200 GB/month
  - UserSessionsStarted: 6,000/month

CloudWatch Logs volume: 300 GB/month from Transfer logging
Cost Explorer (Service=Transfer, last 30 days): $819.50

Workload context: partner file exchange. All partners connect
from the public internet — no internal/VPC-only access required.
Concurrency peak of 3 is well under the configured 10. Workflow
has 5 steps (validation, transformation, notification, archival,
audit) — the archival and audit steps could be combined.
