# Eval prompt: already-optimized-transfer

Optimise the following AWS Transfer Family server for cost. Walk all
optimization dimensions (endpoint, idle, protocol, concurrency,
session, workflow, logs, IdP) and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

ServerId: s-already-optimized-transfer
EndpointType: PUBLIC
Protocols: [SFTP]
Region: us-east-1
IdentityProviderType: SERVICE_MANAGED
Concurrency: 10 (configured), observed avg 3, p99 7
Users: 15 active

Managed workflow: NONE
CloudWatch Logs volume: 20 GB/month (WARNING level only, 7-day
  retention, archived to S3 for long-term)

Metrics (last 30 days):
  - ConcurrentSessions: avg 3, p95 7, p99 7
  - FilesIn: 150,000/month
  - FilesOut: 30,000/month
  - BytesIn: 80 GB/month
  - BytesOut: 20 GB/month
  - UserSessionsStarted: 800/month

Cost Explorer (Service=Transfer, last 30 days): $237.00
  ($219 server + $4 data transfer + $4 logs + $10 S3 storage)

Workload context: well-tuned PUBLIC SFTP server for a small
partner group. Concurrency is right-sized (p99 = 7 vs limit 10).
No managed workflow. Logs are at WARNING level with 7-day
retention and S3 archive. Service-managed identity (no Lambda
IdP cost). No NAT Gateway (PUBLIC endpoint).
