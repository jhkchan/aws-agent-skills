# Eval prompt: idle-server-consolidation

Optimise the following AWS Transfer Family deployment for cost. Walk the
server-consolidation decision framework (concurrency vs server count)
and emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: transfer-idle-server-consolidation
Region: us-east-1
Servers (3 total):
  - ServerId: s-partner-exchange-a
    EndpointType: PUBLIC
    Protocols: [SFTP]
    Concurrency: 10, observed avg 2, p99 4
    Users: 12 active
  - ServerId: s-partner-exchange-b
    EndpointType: PUBLIC
    Protocols: [SFTP]
    Concurrency: 10, observed avg 2, p99 3
    Users: 8 active
  - ServerId: s-internal-reports
    EndpointType: PUBLIC
    Protocols: [SFTP]
    Concurrency: 10, observed avg 0.5, p99 2
    Users: 5 active

Combined ConcurrentSessions: avg 4.5, peak 9, p99 6

Metrics (last 30 days):
  - FilesIn (all servers): 800,000/month
  - FilesOut (all servers): 200,000/month
  - BytesIn: 600 GB/month
  - BytesOut: 100 GB/month
  - UserSessionsStarted: 3,000/month total

No managed workflows configured.
CloudWatch Logs volume: 80 GB/month across all servers
Cost Explorer (Service=Transfer, last 30 days): $727.00

Workload context: three PUBLIC SFTP servers for different partner
groups. All use SERVICE_MANAGED identity. No workflow. Combined
peak (9 sessions) fits within a single server's concurrency limit
of 10. Servers are in the same region and could be consolidated.
